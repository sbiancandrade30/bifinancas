"""
ai_interpreter.py — Integração com Gemini (gratuito) e fallbacks
Arquitetura: Gemini → Groq → erro amigável
Trocar de IA = mudar só este arquivo. Os dados no Sheets não são afetados.
"""
import json
import re
import logging
import base64
from datetime import datetime
from config import GEMINI_API_KEY, CARTOES, CATEGORIAS, SUBCATEGORIAS

logger = logging.getLogger(__name__)

# ─── CLIENTE GEMINI ───────────────────────────────────────────────────────────
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    _model_text  = genai.GenerativeModel("gemini-2.0-flash")
    _model_vision = genai.GenerativeModel("gemini-2.0-flash")
    GEMINI_OK = True
except Exception as e:
    logger.warning(f"Gemini não disponível: {e}")
    GEMINI_OK = False


def _limpar_json(texto: str) -> str:
    return re.sub(r"```json|```", "", texto).strip()


def _prompt_interpretacao(texto: str) -> str:
    hoje = datetime.now().strftime("%d/%m/%Y")
    cartoes_info = {k: v["nome"] for k, v in CARTOES.items()}
    return f"""Você é assistente financeiro pessoal da Bianca. Hoje: {hoje}.

CARTÕES (use a chave exata):
{json.dumps(cartoes_info, ensure_ascii=False)}

FORMAS DE PAGAMENTO válidas para "forma_pagto":
- Chave do cartão: santander, nubank, mercadopago, caedu, bb
- debito, pix, dinheiro, ted
- "perguntar" → se não ficou claro

CATEGORIAS: {', '.join(CATEGORIAS)}
SUBCATEGORIAS: {json.dumps(SUBCATEGORIAS, ensure_ascii=False)}

DETECÇÃO de forma de pagamento:
- "no Nubank" / "roxinho" → nubank
- "no Santander" → santander
- "no pix" / "via pix" → pix
- "em dinheiro" / "espécie" → dinheiro
- "no débito" → debito
- valor alto (>200) sem menção → perguntar
- valor pequeno (<50) sem menção → provavelmente pix ou dinheiro

Mensagem do usuário: "{texto}"

Responda APENAS com JSON válido (sem markdown, sem explicações):
{{
  "tipo": "gasto" | "entrada" | "wishlist" | "simulador" | "invalido",
  "categoria": "<categoria>",
  "subcategoria": "<subcategoria ou vazio>",
  "descricao": "<descrição curta e clara>",
  "valor": <número decimal>,
  "data": "<DD/MM/YYYY — use hoje se não informado>",
  "forma_pagto": "<forma ou 'perguntar'>",
  "parcelas": <inteiro, 1 se à vista>,
  "eh_reserva": <true/false>,
  "eh_pais": <true/false>,
  "wishlist_item": "<nome do item se wishlist>",
  "wishlist_prioridade": "alta" | "media" | "baixa",
  "simulador_descricao": "<o que quer comprar se simulador>",
  "simulador_valor_total": <valor total se simulador>,
  "simulador_parcelas": <parcelas se simulador>,
  "confianca": "alta" | "media" | "baixa",
  "confirmacao": "<frase curta amigável com emoji>"
}}
Se não for financeiro: {{"tipo":"invalido","mensagem":"<orientação breve>"}}"""


def interpretar_texto(texto: str) -> dict | None:
    """Interpreta mensagem de texto com Gemini."""
    if not GEMINI_OK:
        return None
    try:
        resp = _model_text.generate_content(_prompt_interpretacao(texto))
        return json.loads(_limpar_json(resp.text))
    except Exception as e:
        logger.error(f"Gemini texto erro: {e}")
        return None


def interpretar_imagem(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict | None:
    """
    Interpreta foto de nota fiscal ou comprovante.
    Retorna dict com os dados extraídos.
    """
    if not GEMINI_OK:
        return None
    hoje = datetime.now().strftime("%d/%m/%Y")
    prompt = f"""Analise esta imagem financeira. Hoje: {hoje}.
Pode ser: nota fiscal, comprovante de pagamento, extrato, fatura.

Extraia as informações e responda APENAS com JSON válido:
{{
  "tipo_imagem": "nota_fiscal" | "comprovante_pix" | "extrato" | "fatura" | "outro",
  "tipo": "gasto" | "entrada",
  "categoria": "<categoria>",
  "subcategoria": "<subcategoria>",
  "descricao": "<estabelecimento ou descrição>",
  "valor": <valor principal em float>,
  "data": "<DD/MM/YYYY se visível, senão hoje>",
  "forma_pagto": "<forma se visível, senão 'perguntar'>",
  "itens": ["<item1>", "<item2>"],
  "confirmacao": "<frase amigável confirmando o que foi lido>"
}}"""
    try:
        image_part = {"mime_type": mime_type, "data": image_bytes}
        resp = _model_vision.generate_content([prompt, image_part])
        return json.loads(_limpar_json(resp.text))
    except Exception as e:
        logger.error(f"Gemini imagem erro: {e}")
        return None


def interpretar_audio_transcrito(transcricao: str) -> dict | None:
    """Interpreta texto transcrito de áudio."""
    return interpretar_texto(f"[mensagem de voz]: {transcricao}")


def transcrever_audio(audio_bytes: bytes) -> str | None:
    """Transcreve áudio usando Gemini (multimodal)."""
    if not GEMINI_OK:
        return None
    prompt = "Transcreva exatamente o que está sendo dito neste áudio em português."
    try:
        audio_part = {"mime_type": "audio/ogg", "data": audio_bytes}
        resp = _model_vision.generate_content([prompt, audio_part])
        return resp.text.strip()
    except Exception as e:
        logger.error(f"Gemini áudio erro: {e}")
        return None


def gerar_resumo_mes(lancamentos: list, mes_ano: str,
                     meta_guardar: float, limite_gastos: float) -> str:
    """Gera análise do mês com IA."""
    if not GEMINI_OK:
        return _resumo_simples(lancamentos, mes_ano, meta_guardar)

    gastos   = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "gasto")
    entradas = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "entrada")
    saldo    = entradas - gastos

    prompt = f"""Você é agente financeiro pessoal da Bianca. Analise o mês {mes_ano}.

Resumo: Entradas R${entradas:.2f} | Gastos R${gastos:.2f} | Saldo R${saldo:.2f}
Meta poupança: R${meta_guardar:.2f} | Limite gastos: R${limite_gastos:.2f}
Lançamentos: {json.dumps(lancamentos[:60], ensure_ascii=False)}

Gere resumo com:
1. 📊 Visão geral (entradas, gastos, saldo, vs meta)
2. 🏷 Top 5 categorias com valores
3. 🎯 Comparação com o plano financeiro
4. ⚠️ Alertas (algo fora do padrão?)
5. 💡 1 conselho prático personalizado

Tom: informal, direto, use emojis. Máx 28 linhas."""
    try:
        resp = _model_text.generate_content(prompt)
        return resp.text
    except Exception as e:
        logger.error(f"Gemini resumo erro: {e}")
        return _resumo_simples(lancamentos, mes_ano, meta_guardar)


def gerar_relatorio_completo(todos: list) -> str:
    """Gera relatório geral com IA."""
    if not GEMINI_OK:
        return "❌ IA indisponível. Acesse sua planilha Google Sheets para o relatório completo."

    gastos   = sum(float(r["Valor"]) for r in todos if r["Tipo"] == "gasto")
    entradas = sum(float(r["Valor"]) for r in todos if r["Tipo"] == "entrada")
    prompt = f"""Agente financeiro da Bianca. Relatório completo.
Registros: {len(todos)} | Gastos: R${gastos:.2f} | Entradas: R${entradas:.2f}
Dados: {json.dumps(todos[:80], ensure_ascii=False)}

Relatório com: 1) Visão geral 2) Por mês 3) Por categoria
4) Progresso metas 5) Análise de hábitos 6) 3 recomendações personalizadas.
Analítico, use números, máx 38 linhas."""
    try:
        resp = _model_text.generate_content(prompt)
        return resp.text
    except Exception as e:
        logger.error(f"Gemini relatório erro: {e}")
        return "❌ Erro ao gerar relatório. Tente novamente."


def simular_compra(descricao: str, valor_total: float, parcelas: int,
                   lancamentos_mes: list, plano_mes: dict) -> str:
    """Simula impacto de uma compra parcelada no orçamento."""
    if not GEMINI_OK:
        valor_parcela = valor_total / parcelas
        return (f"💳 *Simulação: {descricao}*\n"
                f"Valor total: R$ {valor_total:.2f}\n"
                f"Parcela: R$ {valor_parcela:.2f}/mês por {parcelas} meses\n"
                f"⚠️ Analise se cabe no seu orçamento antes de decidir.")

    gastos_atuais = sum(float(r["Valor"]) for r in lancamentos_mes if r["Tipo"] == "gasto")
    limite = plano_mes.get("limite_gastos", 2000)
    guardar = plano_mes.get("guardar", 0)

    prompt = f"""Bianca está pensando em comprar: {descricao}
Valor total: R${valor_total:.2f} | Parcelas: {parcelas}x de R${valor_total/parcelas:.2f}

Situação atual do mês:
- Gastos até agora: R${gastos_atuais:.2f}
- Limite mensal: R${limite:.2f}
- Meta de poupança: R${guardar:.2f}
- Renda mensal: R$4.820,00

Analise:
1. Cabe no orçamento atual?
2. Impacto nos próximos {parcelas} meses
3. Melhor momento para comprar (agora ou quando?)
4. Recomendação final clara (sim/não/esperar)

Seja direta, use números reais, máx 15 linhas."""
    try:
        resp = _model_text.generate_content(prompt)
        return resp.text
    except Exception as e:
        logger.error(f"Gemini simulação erro: {e}")
        return f"Parcela seria R$ {valor_total/parcelas:.2f}/mês por {parcelas} meses."


def calcular_score(lancamentos: list, mes_ano: str,
                   meta_guardar: float, limite_gastos: float) -> dict:
    """Calcula score financeiro 0-10 do mês."""
    gastos   = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "gasto")
    entradas = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "entrada")
    saldo    = entradas - gastos

    guardou       = saldo >= meta_guardar
    ficou_limite  = gastos <= limite_gastos
    tem_lancamentos = len(lancamentos) >= 5

    nota = 5.0
    if guardou:       nota += 2.0
    if ficou_limite:  nota += 2.0
    if tem_lancamentos: nota += 1.0
    nota = min(nota, 10.0)

    return {
        "nota": round(nota, 1),
        "guardou_meta": guardou,
        "ficou_limite": ficou_limite,
        "gastos": gastos,
        "entradas": entradas,
        "saldo": saldo,
    }


def responder_duvida(pergunta: str, contexto_mes: dict = None) -> str:
    """
    Responde dúvidas sobre o sistema, finanças pessoais ou cadastro.
    Funciona como uma assistente financeira pessoal da Bianca.
    """
    if not GEMINI_OK:
        return "❌ IA indisponível no momento. Tente novamente em breve."

    ctx = ""
    if contexto_mes:
        ctx = f"""
Contexto financeiro atual da Bianca:
- Saldo do mês: R$ {contexto_mes.get('saldo', 0):.2f}
- Gastos: R$ {contexto_mes.get('gastos', 0):.2f}
- Entradas: R$ {contexto_mes.get('entradas', 0):.2f}
- Lançamentos registrados: {contexto_mes.get('n', 0)}
"""

    prompt = f"""Você é a BiFinanças, assistente financeira pessoal e inteligente da Bianca.
Você conhece todo o sistema dela:

SOBRE O SISTEMA:
- Bot no Telegram que registra gastos por texto, áudio e foto
- Dados salvos no Google Sheets
- Dashboard web para visualizar tudo
- 5 cartões: Santander, Nubank, Mercado Pago, Caedu, Banco do Brasil
- Comandos: /saldo /cartoes /parcelas /metas /reserva /pais /wishlist /score /plano /alertas /resumo /relatorio

COMO REGISTRAR:
- Texto: "gastei 45 no mercado no nubank"
- Áudio: manda um áudio falando o gasto
- Foto: manda foto de nota fiscal ou comprovante
- Wishlist: "quero comprar airfryer 350"
- Simulador: "vale a pena comprar TV 2000 em 12x?"

SITUAÇÃO FINANCEIRA DA BIANCA:
- Renda: R$ 4.820/mês
- Reserva de emergência: meta R$ 10.000
- Dívida com os pais: R$ 19.400 (pagou R$ 1.000)
- 5 cartões com faturas mensais
- Plano financeiro até jan/2027
{ctx}

Pergunta da Bianca: "{pergunta}"

Responda de forma:
- Direta e clara, sem enrolação
- Tom informal e amigável, como uma amiga especialista
- Use emojis com moderação
- Se for dúvida sobre como usar o sistema, explique passo a passo
- Se for dúvida financeira, dê conselhos baseados na situação real dela
- Se não souber, diga honestamente
- Máximo 20 linhas"""

    try:
        resp = _model_text.generate_content(prompt)
        return resp.text
    except Exception as e:
        logger.error(f"Gemini dúvida erro: {e}")
        return "❌ Não consegui processar sua pergunta agora. Tente novamente."


def classificar_intencao(texto: str) -> str:
    """
    Classifica rapidamente se a mensagem é um lançamento ou uma dúvida/pergunta.
    Usa regras locais primeiro para economizar chamadas à IA.
    """
    t = texto.lower().strip()

    # Sinais claros de dúvida/pergunta
    palavras_pergunta = [
        "como", "o que", "quando", "por que", "porque", "pra que",
        "qual", "quais", "onde", "quanto tempo", "dá pra", "da pra",
        "posso", "consigo", "você pode", "me explica", "me fala",
        "funciona", "serve", "significa", "diferença", "ajuda",
        "não entendi", "nao entendi", "tô perdida", "to perdida",
        "esqueci", "me lembra", "me diz", "o bot", "o sistema",
        "?", "rsrs", "haha", "oi", "olá", "ola", "bom dia",
        "boa tarde", "boa noite", "tudo bem", "e aí", "e ai"
    ]

    if any(p in t for p in palavras_pergunta):
        return "duvida"

    # Sinais claros de lançamento
    palavras_lancamento = [
        "gastei", "paguei", "comprei", "recebi", "ganhei", "entrou",
        "caiu", "almocei", "jantei", "abasteci", "guardei", "poupei",
        "quero comprar", "vale a pena"
    ]

    if any(p in t for p in palavras_lancamento):
        return "lancamento"

    # Tem valor monetário sem contexto claro → provavelmente lançamento
    import re
    if re.search(r'R\$\s*\d|(?<!\d)\d{2,4}(?:[.,]\d{2})?\s*(?:reais?|conto)', t):
        return "lancamento"

    # Incerto — vai para IA decidir
    return "incerto"
    """Fallback sem IA."""
    gastos   = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "gasto")
    entradas = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "entrada")
    saldo    = entradas - gastos
    ok = "✅" if saldo >= meta_guardar else "⚠️"
    return (f"📊 *Resumo {mes_ano}*\n\n"
            f"➕ Entradas: R$ {entradas:,.2f}\n"
            f"➖ Gastos: R$ {gastos:,.2f}\n"
            f"{ok} Saldo: R$ {saldo:,.2f}\n"
            f"🎯 Meta: R$ {meta_guardar:,.2f}\n"
            f"📌 {len(lancamentos)} lançamentos")
