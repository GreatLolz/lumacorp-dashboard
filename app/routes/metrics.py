import os
import random
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from fastapi import Response
from fastapi import APIRouter

from app.wallet import get_wallet_balance
from app.market import get_profit_indexes, PROFIT_INDEX_PATH
from app.config import settings

wallet_balance_gauge = Gauge("wallet_balance", "Wallet balance per division", ["division"])
profitability_gauge = Gauge("profitability", "Profitability per item", ["item_name", "item_id"])
sell_price_gauge = Gauge("sell_price", "Sell price per item", ["item_name", "item_id"])
production_cost_gauge = Gauge("production_cost", "Production cost per item", ["item_name", "item_id"])

router = APIRouter(prefix="/metrics")

@router.get("/")
def metrics():
    balances = get_wallet_balance()
    for name, balance in balances.items():
        wallet_balance_gauge.labels(division=name).set(balance)

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/profitability")
async def profitability():
    if not os.path.exists(PROFIT_INDEX_PATH):
        return Response(status_code=200)
        
    profit_indexes = await get_profit_indexes()
    
    for index in profit_indexes:
        profitability_gauge.labels(item_name=index.item_name, item_id=index.item_id).set(index.profit_index)
        sell_price_gauge.labels(item_name=index.item_name, item_id=index.item_id).set(index.sell_price)
        production_cost_gauge.labels(item_name=index.item_name, item_id=index.item_id).set(index.production_cost)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
