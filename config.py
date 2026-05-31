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

# O sheets.py está tentando importar GOOGLE_CREDS_JSON
# Então deixamos os dois nomes funcionando
GOOGLE_CREDS_JSON = GOOGLE_CREDENTIALS_JSON

ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0") or 0)


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
