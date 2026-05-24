"""
parser_local.py — Interpreta mensagens comuns sem usar IA.
Modelo híbrido: tenta aqui primeiro, só chama IA quando realmente precisa.
"""
import re
from datetime import datetime
from config import (
    KEYWORDS_GASTO, KEYWORDS_ENTRADA, KEYWORDS_RESERVA,
    KEYWORDS_PAIS, KEYWORDS_WISHLIST, KEYWORDS_SIMULADOR,
    ALIASES_CARTAO,
)


_RE_MAE = re.compile(r"\b(m[aã]e|mam[aã]e|minha m[aã]e)\b", re.IGNORECASE)
_RE_PAI = re.compile(r"\b(pai|papai|meu pai)\b", re.IGNORECASE)
_RE_PAIS_GENERICO = re.compile(r"\b(pais|fam[ií]lia|familia)\b|d[ií]vida dos meus pais|devo pra", re.IGNORECASE)


def _normalizar(texto: str) -> str:
    return " ".join(str(texto or "").strip().split())


def detectar_tipo(texto: str) -> str | None:
    t = texto.lower()

    # Intenções especiais vêm antes de perguntas genéricas e gastos.
    if any(k in t for k in KEYWORDS_SIMULADOR):
        return "simulador"
    if any(k in t for k in KEYWORDS_WISHLIST):
        return "wishlist"

    # Reserva é tratada como entrada no modelo atual do bot para manter
    # compatibilidade com os cálculos já existentes de metas/alertas.
    if any(k in t for k in KEYWORDS_RESERVA) and any(k in t for k in ["guardei", "poupei", "coloquei", "depositei", "aportei", "joguei"]):
        return "entrada"

    if any(k in t for k in KEYWORDS_ENTRADA):
        return "entrada"
    if any(k in t for k in KEYWORDS_GASTO):
        return "gasto"
    return None


def extrair_valor(texto: str) -> float | None:
    """Extrai o valor monetário principal, evitando confundir parcelas com valor."""
    t = texto.replace(".", ".")
    padroes = [
        r"R\$\s*(\d{1,6}(?:[.,]\d{2})?)",
        r"\b(\d{1,6}[.,]\d{2})\b",
        r"\b(\d{1,6})\s*(?:reais?|conto|pila)\b",
    ]
    for p in padroes:
        m = re.search(p, t, re.IGNORECASE)
        if m:
            val = m.group(1).replace(".", "").replace(",", ".") if "," in m.group(1) else m.group(1)
            try:
                return float(val)
            except ValueError:
                continue

    # Número inteiro solto, ignorando o N de "12x".
    numeros = re.findall(r"(?<![\dx])(\d{2,6})(?!\s*[xX]|\d)", t)
    for n in numeros:
        try:
            return float(n)
        except ValueError:
            continue
    return None


def extrair_parcelas(texto: str) -> int:
    t = texto.lower()
    padroes = [
        r"em\s*(\d+)\s*[xX]",
        r"(\d+)\s*vezes",
        r"parcelado\s*em\s*(\d+)",
        r"(\d+)\s*parcelas?",
    ]
    for p in padroes:
        m = re.search(p, t)
        if m:
            try:
                return max(int(m.group(1)), 1)
            except ValueError:
                return 1
    return 1


def extrair_forma_pagto(texto: str) -> str | None:
    t = texto.lower()
    for chave, aliases in ALIASES_CARTAO.items():
        if any(alias in t for alias in aliases):
            return chave
    return None


def _destino_divida(texto: str) -> tuple[bool, bool, bool]:
    """Retorna (eh_divida_familiar, eh_pai, eh_mae).

    Quando a mensagem fala genericamente "pais", a prioridade atual da Bianca
    é pagar o pai primeiro, então o bot direciona para a meta do pai.
    """
    t = texto.lower()
    eh_mae = bool(_RE_MAE.search(t))
    eh_pai = bool(_RE_PAI.search(t)) and not eh_mae
    eh_generico = bool(_RE_PAIS_GENERICO.search(t))
    eh_divida = eh_mae or eh_pai or eh_generico

    if eh_divida and not eh_mae and not eh_pai:
        eh_pai = True
    return eh_divida, eh_pai, eh_mae


def extrair_categoria(texto: str, tipo: str | None = None) -> str:
    t = texto.lower()
    eh_divida, _, _ = _destino_divida(texto)
    if eh_divida:
        return "Dívidas/Compromissos"
    if any(k in t for k in KEYWORDS_RESERVA):
        return "Reserva/Investimentos"
    if tipo == "entrada" and any(k in t for k in ["salário", "salario", "ordenado", "pagamento"]):
        return "Salário"
    if tipo == "entrada" and any(k in t for k in ["freela", "freelance", "extra", "comissão", "comissao"]):
        return "Renda Extra"

    mapa = {
        "Alimentação": [
            "restaurante", "lanche", "hamburguer", "pizza", "ifood", "uber eats", "rappi",
            "delivery", "almoç", "jant", "café", "padaria", "pastel", "açaí", "sorvete", "sushi",
        ],
        "Mercado": [
            "mercado", "supermercado", "atacadão", "atacado", "hortifruti", "extra", "carrefour",
            "assaí", "mart", "kiko", "moacyr",
        ],
        "Transporte/Gasolina": [
            "gasolina", "combustível", "uber", "99", "ônibus", "metrô", "moto", "posto",
            "estacionamento", "pedágio",
        ],
        "Moradia": [
            "aluguel", "condomínio", "água", "luz", "energia", "internet", "net", "claro", "vivo", "gás",
        ],
        "Saúde/Farmácia": [
            "farmácia", "remédio", "médico", "consulta", "exame", "araujo", "drogaria", "ultrafarma", "droga",
        ],
        "Roupas/Beleza": [
            "roupa", "calçado", "tênis", "blusa", "camiseta", "salão", "cabelo", "manicure", "pedicure",
            "caedu", "shein", "shopee",
        ],
        "Lazer/Saídas": [
            "bar", "balada", "show", "cinema", "viagem", "hotel", "parque", "passeio",
        ],
        "Assinaturas": [
            "netflix", "spotify", "amazon", "disney", "youtube", "claude", "google one", "icloud",
            "assinatura", "mensalidade",
        ],
        "Educação": [
            "curso", "faculdade", "escola", "livro", "sesi", "senai", "universidade", "aula", "material",
        ],
        "Seguro": ["seguro"],
        "Parcela/Crédito": ["fatura", "cartão", "parcela", "crédito"],
    }
    for cat, palavras in mapa.items():
        if any(p in t for p in palavras):
            return cat
    return "Outros"


def _remover_valor_e_parcelas(texto: str) -> str:
    t = texto
    t = re.sub(r"R\$\s*\d{1,6}(?:[.,]\d{2})?", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b\d{1,6}[.,]\d{2}\b", "", t)
    t = re.sub(r"\b\d{1,6}\s*(?:reais?|conto|pila)\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bem\s*\d+\s*[xX]\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b\d+\s*(?:vezes|parcelas?)\b", "", t, flags=re.IGNORECASE)
    # Remove um valor inteiro principal restante, mas só se houver contexto financeiro explícito.
    t = re.sub(r"\b\d{2,6}\b", "", t, count=1)
    return t


def _limpar_conectores(texto: str) -> str:
    t = _normalizar(texto)
    t = re.sub(r"^(?:com|de|da|do|dos|das|um|uma|o|a)\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+(?:no|na|em|de|do|da|dos|das)\s*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip(" ,.-?!")


def extrair_descricao(texto: str, tipo: str | None = None) -> str:
    t = _remover_valor_e_parcelas(texto)

    # Remove forma de pagamento mencionada.
    for aliases in ALIASES_CARTAO.values():
        for alias in aliases:
            t = re.sub(rf"\b(?:no|na|em|via)?\s*{re.escape(alias)}\b", "", t, flags=re.IGNORECASE)

    for kw in KEYWORDS_GASTO + KEYWORDS_ENTRADA + ["coloquei", "aportei", "joguei"]:
        t = re.sub(rf"\b{re.escape(kw)}\b", "", t, flags=re.IGNORECASE)

    t = _limpar_conectores(t)

    if any(k in texto.lower() for k in KEYWORDS_RESERVA):
        return "reserva de emergência"
    eh_divida, eh_pai, eh_mae = _destino_divida(texto)
    if eh_divida:
        return "dívida com a mãe" if eh_mae else "dívida com o pai"
    if tipo == "entrada" and any(k in texto.lower() for k in ["salário", "salario"]):
        return "salário"
    if not t:
        return texto[:40]
    return t[:60]


def _extrair_prioridade(texto: str) -> str:
    t = texto.lower()
    if "prioridade alta" in t or "alta prioridade" in t:
        return "alta"
    if "prioridade baixa" in t or "baixa prioridade" in t:
        return "baixa"
    return "media"


def _extrair_item_wishlist(texto: str) -> str:
    t = texto
    t = re.sub(r"quero\s+comprar", "", t, flags=re.IGNORECASE)
    t = re.sub(r"quero\s+(?:um|uma)", "", t, flags=re.IGNORECASE)
    t = re.sub(r"adicionar\s+(?:na\s+)?(?:lista|wishlist)(?:\s*:\s*)?", "", t, flags=re.IGNORECASE)
    t = re.sub(r"lista\s+de\s+desejos(?:\s*:\s*)?", "", t, flags=re.IGNORECASE)
    t = re.sub(r"prioridade\s+(?:alta|media|m[eé]dia|baixa)", "", t, flags=re.IGNORECASE)
    t = _remover_valor_e_parcelas(t)
    t = _limpar_conectores(t)
    return t[:80] or "Item"


def _extrair_item_simulador(texto: str) -> str:
    t = texto
    for padrao in [
        r"vale\s+a\s+pena\s+comprar",
        r"devo\s+comprar",
        r"consigo\s+comprar",
        r"me\s+ajuda\s+a\s+decidir\s+se\s+compro",
    ]:
        t = re.sub(padrao, "", t, flags=re.IGNORECASE)
    t = _remover_valor_e_parcelas(t)
    t = _limpar_conectores(t)
    return t[:80] or "compra"


def calcular_confianca(tipo: str | None, valor: float | None, forma: str | None) -> str:
    if tipo and valor and forma:
        return "alta"
    if tipo and valor:
        return "media"
    return "baixa"


def parse(texto: str) -> dict | None:
    """Interpreta mensagens comuns sem IA."""
    texto = _normalizar(texto)
    tipo = detectar_tipo(texto)
    valor = extrair_valor(texto)
    forma = extrair_forma_pagto(texto)
    parcelas = extrair_parcelas(texto)

    if tipo == "wishlist":
        if not valor:
            return None
        return {
            "tipo": "wishlist",
            "categoria": "Wishlist",
            "subcategoria": "",
            "descricao": _extrair_item_wishlist(texto),
            "valor": valor,
            "forma_pagto": "nao_informado",
            "parcelas": 1,
            "wishlist_item": _extrair_item_wishlist(texto),
            "wishlist_prioridade": _extrair_prioridade(texto),
            "confianca": "alta",
            "via": "local",
        }

    if tipo == "simulador":
        if not valor:
            return None
        return {
            "tipo": "simulador",
            "categoria": "Simulador",
            "subcategoria": "",
            "descricao": _extrair_item_simulador(texto),
            "valor": valor,
            "forma_pagto": "nao_informado",
            "parcelas": parcelas,
            "simulador_descricao": _extrair_item_simulador(texto),
            "simulador_valor_total": valor,
            "simulador_parcelas": parcelas,
            "confianca": "alta",
            "via": "local",
        }

    if not tipo or not valor:
        return None

    eh_divida, eh_pai, eh_mae = _destino_divida(texto)
    eh_reserva = any(k in texto.lower() for k in KEYWORDS_RESERVA)
    categoria = extrair_categoria(texto, tipo)
    descricao = extrair_descricao(texto, tipo)

    # Entradas podem ser salvas sem forma de recebimento, sem chamar IA.
    if tipo == "entrada" and not forma:
        forma = "nao_informado"

    # Gastos sem forma de pagamento seguem para os botões do Telegram.
    forma_saida = forma or "perguntar"
    confianca = calcular_confianca(tipo, valor, forma)

    return {
        "tipo": tipo,
        "categoria": categoria,
        "subcategoria": "",
        "descricao": descricao,
        "valor": valor,
        "forma_pagto": forma_saida,
        "parcelas": parcelas,
        "eh_reserva": eh_reserva,
        "eh_pais": eh_divida,
        "eh_pai": eh_pai,
        "eh_mae": eh_mae,
        "confianca": confianca,
        "via": "local",
        "confirmacao": f"Anotado! R$ {valor:.2f} em {categoria} ✅",
    }
