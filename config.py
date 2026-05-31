import os
import json

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0") or 0)

CARTOES = {
    "santander": {
        "nome": "Santander Free",
        "final": "7648",
        "vencimento": 6,
        "fechamento": 29,
        "aliases": ["santander", "santander free", "free"]
    },
    "nubank": {
        "nome": "Nubank",
        "final": "1160",
        "vencimento": 11,
        "fechamento": 4,
        "aliases": ["nubank", "nu", "roxinho"]
    },
    "mercado_pago": {
        "nome": "Mercado Pago",
        "final": "3106",
        "vencimento": 11,
        "fechamento": 4,
        "aliases": ["mercado pago", "mercado", "mp"]
    },
    "caedu": {
        "nome": "Caedu",
        "final": "9868",
        "vencimento": 10,
        "fechamento": 3,
        "aliases": ["caedu"]
    },
    "banco_do_brasil": {
        "nome": "Banco do Brasil",
        "final": "7881",
        "vencimento": 10,
        "fechamento": 3,
        "aliases": ["banco do brasil", "bb"]
    },
}
def identificar_cartao(texto: str):
    texto = (texto or "").lower()

    for chave, dados in CARTOES.items():
        for alias in dados.get("aliases", []):
            if alias.lower() in texto:
                return chave, dados

    return None, None
