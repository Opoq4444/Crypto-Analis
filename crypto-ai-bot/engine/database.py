"""engine/database.py — База данных сигналов"""
import asyncio
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from loguru import logger
from config import settings

Base = declarative_base()


class SignalRecord(Base):
    __tablename__ = "signals"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    created_at    = Column(DateTime, default=datetime.utcnow, index=True)
    symbol        = Column(String(20), index=True)
    signal        = Column(String(20))
    score         = Column(Float)
    confidence    = Column(Float)
    entry         = Column(Float)
    stop_loss     = Column(Float)
    take_profit   = Column(Float)
    rr_ratio      = Column(Float)
    blocked       = Column(Boolean, default=False)
    block_reason  = Column(String(100), nullable=True)
    rsi           = Column(Float)
    funding_rate  = Column(Float)
    net_flow      = Column(String(30))
    news_sentiment = Column(String(20))
    ai_reason     = Column(Text)


class BacktestRecord(Base):
    __tablename__ = "backtests"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    run_at        = Column(DateTime, default=datetime.utcnow)
    symbol        = Column(String(20))
    period_start  = Column(String(20))
    period_end    = Column(String(20))
    total_trades  = Column(Integer)
    win_trades    = Column(Integer)
    loss_trades   = Column(Integer)
    winrate       = Column(Float)
    profit_factor = Column(Float)
    total_pnl_pct = Column(Float)
    max_drawdown  = Column(Float)
    sharpe_ratio  = Column(Float)


class Database:
    def __init__(self):
        self.engine  = None
        self._session_factory = None

    async def init(self):
        self.engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self._session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("✅ База данных инициализирована")

    async def save_signal(self, trade_setup) -> int:
        async with self._session_factory() as session:
            record = SignalRecord(
                symbol        = trade_setup.symbol,
                signal        = trade_setup.signal.value,
                score         = trade_setup.score,
                confidence    = trade_setup.confidence,
                entry         = trade_setup.entry,
                stop_loss     = trade_setup.stop_loss,
                take_profit   = trade_setup.take_profit,
                rr_ratio      = trade_setup.rr_ratio,
                blocked       = trade_setup.blocked,
                block_reason  = trade_setup.block_reason,
                rsi           = trade_setup.rsi,
                funding_rate  = trade_setup.funding_rate,
                net_flow      = trade_setup.net_flow,
                news_sentiment= trade_setup.news_sentiment,
                ai_reason     = trade_setup.ai_reason,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record.id

    async def get_recent_signals(self, limit: int = 10) -> List[SignalRecord]:
        from sqlalchemy import select, desc
        async with self._session_factory() as session:
            result = await session.execute(
                select(SignalRecord).order_by(desc(SignalRecord.created_at)).limit(limit)
            )
            return result.scalars().all()

    async def close(self):
        if self.engine:
            await self.engine.dispose()


db = Database()
