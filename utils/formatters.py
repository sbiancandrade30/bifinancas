"""
utils/formatters.py — Formatação e helpers visuais
"""
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


def calcular_encerramento_parcela(n_parcelas: int) -> str:
    hoje = date.today()
    mes = hoje.month + n_parcelas - 1
    ano = hoje.year + (mes - 1) // 12
    mes = ((mes - 1) % 12) + 1
    return f"{mes:02d}/{ano}"


def plano_do_mes(mes_ano: str = None) -> dict:
    mes = mes_ano or mes_atual()
    return PLANO_MENSAL.get(mes, {"guardar": 800, "limite_gastos": 2000})


def dias_para_vencimento(dia_vencimento: int) -> int:
    hoje = datetime.now().day
    if dia_vencimento >= hoje:
        return dia_vencimento - hoje
    return 30 - hoje + dia_vencimento


def score_emoji(nota: float) -> str:
    if nota >= 9:  return "🏆"
    if nota >= 7:  return "⭐"
    if nota >= 5:  return "👍"
    return "💪"
