"""
sheets.py — Toda interação com o Google Sheets
"""
import json
import logging
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_CREDS_JSON, GOOGLE_SHEETS_ID

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

ABAS = {
    "Lançamentos": ["Data", "Tipo", "Categoria", "Subcategoria", "Descrição", "Valor", "Forma_Pagto", "Mês", "Parcela"],
    "Cartões":     ["Cartão", "Fatura_Atual", "Vencimento", "Atualizado_Em"],
    "Metas":       ["Nome", "Tipo", "Valor_Meta", "Valor_Atual", "Prazo", "Status"],
    "Wishlist":    ["Item", "Valor_Est", "Prioridade", "Data_Adição", "Observação", "Status"],
    "Parcelas":    ["Descrição", "Cartão", "Valor_Parcela", "Parcela_Atual", "Total_Parcelas", "Encerra_Em"],
    "Orçamento":   ["Categoria", "Limite_Mensal", "Mês"],
    "Score":       ["Mês", "Nota", "Guardou_Meta", "Ficou_Limite", "Pagou_Dia", "Observação"],
}

_sheet_cache = None

def get_sheet():
    global _sheet_cache
    if _sheet_cache:
        try:
            _sheet_cache.worksheets()
            return _sheet_cache
        except:
            _sheet_cache = None
    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_CREDS_JSON), scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    _sheet_cache = gc.open_by_key(GOOGLE_SHEETS_ID)
    return _sheet_cache

def garantir_abas():
    try:
        sh = get_sheet()
        existentes = [ws.title for ws in sh.worksheets()]
        for aba, cabecalhos in ABAS.items():
            if aba not in existentes:
                ws = sh.add_worksheet(title=aba, rows=1000, cols=len(cabecalhos))
                ws.append_row(cabecalhos)
                logger.info(f"Aba '{aba}' criada.")
        # Garante metas padrão
        _garantir_metas_padrao(sh)
        return True
    except Exception as e:
        logger.error(f"Erro ao garantir abas: {e}")
        return False

def _garantir_metas_padrao(sh):
    from config import RESERVA_INICIAL, META_RESERVA, DIVIDA_PAIS_TOTAL, DIVIDA_PAIS_PAGO
    ws = sh.worksheet("Metas")
    registros = ws.get_all_records()
    nomes = [r.get("Nome", "").lower() for r in registros]
    if "reserva de emergência" not in nomes:
        ws.append_row(["Reserva de emergência", "poupança", META_RESERVA,
                        RESERVA_INICIAL, "2027-06", "Em andamento"])
    if "dívida com os pais" not in nomes:
        ws.append_row(["Dívida com os pais", "dívida", DIVIDA_PAIS_TOTAL,
                        DIVIDA_PAIS_PAGO, "2028-08", "Em andamento"])

# ─── LANÇAMENTOS ──────────────────────────────────────────────────────────────

def salvar_lancamento(data, tipo, categoria, subcategoria, descricao,
                      valor, forma_pagto, mes, parcela=""):
    try:
        ws = get_sheet().worksheet("Lançamentos")
        ws.append_row([data, tipo, categoria, subcategoria, descricao,
                       float(valor), forma_pagto, mes, parcela])
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar lançamento: {e}")
        return False

def buscar_lancamentos_mes(mes_ano: str):
    try:
        ws = get_sheet().worksheet("Lançamentos")
        return [r for r in ws.get_all_records()
                if str(r.get("Mês", "")) == mes_ano]
    except Exception as e:
        logger.error(f"Erro: {e}")
        return []

def buscar_todos_lancamentos():
    try:
        return get_sheet().worksheet("Lançamentos").get_all_records()
    except Exception as e:
        logger.error(f"Erro: {e}")
        return []

def buscar_lancamentos_categoria(categoria: str, mes_ano: str = None):
    todos = buscar_lancamentos_mes(mes_ano) if mes_ano else buscar_todos_lancamentos()
    return [r for r in todos if r.get("Categoria", "") == categoria]

# ─── METAS ────────────────────────────────────────────────────────────────────

def buscar_metas():
    try:
        return get_sheet().worksheet("Metas").get_all_records()
    except Exception as e:
        logger.error(f"Erro: {e}")
        return []

def atualizar_meta(nome: str, novo_valor_atual: float):
    try:
        ws = get_sheet().worksheet("Metas")
        registros = ws.get_all_records()
        for i, r in enumerate(registros, start=2):
            if r.get("Nome", "").lower() == nome.lower():
                ws.update_cell(i, 4, round(novo_valor_atual, 2))
                # Atualiza status se atingiu meta
                if novo_valor_atual >= float(r.get("Valor_Meta", 0)):
                    ws.update_cell(i, 6, "✅ Atingida!")
                return True
        return False
    except Exception as e:
        logger.error(f"Erro ao atualizar meta: {e}")
        return False

def buscar_meta_valor(nome: str) -> float:
    metas = buscar_metas()
    for m in metas:
        if nome.lower() in m.get("Nome", "").lower():
            return float(m.get("Valor_Atual", 0))
    return 0.0

# ─── WISHLIST ─────────────────────────────────────────────────────────────────

def salvar_wishlist(item, valor, prioridade, observacao=""):
    try:
        ws = get_sheet().worksheet("Wishlist")
        ws.append_row([item, float(valor), prioridade,
                       datetime.now().strftime("%d/%m/%Y"), observacao, "Pendente"])
        return True
    except Exception as e:
        logger.error(f"Erro: {e}")
        return False

def buscar_wishlist():
    try:
        return get_sheet().worksheet("Wishlist").get_all_records()
    except Exception as e:
        logger.error(f"Erro: {e}")
        return []

def marcar_wishlist_comprado(item: str):
    try:
        ws = get_sheet().worksheet("Wishlist")
        registros = ws.get_all_records()
        for i, r in enumerate(registros, start=2):
            if item.lower() in r.get("Item", "").lower():
                ws.update_cell(i, 6, "✅ Comprado")
                return True
        return False
    except Exception as e:
        logger.error(f"Erro: {e}")
        return False

# ─── PARCELAS ─────────────────────────────────────────────────────────────────

def salvar_parcela(descricao, cartao, valor_parcela, atual, total, encerra_em):
    try:
        ws = get_sheet().worksheet("Parcelas")
        ws.append_row([descricao, cartao, float(valor_parcela), atual, total, encerra_em])
        return True
    except Exception as e:
        logger.error(f"Erro: {e}")
        return False

def buscar_parcelas():
    try:
        return get_sheet().worksheet("Parcelas").get_all_records()
    except Exception as e:
        logger.error(f"Erro: {e}")
        return []

# ─── SCORE ────────────────────────────────────────────────────────────────────

def salvar_score(mes, nota, guardou, ficou_limite, pagou_dia, obs=""):
    try:
        ws = get_sheet().worksheet("Score")
        # Remove registro anterior do mesmo mês se existir
        registros = ws.get_all_records()
        for i, r in enumerate(registros, start=2):
            if r.get("Mês") == mes:
                ws.delete_rows(i)
                break
        ws.append_row([mes, nota, guardou, ficou_limite, pagou_dia, obs])
        return True
    except Exception as e:
        logger.error(f"Erro: {e}")
        return False

def buscar_scores():
    try:
        return get_sheet().worksheet("Score").get_all_records()
    except Exception as e:
        logger.error(f"Erro: {e}")
        return []
