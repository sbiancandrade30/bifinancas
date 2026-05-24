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
from config import GEMINI_API_KEY, CARTOES, CATEGORIAS, SUBCATEGORIAS, RENDA_MENSAL

logger = logging.getLogger(__name__)


def _fmt_brl_local(valor: float) -> str:
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"R$ {valor}"

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
- debito, pix, dinheiro, ted, nao_informado
- "perguntar" → se não ficou claro

CATEGORIAS: {', '.join(CATEGORIAS)}
SUBCATEGORIAS: {json.dumps(SUBCATEGORIAS, ensure_ascii=False)}

DETECÇÃO de forma de pagamento:
- "no Nubank" / "roxinho" → nubank
- "no Santander" → santander
- "no pix" / "via pix" → pix
- "em dinheiro" / "espécie" → dinheiro
- "no débito" → debito
- gasto sem forma clara → perguntar
- entrada sem forma clara → nao_informado

DÍVIDAS FAMILIARES:
- "pai", "meu pai", "papai" → eh_pai=true
- "mãe", "minha mãe", "mamãe" → eh_mae=true
- "pais" de forma genérica → eh_pai=true, porque a prioridade atual é quitar o pai primeiro

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
  "eh_pai": <true/false>,
  "eh_mae": <true/false>,
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
    """Gera análise do mês com IA, com prompt compacto para economizar cota."""
    gastos = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "gasto")
    entradas = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "entrada")
    saldo = entradas - gastos

    por_categoria = {}
    for r in lancamentos:
        if r.get("Tipo") == "gasto":
            cat = str(r.get("Categoria", "Outros"))
            por_categoria[cat] = por_categoria.get(cat, 0.0) + float(r.get("Valor", 0) or 0)
    top_categorias = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:5]

    if not GEMINI_OK:
        return _resumo_simples(lancamentos, mes_ano, meta_guardar)

    prompt = f"""Você é agente financeiro pessoal da Bianca. Analise o mês {mes_ano}.
Resumo: entradas R${entradas:.2f}; gastos R${gastos:.2f}; saldo R${saldo:.2f}.
Meta de poupança: R${meta_guardar:.2f}. Limite de gastos: R${limite_gastos:.2f}.
Top categorias: {json.dumps(top_categorias, ensure_ascii=False)}.
Quantidade de lançamentos: {len(lancamentos)}.

Entregue em no máximo 18 linhas:
1. visão geral
2. leitura dos gastos
3. comparação com a meta
4. alerta principal, se houver
5. um conselho prático bem específico.
Tom direto, natural e humano."""
    try:
        resp = _model_text.generate_content(prompt)
        return resp.text
    except Exception as e:
        logger.error(f"Gemini resumo erro: {e}")
        return _resumo_simples(lancamentos, mes_ano, meta_guardar)

def gerar_relatorio_completo(todos: list) -> str:
    """Gera relatório geral; se a IA limitar, entrega relatório útil sem falhar."""
    if not todos:
        return "Nenhum lançamento ainda. 📭"

    gastos = sum(float(r["Valor"]) for r in todos if r["Tipo"] == "gasto")
    entradas = sum(float(r["Valor"]) for r in todos if r["Tipo"] == "entrada")
    saldo = entradas - gastos

    por_mes = {}
    por_categoria = {}
    for r in todos:
        mes = str(r.get("Mês", "Sem mês"))
        tipo = str(r.get("Tipo", ""))
        valor = float(r.get("Valor", 0) or 0)
        item = por_mes.setdefault(mes, {"entradas": 0.0, "gastos": 0.0})
        if tipo == "entrada":
            item["entradas"] += valor
        elif tipo == "gasto":
            item["gastos"] += valor
            cat = str(r.get("Categoria", "Outros"))
            por_categoria[cat] = por_categoria.get(cat, 0.0) + valor

    meses_resumo = [
        [mes, round(v["entradas"], 2), round(v["gastos"], 2), round(v["entradas"] - v["gastos"], 2)]
        for mes, v in sorted(por_mes.items())
    ]
    top_categorias = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:8]

    fallback = _relatorio_simples(todos, gastos, entradas, saldo, meses_resumo, top_categorias)
    if not GEMINI_OK:
        return fallback

    prompt = f"""Agente financeiro da Bianca. Gere um relatório financeiro geral compacto.
Registros: {len(todos)}. Entradas: R${entradas:.2f}. Gastos: R${gastos:.2f}. Saldo: R${saldo:.2f}.
Meses [mês, entradas, gastos, saldo]: {json.dumps(meses_resumo[-8:], ensure_ascii=False)}
Top categorias: {json.dumps(top_categorias, ensure_ascii=False)}

Estrutura:
1. visão geral
2. evolução por mês
3. categorias que mais pesaram
4. hábitos percebidos
5. três recomendações práticas.
Máximo 28 linhas. Sem enrolação."""
    try:
        resp = _model_text.generate_content(prompt)
        return resp.text
    except Exception as e:
        logger.error(f"Gemini relatório erro: {e}")
        return fallback

def simular_compra(descricao: str, valor_total: float, parcelas: int,
                   lancamentos_mes: list, plano_mes: dict) -> str:
    """Simula impacto da compra sem depender da IA."""
    parcelas = max(int(parcelas or 1), 1)
    valor_total = float(valor_total or 0)
    valor_parcela = valor_total / parcelas if parcelas else valor_total
    gastos_atuais = sum(float(r["Valor"]) for r in lancamentos_mes if r["Tipo"] == "gasto")
    limite = float(plano_mes.get("limite_gastos", 2000) or 2000)
    guardar = float(plano_mes.get("guardar", 0) or 0)

    gasto_com_compra = gastos_atuais + valor_parcela
    restante_limite = limite - gastos_atuais
    restante_apos = limite - gasto_com_compra
    folga_teorica = RENDA_MENSAL - guardar - gasto_com_compra

    if gasto_com_compra > limite:
        veredito = "❌ *Eu esperaria.* A parcela estoura o limite de gastos do mês."
    elif restante_apos < limite * 0.10:
        veredito = "⚠️ *Dá, mas fica apertado.* Você termina o mês com pouca margem no limite."
    else:
        veredito = "✅ *Cabe no plano mensal atual*, desde que os próximos meses sigam parecidos."

    prazo_txt = "à vista" if parcelas == 1 else f"por {parcelas} meses"
    return (
        f"🔢 *Simulação: {descricao}*\n\n"
        f"💳 Valor total: *{_fmt_brl_local(valor_total)}*\n"
        f"📦 Parcela: *{_fmt_brl_local(valor_parcela)}/mês* {prazo_txt}\n\n"
        f"📊 Gastos atuais do mês: *{_fmt_brl_local(gastos_atuais)}*\n"
        f"📌 Limite planejado: *{_fmt_brl_local(limite)}*\n"
        f"🧮 Gastos com essa compra: *{_fmt_brl_local(gasto_com_compra)}*\n"
        f"💡 Margem no limite depois: *{_fmt_brl_local(restante_apos)}*\n"
        f"🎯 Meta de poupança do mês: *{_fmt_brl_local(guardar)}*\n\n"
        f"{veredito}"
    )

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
- Dívidas familiares: pai R$ 5.400 (R$ 1.000 já pago) e mãe R$ 15.000 (pagamento começa depois de quitar o pai)
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
        return "❌ Não consegui processar agora. A IA pode ter atingido o limite gratuito; tente de novo em alguns segundos."


def classificar_intencao(texto: str) -> str:
    """
    Classifica rapidamente se a mensagem é um lançamento ou uma dúvida/pergunta.
    Usa regras locais primeiro para economizar chamadas à IA.
    """
    t = texto.lower().strip()

    # Sinais claros de lançamento que podem vir em formato de pergunta.
    lancamentos_especiais = [
        "vale a pena", "devo comprar", "consigo comprar", "quero comprar",
        "wishlist", "lista de desejos", "guardei", "poupei", "paguei",
        "recebi", "gastei", "comprei",
    ]
    if any(p in t for p in lancamentos_especiais):
        return "lancamento"

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


def _relatorio_simples(todos, gastos, entradas, saldo, meses_resumo, top_categorias) -> str:
    linhas = [
        "📘 *Relatório geral — BiFinanças*",
        "",
        f"➕ Entradas acumuladas: *{_fmt_brl_local(entradas)}*",
        f"➖ Gastos acumulados: *{_fmt_brl_local(gastos)}*",
        f"💰 Saldo acumulado: *{_fmt_brl_local(saldo)}*",
        f"📌 Lançamentos analisados: *{len(todos)}*",
        "",
        "📅 *Por mês:*",
    ]
    for mes, ent, gas, sal in meses_resumo[-6:]:
        linhas.append(f"• {mes}: +{_fmt_brl_local(ent)} · -{_fmt_brl_local(gas)} · saldo {_fmt_brl_local(sal)}")
    linhas.append("")
    linhas.append("🏷 *Categorias com maior gasto:*")
    if top_categorias:
        for cat, val in top_categorias[:5]:
            linhas.append(f"• {cat}: {_fmt_brl_local(val)}")
    else:
        linhas.append("• Nenhum gasto categorizado ainda")
    linhas += [
        "",
        "💡 *Leitura rápida:*",
        "• Este relatório foi gerado localmente para não depender da cota da IA.",
        "• Quanto mais lançamentos você registrar, melhor ficam as análises.",
    ]
    return "\n".join(linhas)


def _resumo_simples(lancamentos, mes_ano, meta_guardar) -> str:
    """Fallback sem IA — estilo GranaZen."""
    gastos   = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "gasto")
    entradas = sum(float(r["Valor"]) for r in lancamentos if r["Tipo"] == "entrada")
    saldo    = entradas - gastos
    ok = "✅" if saldo >= meta_guardar else "⚠️"
    return (
        f"📊 *Resumo Financeiro — {mes_ano}*\n\n"
        f"🏦 *Seu Saldo*\n"
        f"{'—' * 20}\n"
        f"💰 *Disponível:* R$ {saldo:,.2f}\n\n"
        f"📈 *Receitas*\n"
        f"Recebido: R$ {entradas:,.2f}\n\n"
        f"📉 *Despesas*\n"
        f"Pago: R$ {gastos:,.2f}\n\n"
        f"{'—' * 20}\n"
        f"{ok} *Meta de poupança:* R$ {meta_guardar:,.2f}\n"
        f"📌 {len(lancamentos)} lançamentos registrados"
    )
