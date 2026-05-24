"""
handlers/comandos.py — Todos os comandos /saldo, /cartoes, /metas, etc.
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sheets
import ai_interpreter as ai
from config import (
    CARTOES, PLANO_MENSAL, LIMITES_ORCAMENTO, META_RESERVA,
    DIVIDA_PAI_TOTAL, DIVIDA_MAE_TOTAL,
)
from utils.formatters import (fmt_brl, barra, emoji_pagto, emoji_status,
                               mes_atual, plano_do_mes, dias_para_vencimento,
                               score_emoji)

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets.garantir_abas()
    msg = """👋 *Olá, Bianca!* Seu agente financeiro pessoal está pronto. 💚

*📝 Registrar — fale naturalmente:*
_"gastei 45 no mercado no nubank"_
_"almocei fora 32, paguei no pix"_
_"recebi salário 4820"_
_"comprei tênis 480 em 3x no Santander"_
_"quero comprar airfryer 350"_
_"vale a pena comprar TV 2000 em 12x?"_

*🎤 Também aceito áudio e foto de nota fiscal!*

*📋 Comandos:*
/saldo · /ultimos · /cartoes · /parcelas · /orcamento
/metas · /reserva · /pais · /wishlist
/score · /plano · /alertas
/resumo · /relatorio · /ajuda"""
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """📖 *Guia completo*

💰 *Registrar (texto livre):*
• _"gastei 45 no mercado no nubank"_
• _"almocei 32 no pix"_
• _"paguei fatura Santander 1784"_
• _"comprei roupa 280 em 3x caedu"_
• _"recebi salário 4820"_
• _"guardei 200 na reserva"_
• _"paguei 500 pro meu pai"_
• _"paguei 300 pra minha mãe"_

🎤 *Áudio:* mande um áudio falando o gasto
📸 *Foto:* mande foto de nota fiscal ou comprovante

🛍 *Wishlist:*
• _"quero comprar airfryer 350"_
• _"adicionar: notebook 2500, prioridade alta"_

🤔 *Simulador:*
• _"vale a pena comprar TV 2000 em 12x?"_
• _"consigo comprar moto 8000 em 24x?"_

📊 *Consultas:*
/saldo — saldo do mês atual
/ultimos — últimos lançamentos com botão de excluir
/cartoes — faturas e vencimentos
/parcelas — parcelas ativas
/orcamento — gastos vs limites
/metas — todas as metas
/reserva — reserva de emergência
/pais — dívidas com pai e mãe
/wishlist — lista de desejos
/score — nota financeira do mês
/plano — plano jun/26–jan/27
/alertas — o que precisa de atenção
/resumo — análise do mês com IA
/resumo 2026-07 — mês específico
/relatorio — relatório geral completo"""
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mes = mes_atual()
    lst = sheets.buscar_lancamentos_mes(mes)
    gastos   = sum(float(r["Valor"]) for r in lst if r["Tipo"] == "gasto")
    entradas = sum(float(r["Valor"]) for r in lst if r["Tipo"] == "entrada")
    saldo    = entradas - gastos
    plano    = plano_do_mes(mes)
    meta_g   = plano["guardar"]
    limite_g = plano["limite_gastos"]
    pct_g    = gastos / limite_g * 100 if limite_g else 0

    msg = (f"💰 *Saldo — {mes}*\n\n"
           f"➕ Entradas: *{fmt_brl(entradas)}*\n"
           f"➖ Gastos:   *{fmt_brl(gastos)}*\n"
           f"{'✅' if saldo >= meta_g else '⚠️'} Saldo:    *{fmt_brl(saldo)}*\n\n"
           f"{emoji_status(pct_g)} Gastos: {pct_g:.0f}% do limite ({fmt_brl(limite_g)})\n"
           f"🎯 Meta poupança: *{fmt_brl(meta_g)}*\n"
           f"📊 {len(lst)} lançamento(s) registrados")
    teclado = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧾 Ver últimos lançamentos", callback_data="showlast:8")]
    ])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado)


async def cmd_ultimos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ultimos = sheets.buscar_ultimos_lancamentos(8)
    if not ultimos:
        await update.message.reply_text(
            "Nenhum lançamento encontrado ainda."
        )
        return

    for r in ultimos:
        tid = str(r.get("ID", "")).strip().upper()
        tipo = str(r.get("Tipo", ""))
        sinal = "-" if tipo == "gasto" else "+"
        emoji_tipo = "💸" if tipo == "gasto" else "💰"
        descricao = r.get("Descrição", "Lançamento")
        valor = r.get("Valor", 0)
        categoria = r.get("Categoria", "")
        data = r.get("Data", "")
        forma = r.get("Forma_Pagto", "")
        parcela = r.get("Parcela", "")
        parcela_txt = f" · Parcela {parcela}" if parcela else ""

        msg = (
            f"{emoji_tipo} *{descricao}*\n"
            f"{sinal}{fmt_brl(valor)} · {categoria}\n"
            f"{data} · {forma}{parcela_txt}"
        )
        if tid:
            msg += f"\nID: *{tid}*"
            teclado = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 Excluir este lançamento", callback_data=f"delask:{tid}")]
            ])
        else:
            teclado = None
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=teclado)


async def cmd_cartoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mes = mes_atual()
    lst = sheets.buscar_lancamentos_mes(mes)
    linhas = [f"💳 *Faturas — {mes}*\n"]
    for chave, info in CARTOES.items():
        gasto = sum(float(r["Valor"]) for r in lst
                    if r["Tipo"] == "gasto" and
                    str(r.get("Forma_Pagto", "")).lower() == chave)
        dias = dias_para_vencimento(info["vencimento"])
        alerta = "🔴" if dias <= 2 else ("🟡" if dias <= 5 else "🟢")
        linhas.append(
            f"{alerta} *{info['nome']}*\n"
            f"   Gasto este mês: {fmt_brl(gasto)}\n"
            f"   Vence dia {info['vencimento']} ({dias}d restantes)\n"
        )
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def cmd_parcelas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parcelas = sheets.buscar_parcelas_ativas()
    if not parcelas:
        await update.message.reply_text(
            "Nenhuma parcela cadastrada.\n\n"
            "_Ao registrar uma compra parcelada, ela aparece aqui automaticamente._\n"
            "_Ex: 'comprei geladeira 1200 em 10x no Santander'_",
            parse_mode="Markdown"
        )
        return
    total = sum(float(p.get("Valor_Parcela", 0)) for p in parcelas)
    linhas = [f"📦 *Parcelas ativas* — {fmt_brl(total)}/mês\n"]
    for p in parcelas:
        atual = p.get("Parcela_Atual", "?")
        tot   = p.get("Total_Parcelas", "?")
        restam = int(tot) - int(atual) if str(tot).isdigit() and str(atual).isdigit() else "?"
        linhas.append(
            f"• *{p.get('Descrição', '')}*\n"
            f"  {fmt_brl(p.get('Valor_Parcela', 0))}/mês · {atual}/{tot} "
            f"({restam} restantes) · {p.get('Cartão', '')} · até {p.get('Encerra_Em', '?')}\n"
        )
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def cmd_metas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metas = sheets.buscar_metas()
    if not metas:
        await update.message.reply_text(
            "Nenhuma meta. Use /reserva e /pais para ver as metas principais."
        )
        return
    linhas = ["🎯 *Suas metas*\n"]
    for m in metas:
        atual  = float(m.get("Valor_Atual", 0))
        meta_v = float(m.get("Valor_Meta", 1))
        pct    = min(atual / meta_v * 100, 100) if meta_v else 0
        bar    = barra(atual, meta_v)
        status = m.get("Status", "")
        linhas.append(
            f"• *{m.get('Nome', '')}*\n"
            f"  {bar} {pct:.0f}%\n"
            f"  {fmt_brl(atual)} de {fmt_brl(meta_v)} · {status}\n"
        )
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def cmd_reserva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    atual = sheets.buscar_meta_valor("reserva")
    meta  = META_RESERVA
    falta = meta - atual
    pct   = atual / meta * 100
    mes   = mes_atual()
    guardar = plano_do_mes(mes)["guardar"]
    meses_restantes = int(falta / guardar) if guardar > 0 else 99

    msg = (f"🛡 *Reserva de emergência*\n\n"
           f"{barra(atual, meta)} *{pct:.0f}%*\n"
           f"Atual: *{fmt_brl(atual)}*\n"
           f"Meta:  *{fmt_brl(meta)}*\n"
           f"Falta: *{fmt_brl(falta)}*\n\n"
           f"📅 Guardando {fmt_brl(guardar)}/mês → meta em ~{meses_restantes} meses\n"
           f"🏦 *Onde guardar:* Nubank Caixinhas (100% CDI, liquidez diária)\n\n"
           f"_Para atualizar: 'guardei 200 na reserva'_")
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_pais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pago_pai = sheets.buscar_meta_valor("dívida com o pai")
    pago_mae = sheets.buscar_meta_valor("dívida com a mãe")

    falta_pai = max(DIVIDA_PAI_TOTAL - pago_pai, 0)
    falta_mae = max(DIVIDA_MAE_TOTAL - pago_mae, 0)
    pct_pai = pago_pai / DIVIDA_PAI_TOTAL * 100 if DIVIDA_PAI_TOTAL else 0
    pct_mae = pago_mae / DIVIDA_MAE_TOTAL * 100 if DIVIDA_MAE_TOTAL else 0

    total_geral = DIVIDA_PAI_TOTAL + DIVIDA_MAE_TOTAL
    pago_geral = pago_pai + pago_mae
    falta_geral = falta_pai + falta_mae

    msg = (
        "👨‍👩‍👧 *Dívidas familiares*\n\n"
        f"👨 *Pai*\n"
        f"{barra(pago_pai, DIVIDA_PAI_TOTAL)} *{pct_pai:.0f}% pago*\n"
        f"Pago:  *{fmt_brl(pago_pai)}*\n"
        f"Total: *{fmt_brl(DIVIDA_PAI_TOTAL)}*\n"
        f"Falta: *{fmt_brl(falta_pai)}*\n\n"
        f"👩 *Mãe*\n"
        f"{barra(pago_mae, DIVIDA_MAE_TOTAL)} *{pct_mae:.0f}% pago*\n"
        f"Pago:  *{fmt_brl(pago_mae)}*\n"
        f"Total: *{fmt_brl(DIVIDA_MAE_TOTAL)}*\n"
        f"Falta: *{fmt_brl(falta_mae)}*\n\n"
        f"📌 *Prioridade atual:* quitar a dívida com o pai primeiro\n"
        f"🧾 Total familiar: *{fmt_brl(pago_geral)}* de *{fmt_brl(total_geral)}* · falta *{fmt_brl(falta_geral)}*\n\n"
        f"_Para registrar: 'paguei 500 pro meu pai'_\n"
        f"_Depois: 'paguei 300 pra minha mãe'_")
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_orcamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mes = mes_atual()
    lst = sheets.buscar_lancamentos_mes(mes)
    gastos_cat = {}
    for r in lst:
        if r["Tipo"] == "gasto":
            cat = r.get("Categoria", "Outros")
            gastos_cat[cat] = gastos_cat.get(cat, 0) + float(r.get("Valor", 0))

    linhas = [f"📊 *Orçamento por categoria — {mes}*\n"]
    for cat, limite in LIMITES_ORCAMENTO.items():
        gasto = gastos_cat.get(cat, 0)
        pct   = gasto / limite * 100 if limite else 0
        bar   = barra(gasto, limite, 8)
        linhas.append(
            f"{emoji_status(pct)} *{cat}*\n"
            f"   {bar} {fmt_brl(gasto)}/{fmt_brl(limite)}\n"
        )
    outras = sum(v for k, v in gastos_cat.items() if k not in LIMITES_ORCAMENTO)
    if outras > 0:
        linhas.append(f"⚪ *Outras:* {fmt_brl(outras)}")
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def cmd_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = sheets.buscar_wishlist()
    pendentes = [i for i in items if i.get("Status", "") == "Pendente"]
    if not pendentes:
        msg = ("⭐ *Wishlist vazia*\n\n"
               "_Para adicionar:_\n"
               "_'quero comprar airfryer 350'_\n"
               "_'adicionar wishlist: tênis Nike 500, prioridade alta'_")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    total = sum(float(i.get("Valor_Est", 0)) for i in pendentes)
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    pendentes.sort(key=lambda x: ordem.get(str(x.get("Prioridade", "baixa")).lower(), 2))
    emojis = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}
    linhas = [f"⭐ *Wishlist* — {len(pendentes)} itens · {fmt_brl(total)}\n"]
    for i in pendentes:
        pri = str(i.get("Prioridade", "media")).lower()
        linhas.append(
            f"{emojis.get(pri, '⚪')} *{i.get('Item', '')}*\n"
            f"   {fmt_brl(i.get('Valor_Est', 0))} · prioridade {pri} · {i.get('Data_Adição', '')}\n"
        )
    linhas.append("_Para marcar como comprado: 'comprei o [item]'_")
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def cmd_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mes  = mes_atual()
    lst  = sheets.buscar_lancamentos_mes(mes)
    plano = plano_do_mes(mes)
    s = ai.calcular_score(lst, mes, plano["guardar"], plano["limite_gastos"])

    nota   = s["nota"]
    emoji  = score_emoji(nota)
    bar    = barra(nota, 10)

    msg = (f"🏅 *Score financeiro — {mes}*\n\n"
           f"{bar} *{nota}/10* {emoji}\n\n"
           f"{'✅' if s['guardou_meta'] else '❌'} Guardou a meta de poupança\n"
           f"{'✅' if s['ficou_limite'] else '❌'} Ficou dentro do limite de gastos\n\n"
           f"➕ Entradas: {fmt_brl(s['entradas'])}\n"
           f"➖ Gastos:   {fmt_brl(s['gastos'])}\n"
           f"💰 Saldo:    {fmt_brl(s['saldo'])}\n\n"
           f"_Score histórico em /relatorio_")
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    linhas = ["📅 *Plano financeiro jun/26 – jan/27*\n"]
    for mes, d in PLANO_MENSAL.items():
        linhas.append(
            f"*{mes}* — guardar {fmt_brl(d['guardar'])} · "
            f"limite {fmt_brl(d['limite_gastos'])}\n"
        )
    linhas += [
        "\n🎯 *Marcos importantes:*",
        "• Jun/26 — último seguro da moto",
        "• Out/26 — começar pagar a dívida com o pai R$ 500/mês",
        "• Nov/26 — último seguro do carro",
        "• Jan/27 — acelerar a quitação do pai; depois iniciar a dívida com a mãe",
    ]
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mes   = mes_atual()
    lst   = sheets.buscar_lancamentos_mes(mes)
    hoje  = datetime.now().day
    gastos = sum(float(r["Valor"]) for r in lst if r["Tipo"] == "gasto")
    plano  = plano_do_mes(mes)
    limite = plano["limite_gastos"]
    alertas = []

    for chave, info in CARTOES.items():
        dias = dias_para_vencimento(info["vencimento"])
        if dias <= 2:
            alertas.append(f"🔴 *{info['nome']}* vence em {dias}d (dia {info['vencimento']})")
        elif dias <= 5:
            alertas.append(f"🟡 *{info['nome']}* vence em {dias}d (dia {info['vencimento']})")

    pct_gastos = gastos / limite * 100 if limite else 0
    if pct_gastos >= 95:
        alertas.append(f"🔴 Gastos em {pct_gastos:.0f}% do limite! ({fmt_brl(gastos)}/{fmt_brl(limite)})")
    elif pct_gastos >= 75:
        alertas.append(f"🟡 Gastos em {pct_gastos:.0f}% do limite ({fmt_brl(gastos)}/{fmt_brl(limite)})")

    tem_poupanca = any(
        any(k in str(r.get("Descrição", "")).lower() for k in ["reserva", "poupei", "guardei"])
        for r in lst if r["Tipo"] == "entrada"
    )
    if not tem_poupanca and hoje > 10:
        alertas.append(f"💡 Você ainda não guardou este mês (meta: {fmt_brl(plano['guardar'])})")

    if not alertas:
        await update.message.reply_text("✅ *Nenhum alerta no momento.* Tudo em ordem!", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ *Alertas ativos*\n\n" + "\n".join(alertas), parse_mode="Markdown")


async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mes = context.args[0] if context.args else mes_atual()
    await update.message.reply_text(f"⏳ Gerando resumo de {mes}...")
    lst = sheets.buscar_lancamentos_mes(mes)
    if not lst:
        await update.message.reply_text(f"Nenhum lançamento em {mes} ainda. 📭")
        return
    plano = plano_do_mes(mes)
    resumo = ai.gerar_resumo_mes(lst, mes, plano["guardar"], plano["limite_gastos"])
    await update.message.reply_text(resumo, parse_mode="Markdown")


async def cmd_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Gerando relatório completo...")
    todos = sheets.buscar_todos_lancamentos()
    if not todos:
        await update.message.reply_text("Nenhum lançamento ainda. 📭")
        return
    relatorio = ai.gerar_relatorio_completo(todos)
    await update.message.reply_text(relatorio, parse_mode="Markdown")


async def _cmd_simulador_interno(update, context, descricao, valor_total, parcelas):
    await update.message.reply_text(f"🔢 Simulando {descricao}...")
    mes = mes_atual()
    lst = sheets.buscar_lancamentos_mes(mes)
    plano = plano_do_mes(mes)
    resultado = ai.simular_compra(descricao, valor_total, parcelas, lst, plano)
    await update.message.reply_text(resultado, parse_mode="Markdown")
