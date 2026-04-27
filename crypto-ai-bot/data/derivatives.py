"""data/derivatives.py — Деривативы: фандинг, OI, ликвидации"""
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from typing import Dict, Optional
from config import settings


BINANCE_FAPI = "https://fapi.binance.com"
COINGLASS    = "https://open-api.coinglass.com/public/v2"


class DerivativesFetcher:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _session_get(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        return self._session

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, url: str, params: dict = None, headers: dict = None) -> dict:
        s = await self._session_get()
        async with s.get(url, params=params, headers=headers or {}) as r:
            r.raise_for_status()
            return await r.json()

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ── Funding Rate (Binance Futures) ─────────────────────────────
    async def get_funding_rate(self, symbol: str) -> Dict:
        """Текущий фандинг рейт с Binance Futures"""
        try:
            data = await self._get(f"{BINANCE_FAPI}/fapi/v1/premiumIndex", {"symbol": symbol})
            funding = float(data.get("lastFundingRate", 0))
            mark    = float(data.get("markPrice", 0))
            index   = float(data.get("indexPrice", 0))
            spread  = (mark - index) / index * 100 if index > 0 else 0

            # Интерпретация фандинга
            if funding > settings.funding_extreme_long:
                bias = "extreme_long"
            elif funding > 0.01:
                bias = "long"
            elif funding < settings.funding_extreme_short:
                bias = "extreme_short"
            elif funding < -0.01:
                bias = "short"
            else:
                bias = "neutral"

            # Нормализованный скор [-1, 1]: высокий фандинг = медвежий сигнал
            score = -min(max(funding / 0.03, -1), 1)

            return {
                "funding_rate": round(funding * 100, 4),  # в %
                "mark_price":   mark,
                "index_price":  index,
                "spread_pct":   round(spread, 4),
                "bias":         bias,
                "score":        round(score, 3),
            }
        except Exception as e:
            logger.error(f"❌ Funding {symbol}: {e}")
            return {"funding_rate": 0, "bias": "neutral", "score": 0}

    # ── Open Interest (Binance Futures) ────────────────────────────
    async def get_open_interest(self, symbol: str) -> Dict:
        """Открытый интерес"""
        try:
            # Текущий OI
            data = await self._get(f"{BINANCE_FAPI}/fapi/v1/openInterest", {"symbol": symbol})
            oi_now = float(data.get("openInterest", 0))

            # Исторический OI (для определения тренда)
            hist = await self._get(f"{BINANCE_FAPI}/futures/data/openInterestHist", {
                "symbol": symbol, "period": "1h", "limit": 24
            })
            if hist and isinstance(hist, list):
                oi_24h_ago = float(hist[0].get("sumOpenInterest", oi_now))
                oi_change  = (oi_now - oi_24h_ago) / oi_24h_ago * 100 if oi_24h_ago > 0 else 0
            else:
                oi_change = 0

            # OI рост = новые позиции открываются
            score = min(max(oi_change / 20, -1), 1)

            return {
                "oi_current": round(oi_now, 0),
                "oi_change_24h_pct": round(oi_change, 2),
                "score": round(score, 3),
            }
        except Exception as e:
            logger.error(f"❌ OI {symbol}: {e}")
            return {"oi_current": 0, "oi_change_24h_pct": 0, "score": 0}

    # ── Long/Short Ratio ────────────────────────────────────────────
    async def get_long_short_ratio(self, symbol: str) -> Dict:
        """Соотношение лонгов и шортов"""
        try:
            data = await self._get(f"{BINANCE_FAPI}/futures/data/globalLongShortAccountRatio", {
                "symbol": symbol, "period": "1h", "limit": 1
            })
            if data and isinstance(data, list):
                ratio     = float(data[0].get("longShortRatio", 1.0))
                long_pct  = float(data[0].get("longAccount", 0.5)) * 100
                short_pct = float(data[0].get("shortAccount", 0.5)) * 100

                # Экстремальный дисбаланс — сигнал разворота (contrarian)
                if long_pct > 70:
                    score = -0.6  # Слишком много лонгов — медвежий
                elif long_pct < 30:
                    score = 0.6   # Слишком много шортов — бычий
                else:
                    score = (long_pct - 50) / 50 * -0.5  # Contrarian

                return {
                    "ratio":     round(ratio, 3),
                    "long_pct":  round(long_pct, 1),
                    "short_pct": round(short_pct, 1),
                    "score":     round(score, 3),
                }
        except Exception as e:
            logger.error(f"❌ L/S Ratio {symbol}: {e}")
        return {"ratio": 1.0, "long_pct": 50, "short_pct": 50, "score": 0}

    # ── Ликвидации (Coinglass) ─────────────────────────────────────
    async def get_liquidations(self, symbol: str) -> Dict:
        """Данные о ликвидациях — признак экстремальных движений"""
        try:
            key = settings.coinglass_api_key
            if not key:
                return {"long_liq": 0, "short_liq": 0, "score": 0}

            coin = symbol.replace("USDT", "")
            data = await self._get(
                f"{COINGLASS}/liquidation_chart",
                {"symbol": coin, "time_type": "h4"},
                headers={"coinglassSecret": key}
            )
            if data.get("code") == "0" and data.get("data"):
                d = data["data"]
                long_liq  = float(d.get("longLiquidationUsd24h", 0))
                short_liq = float(d.get("shortLiquidationUsd24h", 0))
                total     = long_liq + short_liq
                # Больше лонг-ликвидаций = цена падала
                score = (short_liq - long_liq) / total if total > 0 else 0
                return {"long_liq": long_liq, "short_liq": short_liq, "score": round(score, 3)}
        except Exception as e:
            logger.error(f"❌ Liquidations {symbol}: {e}")
        return {"long_liq": 0, "short_liq": 0, "score": 0}

    # ── Полный анализ деривативов ──────────────────────────────────
    async def get_full_derivatives(self, symbol: str) -> Dict:
        import asyncio
        funding, oi, ls, liq = await asyncio.gather(
            self.get_funding_rate(symbol),
            self.get_open_interest(symbol),
            self.get_long_short_ratio(symbol),
            self.get_liquidations(symbol),
            return_exceptions=True
        )

        def safe(x): return x if isinstance(x, dict) else {}

        funding = safe(funding)
        oi      = safe(oi)
        ls      = safe(ls)
        liq     = safe(liq)

        # Блокировка при экстремальных условиях
        is_extreme = funding.get("bias") in ("extreme_long", "extreme_short")

        # Агрегированный скор деривативов
        deriv_score = (
            funding.get("score", 0) * 0.4 +
            oi.get("score", 0)      * 0.3 +
            ls.get("score", 0)      * 0.2 +
            liq.get("score", 0)     * 0.1
        )

        return {
            "funding":     funding,
            "open_interest": oi,
            "long_short":  ls,
            "liquidations": liq,
            "deriv_score": round(deriv_score, 3),
            "is_extreme":  is_extreme,
        }


derivatives_fetcher = DerivativesFetcher()
