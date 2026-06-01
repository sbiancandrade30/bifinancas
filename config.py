import os
import json

# =========================
# VARIÁVEIS DE AMBIENTE
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")

GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_CREDS_JSON = GOOGLE_CREDENTIALS_JSON

ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0") or 0)


# =========================
# PERFIL FINANCEIRO
# =========================

RENDA_MENSAL = 4820.0

RESERVA_INICIAL = 2000.0
META_RESERVA = 10000.0

DIVIDA_PAIS_TOTAL = 19400.0
DIVIDA_PAIS_PAGO = 1000.0

# Apelidos para versões novas/alternativas do código
RESERVA_ATUAL = RESERVA_INICIAL
RESERVA_META = META_RESERVA
DIVIDA_PAI_TOTAL = 5400.0
DIVIDA_MAE_TOTAL = 15000.0


# =========================
# PLANO FINANCEIRO MÊS A MÊS
# =========================

PLANO_MENSAL = {
    "2026-06": {"guardar": 200, "limite_gastos": 2500},
    "2026-07": {"guardar": 400, "limite_gastos": 2300},
    "2026-08": {"guardar": 600, "limite_gastos": 2100},
    "2026-09": {"guardar": 800, "limite_gastos": 1900},
    "2026-10": {"guardar": 800, "limite_gastos": 1900},
    "2026-11": {"guardar": 1000, "limite_gastos": 1700},
    "2026-12": {"guardar": 1000, "limite_gastos": 1700},
    "2027-01": {"guardar": 1000, "limite_gastos": 1600},
}

# Apelido para versões novas do código
PLANO = {
    mes: {
        "guardar": dados["guardar"],
        "limite": dados["limite_gastos"],
    }
    for mes, dados in PLANO_MENSAL.items()
}


# =========================
# CARTÕES DE CRÉDITO
# =========================

CARTOES = {
    "santander": {
        "nome": "Santander Free ••7648",
        "final": "7648",
        "vencimento": 6,
        "fechamento": 29,
        "limite": 11580.0,
        "aliases": ["santander", "santander free", "free", "san", "7648"],
    },
    "nubank": {
        "nome": "Nubank ••1160",
        "final": "1160",
        "vencimento": 11,
        "fechamento": 4,
        "limite": 4800.0,
        "aliases": ["nubank", "nu", "roxinho", "roxo", "1160"],
    },
    "mercadopago": {
        "nome": "Mercado Pago ••3106",
        "final": "3106",
        "vencimento": 11,
        "fechamento": 4,
        "limite": 6800.0,
        "aliases": ["mercado pago", "mercadopago", "mercado", "mp", "3106"],
    },
    "mercado_pago": {
        "nome": "Mercado Pago ••3106",
        "final": "3106",
        "vencimento": 11,
        "fechamento": 4,
        "limite": 6800.0,
        "aliases": ["mercado pago", "mercadopago", "mercado", "mp", "3106"],
    },
    "caedu": {
        "nome": "Caedu ••9868",
        "final": "9868",
        "vencimento": 10,
        "fechamento": 3,
        "limite": 500.0,
        "aliases": ["caedu", "9868"],
    },
    "bb": {
        "nome": "Banco do Brasil ••7881",
        "final": "7881",
        "vencimento": 10,
        "fechamento": 3,
        "limite": 2000.0,
        "aliases": ["banco do brasil", "bb", "brasil", "7881"],
    },
    "banco_do_brasil": {
        "nome": "Banco do Brasil ••7881",
        "final": "7881",
        "vencimento": 10,
        "fechamento": 3,
        "limite": 2000.0,
        "aliases": ["banco do brasil", "bb", "brasil", "7881"],
    },
}


# =========================
# CATEGORIAS
# =========================

CATEGORIAS = [
    "Alimentação",
    "Mercado",
    "Transporte/Gasolina",
    "Moradia",
    "Saúde/Farmácia",
    "Roupas/Beleza",
    "Lazer/Saídas",
    "Assinaturas",
    "Educação",
    "Parcela/Crédito",
    "Seguro",
    "Salário",
    "VA/VR",
    "Renda Extra",
    "Transferência",
    "Dívidas/Compromissos",
    "Reserva/Investimentos",
    "Casa",
    "Presentes",
    "Outros",
]


SUBCATEGORIAS = {
    "Alimentação": ["Restaurante", "Lanchonete", "Delivery", "Café", "Padaria"],
    "Mercado": ["Supermercado", "Hortifruti", "Açougue", "Atacado"],
    "Transporte/Gasolina": ["Gasolina", "Uber/99", "Ônibus", "Manutenção"],
    "Moradia": ["Aluguel", "Condomínio", "Água", "Luz", "Energia", "Internet", "Gás"],
    "Saúde/Farmácia": ["Farmácia", "Médico", "Exames", "Plano de Saúde", "Terapia"],
    "Roupas/Beleza": ["Roupas", "Calçados", "Salão", "Cosméticos", "Cabelo", "Unhas"],
    "Lazer/Saídas": ["Bares", "Cinema", "Shows", "Viagem", "Jogos", "Passeio"],
    "Assinaturas": ["Streaming", "Software", "Academia", "Clube", "Aplicativos"],
    "Educação": ["Curso", "Faculdade", "Livro", "Material", "Pós-graduação"],
    "Parcela/Crédito": ["Fatura", "Cartão", "Parcela", "Crédito"],
    "Seguro": ["Seguro"],
    "Salário": ["Salário"],
    "VA/VR": ["VA", "VR", "Vale alimentação", "Vale refeição"],
    "Renda Extra": ["Freelance", "Extra", "Comissão"],
    "Transferência": ["Pix", "TED", "Transferência"],
    "Dívidas/Compromissos": ["Pai", "Mãe", "Pais", "Empréstimo", "Outros"],
    "Reserva/Investimentos": ["Reserva de emergência", "Caixinha", "Investimento", "Outros"],
    "Casa": ["Aluguel", "Energia", "Água", "Internet", "Móveis", "Outros"],
    "Presentes": ["Família", "Amigos", "Namorado", "Datas comemorativas", "Outros"],
    "Outros": ["Outros"],
}


# =========================
# LIMITES DE ORÇAMENTO
# =========================

LIMITES_ORCAMENTO = {
    "Alimentação": 600.0,
    "Mercado": 400.0,
    "Transporte/Gasolina": 450.0,
    "Lazer/Saídas": 300.0,
    "Roupas/Beleza": 200.0,
    "Assinaturas": 200.0,
    "Saúde/Farmácia": 150.0,
}

# Apelido para versões novas do código
LIMITES = LIMITES_ORCAMENTO


# =========================
# FORMAS DE PAGAMENTO
# =========================

FORMAS_PAGTO = {
    "santander": "💳 Santander",
    "nubank": "💜 Nubank",
    "mercadopago": "💛 Mercado Pago",
    "mercado_pago": "💛 Mercado Pago",
    "caedu": "🟢 Caedu",
    "bb": "💛 Banco do Brasil",
    "banco_do_brasil": "💛 Banco do Brasil",
    "debito": "💳 Débito",
    "débito": "💳 Débito",
    "pix": "⚡ Pix",
    "dinheiro": "💵 Dinheiro",
    "ted": "🏦 TED",
}


# =========================
# PALAVRAS-CHAVE PARA PARSER LOCAL
# =========================

KEYWORDS_GASTO = [
    "gastei",
    "paguei",
    "comprei",
    "almocei",
    "jantei",
    "tomei café",
    "fui no",
    "fui à",
    "passei no",
    "abasteci",
    "consertei",
    "contratei",
    "renovei",
    "assinei",
    "parcelei",
    "dividi",
]

KEYWORDS_ENTRADA = [
    "recebi",
    "entrou",
    "caiu",
    "depositei",
    "transferiram",
    "ganhei",
    "salário",
    "salario",
    "va ",
    "vr ",
    "freelance",
    "renda",
    "comissão",
]

KEYWORDS_RESERVA = [
    "reserva",
    "guardei",
    "guardar",
    "poupei",
    "caixinha",
    "poupança",
    "emergência",
    "investi",
]

KEYWORDS_PAIS = [
    "pai",
    "mae",
    "mãe",
    "mamãe",
    "papai",
    "família",
    "familia",
    "empréstimo dos pais",
    "devo pra",
]

KEYWORDS_DIVIDA_PAI = [
    "paguei pai",
    "paguei pro pai",
    "paguei para o pai",
    "meu pai",
    "dívida com o pai",
    "divida com o pai",
]

KEYWORDS_DIVIDA_MAE = [
    "paguei mãe",
    "paguei mae",
    "paguei pra mãe",
    "paguei para a mãe",
    "minha mãe",
    "minha mae",
    "dívida com a mãe",
    "divida com a mae",
]

KEYWORDS_WISHLIST = [
    "quero comprar",
    "quero um",
    "quero uma",
    "sonho em ter",
    "adicionar na lista",
    "wishlist",
    "lista de desejos",
    "quero ter",
    "tô de olho",
    "to de olho",
]

KEYWORDS_SIMULADOR = [
    "vale a pena",
    "devo comprar",
    "consigo comprar",
    "quando consigo",
    "me ajuda a decidir",
    "parcelado em",
    "em quantas vezes",
]


# =========================
# ALIASES DE PAGAMENTO
# =========================

ALIASES_CARTAO = {
    "santander": ["santander", "san", "7648", "santander free", "free"],
    "nubank": ["nubank", "nu", "roxinho", "roxo", "1160"],
    "mercadopago": ["mercado pago", "mp", "mercadopago", "mercado", "3106"],
    "mercado_pago": ["mercado pago", "mp", "mercadopago", "mercado", "3106"],
    "caedu": ["caedu", "9868"],
    "bb": ["banco do brasil", "bb", "brasil", "7881"],
    "banco_do_brasil": ["banco do brasil", "bb", "brasil", "7881"],
    "debito": ["débito", "debito", "cartão de débito"],
    "pix": ["pix", "via pix", "mandei pix", "chave pix"],
    "dinheiro": ["dinheiro", "espécie", "especie", "cash", "na mão", "na mao"],
    "ted": ["ted", "transferência", "transferencia", "doc"],
}


# =========================
# FUNÇÕES AUXILIARES
# =========================

def identificar_cartao(texto: str):
    texto = (texto or "").lower()

    for chave, dados in CARTOES.items():
        nomes = [
            chave,
            dados.get("nome", ""),
            dados.get("final", ""),
            *dados.get("aliases", []),
        ]

        for nome in nomes:
            if nome and str(nome).lower() in texto:
                return chave, dados

    return None, None
