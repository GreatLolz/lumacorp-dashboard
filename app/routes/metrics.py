from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from fastapi import Response
from fastapi import APIRouter

from app.wallet import get_wallet_balance
from app.market import get_profit_indexes, get_corp_profit_indexes
from app.config import settings

# Gauges follow Prometheus conventions: value is the metric, labels identify the series.
item_labels = ["item_id", "item_name", "source"]

profit_index_gauge = Gauge("esi_item_profit_index", "Profit index per item", item_labels)
sell_price_gauge = Gauge("esi_item_sell_price", "Sell price per item", item_labels)
production_cost_gauge = Gauge("esi_item_production_cost", "Production cost per item", item_labels)
avg_volume_gauge = Gauge("esi_item_avg_volume", "Average daily volume per item", item_labels)
blueprint_cost_gauge = Gauge("esi_item_blueprint_cost", "Blueprint cost per item", item_labels)
return_time_gauge = Gauge("esi_item_return_time_seconds", "Return time per item (seconds)", item_labels)

wallet_balance_gauge = Gauge(
    "esi_wallet_balance",
    "Wallet balance per division",
    ["division"]
)

router = APIRouter(prefix="/metrics")


def _set_item_metrics(indexes, source: str):
    for index in indexes:
        labels = dict(item_id=index.item_id, item_name=index.item_name, source=source)
        profit_index_gauge.labels(**labels).set(index.profit_index)
        sell_price_gauge.labels(**labels).set(index.sell_price)
        production_cost_gauge.labels(**labels).set(index.production_cost)
        avg_volume_gauge.labels(**labels).set(index.avg_volume)
        blueprint_cost_gauge.labels(**labels).set(index.blueprint_cost)
        return_time_gauge.labels(**labels).set(index.return_time_seconds)


@router.get("/")
async def metrics():
    # Clear gauges so removed items go stale and stop emitting.
    wallet_balance_gauge.clear()
    profit_index_gauge.clear()
    sell_price_gauge.clear()
    production_cost_gauge.clear()
    avg_volume_gauge.clear()
    blueprint_cost_gauge.clear()
    return_time_gauge.clear()

    balances = get_wallet_balance()
    for name, balance in balances.items():
        wallet_balance_gauge.labels(division=name).set(balance)

    profit_indexes = await get_profit_indexes()
    _set_item_metrics(profit_indexes, source="market")

    corp_profit_indexes = await get_corp_profit_indexes()
    _set_item_metrics(corp_profit_indexes, source="corp")

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    
