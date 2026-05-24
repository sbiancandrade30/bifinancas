"""
utils/formatters.py — Formatação e helpers visuais
"""
import calendar
from datetime import datetime, date
from config import FORMAS_PAGTO, PLANO_MENSAL


def fmt_brl(valor) -> str:
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"R$ {valor}"


def barra(atual, meta, tamanho=10) -> str:
    if meta <= 0:
        return "░" * tamanho
    pct = min(float(atual) / float(meta), 1.0)
    cheios = int(pct * tamanho)
    return "█" * cheios + "░" * (tamanho - cheios)


def emoji_pagto(forma: str) -> str:
    return FORMAS_PAGTO.get(forma, f"💳 {forma}")


def emoji_status(pct: float) -> str:
    if pct < 70:  return "🟢"
    if pct < 90:  return "🟡"
    return "🔴"


def mes_atual() -> str:
    return datetime.now().strftime("%Y-%m")


def calcular_encerramento_parcela(n_parcelas: int, data_base=None) -> str:
    """Retorna MM/AAAA do último mês da compra parcelada."""
    if isinstance(data_base, str):
        try:
            base = datetime.strptime(data_base, "%d/%m/%Y").date()
        except Exception:
            base = date.today()
    elif isinstance(data_base, datetime):
        base = data_base.date()
    elif isinstance(data_base, date):
        base = data_base
    else:
        base = date.today()

    mes_index = base.month - 1 + max(int(n_parcelas), 1) - 1
    ano = base.year + mes_index // 12
    mes = mes_index % 12 + 1
    return f"{mes:02d}/{ano}"


def plano_do_mes(mes_ano: str = None) -> dict:
    mes = mes_ano or mes_atual()
    return PLANO_MENSAL.get(mes, {"guardar": 800, "limite_gastos": 2000})


def dias_para_vencimento(dia_vencimento: int) -> int:
    """Calcula dias até o próximo vencimento usando o calendário real."""
    hoje = date.today()
    ano = hoje.year
    mes = hoje.month
    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    venc_dia = min(int(dia_vencimento), ultimo_dia_mes)
    venc = date(ano, mes, venc_dia)

    if venc < hoje:
        if mes == 12:
            ano += 1
            mes = 1
        else:
            mes += 1
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        venc_dia = min(int(dia_vencimento), ultimo_dia_mes)
        venc = date(ano, mes, venc_dia)

    return (venc - hoje).days


def score_emoji(nota: float) -> str:
    if nota >= 9:  return "🏆"
    if nota >= 7:  return "⭐"
    if nota >= 5:  return "👍"
    return "💪"
