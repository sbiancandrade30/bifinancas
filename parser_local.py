"""
parser_local.py — Interpreta mensagens simples sem usar IA
Modelo híbrido: tenta aqui primeiro, só chama IA se não conseguir.
"""
import re
from config import (KEYWORDS_GASTO, KEYWORDS_ENTRADA, KEYWORDS_RESERVA,
                    KEYWORDS_PAIS, KEYWORDS_WISHLIST, KEYWORDS_SIMULADOR,
                    ALIASES_CARTAO, CATEGORIAS)


def detectar_tipo(texto: str) -> str | None:
    t = texto.lower()
    if any(k in t for k in KEYWORDS_SIMULADOR):
        return "simulador"
    if any(k in t for k in KEYWORDS_WISHLIST):
        return "wishlist"
    if any(k in t for k in KEYWORDS_ENTRADA):
        return "entrada"
    if any(k in t for k in KEYWORDS_GASTO):
        return "gasto"
    return None


def extrair_valor(texto: str) -> float | None:
    # Padrões: 45, 45.90, 45,90, R$45, R$ 45,90
    padroes = [
        r'R\$\s*(\d{1,6}[.,]\d{2})',
        r'R\$\s*(\d{1,6})',
        r'(\d{1,6}[.,]\d{2})\s*(?:reais?|conto|pila)',
        r'(\d{1,6})\s*(?:reais?|conto|pila)',
        r'\b(\d{1,6}[.,]\d{2})\b',
        r'\b(\d{2,6})\b',
    ]
    for p in padroes:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            val = m.group(1).replace(',', '.')
            try:
                return float(val)
            except:
                continue
    return None


def extrair_parcelas(texto: str) -> int:
    t = texto.lower()
    # "em 10x", "10 vezes", "parcelado em 3", "3 parcelas"
    padroes = [
        r'em\s*(\d+)\s*[xX]',
        r'(\d+)\s*vezes',
        r'parcelado\s*em\s*(\d+)',
        r'(\d+)\s*parcelas?',
    ]
    for p in padroes:
        m = re.search(p, t)
        if m:
            return int(m.group(1))
    return 1


def extrair_forma_pagto(texto: str) -> str | None:
    t = texto.lower()
    for chave, aliases in ALIASES_CARTAO.items():
        if any(alias in t for alias in aliases):
            return chave
    return None


def extrair_categoria(texto: str) -> str:
    t = texto.lower()
    mapa = {
        "Alimentação":         ["restaurante", "lanche", "hamburguer", "pizza", "ifood",
                                 "uber eats", "rappi", "delivery", "almoç", "jant", "café",
                                 "padaria", "pastel", "açaí", "sorvete", "sushi"],
        "Mercado":             ["mercado", "supermercado", "atacadão", "atacado", "hortifruti",
                                 "extra", "carrefour", "assaí", "mart", "kiko", "moacyr"],
        "Transporte/Gasolina": ["gasolina", "combustível", "uber", "99", "ônibus", "metrô",
                                 "moto", "posto", "estacionamento", "pedágio", "gasolina"],
        "Moradia":             ["aluguel", "condomínio", "água", "luz", "energia", "internet",
                                 "net", "claro", "vivo", "gás"],
        "Saúde/Farmácia":      ["farmácia", "remédio", "médico", "consulta", "exame",
                                 "araujo", "drogaria", "ultrafarma", "droga"],
        "Roupas/Beleza":       ["roupa", "calçado", "tênis", "blusa", "camiseta", "salão",
                                 "cabelo", "manicure", "pedicure", "caedu", "shein", "shopee"],
        "Lazer/Saídas":        ["bar", "balada", "show", "cinema", "viagem", "hotel",
                                 "sorvete", "parque", "passeio"],
        "Assinaturas":         ["netflix", "spotify", "amazon", "disney", "youtube", "claude",
                                 "google one", "icloud", "assinatura", "mensalidade"],
        "Educação":            ["curso", "faculdade", "escola", "livro", "sesi", "senai",
                                 "universidade", "aula", "material"],
        "Seguro":              ["seguro"],
        "Parcela/Crédito":     ["fatura", "cartão", "parcela", "crédito"],
    }
    for cat, palavras in mapa.items():
        if any(p in t for p in palavras):
            return cat
    return "Outros"


def extrair_descricao(texto: str) -> str:
    # Remove valor e forma de pagamento para deixar só a descrição
    t = re.sub(r'R\$\s*[\d.,]+', '', texto)
    t = re.sub(r'\b\d+[.,]\d{2}\b', '', t)
    t = re.sub(r'\b\d+\s*(reais?|conto|pila|x)\b', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bem\s*\d+\s*[xX]\b', '', t)
    # Remove keywords de gasto/entrada
    for kw in KEYWORDS_GASTO + KEYWORDS_ENTRADA:
        t = re.sub(rf'\b{re.escape(kw)}\b', '', t, flags=re.IGNORECASE)
    t = ' '.join(t.split())
    return t[:60].strip(' ,.') or texto[:40]


def calcular_confianca(tipo, valor, forma) -> str:
    if tipo and valor and forma:
        return "alta"
    if tipo and valor:
        return "media"
    return "baixa"


def parse(texto: str) -> dict | None:
    """
    Tenta interpretar a mensagem com regras locais.
    Retorna dict se conseguiu com confiança média ou alta.
    Retorna None se deve chamar a IA.
    """
    tipo   = detectar_tipo(texto)
    valor  = extrair_valor(texto)
    forma  = extrair_forma_pagto(texto)
    parcelas = extrair_parcelas(texto)

    confianca = calcular_confianca(tipo, valor, forma)

    # Simulador e wishlist sempre vão para IA (contexto complexo)
    if tipo in ("simulador", "wishlist"):
        return None

    # Se não detectou tipo ou valor, vai para IA
    if not tipo or not valor:
        return None

    # Confiança baixa sem forma de pagamento — vai para IA para frases complexas
    # Ex: "paguei 300 daqueles 19400 dos meus pais"
    if confianca == "baixa":
        return None

    categoria  = extrair_categoria(texto)
    descricao  = extrair_descricao(texto)

    eh_reserva = any(k in texto.lower() for k in KEYWORDS_RESERVA)
    eh_pais    = any(k in texto.lower() for k in KEYWORDS_PAIS)

    return {
        "tipo":        tipo,
        "categoria":   categoria,
        "subcategoria": "",
        "descricao":   descricao,
        "valor":       valor,
        "forma_pagto": forma or "perguntar",
        "parcelas":    parcelas,
        "eh_reserva":  eh_reserva,
        "eh_pais":     eh_pais,
        "confianca":   confianca,
        "via":         "local",
        "confirmacao": f"Anotado! R$ {valor:.2f} em {categoria} ✅"
    }
