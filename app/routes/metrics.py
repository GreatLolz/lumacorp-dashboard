import os
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from fastapi import Response
from fastapi import APIRouter

from app.wallet import get_wallet_balance
from app.market import get_profit_indexes, PROFIT_INDEX_PATH
from app.config import settings

# Single gauge for all item metrics with each metric as a separate label
item_metrics_gauge = Gauge(
    "item_metrics",
    "All item metrics",
    [
        "item_name",
        "item_id",
        "profitability",
        "sell_price",
        "production_cost",
        "avg_volume",
        "blueprint_cost",
        "return_time_seconds"
    ]
)

wallet_balance_gauge = Gauge(
    "wallet_balance",
    "Wallet balance per division",
    ["division"]
)

router = APIRouter(prefix="/metrics")

@router.get("/")
async def metrics():
    wallet_balance_gauge.clear()
    item_metrics_gauge.clear()

    balances = get_wallet_balance()
    for name, balance in balances.items():
        wallet_balance_gauge.labels(division=name).set(balance)

    if not os.path.exists(PROFIT_INDEX_PATH):
        return Response(status_code=200)
        
    profit_indexes = await get_profit_indexes()
    
    for index in profit_indexes:
        item_metrics_gauge.labels(
            item_name=index.item_name,
            item_id=index.item_id,
            profitability=index.profit_index,
            sell_price=index.sell_price,
            production_cost=index.production_cost,
            avg_volume=index.avg_volume,
            blueprint_cost=index.blueprint_cost,
            return_time_seconds=index.return_time_seconds
        ).set(index.profit_index)
        
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    
