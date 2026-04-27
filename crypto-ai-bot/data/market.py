"""data/market.py — Рыночные данные: Binance / OKX"""
import asyncio
from typing import Optional, Dict, List
import pandas as pd
import numpy as np
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from config import settings


BINANCE_BASE = "https://api.binance.com"
OKX_BASE     = "https://www.okx.com"


class MarketDataFetcher:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": "HedgeSigBot/1.0"}
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, url: str, params: dict = None) -> dict:
        session = await self._get_session()
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    # ── OHLCV ──────────────────────────────────────────────────────
    async def get_klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
        """Получить свечи с Binance"""
        try:
            data = await self._get(f"{BINANCE_BASE}/api/v3/klines", {
                "symbol": symbol, "interval": interval, "limit": limit
            })
            df = pd.DataFrame(data, columns=[
                "open_time","open","high","low","close","volume",
                "close_time","quote_vol","trades","taker_buy_base",
                "taker_buy_quote","ignore"
            ])
            for col in ["open","high","low","close","volume","quote_vol"]:
                df[col] = pd.to_numeric(df[col])
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
            df.set_index("open_time", inplace=True)
            logger.debug(f"✅ Klines {symbol}: {len(df)} свечей")
            return df
        except Exception as e:
            logger.error(f"❌ Klines {symbol}: {e}")
            return pd.DataFrame()

    # ── Цена и объём ───────────────────────────────────────────────
    async def get_ticker(self, symbol: str) -> Dict:
        """24h тикер"""
        try:
            data = await self._get(f"{BINANCE_BASE}/api/v3/ticker/24hr", {"symbol": symbol})
            return {
                "price":       float(data["lastPrice"]),
                "change_24h":  float(data["priceChangePercent"]),
                "volume_24h":  float(data["quoteVolume"]),
                "high_24h":    float(data["highPrice"]),
                "low_24h":     float(data["lowPrice"]),
                "trades_24h":  int(data["count"]),
            }
        except Exception as e:
            logger.error(f"❌ Ticker {symbol}: {e}")
            return {}

    # ── Order book глубина ─────────────────────────────────────────
    async def get_order_book_depth(self, symbol: str, limit: int = 20) -> Dict:
        """Анализ стакана заявок"""
        try:
            data = await self._get(f"{BINANCE_BASE}/api/v3/depth", {"symbol": symbol, "limit": limit})
            bids = [(float(p), float(q)) for p, q in data["bids"]]
            asks = [(float(p), float(q)) for p, q in data["asks"]]
            bid_vol = sum(p * q for p, q in bids)
            ask_vol = sum(p * q for p, q in asks)
            ratio   = bid_vol / ask_vol if ask_vol > 0 else 1.0
            return {
                "bid_volume": bid_vol,
                "ask_volume": ask_vol,
                "ratio":      ratio,          # >1 = больше покупателей
                "liquidity":  bid_vol + ask_vol,
                "spread_pct": (asks[0][0] - bids[0][0]) / bids[0][0] * 100,
            }
        except Exception as e:
            logger.error(f"❌ OrderBook {symbol}: {e}")
            return {}

    # ── Технический анализ ─────────────────────────────────────────
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """RSI, MACD, EMA, Bollinger, ATR"""
        if df.empty or len(df) < 50:
            return {}
        try:
            import ta
            close = df["close"]
            high  = df["high"]
            low   = df["low"]
            vol   = df["volume"]

            # RSI
            rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]

            # MACD
            macd_obj   = ta.trend.MACD(close)
            macd       = macd_obj.macd().iloc[-1]
            macd_sig   = macd_obj.macd_signal().iloc[-1]
            macd_hist  = macd_obj.macd_diff().iloc[-1]

            # EMA
            ema20  = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
            ema50  = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
            ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1] if len(df) >= 200 else None

            # Bollinger
            bb     = ta.volatility.BollingerBands(close, window=20, window_dev=2)
            bb_pct = bb.bollinger_pband().iloc[-1]   # 0=нижняя, 1=верхняя

            # ATR (волатильность)
            atr      = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
            atr_pct  = atr / close.iloc[-1] * 100

            # Volume SMA
            vol_sma   = vol.rolling(20).mean().iloc[-1]
            vol_ratio = vol.iloc[-1] / vol_sma if vol_sma > 0 else 1.0

            # Stochastic
            stoch  = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
            stoch_k = stoch.stoch().iloc[-1]

            price = close.iloc[-1]

            # Тренд
            trend_score = 0.0
            if ema20 > ema50: trend_score += 0.3
            if ema200 and price > ema200: trend_score += 0.4
            if macd > macd_sig: trend_score += 0.3
            trend_score = trend_score * 2 - 1  # → [-1, 1]

            return {
                "price":        price,
                "rsi":          round(rsi, 2),
                "macd":         round(macd, 6),
                "macd_signal":  round(macd_sig, 6),
                "macd_hist":    round(macd_hist, 6),
                "ema20":        round(ema20, 4),
                "ema50":        round(ema50, 4),
                "ema200":       round(ema200, 4) if ema200 else None,
                "bb_pct":       round(bb_pct, 3),
                "atr":          round(atr, 4),
                "atr_pct":      round(atr_pct, 2),
                "vol_ratio":    round(vol_ratio, 2),
                "stoch_k":      round(stoch_k, 2),
                "trend_score":  round(trend_score, 3),
            }
        except Exception as e:
            logger.error(f"❌ Indicators: {e}")
            return {}

    # ── Полный анализ по символу ───────────────────────────────────
    async def get_full_market_data(self, symbol: str) -> Dict:
        tf = settings.timeframe
        n  = settings.lookback_candles

        klines, ticker, ob = await asyncio.gather(
            self.get_klines(symbol, tf, n),
            self.get_ticker(symbol),
            self.get_order_book_depth(symbol),
            return_exceptions=True
        )
        indicators = self.calculate_indicators(klines) if isinstance(klines, pd.DataFrame) else {}

        return {
            "symbol":     symbol,
            "ticker":     ticker if isinstance(ticker, dict) else {},
            "indicators": indicators,
            "order_book": ob if isinstance(ob, dict) else {},
        }


market_fetcher = MarketDataFetcher()
