from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import engine, Base
from app.market import get_profit_indexes
import asyncio

async def load_data():
    try:
        while True:
            try:
                await get_profit_indexes(refresh=True)
            except Exception as e:
                print(f"Error loading profit data: {e}")
            for _ in range(24 * 60 * 60 // 10):
                try:
                    await asyncio.sleep(10)
                except asyncio.CancelledError:
                    print("Background task cancelled")
                    return
    except asyncio.CancelledError:
        print("Background task cancelled")
        return

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(load_data())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

Base.metadata.create_all(bind=engine)

from app.routes import auth, metrics

app.include_router(auth.router)
app.include_router(metrics.router)