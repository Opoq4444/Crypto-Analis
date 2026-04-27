"""engine/signal.py — Сигнальный движок хедж-фонда"""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from loguru import logger
from config import settings


class SignalType(str, Enum):
    STRONG_BUY  = "STRONG BUY"
    BUY         = "BUY"
    NO_TRADE    = "NO TRADE"
    SELL        = "SELL"
    STRONG_SELL = "STRONG SELL"


class BlockReason(str, Enum):
    LOW_CONFIDENCE    = "Низкая уверенность AI"
    HIGH_RISK         = "Высокий риск"
    EXTREME_FUNDING   = "Экстремальный фандинг"
    LOW_LIQUIDITY     = "Низкая ликвидность"
    CONTRADICTING     = "Противоречивые сигналы"


@dataclass
class TradeSetup:
    signal:     SignalType
    symbol:     str
    entry:      float
    stop_loss:  float
    take_profit: float
    rr_ratio:   float
    confidence: float
    score:      float
    blocked:    bool           = False
    block_reason: Optional[str] = None

    # Компоненты скора
    trend_score:  float = 0.0
    whale_score:  float = 0.0
    deriv_score:  float = 0.0
    funding_score: float = 0.0
    sentiment_score: float = 0.0

    # Детали
    rsi:         float = 50.0
    funding_rate: float = 0.0
    long_pct:    float = 50.0
    net_flow:    str   = "NEUTRAL"
    news_sentiment: str = "neutral"
    ai_reason:   str   = ""

    def to_emoji(self) -> str:
        return {
            SignalType.STRONG_BUY:  "🚀",
            SignalType.BUY:         "🟢",
            SignalType.NO_TRADE:    "🟡",
            SignalType.SELL:        "🔴",
            SignalType.STRONG_SELL: "💀",
        }.get(self.signal, "⚪")

    def format_telegram(self) -> str:
        """Форматирование для Telegram"""
        e = self.to_emoji()
        bar = "█" * int(abs(self.score) * 10) + "░" * (10 - int(abs(self.score) * 10))

        if self.blocked:
            msg  = f"🚫 <b>СИГНАЛ ЗАБЛОКИРОВАН</b>\n"
            msg += f"<code>{self.symbol}</code> | {self.block_reason}\n\n"
            msg += f"Уверенность: <code>{self.confidence:.0%}</code>\n"
            msg += f"Скор: <code>{self.score:+.3f}</code>\n\n"
            msg += "<i>Торговля заблокирована системой риск-менеджмента.</i>"
            return msg

        direction = "▲ ЛОНГ" if self.score > 0 else "▼ ШОРТ"
        msg  = f"{e} <b>{self.signal.value}</b> | <code>{self.symbol}</code>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💰 Вход:         <code>${self.entry:,.2f}</code>\n"
        msg += f"🔴 Стоп-лосс:   <code>${self.stop_loss:,.2f}</code>\n"
        msg += f"🎯 Тейк-профит: <code>${self.take_profit:,.2f}</code>\n"
        msg += f"⚖️ R/R ratio:   <code>{self.rr_ratio:.2f}</code>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 Скор:   <code>{self.score:+.3f}  {bar}</code>\n"
        msg += f"🎯 Уверен: <code>{self.confidence:.0%}</code>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"<b>Компоненты:</b>\n"
        msg += f"📈 Тренд:      <code>{self.trend_score:+.3f}</code>\n"
        msg += f"🐋 Киты:       <code>{self.whale_score:+.3f}</code>\n"
        msg += f"📊 Деривативы: <code>{self.deriv_score:+.3f}</code>\n"
        msg += f"💸 Фандинг:    <code>{self.funding_score:+.3f}</code>\n"
        msg += f"📰 Сентимент:  <code>{self.sentiment_score:+.3f}</code>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"RSI: <code>{self.rsi:.1f}</code> | "
        msg += f"Фандинг: <code>{self.funding_rate:+.4f}%</code> | "
        msg += f"L/S: <code>{self.long_pct:.0f}%/{100-self.long_pct:.0f}%</code>\n"
        msg += f"Киты: <code>{self.net_flow}</code> | "
        msg += f"Новости: <code>{self.news_sentiment.upper()}</code>\n"
        if self.ai_reason:
            msg += f"\n🤖 <i>{self.ai_reason}</i>\n"
        msg += f"\n<i>⚠️ Не финансовый совет. DYOR.</i>"
        return msg


class SignalEngine:
    """
    Основной движок генерации сигналов.
    Взвешенное агрегирование всех источников данных.
    """

    def __init__(self):
        self.weights = {
            "trend":       settings.weight_trend,
            "whales":      settings.weight_whales,
            "derivatives": settings.weight_derivatives,
            "funding":     settings.weight_funding,
            "sentiment":   settings.weight_sentiment,
        }
        self.total_weight = sum(self.weights.values())

    def _normalize(self, score: float) -> float:
        """Нормализация в [-1, 1]"""
        return max(-1.0, min(1.0, score))

    def _weighted_score(
        self,
        trend: float,
        whales: float,
        derivatives: float,
        funding: float,
        sentiment: float,
        ai_sentiment: str,
        ai_confidence: float,
    ) -> Tuple[float, float]:
        """
        Взвешенный скор [-1, 1] и уверенность [0, 1]
        """
        # AI корректировка
        ai_factor = {"bullish": 1.0, "bearish": -1.0, "neutral": 0.0}.get(ai_sentiment, 0.0)
        ai_boost  = ai_factor * ai_confidence * 0.3  # AI даёт до 30% бонуса

        raw_score = (
            trend       * self.weights["trend"] +
            whales      * self.weights["whales"] +
            derivatives * self.weights["derivatives"] +
            funding     * self.weights["funding"] +
            sentiment   * self.weights["sentiment"]
        ) / self.total_weight

        final_score = self._normalize(raw_score + ai_boost)

        # Уверенность — насколько все источники согласуются
        scores = [trend, whales, derivatives, funding, sentiment]
        signs  = [s > 0 for s in scores if abs(s) > 0.05]
        if not signs:
            agreement = 0.5
        else:
            dominant = max(sum(signs), len(signs) - sum(signs)) / len(signs)
            agreement = dominant

        confidence = agreement * ai_confidence * (0.5 + abs(final_score) * 0.5)
        confidence = max(0.1, min(0.95, confidence))

        return final_score, confidence

    def _check_blocks(
        self,
        confidence: float,
        ai_risk: str,
        derivatives_data: Dict,
        market_data: Dict,
    ) -> Optional[BlockReason]:
        """Проверка блокировок риск-менеджмента"""

        # 1. Низкая уверенность
        if confidence < settings.min_confidence:
            return BlockReason.LOW_CONFIDENCE

        # 2. AI говорит высокий риск
        if ai_risk == "high":
            return BlockReason.HIGH_RISK

        # 3. Экстремальный фандинг
        funding = derivatives_data.get("funding", {})
        if funding.get("bias") in ("extreme_long", "extreme_short"):
            return BlockReason.EXTREME_FUNDING

        # 4. Низкая ликвидность
        ticker = market_data.get("ticker", {})
        if ticker.get("volume_24h", 1e9) < settings.min_liquidity_usdt:
            return BlockReason.LOW_LIQUIDITY

        return None

    def _calculate_levels(
        self,
        price: float,
        signal: SignalType,
        atr: float,
    ) -> Tuple[float, float, float]:
        """
        Вычислить entry, stop_loss, take_profit на основе ATR.
        R/R минимум 2:1
        """
        if atr <= 0:
            atr = price * 0.02  # Fallback 2%

        if signal in (SignalType.STRONG_BUY, SignalType.BUY):
            entry       = price
            stop_loss   = round(price - atr * 1.5, 2)
            take_profit = round(price + atr * 3.0, 2)  # 2:1 R/R
        elif signal in (SignalType.STRONG_SELL, SignalType.SELL):
            entry       = price
            stop_loss   = round(price + atr * 1.5, 2)
            take_profit = round(price - atr * 3.0, 2)
        else:
            entry       = price
            stop_loss   = round(price - atr * 1.5, 2)
            take_profit = round(price + atr * 3.0, 2)

        risk   = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr     = round(reward / risk, 2) if risk > 0 else 0.0

        return entry, stop_loss, take_profit, rr

    def _score_to_signal(self, score: float, confidence: float) -> SignalType:
        """Перевод числового скора в торговый сигнал"""
        if confidence < settings.min_confidence:
            return SignalType.NO_TRADE

        if score >= 0.6:    return SignalType.STRONG_BUY
        elif score >= 0.25: return SignalType.BUY
        elif score <= -0.6: return SignalType.STRONG_SELL
        elif score <= -0.25: return SignalType.SELL
        else:               return SignalType.NO_TRADE

    async def generate_signal(
        self,
        symbol:     str,
        market_data: Dict,
        derivatives_data: Dict,
        whale_data:  Dict,
        news_data:   Dict,
        ai_analysis: Dict,
    ) -> TradeSetup:
        """Генерация торгового сигнала"""

        ind  = market_data.get("indicators", {})
        tick = market_data.get("ticker", {})

        # Скоры компонентов
        trend_score     = ind.get("trend_score", 0.0)
        whale_score     = whale_data.get("score", 0.0)
        deriv_score     = derivatives_data.get("deriv_score", 0.0)
        funding_score   = derivatives_data.get("funding", {}).get("score", 0.0)
        sentiment_score = news_data.get("score", 0.0)

        ai_sentiment  = ai_analysis.get("sentiment", "neutral")
        ai_confidence = ai_analysis.get("confidence", 0.5)
        ai_risk       = ai_analysis.get("risk", "medium")
        ai_reason     = ai_analysis.get("reason", "")

        # Итоговый скор и уверенность
        score, confidence = self._weighted_score(
            trend_score, whale_score, deriv_score,
            funding_score, sentiment_score,
            ai_sentiment, ai_confidence
        )

        # Определяем сигнал
        signal = self._score_to_signal(score, confidence)

        # Уровни входа
        price = tick.get("price", 0) or ind.get("price", 0)
        atr   = ind.get("atr", price * 0.02)
        entry, stop_loss, take_profit, rr = self._calculate_levels(price, signal, atr)

        # Проверка блокировок
        block = self._check_blocks(confidence, ai_risk, derivatives_data, market_data)
        if block:
            logger.warning(f"🚫 Сигнал заблокирован: {block.value}")
            signal = SignalType.NO_TRADE

        return TradeSetup(
            signal       = signal,
            symbol       = symbol,
            entry        = round(entry, 2),
            stop_loss    = round(stop_loss, 2),
            take_profit  = round(take_profit, 2),
            rr_ratio     = rr,
            confidence   = round(confidence, 3),
            score        = round(score, 4),
            blocked      = block is not None,
            block_reason = block.value if block else None,

            trend_score     = round(trend_score, 3),
            whale_score     = round(whale_score, 3),
            deriv_score     = round(deriv_score, 3),
            funding_score   = round(funding_score, 3),
            sentiment_score = round(sentiment_score, 3),

            rsi          = ind.get("rsi", 50),
            funding_rate = derivatives_data.get("funding", {}).get("funding_rate", 0),
            long_pct     = derivatives_data.get("long_short", {}).get("long_pct", 50),
            net_flow     = whale_data.get("net_flow", "NEUTRAL"),
            news_sentiment = news_data.get("sentiment", "neutral"),
            ai_reason    = ai_reason,
        )


signal_engine = SignalEngine()
