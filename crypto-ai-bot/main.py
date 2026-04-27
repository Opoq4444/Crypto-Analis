"""main.py — Точка входа HedgeΣSignal"""
import asyncio
import sys
from pathlib import Path
from loguru import logger
from config import settings

# Создаём нужные директории
Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)
Path("ai").mkdir(exist_ok=True)
Path("bot").mkdir(exist_ok=True)
Path("engine").mkdir(exist_ok=True)
Path("backtest").mkdir(exist_ok=True)

# __init__.py для пакетов
for pkg in ["data","ai","engine","bot","backtest"]:
    init = Path(pkg) / "__init__.py"
    if not init.exists():
        init.write_text("")

# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level=settings.log_level,
    colorize=True,
)
logger.add(
    settings.log_file,
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    encoding="utf-8",
)


def main():
    logger.info("=" * 50)
    logger.info("  HedgeΣSignal — Crypto Fund Engine")
    logger.info("=" * 50)
    logger.info(f"Символы:   {settings.symbols}")
    logger.info(f"Таймфрейм: {settings.timeframe}")
    logger.info(f"Интервал:  {settings.signal_interval} мин")
    logger.info(f"Gemini AI: {'✅' if settings.gemini_api_key else '⚠️ не задан'}")
    logger.info(f"Etherscan: {'✅' if settings.etherscan_api_key else '⚠️ не задан'}")
    logger.info("=" * 50)

    from bot.telegram_bot import run_bot
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
