"""
sheets.py — Toda interação com o Google Sheets
"""
import calendar
import json
import logging
from collections import defaultdict
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDS_JSON, GOOGLE_SHEETS_ID

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Os primeiros campos de Lançamentos/Parcelas preservam o formato já usado pelo dashboard.
# As novas colunas ficam no final para não quebrar a leitura existente.
ABAS = {
    "Lançamentos": [
        "Data", "Tipo", "Categoria", "Subcategoria", "Descrição", "Valor",
        "Forma_Pagto", "Mês", "Parcela", "ID", "Valor_Total", "Meta"
    ],
    "Cartões": ["Cartão", "Fatura_Atual", "Vencimento", "Atualizado_Em"],
    "Metas": ["Nome", "Tipo", "Valor_Meta", "Valor_Atual", "Prazo", "Status"],
    "Wishlist": ["Item", "Valor_Est", "Prioridade", "Data_Adição", "Observação", "Status"],
    "Parcelas": [
        "Descrição", "Cartão", "Valor_Parcela", "Parcela_Atual", "Total_Parcelas",
        "Encerra_Em", "Mês_Início", "ID", "Valor_Total"
    ],
    "Orçamento": ["Categoria", "Limite_Mensal", "Mês"],
    "Score": ["Mês", "Nota", "Guardou_Meta", "Ficou_Limite", "Pagou_Dia", "Observação"],
}

_sheet_cache = None


def get_sheet():
    global _sheet_cache
    if _sheet_cache:
        try:
            _sheet_cache.worksheets()
            return _sheet_cache
        except Exception:
            _sheet_cache = None

    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_CREDS_JSON), scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    _sheet_cache = gc.open_by_key(GOOGLE_SHEETS_ID)
    return _sheet_cache


def _garantir_cabecalhos(ws, cabecalhos: list[str]):
    """Cria ou complementa cabeçalhos sem apagar dados existentes."""
    atuais = ws.row_values(1)
    if not atuais:
        ws.append_row(cabecalhos)
        return

    for cab in cabecalhos:
        if cab not in atuais:
            atuais.append(cab)
            ws.update_cell(1, len(atuais), cab)
            logger.info("Coluna '%s' adicionada à aba '%s'.", cab, ws.title)


def garantir_abas():
    try:
        sh = get_sheet()
        existentes = [ws.title for ws in sh.worksheets()]
        for aba, cabecalhos in ABAS.items():
            if aba not in existentes:
                ws = sh.add_worksheet(title=aba, rows=1000, cols=len(cabecalhos))
                ws.append_row(cabecalhos)
                logger.info("Aba '%s' criada.", aba)
            else:
                ws = sh.worksheet(aba)
                _garantir_cabecalhos(ws, cabecalhos)

        _garantir_metas_padrao(sh)
        return True
    except Exception as e:
        logger.error("Erro ao garantir abas: %s", e)
        return False


def _garantir_metas_padrao(sh):
    from config import RESERVA_INICIAL, META_RESERVA, DIVIDA_PAIS_TOTAL, DIVIDA_PAIS_PAGO

    ws = sh.worksheet("Metas")
    _garantir_cabecalhos(ws, ABAS["Metas"])
    registros = ws.get_all_records()
    nomes = [str(r.get("Nome", "")).lower() for r in registros]

    if "reserva de emergência" not in nomes:
        ws.append_row([
            "Reserva de emergência", "poupança", META_RESERVA,
            RESERVA_INICIAL, "2027-06", "Em andamento"
        ])
    if "dívida com os pais" not in nomes:
        ws.append_row([
            "Dívida com os pais", "dívida", DIVIDA_PAIS_TOTAL,
            DIVIDA_PAIS_PAGO, "2028-08", "Em andamento"
        ])


# ─── HELPERS DE DATA / PARCELAMENTO ──────────────────────────────────────────

def _somar_meses(data_obj: datetime, meses: int) -> datetime:
    """Soma meses preservando o dia quando possível."""
    mes_index = data_obj.month - 1 + meses
    ano = data_obj.year + mes_index // 12
    mes = mes_index % 12 + 1
    dia = min(data_obj.day, calendar.monthrange(ano, mes)[1])
    return data_obj.replace(year=ano, month=mes, day=dia)


def _valores_parcelas(valor_total: float, total_parcelas: int) -> list[float]:
    """Divide em centavos para evitar diferença de arredondamento."""
    total_parcelas = max(int(total_parcelas), 1)
    centavos = int(round(float(valor_total) * 100))
    base = centavos // total_parcelas
    resto = centavos % total_parcelas
    return [round((base + (1 if i < resto else 0)) / 100, 2) for i in range(total_parcelas)]


def _diferenca_meses(mes_inicio: str, mes_ref: str) -> int | None:
    try:
        ano_i, mes_i = [int(x) for x in mes_inicio.split("-")]
        ano_r, mes_r = [int(x) for x in mes_ref.split("-")]
        return (ano_r - ano_i) * 12 + (mes_r - mes_i)
    except Exception:
        return None


# ─── LANÇAMENTOS ──────────────────────────────────────────────────────────────

def salvar_lancamento(
    data, tipo, categoria, subcategoria, descricao, valor, forma_pagto, mes,
    parcela="", transacao_id="", valor_total=None, meta=""
):
    try:
        ws = get_sheet().worksheet("Lançamentos")
        _garantir_cabecalhos(ws, ABAS["Lançamentos"])
        ws.append_row([
            data, tipo, categoria, subcategoria, descricao,
            float(valor), forma_pagto, mes, parcela, transacao_id,
            float(valor_total if valor_total is not None else valor), meta,
        ])
        return True
    except Exception as e:
        logger.error("Erro ao salvar lançamento: %s", e)
        return False


def salvar_lancamento_parcelado(
    data, tipo, categoria, subcategoria, descricao, valor_total, forma_pagto,
    mes_inicio, total_parcelas, transacao_id="", meta=""
):
    """
    Salva uma linha por parcela na aba Lançamentos.
    Ex.: R$ 500 em 10x → dez lançamentos de R$ 50, um em cada mês.
    """
    try:
        ws = get_sheet().worksheet("Lançamentos")
        _garantir_cabecalhos(ws, ABAS["Lançamentos"])

        data_obj = datetime.strptime(data, "%d/%m/%Y")
        valores = _valores_parcelas(float(valor_total), int(total_parcelas))
        rows = []

        for idx, valor_parcela in enumerate(valores, start=1):
            data_parcela = _somar_meses(data_obj, idx - 1)
            mes_parcela = data_parcela.strftime("%Y-%m")
            rows.append([
                data_parcela.strftime("%d/%m/%Y"), tipo, categoria, subcategoria,
                descricao, float(valor_parcela), forma_pagto, mes_parcela,
                f"{idx}/{total_parcelas}", transacao_id, float(valor_total),
                meta if idx == 1 else "",
            ])

        ws.append_rows(rows, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        logger.error("Erro ao salvar lançamento parcelado: %s", e)
        return False


def buscar_lancamentos_mes(mes_ano: str):
    try:
        ws = get_sheet().worksheet("Lançamentos")
        return [
            r for r in ws.get_all_records()
            if str(r.get("Mês", "")) == mes_ano
        ]
    except Exception as e:
        logger.error("Erro: %s", e)
        return []


def buscar_todos_lancamentos():
    try:
        return get_sheet().worksheet("Lançamentos").get_all_records()
    except Exception as e:
        logger.error("Erro: %s", e)
        return []


def buscar_lancamentos_categoria(categoria: str, mes_ano: str = None):
    todos = buscar_lancamentos_mes(mes_ano) if mes_ano else buscar_todos_lancamentos()
    return [r for r in todos if r.get("Categoria", "") == categoria]


def excluir_transacao(transacao_id: str) -> dict:
    """Exclui lançamento(s) por ID e desfaz impactos diretos em metas."""
    tid = str(transacao_id or "").strip().upper()
    resultado = {
        "ok": False,
        "id": tid,
        "lancamentos_excluidos": 0,
        "parcelas_excluidas": 0,
        "descricao": "",
        "metas_revertidas": [],
    }

    if not tid:
        return resultado

    try:
        sh = get_sheet()
        ws_l = sh.worksheet("Lançamentos")
        _garantir_cabecalhos(ws_l, ABAS["Lançamentos"])
        regs_l = ws_l.get_all_records()

        linhas_l = []
        ajustes_meta = defaultdict(float)
        for row_idx, r in enumerate(regs_l, start=2):
            if str(r.get("ID", "")).strip().upper() != tid:
                continue
            linhas_l.append(row_idx)
            if not resultado["descricao"]:
                resultado["descricao"] = str(r.get("Descrição", ""))
            meta = str(r.get("Meta", "")).strip().lower()
            if meta in {"reserva", "pais"}:
                try:
                    ajustes_meta[meta] += float(r.get("Valor", 0) or 0)
                except Exception:
                    pass

        for row_idx in sorted(linhas_l, reverse=True):
            ws_l.delete_rows(row_idx)
        resultado["lancamentos_excluidos"] = len(linhas_l)

        ws_p = sh.worksheet("Parcelas")
        _garantir_cabecalhos(ws_p, ABAS["Parcelas"])
        regs_p = ws_p.get_all_records()
        linhas_p = [
            row_idx for row_idx, r in enumerate(regs_p, start=2)
            if str(r.get("ID", "")).strip().upper() == tid
        ]
        for row_idx in sorted(linhas_p, reverse=True):
            ws_p.delete_rows(row_idx)
        resultado["parcelas_excluidas"] = len(linhas_p)

        if ajustes_meta.get("reserva"):
            atual = buscar_meta_valor("reserva")
            novo = max(0.0, atual - ajustes_meta["reserva"])
            if atualizar_meta("Reserva de emergência", novo):
                resultado["metas_revertidas"].append("reserva")

        if ajustes_meta.get("pais"):
            atual = buscar_meta_valor("pais")
            novo = max(0.0, atual - ajustes_meta["pais"])
            if atualizar_meta("Dívida com os pais", novo):
                resultado["metas_revertidas"].append("pais")

        resultado["ok"] = bool(linhas_l or linhas_p)
        return resultado
    except Exception as e:
        logger.error("Erro ao excluir transação %s: %s", tid, e)
        return resultado


# ─── METAS ────────────────────────────────────────────────────────────────────

def buscar_metas():
    try:
        return get_sheet().worksheet("Metas").get_all_records()
    except Exception as e:
        logger.error("Erro: %s", e)
        return []


def atualizar_meta(nome: str, novo_valor_atual: float):
    try:
        ws = get_sheet().worksheet("Metas")
        registros = ws.get_all_records()
        for i, r in enumerate(registros, start=2):
            if str(r.get("Nome", "")).lower() == nome.lower():
                novo_valor_atual = round(float(novo_valor_atual), 2)
                ws.update_cell(i, 4, novo_valor_atual)
                valor_meta = float(r.get("Valor_Meta", 0) or 0)
                if valor_meta and novo_valor_atual >= valor_meta:
                    ws.update_cell(i, 6, "✅ Atingida!")
                elif str(r.get("Status", "")) == "✅ Atingida!":
                    ws.update_cell(i, 6, "Em andamento")
                return True
        return False
    except Exception as e:
        logger.error("Erro ao atualizar meta: %s", e)
        return False


def buscar_meta_valor(nome: str) -> float:
    metas = buscar_metas()
    for m in metas:
        if nome.lower() in str(m.get("Nome", "")).lower():
            return float(m.get("Valor_Atual", 0) or 0)
    return 0.0


# ─── WISHLIST ─────────────────────────────────────────────────────────────────

def salvar_wishlist(item, valor, prioridade, observacao=""):
    try:
        ws = get_sheet().worksheet("Wishlist")
        _garantir_cabecalhos(ws, ABAS["Wishlist"])
        ws.append_row([
            item, float(valor), prioridade,
            datetime.now().strftime("%d/%m/%Y"), observacao, "Pendente"
        ])
        return True
    except Exception as e:
        logger.error("Erro: %s", e)
        return False


def buscar_wishlist():
    try:
        return get_sheet().worksheet("Wishlist").get_all_records()
    except Exception as e:
        logger.error("Erro: %s", e)
        return []


def marcar_wishlist_comprado(item: str):
    try:
        ws = get_sheet().worksheet("Wishlist")
        registros = ws.get_all_records()
        for i, r in enumerate(registros, start=2):
            if item.lower() in str(r.get("Item", "")).lower():
                ws.update_cell(i, 6, "✅ Comprado")
                return True
        return False
    except Exception as e:
        logger.error("Erro: %s", e)
        return False


# ─── PARCELAS ─────────────────────────────────────────────────────────────────

def salvar_parcela(
    descricao, cartao, valor_parcela, atual, total, encerra_em,
    mes_inicio="", transacao_id="", valor_total=None
):
    try:
        ws = get_sheet().worksheet("Parcelas")
        _garantir_cabecalhos(ws, ABAS["Parcelas"])
        ws.append_row([
            descricao, cartao, float(valor_parcela), atual, total, encerra_em,
            mes_inicio, transacao_id,
            float(valor_total if valor_total is not None else float(valor_parcela) * int(total)),
        ])
        return True
    except Exception as e:
        logger.error("Erro: %s", e)
        return False


def buscar_parcelas():
    try:
        return get_sheet().worksheet("Parcelas").get_all_records()
    except Exception as e:
        logger.error("Erro: %s", e)
        return []


def buscar_parcelas_ativas(mes_ano: str | None = None):
    """Retorna parcelas ativas e calcula a parcela atual pelo mês de referência."""
    mes_ref = mes_ano or datetime.now().strftime("%Y-%m")
    parcelas = buscar_parcelas()
    ativas = []

    for p in parcelas:
        mes_inicio = str(p.get("Mês_Início", "")).strip()
        total = p.get("Total_Parcelas", "")
        try:
            total_i = int(total)
        except Exception:
            ativas.append(p)
            continue

        diff = _diferenca_meses(mes_inicio, mes_ref) if mes_inicio else None
        if diff is None:
            ativas.append(p)
            continue
        if diff < 0 or diff >= total_i:
            continue

        p_atualizada = dict(p)
        p_atualizada["Parcela_Atual"] = diff + 1
        ativas.append(p_atualizada)

    return ativas


# ─── SCORE ────────────────────────────────────────────────────────────────────

def salvar_score(mes, nota, guardou, ficou_limite, pagou_dia, obs=""):
    try:
        ws = get_sheet().worksheet("Score")
        _garantir_cabecalhos(ws, ABAS["Score"])
        registros = ws.get_all_records()
        for i, r in enumerate(registros, start=2):
            if r.get("Mês") == mes:
                ws.delete_rows(i)
                break
        ws.append_row([mes, nota, guardou, ficou_limite, pagou_dia, obs])
        return True
    except Exception as e:
        logger.error("Erro: %s", e)
        return False


def buscar_scores():
    try:
        return get_sheet().worksheet("Score").get_all_records()
    except Exception as e:
        logger.error("Erro: %s", e)
        return []
