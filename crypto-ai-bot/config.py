"""config.py — Централизованная конфигурация"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from pathlib import Path

BASE_DIR = Path(__file__).parent

class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str   = Field("",  env="TELEGRAM_CHAT_ID")

    # AI
    gemini_api_key: str = Field("", env="GEMINI_API_KEY")

    # Внешние API
    etherscan_api_key:  str = Field("", env="ETHERSCAN_API_KEY")
    coinglass_api_key:  str = Field("", env="COINGLASS_API_KEY")
    okx_api_key:        str = Field("", env="OKX_API_KEY")
    okx_secret_key:     str = Field("", env="OKX_SECRET_KEY")
    okx_passphrase:     str = Field("", env="OKX_PASSPHRASE")

    # Торговые параметры
    symbols:           str   = Field("BTCUSDT,ETHUSDT,XRPUSDT,SOLUSDT", env="SYMBOLS")
    signal_interval:   int   = Field(60,   env="SIGNAL_INTERVAL")
    min_confidence:    float = Field(0.65, env="MIN_CONFIDENCE")
    risk_per_trade:    float = Field(1.0,  env="RISK_PER_TRADE")
    timeframe:         str   = Field("1h", env="TIMEFRAME")
    lookback_candles:  int   = Field(200,  env="LOOKBACK_CANDLES")

    # БД и логи
    database_url: str = Field("sqlite+aiosqlite:///data/signals.db", env="DATABASE_URL")
    log_level:    str = Field("INFO",                env="LOG_LEVEL")
    log_file:     str = Field("logs/hedgesignal.log", env="LOG_FILE")

    # Веса сигнального движка
    weight_trend:       float = 2.0
    weight_whales:      float = 1.5
    weight_derivatives: float = 2.0
    weight_funding:     float = 1.0
    weight_sentiment:   float = 1.0

    # Пороги риска
    funding_extreme_long:  float = 0.03
    funding_extreme_short: float = -0.03
    min_liquidity_usdt:    float = 1_000_000

    @property
    def symbol_list(self) -> List[str]:
        return [s.strip() for s in self.symbols.split(",")]

    @property
    def data_dir(self) -> Path:
        d = BASE_DIR / "data"; d.mkdir(exist_ok=True); return d

    @property
    def logs_dir(self) -> Path:
        d = BASE_DIR / "logs"; d.mkdir(exist_ok=True); return d

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
