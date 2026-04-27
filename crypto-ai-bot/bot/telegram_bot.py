"""bot/telegram_bot.py — Telegram бот с полным функционалом"""
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, JobQueue
)
from telegram.constants import ParseMode
from loguru import logger
from config import settings

# Ленивые импорты для скорости старта
from data.market      import market_fetcher
from data.derivatives import derivatives_fetcher
from data.whales      import whale_fetcher
from data.news        import news_fetcher
from ai.gemini        import gemini_analyzer
from engine.signal    import signal_engine
from engine.database  import db
from backtest.engine  import backtest_engine


# ── Главное меню ─────────────────────────────────────────────────
MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎯 Полный AI-сигнал",       callback_data="signal_BTCUSDT")],
    [
        InlineKeyboardButton("📊 BTC",  callback_data="signal_BTCUSDT"),
        InlineKeyboardButton("Ξ ETH",   callback_data="signal_ETHUSDT"),
        InlineKeyboardButton("◎ SOL",   callback_data="signal_SOLUSDT"),
    ],
    [
        InlineKeyboardButton("📰 Новости",    callback_data="news"),
        InlineKeyboardButton("🐋 Киты",       callback_data="whales"),
        InlineKeyboardButton("💸 Фандинг",    callback_data="funding"),
    ],
    [
        InlineKeyboardButton("🔄 Бэктест BTC", callback_data="backtest_BTCUSDT"),
        InlineKeyboardButton("📈 История",     callback_data="history"),
    ],
    [InlineKeyboardButton("⏰ Авто-сигнал",   callback_data="auto_toggle")],
])


# ── Вспомогательные ──────────────────────────────────────────────
async def safe_edit(msg, text: str):
    try:
        await msg.edit_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        try:
            await msg.reply_text(text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"safe_edit: {e}")


async def run_full_analysis(symbol: str) -> str:
    """Запуск полного анализа по символу"""
    logger.info(f"🔄 Анализ {symbol}...")

    results = await asyncio.gather(
        market_fetcher.get_full_market_data(symbol),
        derivatives_fetcher.get_full_derivatives(symbol),
        whale_fetcher.analyze_whale_activity(symbol),
        news_fetcher.get_news_sentiment(symbol),
        return_exceptions=True
    )

    market_data   = results[0] if isinstance(results[0], dict) else {}
    deriv_data    = results[1] if isinstance(results[1], dict) else {}
    whale_data    = results[2] if isinstance(results[2], dict) else {}
    news_data     = results[3] if isinstance(results[3], dict) else {}

    ai_analysis = await gemini_analyzer.analyze(market_data, news_data, deriv_data)
    trade       = await signal_engine.generate_signal(
        symbol, market_data, deriv_data, whale_data, news_data, ai_analysis
    )

    await db.save_signal(trade)
    return trade.format_telegram()


# ── Handlers ─────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"📡 <b>HedgeΣSignal</b> — Crypto Fund Engine\n\n"
        f"Привет, {user.first_name}! 👋\n\n"
        f"Анализирую рынок как профессиональный хедж-фонд:\n"
        f"• 🌍 Макро и геополитика\n"
        f"• 🐋 Движения китов и институционалов\n"
        f"• 📰 Новостной сентимент\n"
        f"• 📊 Технический анализ + деривативы\n"
        f"• 🤖 Gemini AI синтез\n"
        f"• 🛡 Институциональный риск-менеджмент\n\n"
        f"Выберите действие:"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=MAIN_MENU)


async def cmd_signal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sym  = ctx.args[0].upper() + "USDT" if ctx.args else "BTCUSDT"
    msg  = await update.message.reply_text(
        f"⚙️ <b>Анализирую {sym}...</b>\n\n"
        f"⏳ Загружаю рыночные данные...\n"
        f"⏳ Деривативы и фандинг...\n"
        f"⏳ Активность китов...\n"
        f"⏳ Новостной сентимент...\n"
        f"⏳ Gemini AI синтез...\n\n"
        f"<i>~30-60 секунд</i>",
        parse_mode=ParseMode.HTML
    )
    result = await run_full_analysis(sym)
    await safe_edit(msg, result)


async def cmd_prices(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    syms   = settings.symbol_list
    tickers = await asyncio.gather(*[market_fetcher.get_ticker(s) for s in syms])

    text = "📊 <b>Рыночные цены</b>\n"
    text += f"<code>{datetime.now().strftime('%d.%m.%Y %H:%M')} МСК</code>\n\n"
    icons = {"BTC":"₿","ETH":"Ξ","XRP":"✕","SOL":"◎","BNB":"⬡"}

    for sym, tick in zip(syms, tickers):
        if not isinstance(tick, dict) or not tick.get("price"): continue
        coin  = sym.replace("USDT","")
        ico   = icons.get(coin, "•")
        ch    = tick.get("change_24h", 0)
        arrow = "▲" if ch > 0 else "▼" if ch < 0 else "–"
        color = "🟢" if ch > 2 else "🔴" if ch < -2 else "🟡"
        text += f"{color}{ico} <b>{coin}</b>  <code>${tick['price']:,.2f}</code>  {arrow}<code>{ch:+.2f}%</code>\n"
        text += f"   Vol: <code>${tick.get('volume_24h',0):,.0f}</code>\n"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=MAIN_MENU)


async def cmd_backtest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sym = (ctx.args[0].upper() + "USDT") if ctx.args else "BTCUSDT"
    msg = await update.message.reply_text(
        f"🔄 <b>Запускаю бэктест {sym}...</b>\n\n"
        f"<i>Симулирую 180 дней истории на 4H свечах...</i>",
        parse_mode=ParseMode.HTML
    )
    try:
        result = await backtest_engine.run(sym, days=180)
        await safe_edit(msg, result.format_telegram())
    except Exception as e:
        await safe_edit(msg, f"❌ Ошибка бэктеста: {e}")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📡 <b>HedgeΣSignal — Команды</b>\n\n"
        "/start — Главное меню\n"
        "/signal [BTC|ETH|SOL|XRP] — AI-сигнал\n"
        "/prices — Текущие цены\n"
        "/backtest [BTC|ETH] — Бэктест 180 дней\n"
        "/help — Это сообщение\n\n"
        "<b>Сигналы:</b>\n"
        "🚀 STRONG BUY — очень сильный лонг\n"
        "🟢 BUY — лонг\n"
        "🟡 NO TRADE — воздержаться\n"
        "🔴 SELL — шорт\n"
        "💀 STRONG SELL — очень сильный шорт\n"
        "🚫 BLOCKED — риск-менеджмент заблокировал"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=MAIN_MENU)


# ── Callback кнопок ──────────────────────────────────────────────
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data
    chat  = query.message.chat_id

    # Сигнал по символу
    if data.startswith("signal_"):
        sym = data.split("_")[1]
        msg = await query.message.reply_text(
            f"⚙️ <b>Анализирую {sym}...</b>\n\n"
            f"⏳ Рыночные данные...\n"
            f"⏳ Деривативы...\n"
            f"⏳ Киты...\n"
            f"⏳ Новости...\n"
            f"⏳ Gemini AI...\n\n"
            f"<i>~30-60 секунд</i>",
            parse_mode=ParseMode.HTML
        )
        try:
            result = await run_full_analysis(sym)
            await safe_edit(msg, result)
        except Exception as e:
            await safe_edit(msg, f"❌ Ошибка: {e}")

    # Новости
    elif data == "news":
        msg = await query.message.reply_text("📰 Загружаю новости...", parse_mode=ParseMode.HTML)
        try:
            news = await news_fetcher.get_news_sentiment("BTCUSDT")
            text = f"📰 <b>Крипто-новости</b>\n\n"
            text += f"Сентимент: <code>{news.get('sentiment','?').upper()}</code> | "
            text += f"Скор: <code>{news.get('score',0):+.3f}</code>\n"
            text += f"Статей: <code>{news.get('articles_count',0)}</code> | "
            text += f"🐂 {news.get('bullish_count',0)} / 🐻 {news.get('bearish_count',0)}\n\n"
            text += "<b>Топ заголовки:</b>\n"
            for h in news.get("top_headlines", [])[:5]:
                text += f"• {h[:120]}\n"
            await safe_edit(msg, text)
        except Exception as e:
            await safe_edit(msg, f"❌ Ошибка: {e}")

    # Киты
    elif data == "whales":
        msg = await query.message.reply_text("🐋 Анализирую активность китов...", parse_mode=ParseMode.HTML)
        try:
            whales = await whale_fetcher.analyze_whale_activity("BTCUSDT")
            text  = f"🐋 <b>Активность китов</b>\n\n"
            text += f"Поток: <code>{whales.get('net_flow','?')}</code>\n"
            text += f"Скор: <code>{whales.get('score',0):+.3f}</code>\n"
            text += f"На биржу: <code>{whales.get('to_exchange',0)}</code> | "
            text += f"С биржи: <code>{whales.get('from_exchange',0)}</code>\n"
            text += f"Объём: <code>${whales.get('total_volume_usd',0):,.0f}</code>\n"
            top = whales.get("top_txs",[])
            if top:
                text += "\n<b>Крупные сделки:</b>\n"
                for t in top[:3]:
                    text += f"• {t.get('from_label','?')} → {t.get('to_label','?')}: <code>${t.get('value_usd',0):,.0f}</code> ({t.get('direction','?')})\n"
            await safe_edit(msg, text)
        except Exception as e:
            await safe_edit(msg, f"❌ Ошибка: {e}")

    # Фандинг
    elif data == "funding":
        syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        msg  = await query.message.reply_text("💸 Загружаю данные деривативов...", parse_mode=ParseMode.HTML)
        try:
            results = await asyncio.gather(*[derivatives_fetcher.get_full_derivatives(s) for s in syms])
            text = "💸 <b>Деривативы и фандинг</b>\n\n"
            for sym, d in zip(syms, results):
                if not isinstance(d, dict): continue
                f   = d.get("funding", {})
                oi  = d.get("open_interest", {})
                ls  = d.get("long_short", {})
                coin = sym.replace("USDT","")
                text += f"<b>{coin}</b>\n"
                text += f"  Фандинг: <code>{f.get('funding_rate',0):+.4f}%</code> ({f.get('bias','?')})\n"
                text += f"  OI Δ24h: <code>{oi.get('oi_change_24h_pct',0):+.2f}%</code>\n"
                text += f"  L/S: <code>{ls.get('long_pct',50):.1f}%/{ls.get('short_pct',50):.1f}%</code>\n\n"
            await safe_edit(msg, text)
        except Exception as e:
            await safe_edit(msg, f"❌ Ошибка: {e}")

    # Бэктест
    elif data.startswith("backtest_"):
        sym = data.split("_")[1]
        msg = await query.message.reply_text(
            f"🔄 <b>Запускаю бэктест {sym}...</b>\n\n<i>180 дней | 4H таймфрейм</i>",
            parse_mode=ParseMode.HTML
        )
        try:
            result = await backtest_engine.run(sym, days=180)
            await safe_edit(msg, result.format_telegram())
        except Exception as e:
            await safe_edit(msg, f"❌ Ошибка: {e}")

    # История сигналов
    elif data == "history":
        try:
            signals = await db.get_recent_signals(10)
            if not signals:
                await query.message.reply_text("📭 Нет сохранённых сигналов.", parse_mode=ParseMode.HTML)
                return
            text = "📈 <b>Последние 10 сигналов</b>\n\n"
            icons = {"STRONG BUY":"🚀","BUY":"🟢","NO TRADE":"🟡","SELL":"🔴","STRONG SELL":"💀"}
            for s in signals:
                ico  = icons.get(s.signal, "⚪")
                dt   = s.created_at.strftime("%d.%m %H:%M") if s.created_at else "?"
                text += f"{ico} <code>{s.symbol}</code> <b>{s.signal}</b> | conf:{s.confidence:.0%} | {dt}\n"
                if not s.blocked:
                    text += f"   Entry: <code>${s.entry:,.0f}</code> | Score: <code>{s.score:+.3f}</code>\n"
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=MAIN_MENU)
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка: {e}", parse_mode=ParseMode.HTML)

    # Авто-сигнал
    elif data == "auto_toggle":
        jobs = ctx.job_queue.get_jobs_by_name(f"auto_{chat}")
        if jobs:
            for j in jobs: j.schedule_removal()
            await query.message.reply_text(
                "⏹ <b>Авто-сигнал отключён</b>", parse_mode=ParseMode.HTML, reply_markup=MAIN_MENU
            )
        else:
            interval = settings.signal_interval * 60
            ctx.job_queue.run_repeating(
                auto_signal_job, interval=interval,
                first=10, name=f"auto_{chat}", data={"chat_id": chat}
            )
            await query.message.reply_text(
                f"✅ <b>Авто-сигнал включён!</b>\n\n"
                f"Буду присылать BTC-сигнал каждые <b>{settings.signal_interval} мин</b>.\n"
                f"Нажмите снова чтобы отключить.",
                parse_mode=ParseMode.HTML, reply_markup=MAIN_MENU
            )


async def auto_signal_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Автоматическая отправка сигнала по расписанию"""
    chat_id = ctx.job.data["chat_id"]
    try:
        result = await run_full_analysis("BTCUSDT")
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ <b>Авто-сигнал</b>\n\n{result}",
            parse_mode=ParseMode.HTML,
            reply_markup=MAIN_MENU
        )
    except Exception as e:
        logger.error(f"Auto signal error: {e}")


# ── Запуск бота ──────────────────────────────────────────────────
async def run_bot():
    await db.init()

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("signal",   cmd_signal))
    app.add_handler(CommandHandler("prices",   cmd_prices))
    app.add_handler(CommandHandler("backtest", cmd_backtest))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CallbackQueryHandler(on_callback))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=["message","callback_query"])

    logger.info("✅ @ProfitMachineBot запущен!")

    # Отправляем приветственное сообщение в чат
    if settings.telegram_chat_id:
        try:
            await app.bot.send_message(
                chat_id=settings.telegram_chat_id,
                text="📡 <b>HedgeΣSignal запущен!</b>\n\nСистема готова к работе. Нажмите /start",
                parse_mode=ParseMode.HTML
            )
        except Exception: pass

    # Бесконечный цикл
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await market_fetcher.close()
        await derivatives_fetcher.close()
        await whale_fetcher.close()
        await db.close()
