"""
config.py — Configurações centrais do BiFinanças
Edite este arquivo para personalizar o bot para sua situação.
"""
import os

# ─── CREDENCIAIS (via variáveis de ambiente) ──────────────────────────────────
TELEGRAM_TOKEN      = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY      = os.environ["GEMINI_API_KEY"]
GOOGLE_SHEETS_ID    = os.environ["GOOGLE_SHEETS_ID"]
GOOGLE_CREDS_JSON   = os.environ["GOOGLE_CREDENTIALS_JSON"]
ALLOWED_USER_ID     = int(os.environ.get("ALLOWED_USER_ID", "0"))

# ─── PERFIL FINANCEIRO ────────────────────────────────────────────────────────
RENDA_MENSAL = 4820.0
RESERVA_INICIAL = 2000.0
META_RESERVA = 10000.0
DIVIDA_PAI_TOTAL = 5400.0
DIVIDA_PAI_PAGO = 1000.0
DIVIDA_MAE_TOTAL = 15000.0
DIVIDA_MAE_PAGO = 0.0

# ─── PLANO FINANCEIRO MÊS A MÊS ──────────────────────────────────────────────
PLANO_MENSAL = {
    "2026-06": {"guardar": 200,  "limite_gastos": 2500},
    "2026-07": {"guardar": 400,  "limite_gastos": 2300},
    "2026-08": {"guardar": 600,  "limite_gastos": 2100},
    "2026-09": {"guardar": 800,  "limite_gastos": 1900},
    "2026-10": {"guardar": 800,  "limite_gastos": 1900},
    "2026-11": {"guardar": 1000, "limite_gastos": 1700},
    "2026-12": {"guardar": 1000, "limite_gastos": 1700},
    "2027-01": {"guardar": 1000, "limite_gastos": 1600},
}

# ─── CARTÕES ──────────────────────────────────────────────────────────────────
CARTOES = {
    "santander":    {"nome": "Santander Free ••7648",   "vencimento": 6,  "limite": 11580.0},
    "nubank":       {"nome": "Nubank ••1160",            "vencimento": 11, "limite": 4800.0},
    "mercadopago":  {"nome": "Mercado Pago ••3106",      "vencimento": 11, "limite": 6800.0},
    "caedu":        {"nome": "Caedu ••9868",             "vencimento": 10, "limite": 500.0},
    "bb":           {"nome": "Banco do Brasil ••7881",   "vencimento": 10, "limite": 2000.0},
}

# ─── CATEGORIAS ───────────────────────────────────────────────────────────────
CATEGORIAS = [
    "Alimentação", "Mercado", "Transporte/Gasolina", "Moradia",
    "Saúde/Farmácia", "Roupas/Beleza", "Lazer/Saídas", "Assinaturas",
    "Educação", "Parcela/Crédito", "Seguro", "Salário", "VA/VR",
    "Renda Extra", "Transferência", "Reserva/Investimentos",
    "Dívidas/Compromissos", "Outros"
]

# ─── SUBCATEGORIAS ────────────────────────────────────────────────────────────
SUBCATEGORIAS = {
    "Alimentação":  ["Restaurante", "Lanchonete", "Delivery", "Café", "Padaria"],
    "Mercado":      ["Supermercado", "Hortifruti", "Açougue", "Atacado"],
    "Transporte/Gasolina": ["Gasolina", "Uber/99", "Ônibus", "Manutenção"],
    "Roupas/Beleza": ["Roupas", "Calçados", "Salão", "Cosméticos"],
    "Lazer/Saídas": ["Bares", "Cinema", "Shows", "Viagem", "Jogos"],
    "Assinaturas":  ["Streaming", "Software", "Academia", "Clube"],
    "Saúde/Farmácia": ["Farmácia", "Médico", "Exames", "Plano de Saúde"],
}

# ─── LIMITES DE ORÇAMENTO POR CATEGORIA ──────────────────────────────────────
LIMITES_ORCAMENTO = {
    "Alimentação":          600.0,
    "Mercado":              400.0,
    "Transporte/Gasolina":  450.0,
    "Lazer/Saídas":         300.0,
    "Roupas/Beleza":        200.0,
    "Assinaturas":          200.0,
    "Saúde/Farmácia":       150.0,
}

# ─── FORMAS DE PAGAMENTO ──────────────────────────────────────────────────────
FORMAS_PAGTO = {
    "santander":    "💳 Santander",
    "nubank":       "💜 Nubank",
    "mercadopago":  "💛 Mercado Pago",
    "caedu":        "🟢 Caedu",
    "bb":           "💛 Banco do Brasil",
    "debito":       "💳 Débito",
    "pix":          "⚡ Pix",
    "dinheiro":     "💵 Dinheiro",
    "ted":          "🏦 TED",
    "nao_informado": "🏦 Recebimento não informado",
}

# ─── PALAVRAS-CHAVE PARA PARSER LOCAL ────────────────────────────────────────
KEYWORDS_GASTO = [
    "gastei", "paguei", "comprei", "almocei", "jantei", "tomei café",
    "fui no", "fui à", "passei no", "abasteci", "consertei", "contratei",
    "renovei", "assinei", "parcelei", "dividi"
]

KEYWORDS_ENTRADA = [
    "recebi", "entrou", "caiu", "depositei", "transferiram", "ganhei",
    "salário", "salario", "va ", "vr ", "freelance", "renda", "comissão"
]

KEYWORDS_RESERVA = [
    "reserva", "guardei", "poupei", "caixinha", "poupança", "emergência"
]

KEYWORDS_PAIS = [
    "pai", "mae", "mãe", "mamãe", "papai", "família", "familia",
    "empréstimo dos pais", "devo pra"
]

KEYWORDS_WISHLIST = [
    "quero comprar", "quero um", "quero uma", "sonho em ter",
    "adicionar na lista", "wishlist", "lista de desejos", "quero ter",
    "tô de olho", "to de olho"
]

KEYWORDS_SIMULADOR = [
    "vale a pena", "devo comprar", "consigo comprar", "quando consigo",
    "me ajuda a decidir", "parcelado em", "em quantas vezes"
]

# ─── ALIASES DE CARTÃO ────────────────────────────────────────────────────────
ALIASES_CARTAO = {
    "santander": ["santander", "san", "7648"],
    "nubank":    ["nubank", "nu", "roxinho", "roxo", "1160"],
    "mercadopago": ["mercado pago", "mp", "mercadopago", "3106"],
    "caedu":     ["caedu", "9868"],
    "bb":        ["banco do brasil", "bb", "brasil", "7881"],
    "debito":    ["débito", "debito", "cartão de débito"],
    "pix":       ["pix", "via pix", "mandei pix", "chave pix"],
    "dinheiro":  ["dinheiro", "espécie", "especie", "cash", "na mão", "na mao"],
    "ted":       ["ted", "transferência", "transferencia", "doc"],
}
