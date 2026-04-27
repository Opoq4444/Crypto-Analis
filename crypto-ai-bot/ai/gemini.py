"""ai/gemini.py — Google Gemini AI для анализа рынка"""
import json
import re
from typing import Dict, Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings


class GeminiAnalyzer:
    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY не задан в .env")
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self._model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config={
                    "temperature":      0.1,   # Низкая температура = стабильные ответы
                    "top_p":            0.8,
                    "max_output_tokens": 512,
                    "response_mime_type": "application/json",
                }
            )
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def analyze(self, market_data: Dict, news_data: Dict, derivatives_data: Dict) -> Dict:
        """
        Gemini анализирует все данные и возвращает строго JSON:
        {
            "sentiment": "bullish|bearish|neutral",
            "confidence": 0.0-1.0,
            "risk": "low|medium|high",
            "reason": "краткое объяснение"
        }
        """
        try:
            model = self._get_model()
        except Exception as e:
            logger.warning(f"⚠️ Gemini недоступен: {e}. Используем fallback.")
            return self._fallback_analysis(market_data, news_data, derivatives_data)

        # Формируем контекст для Gemini
        indicators = market_data.get("indicators", {})
        ticker     = market_data.get("ticker", {})
        funding    = derivatives_data.get("funding", {})
        oi         = derivatives_data.get("open_interest", {})
        ls         = derivatives_data.get("long_short", {})
        headlines  = news_data.get("top_headlines", [])[:5]

        prompt = f"""
Ты — квантовый аналитик хедж-фонда. Проанализируй данные и верни ТОЛЬКО JSON.

РЫНОЧНЫЕ ДАННЫЕ ({market_data.get('symbol', 'BTC')}):
- Цена: ${ticker.get('price', 0):,.2f}
- Изменение 24ч: {ticker.get('change_24h', 0):.2f}%
- Объём 24ч: ${ticker.get('volume_24h', 0):,.0f}
- RSI(14): {indicators.get('rsi', 50):.1f}
- MACD гистограмма: {indicators.get('macd_hist', 0):.6f}
- EMA20: {indicators.get('ema20', 0):.4f}
- EMA50: {indicators.get('ema50', 0):.4f}
- Bollinger %B: {indicators.get('bb_pct', 0.5):.3f}
- ATR%: {indicators.get('atr_pct', 0):.2f}%
- Объём/SMA20: {indicators.get('vol_ratio', 1):.2f}x
- Тренд-скор: {indicators.get('trend_score', 0):.3f}

ДЕРИВАТИВЫ:
- Funding rate: {funding.get('funding_rate', 0):.4f}% (bias: {funding.get('bias', 'neutral')})
- OI изменение 24ч: {oi.get('oi_change_24h_pct', 0):.2f}%
- Long/Short ratio: {ls.get('long_pct', 50):.1f}% / {ls.get('short_pct', 50):.1f}%

НОВОСТИ (топ заголовки):
{chr(10).join(f'- {h}' for h in headlines) if headlines else '- Нет данных'}
Новостной сентимент: {news_data.get('sentiment', 'neutral')} (скор: {news_data.get('score', 0):.3f})

ЗАДАЧА: Верни ТОЛЬКО валидный JSON без пояснений:
{{
  "sentiment": "bullish",
  "confidence": 0.75,
  "risk": "medium",
  "reason": "Краткое объяснение на русском (1-2 предложения)"
}}

Правила:
- sentiment: только "bullish", "bearish", или "neutral"
- confidence: от 0.0 до 1.0 (0.65+ = уверенный сигнал)
- risk: только "low", "medium", или "high"
- При RSI > 75 или < 25 — высокий риск
- При extreme funding — высокий риск
- При противоречии данных — снижай confidence и ставь high risk
"""
        try:
            import asyncio
            loop    = asyncio.get_event_loop()
            resp    = await loop.run_in_executor(None, model.generate_content, prompt)
            raw     = resp.text.strip()
            # Очищаем от возможных markdown обёрток
            raw     = re.sub(r'```json|```', '', raw).strip()
            result  = json.loads(raw)

            # Валидация ответа
            assert result.get("sentiment") in ("bullish", "bearish", "neutral")
            assert 0.0 <= float(result.get("confidence", 0)) <= 1.0
            assert result.get("risk") in ("low", "medium", "high")

            logger.info(f"✅ Gemini: {result['sentiment']} conf={result['confidence']:.2f} risk={result['risk']}")
            return result

        except Exception as e:
            logger.error(f"❌ Gemini parse error: {e}")
            return self._fallback_analysis(market_data, news_data, derivatives_data)

    def _fallback_analysis(self, market_data: Dict, news_data: Dict, derivatives_data: Dict) -> Dict:
        """Rule-based fallback если Gemini недоступен"""
        ind     = market_data.get("indicators", {})
        rsi     = ind.get("rsi", 50)
        trend   = ind.get("trend_score", 0)
        funding = derivatives_data.get("funding", {})
        news_sc = news_data.get("score", 0)

        score = trend * 0.4 + (news_sc) * 0.3 + (-(funding.get("score", 0))) * 0.3

        if score > 0.3:   sentiment = "bullish"
        elif score < -0.3: sentiment = "bearish"
        else:              sentiment = "neutral"

        # Risk
        is_extreme = funding.get("bias") in ("extreme_long", "extreme_short")
        if rsi > 80 or rsi < 20 or is_extreme:
            risk = "high"
        elif rsi > 70 or rsi < 30:
            risk = "medium"
        else:
            risk = "low"

        confidence = min(abs(score) + 0.4, 0.9)

        return {
            "sentiment":  sentiment,
            "confidence": round(confidence, 2),
            "risk":       risk,
            "reason":     f"Rule-based: trend={trend:.2f}, rsi={rsi:.0f}, news={news_sc:.2f}",
        }


gemini_analyzer = GeminiAnalyzer()
