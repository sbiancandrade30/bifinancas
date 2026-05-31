import os
import json

# =========================
# VARIÁVEIS DE AMBIENTE
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")

# No Northflank você usa GOOGLE_CREDENTIALS_JSON
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

# O sheets.py usa este nome
GOOGLE_CREDS_JSON = GOOGLE_CREDENTIALS_JSON

ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0") or 0)


# =========================
# DADOS FINANCEIROS BASE
# =========================

RENDA_MENSAL = 4820

RESERVA_META = 10000
RESERVA_ATUAL = 2000

DIVIDA_PAI_TOTAL = 5400
DIVIDA_MAE_TOTAL = 15000


# =========================
# CARTÕES DE CRÉDITO
# =========================
# Ajuste os dias de fechamento conforme aparecem no app de cada cartão.

CARTOES = {
    "santander": {
        "nome": "Santander Free",
        "final": "7648",
        "vencimento": 6,
        "fechamento": 29,
        "aliases": ["santander", "santander free", "free", "7648"],
    },
    "nubank": {
        "nome": "Nubank",
        "final": "1160",
        "vencimento": 11,
        "fechamento": 4,
        "aliases": ["nubank", "nu", "roxinho", "1160"],
    },
    "mercado_pago": {
        "nome": "Mercado Pago",
        "final": "3106",
        "vencimento": 11,
        "fechamento": 4,
        "aliases": ["mercado pago", "mercadopago", "mercado", "mp", "3106"],
    },
    "caedu": {
        "nome": "Caedu",
        "final": "9868",
        "vencimento": 10,
        "fechamento": 3,
        "aliases": ["caedu", "9868"],
    },
    "banco_do_brasil": {
        "nome": "Banco do Brasil",
        "final": "7881",
        "vencimento": 10,
        "fechamento": 3,
        "aliases": ["banco do brasil", "bb", "7881"],
    },
}


# =========================
# FORMAS DE PAGAMENTO
# =========================

FORMAS_PAGTO = [
    "dinheiro",
    "pix",
    "debito",
    "débito",
    "nubank",
    "santander",
    "mercado pago",
    "mercadopago",
    "caedu",
    "banco do brasil",
    "bb",
]


# =========================
# CATEGORIAS
# =========================

CATEGORIAS = [
    "Alimentação",
    "Mercado",
    "Transporte/Gasolina",
    "Lazer/Saídas",
    "Roupas/Beleza",
    "Assinaturas",
    "Saúde/Farmácia",
    "Dívidas/Compromissos",
    "Reserva/Investimentos",
    "Casa",
    "Educação",
    "Presentes",
    "Outros",
]


SUBCATEGORIAS = {
    "Alimentação": [
        "Restaurante",
        "Lanche",
        "Padaria",
        "Delivery",
        "Café",
        "Outros",
    ],
    "Mercado": [
        "Supermercado",
        "Açougue",
        "Hortifruti",
        "Produtos de limpeza",
        "Higiene",
        "Outros",
    ],
    "Transporte/Gasolina": [
        "Gasolina",
        "Uber",
        "Ônibus",
        "Manutenção",
        "Estacionamento",
        "Outros",
    ],
    "Lazer/Saídas": [
        "Cinema",
        "Bar",
        "Passeio",
        "Viagem",
        "Evento",
        "Outros",
    ],
    "Roupas/Beleza": [
        "Roupas",
        "Sapatos",
        "Maquiagem",
        "Cabelo",
        "Unhas",
        "Outros",
    ],
    "Assinaturas": [
        "Streaming",
        "Aplicativos",
        "Academia",
        "Cursos",
        "Outros",
    ],
    "Saúde/Farmácia": [
        "Farmácia",
        "Consulta",
        "Exames",
        "Terapia",
        "Outros",
    ],
    "Dívidas/Compromissos": [
        "Pai",
        "Mãe",
        "Carro",
        "Empréstimo",
        "Outros",
    ],
    "Reserva/Investimentos": [
        "Reserva de emergência",
        "Caixinha",
        "Investimento",
        "Outros",
    ],
    "Casa": [
        "Aluguel",
        "Energia",
        "Água",
        "Internet",
        "Móveis",
        "Outros",
    ],
    "Educação": [
        "Pós-graduação",
        "Curso",
        "Livro",
        "Material",
        "Outros",
    ],
    "Presentes": [
        "Família",
        "Amigos",
        "Namorado",
        "Datas comemorativas",
        "Outros",
    ],
    "Outros": [
        "Outros",
    ],
}


# =========================
# LIMITES DE ORÇAMENTO
# =========================

LIMITES = {
    "Alimentação": 600,
    "Mercado": 400,
    "Transporte/Gasolina": 450,
    "Lazer/Saídas": 300,
    "Roupas/Beleza": 200,
    "Assinaturas": 200,
    "Saúde/Farmácia": 150,
}


# =========================
# PLANO FINANCEIRO
# =========================

PLANO = {
    "2026-06": {"guardar": 200, "limite": 2500},
    "2026-07": {"guardar": 400, "limite": 2300},
    "2026-08": {"guardar": 600, "limite": 2100},
    "2026-09": {"guardar": 800, "limite": 1900},
    "2026-10": {"guardar": 800, "limite": 1900},
    "2026-11": {"guardar": 1000, "limite": 1700},
    "2026-12": {"guardar": 1000, "limite": 1700},
    "2027-01": {"guardar": 1000, "limite": 1600},
}


# =========================
# PALAVRAS-CHAVE
# =========================

KEYWORDS_RESERVA = [
    "guardei",
    "guardar",
    "reserva",
    "poupei",
    "caixinha",
    "investi",
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
