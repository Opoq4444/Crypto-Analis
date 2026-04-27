"""data/news.py — Новостной сентимент через RSS"""
import asyncio
import re
from typing import Dict, List
from loguru import logger
import feedparser


# Топ крипто-RSS источников (бесплатно)
RSS_FEEDS = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Bitcoin.com",   "https://news.bitcoin.com/feed/"),
    ("Decrypt",       "https://decrypt.co/feed"),
    ("TheBlock",      "https://www.theblock.co/rss.xml"),
]

# Ключевые слова для сентимента
BULLISH_KEYWORDS = [
    "bullish", "surge", "rally", "breakout", "all-time high", "ath",
    "adoption", "buy", "bull", "moon", "pump", "institutional",
    "etf approved", "partnership", "launch", "upgrade", "накопление",
    "рост", "ралли", "покупка", "одобрен", "принятие",
]

BEARISH_KEYWORDS = [
    "bearish", "crash", "dump", "fall", "drop", "hack", "ban",
    "regulation", "crackdown", "sell", "bear", "liquidation",
    "lawsuit", "arrested", "fraud", "scam", "bankrupt",
    "падение", "запрет", "продажа", "регуляция", "взлом", "мошенничество",
]

SYMBOL_MAP = {
    "BTC": ["bitcoin", "btc"],
    "ETH": ["ethereum", "eth", "ether"],
    "XRP": ["xrp", "ripple"],
    "SOL": ["solana", "sol"],
    "BNB": ["bnb", "binance"],
}


class NewsSentimentFetcher:

    def _score_text(self, text: str) -> float:
        """Простой rule-based сентимент: [-1, 1]"""
        text_lower = text.lower()
        bull = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
        bear = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)
        total = bull + bear
        if total == 0:
            return 0.0
        return (bull - bear) / total

    def _is_relevant(self, text: str, symbol: str) -> bool:
        """Проверить, относится ли новость к данному символу"""
        text_lower = text.lower()
        keywords   = SYMBOL_MAP.get(symbol.replace("USDT", ""), ["crypto", "bitcoin"])
        return any(kw in text_lower for kw in keywords + ["crypto", "market"])

    async def fetch_feed(self, name: str, url: str) -> List[Dict]:
        """Парсим RSS в отдельном потоке"""
        try:
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            items = []
            for entry in feed.entries[:10]:
                title   = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "")
                text    = f"{title} {summary}"
                score   = self._score_text(text)
                items.append({
                    "source":  name,
                    "title":   title[:200],
                    "score":   score,
                    "text":    text[:500],
                })
            return items
        except Exception as e:
            logger.debug(f"RSS {name}: {e}")
            return []

    async def get_news_sentiment(self, symbol: str) -> Dict:
        """Агрегированный сентимент по всем источникам"""
        # Параллельный парсинг всех RSS
        tasks   = [self.fetch_feed(name, url) for name, url in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for r in results:
            if isinstance(r, list):
                all_items.extend(r)

        # Фильтруем по символу
        sym_clean   = symbol.replace("USDT", "")
        relevant    = [i for i in all_items if self._is_relevant(i["text"], sym_clean)]
        all_scored  = relevant if relevant else all_items  # Fallback: все новости

        if not all_scored:
            return {"score": 0, "sentiment": "neutral",
                    "articles_count": 0, "top_headlines": []}

        # Средний скор
        avg_score = sum(i["score"] for i in all_scored) / len(all_scored)

        # Классификация
        if avg_score > 0.2:   sentiment = "bullish"
        elif avg_score < -0.2: sentiment = "bearish"
        else:                  sentiment = "neutral"

        # Топ заголовки
        top = sorted(all_scored, key=lambda x: abs(x["score"]), reverse=True)[:5]

        return {
            "symbol":          symbol,
            "score":           round(avg_score, 3),
            "sentiment":       sentiment,
            "articles_count":  len(all_scored),
            "bullish_count":   sum(1 for i in all_scored if i["score"] > 0.1),
            "bearish_count":   sum(1 for i in all_scored if i["score"] < -0.1),
            "top_headlines":   [i["title"] for i in top],
        }


news_fetcher = NewsSentimentFetcher()
