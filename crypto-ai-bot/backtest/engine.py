"""backtest/engine.py — Исторический бэктест"""
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger
from config import settings


@dataclass
class BacktestTrade:
    symbol:     str
    direction:  str          # LONG / SHORT
    entry_price: float
    exit_price:  float
    stop_loss:   float
    take_profit: float
    entry_time:  datetime
    exit_time:   datetime
    result:      str          # WIN / LOSS / BREAKEVEN
    pnl_pct:     float
    rr_actual:   float
    signal_score: float
    confidence:  float


@dataclass
class BacktestResult:
    symbol:       str
    period_start: str
    period_end:   str
    total_trades: int
    win_trades:   int
    loss_trades:  int
    winrate:      float
    profit_factor: float
    total_pnl_pct: float
    max_drawdown:  float
    sharpe_ratio:  float
    trades:        List[BacktestTrade] = field(default_factory=list)
    equity_curve:  List[float]         = field(default_factory=list)

    def format_telegram(self) -> str:
        emoji = "✅" if self.profit_factor > 1.5 else "⚠️" if self.profit_factor > 1.0 else "❌"
        msg  = f"{emoji} <b>БЭКТЕСТ: {self.symbol}</b>\n"
        msg += f"<code>{self.period_start} → {self.period_end}</code>\n\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 Всего сделок:    <code>{self.total_trades}</code>\n"
        msg += f"✅ Прибыльных:      <code>{self.win_trades}</code>\n"
        msg += f"❌ Убыточных:       <code>{self.loss_trades}</code>\n"
        msg += f"🎯 Winrate:         <code>{self.winrate:.1f}%</code>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💰 Profit Factor:   <code>{self.profit_factor:.2f}</code>\n"
        msg += f"📈 Итого P&L:       <code>{self.total_pnl_pct:+.1f}%</code>\n"
        msg += f"📉 Макс. просадка:  <code>{self.max_drawdown:.1f}%</code>\n"
        msg += f"📊 Sharpe Ratio:    <code>{self.sharpe_ratio:.2f}</code>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        if self.trades:
            msg += f"\n<b>Последние сделки:</b>\n"
            for t in self.trades[-5:]:
                icon = "✅" if t.result == "WIN" else "❌"
                msg += f"{icon} {t.direction} {t.entry_price:.0f}→{t.exit_price:.0f} <code>{t.pnl_pct:+.1f}%</code>\n"
        return msg


class BacktestEngine:
    """
    Исторический бэктест на основе OHLCV данных.
    Симулирует сигнальный движок на исторических свечах.
    """

    def __init__(self):
        self.commission = 0.001   # 0.1% на сделку
        self.slippage   = 0.0005  # 0.05% проскальзывание

    async def fetch_historical(self, symbol: str, interval: str = "4h", days: int = 180) -> pd.DataFrame:
        """Скачиваем исторические данные с Binance"""
        import aiohttp
        limit   = min(1000, days * 6)  # 4h свечей в день = 6
        url     = "https://api.binance.com/api/v3/klines"
        params  = {"symbol": symbol, "interval": interval, "limit": limit}

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, params=params) as r:
                    data = await r.json()

            df = pd.DataFrame(data, columns=[
                "time","open","high","low","close","volume",
                "close_time","quote_vol","trades","taker_buy_base","taker_buy_quote","ignore"
            ])
            df["time"]  = pd.to_datetime(df["time"], unit="ms")
            for col in ["open","high","low","close","volume"]:
                df[col] = pd.to_numeric(df[col])
            df.set_index("time", inplace=True)
            logger.info(f"✅ Backtest data {symbol}: {len(df)} свечей ({interval})")
            return df
        except Exception as e:
            logger.error(f"❌ Historical data {symbol}: {e}")
            return pd.DataFrame()

    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Применяем технические индикаторы к историческим данным"""
        import ta
        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        df["rsi"]      = ta.momentum.RSIIndicator(close, 14).rsi()
        df["ema20"]    = ta.trend.EMAIndicator(close, 20).ema_indicator()
        df["ema50"]    = ta.trend.EMAIndicator(close, 50).ema_indicator()
        df["macd_hist"]= ta.trend.MACD(close).macd_diff()
        df["atr"]      = ta.volatility.AverageTrueRange(high, low, close, 14).average_true_range()
        df["bb_pct"]   = ta.volatility.BollingerBands(close, 20).bollinger_pband()
        df["vol_sma"]  = df["volume"].rolling(20).mean()

        # Тренд скор (упрощённый)
        df["trend_score"] = (
            (df["ema20"] > df["ema50"]).astype(float) * 0.5 +
            (df["macd_hist"] > 0).astype(float) * 0.5
        ) * 2 - 1  # → [-1, 1]

        # Простой составной сигнал
        df["signal_score"] = (
            df["trend_score"] * 2.0 +
            ((50 - df["rsi"]) / 50) * 1.5 +  # RSI mean reversion
            (df["bb_pct"] - 0.5) * -1.0       # BB contrarian
        ) / 4.5  # нормализация

        return df.dropna()

    def _simulate_trade(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        direction: str,
        entry_price: float,
        atr: float,
    ) -> Optional[BacktestTrade]:
        """Симулируем одну сделку"""
        entry_price *= (1 + self.slippage if direction == "LONG" else 1 - self.slippage)

        if direction == "LONG":
            stop_loss   = entry_price - atr * 1.5
            take_profit = entry_price + atr * 3.0
        else:
            stop_loss   = entry_price + atr * 1.5
            take_profit = entry_price - atr * 3.0

        entry_time = df.index[entry_idx]

        # Проходим по следующим свечам
        for i in range(entry_idx + 1, min(entry_idx + 48, len(df))):  # Макс 48 свечей (4h * 48 = 8 дней)
            high  = df["high"].iloc[i]
            low   = df["low"].iloc[i]
            close = df["close"].iloc[i]

            if direction == "LONG":
                if low <= stop_loss:
                    exit_price = stop_loss
                    result     = "LOSS"
                elif high >= take_profit:
                    exit_price = take_profit
                    result     = "WIN"
                else:
                    continue
            else:
                if high >= stop_loss:
                    exit_price = stop_loss
                    result     = "LOSS"
                elif low <= take_profit:
                    exit_price = take_profit
                    result     = "WIN"
                else:
                    continue

            pnl = (exit_price - entry_price) / entry_price
            if direction == "SHORT":
                pnl = -pnl
            pnl -= self.commission * 2  # Комиссия туда-обратно

            risk   = abs(entry_price - stop_loss)
            reward = abs(exit_price - entry_price)
            rr     = reward / risk if risk > 0 else 0

            return BacktestTrade(
                symbol      = df.attrs.get("symbol", "BTC"),
                direction   = direction,
                entry_price = round(entry_price, 2),
                exit_price  = round(exit_price, 2),
                stop_loss   = round(stop_loss, 2),
                take_profit = round(take_profit, 2),
                entry_time  = entry_time,
                exit_time   = df.index[i],
                result      = result,
                pnl_pct     = round(pnl * 100, 3),
                rr_actual   = round(rr, 2),
                signal_score = df["signal_score"].iloc[entry_idx],
                confidence   = 0.7,
            )

        # Сделка не закрылась — закрываем по последней цене
        exit_price = df["close"].iloc[min(entry_idx + 47, len(df) - 1)]
        pnl = (exit_price - entry_price) / entry_price
        if direction == "SHORT": pnl = -pnl
        pnl -= self.commission * 2

        return BacktestTrade(
            symbol      = df.attrs.get("symbol", "BTC"),
            direction   = direction,
            entry_price = round(entry_price, 2),
            exit_price  = round(exit_price, 2),
            stop_loss   = round(stop_loss, 2),
            take_profit = round(take_profit, 2),
            entry_time  = entry_time,
            exit_time   = df.index[min(entry_idx + 47, len(df) - 1)],
            result      = "WIN" if pnl > 0 else "LOSS",
            pnl_pct     = round(pnl * 100, 3),
            rr_actual   = 0.0,
            signal_score = df["signal_score"].iloc[entry_idx],
            confidence   = 0.7,
        )

    async def run(self, symbol: str, days: int = 180) -> BacktestResult:
        """Запуск полного бэктеста"""
        logger.info(f"🔄 Запуск бэктеста {symbol} ({days} дней)...")

        df = await self.fetch_historical(symbol, "4h", days)
        if df.empty:
            raise ValueError(f"Нет исторических данных для {symbol}")

        df.attrs["symbol"] = symbol
        df = self._calculate_signals(df)

        trades: List[BacktestTrade] = []
        open_trade_end = 0

        for i in range(50, len(df) - 1):
            if i < open_trade_end:
                continue

            score = df["signal_score"].iloc[i]
            rsi   = df["rsi"].iloc[i]
            atr   = df["atr"].iloc[i]
            price = df["close"].iloc[i]

            # Торговые условия (упрощённый вариант движка)
            if score >= 0.35 and rsi < 70:
                direction = "LONG"
            elif score <= -0.35 and rsi > 30:
                direction = "SHORT"
            else:
                continue

            trade = self._simulate_trade(df, i, direction, price, atr)
            if trade:
                trades.append(trade)
                # Блокируем наложение сделок
                duration       = (trade.exit_time - trade.entry_time).seconds // (4 * 3600)
                open_trade_end = i + max(duration, 2)

        # Метрики
        if not trades:
            return BacktestResult(
                symbol=symbol, period_start=str(df.index[0].date()),
                period_end=str(df.index[-1].date()), total_trades=0,
                win_trades=0, loss_trades=0, winrate=0, profit_factor=0,
                total_pnl_pct=0, max_drawdown=0, sharpe_ratio=0, trades=[]
            )

        wins      = [t for t in trades if t.result == "WIN"]
        losses    = [t for t in trades if t.result == "LOSS"]
        win_pnl   = sum(t.pnl_pct for t in wins)
        loss_pnl  = abs(sum(t.pnl_pct for t in losses))

        # Equity curve
        equity = [100.0]
        for t in trades:
            equity.append(equity[-1] * (1 + t.pnl_pct / 100))

        # Max drawdown
        eq_arr  = np.array(equity)
        peak    = np.maximum.accumulate(eq_arr)
        dd      = (eq_arr - peak) / peak * 100
        max_dd  = float(np.min(dd))

        # Sharpe (упрощённый)
        returns = np.array([t.pnl_pct for t in trades])
        sharpe  = float(returns.mean() / returns.std() * np.sqrt(365)) if returns.std() > 0 else 0

        result = BacktestResult(
            symbol        = symbol,
            period_start  = str(df.index[0].date()),
            period_end    = str(df.index[-1].date()),
            total_trades  = len(trades),
            win_trades    = len(wins),
            loss_trades   = len(losses),
            winrate       = round(len(wins) / len(trades) * 100, 1),
            profit_factor = round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else 999.0,
            total_pnl_pct = round(equity[-1] - 100, 2),
            max_drawdown  = round(max_dd, 2),
            sharpe_ratio  = round(sharpe, 2),
            trades        = trades,
            equity_curve  = [round(e, 2) for e in equity],
        )

        logger.info(
            f"✅ Бэктест {symbol}: {result.total_trades} сделок, "
            f"WR={result.winrate}%, PF={result.profit_factor}, "
            f"PnL={result.total_pnl_pct:+.1f}%"
        )
        return result


backtest_engine = BacktestEngine()
