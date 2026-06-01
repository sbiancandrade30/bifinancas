"""
handlers/lancamentos.py — Registro de gastos e entradas
Suporta: texto, foto de nota fiscal, áudio
"""

import logging
import random
import re
import string
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import ai_interpreter as ai
import parser_local
import sheets
from config import CARTOES, FORMAS_PAGTO
from utils.formatters import (
    fmt_brl,
    emoji_pagto,
    calcular_encerramento_parcela,
    mes_atual,
)

logger = logging.getLogger(__name__)


def _normalizar_txt(valor: str) -> str:
    """Normaliza texto para comparar cartão/forma de pagamento."""
    return (
        str(valor or "")
        .lower()
        .strip()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace(".", "")
    )


def _proximo_mes(mes_ano: str) -> str:
    ano, mes = map(int, mes_ano.split("-"))

    if mes == 12:
        return f"{ano + 1}-01"

    return f"{ano}-{mes + 1:02d}"


def _identificar_cartao_por_forma(forma_pagto: str):
    """
    Identifica se a forma de pagamento é um cartão cadastrado no config.py.
    Aceita chave, nome, final e aliases.
    """
    forma_norm = _normalizar_txt(forma_pagto)

    for chave, dados in CARTOES.items():
        nomes = [
            chave,
            dados.get("nome", ""),
            dados.get("final", ""),
            *dados.get("aliases", []),
        ]

        for nome in nomes:
            nome_norm = _normalizar_txt(nome)
            if nome_norm and nome_norm in forma_norm:
                return dados

    return None


def calcular_mes_fatura(data_str: str, forma_pagto: str, mes_compra: str) -> str:
    """
    Calcula o mês da fatura.

    Regra:
    - Se não for cartão: Mês_Fatura = Mês da compra
    - Se for cartão e passou do fechamento: Mês_Fatura = próximo mês
    - Se for cartão e ainda não passou do fechamento: Mês_Fatura = mês da compra
    """
    cartao = _identificar_cartao_por_forma(forma_pagto)

    if not cartao:
        return mes_compra

    fechamento = cartao.get("fechamento")

    if not fechamento:
        return mes_compra

    try:
        data_obj = datetime.strptime(data_str, "%d/%m/%Y")
        fechamento = int(fechamento)
    except Exception:
        return mes_compra

    if data_obj.day > fechamento:
        return _proximo_mes(mes_compra)

    return mes_compra


BOTOES_PAGTO = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("💜 Nubank", callback_data="pagto:nubank"),
        InlineKeyboardButton("💳 Santander", callback_data="pagto:santander"),
    ],
    [
        InlineKeyboardButton("💛 Mercado Pago", callback_data="pagto:mercadopago"),
        InlineKeyboardButton("🟢 Caedu", callback_data="pagto:caedu"),
    ],
    [
        InlineKeyboardButton("💛 Banco do Brasil", callback_data="pagto:bb"),
        InlineKeyboardButton("💳 Débito", callback_data="pagto:debito"),
    ],
    [
        InlineKeyboardButton("⚡ Pix", callback_data="pagto:pix"),
        InlineKeyboardButton("💵 Dinheiro", callback_data="pagto:dinheiro"),
    ],
])


def teclado_excluir(transacao_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Excluir lançamento", callback_data=f"delask:{transacao_id}")],
    ])


def teclado_confirmar_exclusao(transacao_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Sim, excluir", callback_data=f"delyes:{transacao_id}"),
            InlineKeyboardButton("↩️ Cancelar", callback_data=f"delno:{transacao_id}"),
        ]
    ])


async def processar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    # Exclusão por identificador, antes de passar por IA/parser.
    match_exclusao = re.match(
        r"^\s*(?:excluir|apagar|remover)\s+(?:a\s+)?(?:transa[cç][aã]o|lan[cç]amento)?\s*([A-Z0-9]{5})\s*$",
        texto,
        flags=re.IGNORECASE,
    )

    if match_exclusao:
        await _processar_exclusao(update, match_exclusao.group(1).upper())
        return

    # Lista de mercado: trata localmente antes de chamar IA/Gemini.
    # Isso evita erro de limite da IA em mensagens simples como:
    # "coloca arroz e leite na lista de mercado"
    if _eh_lista_mercado(texto):
        await _processar_lista_mercado(update, context, texto)
        return

    # 1. Classifica a intenção da mensagem
    intencao = ai.classificar_intencao(texto)

    # 2. Se for dúvida clara — responde como assistente
    if intencao == "duvida":
        contexto_mes = _calcular_saldo_mes(mes_atual())
        resposta = ai.responder_duvida(texto, contexto_mes)
        await update.message.reply_text(resposta, parse_mode="Markdown")
        return

    # 3. Se for lançamento ou incerto — tenta registrar
    dados = parser_local.parse(texto)

    # Se não conseguiu, chama Gemini
    if not dados:
        dados = ai.interpretar_texto(texto)

    # Se o Gemini também não conseguiu reconhecer como lançamento
    if not dados:
        contexto_mes = _calcular_saldo_mes(mes_atual())
        resposta = ai.responder_duvida(texto, contexto_mes)
        await update.message.reply_text(resposta, parse_mode="Markdown")
        return

    tipo = dados.get("tipo", "invalido")

    if tipo == "invalido":
        contexto_mes = _calcular_saldo_mes(mes_atual())
        resposta = ai.responder_duvida(texto, contexto_mes)
        await update.message.reply_text(resposta, parse_mode="Markdown")
        return

    if tipo == "wishlist":
        await _processar_wishlist(update, context, dados)
        return

    if tipo == "simulador":
        await _processar_simulador(update, context, dados, texto)
        return

    await _finalizar_lancamento(update, context, dados, texto)


def _eh_lista_mercado(texto: str) -> bool:
    t = (texto or "").lower().strip()
    return (
        "lista de mercado" in t
        or "lista de compras" in t
        or "lista do mercado" in t
        or "na lista" in t
        or "pra lista" in t
        or "para lista" in t
        or "para a lista" in t
    )


def _extrair_itens_lista_mercado(texto: str):
    t = (texto or "").strip()

    # Remove comandos comuns
    t = re.sub(r"(?i)\b(coloca|coloque|adiciona|adicione|inclui|inclua|bota|botar)\b", "", t)
    t = re.sub(r"(?i)\b(na|no|para a|pra|para)\s+(minha\s+)?lista\s+(de mercado|de compras|do mercado)?\b", "", t)
    t = re.sub(r"(?i)\b(lista de mercado|lista de compras|lista do mercado)\b", "", t)
    t = re.sub(r"(?i)\b(na lista|pra lista|para lista|para a lista)\b", "", t)

    # Separa por vírgula, quebra de linha e " e "
    partes = re.split(r",|\n|\s+e\s+", t)

    itens = []
    for parte in partes:
        item = parte.strip(" .;:-").strip()
        if not item:
            continue

        # Tenta separar unidade:
        # "2 leite", "1 detergente", "500g de músculo moído",
        # "1kg arroz", "500 ml detergente"
        m = re.match(
            r"^(\d+(?:[,.]\d+)?\s*(?:g|kg|ml|l|un|unid|unidade|unidades)?)\s+(.+)$",
            item,
            flags=re.IGNORECASE,
        )

        if m:
            unidades = m.group(1).replace(",", ".").strip()
            nome = m.group(2).strip()

            # Remove "de/da/do" depois da unidade:
            # "500g de músculo moído" -> "músculo moído"
            nome = re.sub(r"(?i)^(de|da|do|dos|das)\s+", "", nome).strip()
        else:
            unidades = ""
            nome = item

        if nome:
            itens.append({
                "item": nome,
                "unidades": unidades,
                "observacao": "",
            })

    return itens


async def _processar_lista_mercado(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    itens = _extrair_itens_lista_mercado(texto)

    if not itens:
        await update.message.reply_text(
            "🛒 Entendi que é lista de mercado, mas não consegui identificar os itens."
        )
        return

    salvos = []
    erros = []

    for dado in itens:
        ok = sheets.salvar_item_lista_mercado(
            dado["item"],
            unidades=dado["unidades"],
            observacao=dado["observacao"],
        )
        if ok:
            if dado["unidades"]:
                salvos.append(f"• {dado['item'].title()} ({dado['unidades']})")
            else:
                salvos.append(f"• {dado['item'].title()}")
        else:
            erros.append(dado["item"])

    if salvos:
        msg = "🛒 *Adicionado à lista de mercado:*\n" + "\n".join(salvos)
    else:
        msg = "⚠️ Não consegui salvar os itens na lista de mercado."

    if erros:
        msg += "\n\n⚠️ Não consegui salvar:\n" + "\n".join(f"• {e}" for e in erros)

    await update.message.reply_text(msg, parse_mode="Markdown")

async def processar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa foto de nota fiscal, comprovante de pix, fatura de cartão.
    Extrai valor, estabelecimento, data e itens automaticamente.
    """
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    await update.message.reply_text(
        "📸 Lendo a imagem... pode levar alguns segundos."
    )

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = bytes(await file.download_as_bytearray())

    legenda = update.message.caption or ""

    dados = ai.interpretar_imagem(image_bytes)

    if not dados:
        await update.message.reply_text(
            "❌ Não consegui ler a imagem.\n\n"
            "Dicas para funcionar melhor:\n"
            "• Foto nítida e bem iluminada\n"
            "• Cupom fiscal completo na imagem\n"
            "• Ou descreva o gasto em texto mesmo 😊"
        )
        return

    tipo_img = dados.get("tipo_imagem", "")
    valor = float(dados.get("valor", 0))
    descricao = dados.get("descricao", "")
    categoria = dados.get("categoria", "Outros")
    data_str = dados.get("data", datetime.now().strftime("%d/%m/%Y"))
    forma = dados.get("forma_pagto", "perguntar")
    itens = dados.get("itens", [])

    icone_tipo = {
        "nota_fiscal": "🧾",
        "comprovante_pix": "⚡",
        "extrato": "📋",
        "fatura": "💳",
    }.get(tipo_img, "📸")

    itens_str = ""
    if itens:
        itens_str = "\n\n*Itens identificados:*\n" + "\n".join(f"  • {i}" for i in itens[:8])
        if len(itens) > 8:
            itens_str += f"\n  _... e mais {len(itens) - 8} itens_"

    legenda_str = f"\n📝 _Contexto: {legenda}_" if legenda else ""

    preview = (
        f"{icone_tipo} *Imagem lida com sucesso!*\n\n"
        f"💰 Valor: *{fmt_brl(valor)}*\n"
        f"🏪 Local: _{descricao}_\n"
        f"📁 Categoria: _{categoria}_\n"
        f"📅 Data: _{data_str}_"
        f"{legenda_str}"
        f"{itens_str}\n\n"
        f"_Salvando..._"
    )

    await update.message.reply_text(preview, parse_mode="Markdown")

    if legenda and not dados.get("forma_pagto"):
        dados_legenda = ai.interpretar_texto(legenda)
        if dados_legenda and dados_legenda.get("forma_pagto"):
            forma = dados_legenda.get("forma_pagto", forma)

    dados["forma_pagto"] = forma
    dados["descricao"] = descricao or legenda[:50] or "Nota fiscal"
    dados["eh_reserva"] = False
    dados["eh_pais"] = False
    dados["subcategoria"] = dados.get("subcategoria", "")

    await _finalizar_lancamento(update, context, dados, legenda or "foto")


async def processar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagem de voz."""
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    await update.message.reply_text("🎤 Ouvindo...")

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    audio_bytes = await file.download_as_bytearray()

    transcricao = ai.transcrever_audio(bytes(audio_bytes))

    if not transcricao:
        await update.message.reply_text(
            "❌ Não consegui entender o áudio. Tente digitar o lançamento."
        )
        return

    await update.message.reply_text(f"🎤 _\"{transcricao}\"_", parse_mode="Markdown")

    dados = ai.interpretar_audio_transcrito(transcricao)

    if not dados:
        await update.message.reply_text("❌ Não entendi o que foi dito.")
        return

    await _finalizar_lancamento(update, context, dados, transcricao)


async def _finalizar_lancamento(update, context, dados, texto_original):
    """Salva o lançamento ou pergunta a forma de pagamento."""
    tipo = dados.get("tipo", "gasto")
    valor = float(dados.get("valor", 0))
    categoria = dados.get("categoria", "Outros")
    subcategoria = dados.get("subcategoria", "")
    descricao = dados.get("descricao", texto_original[:50])
    forma = dados.get("forma_pagto", "perguntar")
    parcelas = int(dados.get("parcelas", 1))
    eh_reserva = dados.get("eh_reserva", False)
    eh_pais = dados.get("eh_pais", False)
    eh_pai = dados.get("eh_pai", False)
    eh_mae = dados.get("eh_mae", False)

    # Processar data
    data_str = dados.get("data", datetime.now().strftime("%d/%m/%Y"))

    try:
        data_obj = datetime.strptime(data_str, "%d/%m/%Y")
        mes_ano = data_obj.strftime("%Y-%m")
    except Exception:
        data_obj = datetime.now()
        mes_ano = data_obj.strftime("%Y-%m")
        data_str = data_obj.strftime("%d/%m/%Y")

    parcela_info = f"1/{parcelas}" if parcelas > 1 else ""

    # Se forma não foi detectada, pergunta com botões
    if forma == "perguntar" and tipo == "gasto":
        context.user_data["pendente"] = {
            "data_str": data_str,
            "tipo": tipo,
            "categoria": categoria,
            "subcategoria": subcategoria,
            "descricao": descricao,
            "valor": valor,
            "mes_ano": mes_ano,
            "parcelas": parcelas,
            "parcela_info": parcela_info,
            "eh_reserva": eh_reserva,
            "eh_pais": eh_pais,
            "eh_pai": eh_pai,
            "eh_mae": eh_mae,
            "confirmacao": dados.get("confirmacao", f"Anotado! {fmt_brl(valor)}"),
        }

        if parcelas > 1:
            valor_parcela = valor / parcelas
            texto_pagto = (
                f"*{fmt_brl(valor)}* em _{descricao}_\n"
                f"📦 {parcelas}x de *{fmt_brl(valor_parcela)}*\n\n"
                "Como você pagou?"
            )
        else:
            texto_pagto = f"*{fmt_brl(valor)}* em _{descricao}_\n\nComo você pagou?"

        await update.message.reply_text(
            texto_pagto,
            parse_mode="Markdown",
            reply_markup=BOTOES_PAGTO,
        )
        return

    await _salvar_e_confirmar(update, context, {
        "data_str": data_str,
        "tipo": tipo,
        "categoria": categoria,
        "subcategoria": subcategoria,
        "descricao": descricao,
        "valor": valor,
        "forma": forma,
        "mes_ano": mes_ano,
        "parcelas": parcelas,
        "parcela_info": parcela_info,
        "eh_reserva": eh_reserva,
        "eh_pais": eh_pais,
        "eh_pai": eh_pai,
        "eh_mae": eh_mae,
        "confirmacao": dados.get("confirmacao", f"Anotado! {fmt_brl(valor)}"),
    })


def _gerar_id() -> str:
    """Gera um identificador curto único para cada transação."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=5))


def _calcular_saldo_mes(mes_ano: str) -> dict:
    """Calcula saldo atualizado do mês após salvar."""
    lst = sheets.buscar_lancamentos_mes(mes_ano)

    gastos = sum(float(r["Valor"]) for r in lst if r["Tipo"] == "gasto")
    entradas = sum(float(r["Valor"]) for r in lst if r["Tipo"] == "entrada")
    saldo = entradas - gastos

    return {
        "gastos": gastos,
        "entradas": entradas,
        "saldo": saldo,
        "n": len(lst),
    }


async def _salvar_e_confirmar(update_or_query, context, d, edit=False):
    """Salva na planilha e envia confirmação no estilo GranaZen."""
    tid = _gerar_id()

    parcelas = max(int(d.get("parcelas", 1) or 1), 1)
    valor_total = float(d["valor"])
    eh_parcelado = d["tipo"] == "gasto" and parcelas > 1
    valor_mes = round(valor_total / parcelas, 2) if eh_parcelado else valor_total

    if d.get("eh_reserva"):
        meta = "reserva"
    elif d.get("eh_mae"):
        meta = "mae"
    elif d.get("eh_pai") or d.get("eh_pais"):
        meta = "pai"
    else:
        meta = ""

    mes_fatura = calcular_mes_fatura(
        d["data_str"],
        d["forma"],
        d["mes_ano"],
    )

    if eh_parcelado:
        ok = sheets.salvar_lancamento_parcelado(
            d["data_str"],
            d["tipo"],
            d["categoria"],
            d["subcategoria"],
            d["descricao"],
            valor_total,
            d["forma"],
            mes_fatura,
            parcelas,
            transacao_id=tid,
            meta=meta,
        )
    else:
        ok = sheets.salvar_lancamento(
            data=d["data_str"],
            tipo=d["tipo"],
            categoria=d["categoria"],
            subcategoria=d["subcategoria"],
            descricao=d["descricao"],
            valor=valor_mes,
            forma_pagto=d["forma"],
            mes=d["mes_ano"],
            parcela=d["parcela_info"],
            transacao_id=tid,
            valor_total=valor_total,
            meta=meta,
            mes_fatura=mes_fatura,
        )

    if ok:
        # Atualiza metas automaticamente apenas depois de confirmar que o lançamento foi salvo.
        if d["tipo"] == "entrada" and d.get("eh_reserva"):
            atual = sheets.buscar_meta_valor("reserva")
            sheets.atualizar_meta("Reserva de emergência", atual + valor_mes)

        if d["tipo"] == "gasto" and (
            d.get("eh_pai") or (d.get("eh_pais") and not d.get("eh_mae"))
        ):
            atual = sheets.buscar_meta_valor("dívida com o pai")
            sheets.atualizar_meta("Dívida com o pai", atual + valor_mes)

        if d["tipo"] == "gasto" and d.get("eh_mae"):
            atual = sheets.buscar_meta_valor("dívida com a mãe")
            sheets.atualizar_meta("Dívida com a mãe", atual + valor_mes)

        # Salva a compra parcelada em aba própria para acompanhamento de parcelas ativas.
        if eh_parcelado:
            encerra = calcular_encerramento_parcela(parcelas, d["data_str"])
            sheets.salvar_parcela(
                d["descricao"],
                d["forma"],
                valor_mes,
                1,
                parcelas,
                encerra,
                mes_inicio=mes_fatura,
                transacao_id=tid,
                valor_total=valor_total,
            )

    # Busca saldo atualizado do mês corrente da transação.
    saldo_info = _calcular_saldo_mes(d["mes_ano"])

    tipo_emoji = "🟥 Despesa" if d["tipo"] == "gasto" else "🟩 Receita"
    pagto_label = emoji_pagto(d["forma"]) if d["forma"] != "perguntar" else "💳 Cartão"
    saldo_emoji = "✅" if saldo_info["saldo"] >= 0 else "⚠️"

    extras = []

    if eh_parcelado:
        extras.append(f"📦 *Parcelas:* {parcelas}x de {fmt_brl(valor_mes)}")
        extras.append("🗓 *Impacto mensal:* as parcelas futuras já foram distribuídas nos próximos meses")

    if d.get("eh_reserva"):
        extras.append("🛡 *Reserva de emergência atualizada!*")

    if d.get("eh_mae"):
        extras.append("👩 *Dívida com a mãe atualizada!*")
    elif d.get("eh_pai") or d.get("eh_pais"):
        extras.append("👨 *Dívida com o pai atualizada!*")

    if d["tipo"] == "gasto" and _identificar_cartao_por_forma(d["forma"]):
        extras.append(f"💳 *Fatura:* {mes_fatura}")

    extras_str = ("\n" + "\n".join(extras)) if extras else ""

    if eh_parcelado:
        bloco_valor = (
            f"💸 *Valor total:* {fmt_brl(valor_total)}\n"
            f"📅 *Lançado neste mês:* {fmt_brl(valor_mes)}\n"
        )
    else:
        bloco_valor = f"💸 *Valor:* {fmt_brl(valor_mes)}\n"

    msg = (
        f"✅ *Transação registrada com sucesso!*\n"
        f"Identificador: *{tid}*\n\n"
        f"📋 *Resumo da transação:*\n"
        f"{'—' * 20}\n"
        f"✏️ *Descrição:* {d['descricao']}\n"
        f"{bloco_valor}"
        f"🔵 *Tipo:* {tipo_emoji}\n"
        f"🏷 *Categoria:* {d['categoria']}"
        + (f" › {d['subcategoria']}" if d.get("subcategoria") else "") + "\n"
        f"{pagto_label}\n"
        f"📅 *Data:* {d['data_str']}\n"
        f"✔️ *Pago:* ✅"
        f"{extras_str}\n\n"
        f"{'—' * 20}\n"
        f"{saldo_emoji} *Saldo atual:* {fmt_brl(saldo_info['saldo'])}\n"
        f"_Entradas: {fmt_brl(saldo_info['entradas'])} · Gastos: {fmt_brl(saldo_info['gastos'])}_"
    )

    if not ok:
        msg = (
            "⚠️ *Não consegui salvar essa transação na planilha.*\n\n"
            "Tente enviar de novo. Se acontecer novamente, me avise para eu revisar a integração."
        )

    reply_markup = teclado_excluir(tid) if ok else None

    if edit and hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(
            msg,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    else:
        await update_or_query.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


async def _processar_exclusao(update: Update, transacao_id: str):
    resultado = sheets.excluir_transacao(transacao_id)

    if not resultado.get("ok"):
        await update.message.reply_text(
            f"Não encontrei uma transação com o identificador *{transacao_id}*.",
            parse_mode="Markdown",
        )
        return

    detalhes = []
    lancamentos = resultado.get("lancamentos_excluidos", 0)
    parcelas = resultado.get("parcelas_excluidas", 0)

    if lancamentos:
        detalhes.append(f"{lancamentos} lançamento(s) removido(s)")

    if parcelas:
        detalhes.append("controle de parcelas removido")

    if resultado.get("metas_revertidas"):
        detalhes.append("meta atualizada de volta")

    detalhe_txt = " · ".join(detalhes)
    descricao = resultado.get("descricao") or "transação"

    await update.message.reply_text(
        f"✅ Excluí *{descricao}* ({transacao_id}).\n_{detalhe_txt}_",
        parse_mode="Markdown",
    )


async def callback_atalhos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callbacks simples de navegação, como mostrar últimos lançamentos."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    if not data.startswith("showlast:"):
        return

    try:
        limite = int(data.split(":", 1)[1])
    except Exception:
        limite = 8

    ultimos = sheets.buscar_ultimos_lancamentos(limite)

    if not ultimos:
        await query.message.reply_text("Nenhum lançamento encontrado ainda.")
        return

    for r in ultimos:
        tid = str(r.get("ID", "")).strip().upper()
        tipo = str(r.get("Tipo", ""))
        sinal = "-" if tipo == "gasto" else "+"
        emoji_tipo = "💸" if tipo == "gasto" else "💰"
        descricao = r.get("Descrição", "Lançamento")
        valor = r.get("Valor", 0)
        categoria = r.get("Categoria", "")
        data_reg = r.get("Data", "")
        forma = r.get("Forma_Pagto", "")
        parcela = r.get("Parcela", "")
        parcela_txt = f" · Parcela {parcela}" if parcela else ""

        msg = (
            f"{emoji_tipo} *{descricao}*\n"
            f"{sinal}{fmt_brl(valor)} · {categoria}\n"
            f"{data_reg} · {forma}{parcela_txt}"
        )

        teclado = None

        if tid:
            msg += f"\nID: *{tid}*"
            teclado = teclado_excluir(tid)

        await query.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=teclado,
        )


async def callback_exclusao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback dos botões de exclusão com confirmação."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    if data.startswith("delask:"):
        transacao_id = data.split(":", 1)[1].upper()

        await query.edit_message_text(
            f"⚠️ *Confirmar exclusão*\n\n"
            f"Deseja excluir a transação *{transacao_id}*?\n\n"
            f"Se ela tiver parcelas futuras ou meta vinculada, o bot vai remover tudo e reverter a meta automaticamente.",
            parse_mode="Markdown",
            reply_markup=teclado_confirmar_exclusao(transacao_id),
        )
        return

    if data.startswith("delno:"):
        await query.edit_message_text("↩️ Exclusão cancelada.")
        return

    if data.startswith("delyes:"):
        transacao_id = data.split(":", 1)[1].upper()
        resultado = sheets.excluir_transacao(transacao_id)

        if not resultado.get("ok"):
            await query.edit_message_text(
                f"Não encontrei uma transação com o identificador *{transacao_id}*.",
                parse_mode="Markdown",
            )
            return

        detalhes = []
        lancamentos = resultado.get("lancamentos_excluidos", 0)
        parcelas = resultado.get("parcelas_excluidas", 0)

        if lancamentos:
            detalhes.append(f"{lancamentos} lançamento(s) removido(s)")

        if parcelas:
            detalhes.append("controle de parcelas removido")

        if resultado.get("metas_revertidas"):
            detalhes.append("meta atualizada de volta")

        detalhe_txt = " · ".join(detalhes) or "transação removida"
        descricao = resultado.get("descricao") or "transação"

        await query.edit_message_text(
            f"✅ Excluí *{descricao}* ({transacao_id}).\n_{detalhe_txt}_",
            parse_mode="Markdown",
        )
        return


async def callback_pagto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback dos botões de forma de pagamento."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("pagto:"):
        return

    forma = query.data.split(":")[1]
    pendente = context.user_data.get("pendente")

    if not pendente:
        await query.edit_message_text("⚠️ Sessão expirada. Registre novamente.")
        return

    context.user_data.pop("pendente", None)
    pendente["forma"] = forma

    await _salvar_e_confirmar(query, context, pendente, edit=True)


async def _processar_wishlist(update, context, dados):
    item = dados.get("wishlist_item") or dados.get("descricao", "Item")
    valor = float(dados.get("valor", 0))
    prioridade = dados.get("wishlist_prioridade", "media")

    ok = sheets.salvar_wishlist(item, valor, prioridade)

    emoji_pri = {
        "alta": "🔴",
        "media": "🟡",
        "baixa": "🟢",
    }.get(prioridade, "⚪")

    if ok:
        msg = (
            f"⭐ *{item}* adicionado à wishlist!\n"
            f"{fmt_brl(valor)} · {emoji_pri} prioridade {prioridade}\n\n"
            f"_/wishlist para ver tudo_"
        )
    else:
        msg = "⚠️ Não consegui salvar na wishlist."

    await update.message.reply_text(msg, parse_mode="Markdown")


async def _processar_simulador(update, context, dados, texto_original):
    from handlers.comandos import _cmd_simulador_interno

    descricao = dados.get("simulador_descricao") or dados.get("descricao", texto_original)
    valor = float(dados.get("simulador_valor_total") or dados.get("valor", 0))
    parcelas = int(dados.get("simulador_parcelas") or dados.get("parcelas", 1))

    await _cmd_simulador_interno(update, context, descricao, valor, parcelas)
