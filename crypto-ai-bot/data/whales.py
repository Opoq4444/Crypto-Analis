"""data/whales.py — Отслеживание китов: Etherscan + BSCScan"""
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from typing import Dict, List, Optional
from config import settings


ETHERSCAN_API  = "https://api.etherscan.io/api"
BSCSCAN_API    = "https://api.bscscan.com/api"

# Известные адреса бирж (для определения направления)
EXCHANGE_ADDRS = {
    "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE": "Binance Hot",
    "0xd551234ae421e3bcba99a0da6d736074f22192ff": "Binance Cold",
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43": "Coinbase",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase 2",
    "0x2b5634c42055806a59e9107ed44d43c426e58258": "KuCoin",
    "0xd882cfc20f52f2599d84b8e8d58c7fb62cfe344b": "OKX",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX 2",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance 14",
}

# Порог крупной транзакции (USD)
WHALE_THRESHOLD = 1_000_000  # $1M


class WhaleFetcher:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        return self._session

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, url: str, params: dict) -> dict:
        s = await self._get_session()
        async with s.get(url, params=params) as r:
            r.raise_for_status()
            return await r.json()

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ── ETH крупные транзакции ─────────────────────────────────────
    async def get_eth_large_txs(self, limit: int = 20) -> List[Dict]:
        """Получить крупные ETH транзакции за последние 24ч"""
        key = settings.etherscan_api_key
        if not key:
            logger.warning("⚠️ ETHERSCAN_API_KEY не задан, пропускаю")
            return []
        try:
            # Берём последние транзакции по крупным ETH адресам
            data = await self._get(ETHERSCAN_API, {
                "module":  "account",
                "action":  "txlist",
                "address": "0xd551234ae421e3bcba99a0da6d736074f22192ff",  # Binance Cold
                "sort":    "desc",
                "page":    1,
                "offset":  limit,
                "apikey":  key,
            })
            txs = []
            if data.get("status") == "1":
                for tx in data.get("result", []):
                    val_eth = int(tx.get("value", 0)) / 1e18
                    price   = await self._get_eth_price()
                    val_usd = val_eth * price
                    if val_usd >= WHALE_THRESHOLD:
                        from_addr = tx.get("from", "").lower()
                        to_addr   = tx.get("to", "").lower()
                        txs.append({
                            "hash":    tx.get("hash"),
                            "from":    from_addr,
                            "to":      to_addr,
                            "value_eth": round(val_eth, 2),
                            "value_usd": round(val_usd, 0),
                            "from_label": EXCHANGE_ADDRS.get(tx.get("from", ""), "Unknown"),
                            "to_label":   EXCHANGE_ADDRS.get(tx.get("to", ""), "Unknown"),
                            "direction":  self._get_direction(from_addr, to_addr),
                        })
            return txs[:10]
        except Exception as e:
            logger.error(f"❌ ETH whale txs: {e}")
            return []

    async def _get_eth_price(self) -> float:
        try:
            data = await self._get(ETHERSCAN_API, {
                "module": "stats", "action": "ethprice",
                "apikey": settings.etherscan_api_key
            })
            return float(data["result"]["ethusd"])
        except:
            return 3000.0

    def _get_direction(self, from_addr: str, to_addr: str) -> str:
        """Определить: деньги идут на биржу или с биржи"""
        from_is_exchange = from_addr in {a.lower() for a in EXCHANGE_ADDRS}
        to_is_exchange   = to_addr   in {a.lower() for a in EXCHANGE_ADDRS}
        if to_is_exchange and not from_is_exchange:
            return "TO_EXCHANGE"      # Продажное давление
        elif from_is_exchange and not to_is_exchange:
            return "FROM_EXCHANGE"    # Вывод с биржи — держат
        return "EXCHANGE_TO_EXCHANGE" # Внутреннее перемещение

    # ── Whale Alert через RSS (бесплатно) ──────────────────────────
    async def get_whale_alert_rss(self) -> List[Dict]:
        """Парсим whale alert данные без API ключа"""
        import feedparser
        try:
            feed = feedparser.parse("https://api.whale-alert.io/v1/transactions?api_key=&min_value=1000000&limit=10")
            txs = []
            for entry in feed.entries[:10]:
                txs.append({
                    "title":   getattr(entry, "title", ""),
                    "summary": getattr(entry, "summary", ""),
                })
            return txs
        except Exception as e:
            logger.debug(f"Whale Alert RSS: {e}")
            return []

    # ── Анализ активности китов ─────────────────────────────────────
    async def analyze_whale_activity(self, symbol: str) -> Dict:
        """
        Агрегированный анализ:
        - Направление крупных переводов
        - Exchange net flow
        - Сигнал для движка
        """
        eth_txs = await self.get_eth_large_txs()

        to_ex   = sum(1 for t in eth_txs if t.get("direction") == "TO_EXCHANGE")
        from_ex = sum(1 for t in eth_txs if t.get("direction") == "FROM_EXCHANGE")
        total   = len(eth_txs)

        if total == 0:
            net_flow = "NEUTRAL"
            score    = 0.0
        else:
            # Больше на биржу = продажи
            ratio = (from_ex - to_ex) / total
            score = min(max(ratio, -1), 1)

            if score > 0.4:    net_flow = "ACCUMULATION"
            elif score < -0.4: net_flow = "DISTRIBUTION"
            else:              net_flow = "NEUTRAL"

        # Суммарный объём
        total_usd = sum(t.get("value_usd", 0) for t in eth_txs)

        return {
            "symbol":       symbol,
            "txs_analyzed": total,
            "to_exchange":  to_ex,
            "from_exchange": from_ex,
            "net_flow":     net_flow,
            "total_volume_usd": total_usd,
            "score":        round(score, 3),
            "top_txs":      eth_txs[:5],
        }


whale_fetcher = WhaleFetcher()
