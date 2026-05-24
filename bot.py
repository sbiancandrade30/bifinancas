"""
bot.py — Ponto de entrada do BiFinanças
"""
import logging
from telegram import Update
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          CallbackQueryHandler, filters, ContextTypes)
from config import TELEGRAM_TOKEN, ALLOWED_USER_ID
import sheets
from handlers.lancamentos import (processar_texto, processar_foto,
                                   processar_audio, callback_pagto, callback_exclusao, callback_atalhos)
from handlers.comandos import (cmd_start, cmd_ajuda, cmd_saldo, cmd_cartoes,
                                cmd_parcelas, cmd_metas, cmd_reserva, cmd_pais,
                                cmd_orcamento, cmd_wishlist, cmd_score,
                                cmd_plano, cmd_alertas, cmd_resumo, cmd_relatorio, cmd_ultimos)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def autorizado(update: Update) -> bool:
    if ALLOWED_USER_ID == 0:
        return True
    return update.effective_user.id == ALLOWED_USER_ID


def proteger(handler):
    """Decorator que bloqueia usuários não autorizados."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not autorizado(update):
            logger.warning(f"Acesso negado: {update.effective_user.id}")
            return
        await handler(update, context)
    return wrapper


async def handle_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    await processar_texto(update, context, update.message.text.strip())


async def handle_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    await processar_foto(update, context)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    await processar_audio(update, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    await callback_pagto(update, context)


async def handle_callback_exclusao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    await callback_exclusao(update, context)


async def handle_callback_atalhos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    await callback_atalhos(update, context)


def main():
    if sheets.garantir_abas():
        logger.info("Planilha verificada e estruturas atualizadas.")
    else:
        logger.warning("Não foi possível verificar a planilha no início; o bot seguirá tentando em uso.")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Comandos
    cmds = [
        ("start",     proteger(cmd_start)),
        ("ajuda",     proteger(cmd_ajuda)),
        ("saldo",     proteger(cmd_saldo)),
        ("ultimos",   proteger(cmd_ultimos)),
        ("cartoes",   proteger(cmd_cartoes)),
        ("parcelas",  proteger(cmd_parcelas)),
        ("metas",     proteger(cmd_metas)),
        ("reserva",   proteger(cmd_reserva)),
        ("pais",      proteger(cmd_pais)),
        ("orcamento", proteger(cmd_orcamento)),
        ("wishlist",  proteger(cmd_wishlist)),
        ("score",     proteger(cmd_score)),
        ("plano",     proteger(cmd_plano)),
        ("alertas",   proteger(cmd_alertas)),
        ("resumo",    proteger(cmd_resumo)),
        ("relatorio", proteger(cmd_relatorio)),
    ]
    for nome, handler in cmds:
        app.add_handler(CommandHandler(nome, handler))

    # Mensagens
    app.add_handler(MessageHandler(filters.PHOTO, handle_foto))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_texto))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^pagto:"))
    app.add_handler(CallbackQueryHandler(handle_callback_exclusao, pattern="^del(ask|yes|no):"))
    app.add_handler(CallbackQueryHandler(handle_callback_atalhos, pattern="^showlast:"))

    logger.info("🚀 BiFinanças iniciado com sucesso!")
    logger.info("Stack: Gemini (grátis) + Northflank (grátis) + Google Sheets (grátis)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
