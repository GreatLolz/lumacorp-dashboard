import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.config import settings
from app.db import engine, Base
from app.esi import esi_manager
import app.models.token  # ensure tables are registered
import app.models.transaction  # ensure tables are registered
from app.market import get_profit_indexes, get_corp_profit_indexes
from app.wallet import refresh_wallet_balances
from app.sales import ingest_corp_sales

from app.routes import auth, metrics

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


def _job_wrapper(coro: Callable, name: str, run_in_thread: bool = False) -> Callable[[], Awaitable[None]]:
    async def runner():
        try:
            if asyncio.iscoroutinefunction(coro):
                await coro()
            elif run_in_thread:
                await asyncio.to_thread(coro)
            else:
                coro()
        except Exception as exc:
            print(f"[SCHED] Job '{name}' error: {exc}")
    return runner


def _start_scheduler() -> AsyncIOScheduler:
    # Allow limited overlap and set a grace window to avoid missed runs.
    scheduler = AsyncIOScheduler(
        timezone=timezone.utc,
        job_defaults={"coalesce": True, "max_instances": 2, "misfire_grace_time": 300},
    )

    scheduler.add_job(
        _job_wrapper(refresh_profit_data, "profit-refresh"),
        trigger="interval",
        seconds=max(1, settings.profit_refresh_seconds),
        id="profit-refresh",
        next_run_time=datetime.now(tz=timezone.utc),
    )
    scheduler.add_job(
        _job_wrapper(refresh_wallet_data, "wallet-refresh"),
        trigger="interval",
        seconds=max(1, settings.wallet_refresh_seconds),
        id="wallet-refresh",
        next_run_time=datetime.now(tz=timezone.utc) + timedelta(seconds=5),
    )
    scheduler.add_job(
        _job_wrapper(ingest_corp_sales, "corp-sales-ingest", run_in_thread=True),
        trigger="interval",
        seconds=max(1, settings.corp_sales_refresh_seconds),
        id="corp-sales-ingest",
        next_run_time=datetime.now(tz=timezone.utc) + timedelta(seconds=10),
    )

    scheduler.start()
    print("[SCHED] Scheduler started with jobs: profit-refresh, wallet-refresh, corp-sales-ingest", flush=True)
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

app.include_router(auth.router)
app.include_router(metrics.router)
