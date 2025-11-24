from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.config import settings
from app.db import engine, Base
from app.esi import esi_manager
from app.market import get_profit_indexes, get_corp_profit_indexes
from app.wallet import refresh_wallet_balances


async def refresh_profit_data() -> None:
    """Refresh both public and corp blueprint profitability snapshots."""
    esi_manager.get_client()
    if not settings.character_id:
        print("[SCHED] Profit refresh skipped; character not authenticated")
        return

    await get_profit_indexes(refresh=True)
    await get_corp_profit_indexes(refresh=True)


async def refresh_wallet_data() -> None:
    """Refresh wallet balances snapshot."""
    esi_manager.get_client()
    if not settings.corp_id:
        print("[SCHED] Wallet refresh skipped; corp not set")
        return
    await refresh_wallet_balances()


def _job_wrapper(coro: Callable[[], Awaitable[None]], name: str) -> Callable[[], Awaitable[None]]:
    async def runner():
        try:
            await coro()
        except Exception as exc:
            print(f"[SCHED] Job '{name}' error: {exc}")
    return runner


def _start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=timezone.utc)

    scheduler.add_job(
        _job_wrapper(refresh_profit_data, "profit-refresh"),
        trigger="interval",
        seconds=max(1, settings.profit_refresh_seconds),
        id="profit-refresh",
        coalesce=True,
        max_instances=1,
        next_run_time=datetime.now(tz=timezone.utc),
    )
    scheduler.add_job(
        _job_wrapper(refresh_wallet_data, "wallet-refresh"),
        trigger="interval",
        seconds=max(1, settings.wallet_refresh_seconds),
        id="wallet-refresh",
        coalesce=True,
        max_instances=1,
        next_run_time=datetime.now(tz=timezone.utc),
    )

    scheduler.start()
    print("[SCHED] Scheduler started with jobs: profit-refresh, wallet-refresh")
    return scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = _start_scheduler()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        print("[SCHED] Scheduler stopped")


app = FastAPI(lifespan=lifespan)

Base.metadata.create_all(bind=engine)

from app.routes import auth, metrics

app.include_router(auth.router)
app.include_router(metrics.router)
