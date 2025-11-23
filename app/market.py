from app.esi import esi_manager
from app.config import settings
from app.sde import Item, get_items
import os
import json
from typing import List, Dict
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
import asyncio
from datetime import datetime, timedelta, timezone

material_prices = {}

PROFIT_INDEX_PATH = "./data/market/profit_index.json"

executor = ThreadPoolExecutor(max_workers=4)

class ProfitIndex(BaseModel):
    item_name: str
    item_id: int
    profit_index: float
    sell_price: float
    production_cost: float
    avg_volume: float
    blueprint_cost: float
    return_time_seconds: float


def _get_lowest_order_price(type_id: int, order_type: str) -> float:
    esi = esi_manager.get_client()
    orders = esi.get_op("get_markets_region_id_orders", region_id=settings.region_id, type_id=type_id, order_type=order_type)
    if not orders:
        return 0

    lowest_price = 0
    for order in orders:
        if not lowest_price or order["price"] < lowest_price:
            lowest_price = order["price"]
    return lowest_price

def _get_item_margin(item: Item) -> float:
    sell_price = _get_lowest_order_price(item.type_id, "sell")
    if not sell_price:
        return 0

    production_cost = 0
    for material in item.materials:
        material_price = material_prices.get(material.type_id)
        if not material_price:
            material_price = _get_lowest_order_price(material.type_id, "sell")
            material_prices[material.type_id] = material_price
        production_cost += material_price * material.quantity

    return sell_price - production_cost

def _get_item_daily_avg_volume(item: Item) -> float:
    esi = esi_manager.get_client()
    
    # Get history data
    history = esi.get_op("get_markets_region_id_history", region_id=settings.region_id, type_id=item.type_id)
    
    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=settings.avg_daily_volume_window)
    
    total_volume = 0
    
    for entry in history:
        entry_date = datetime.strptime(entry['date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
        if start_date <= entry_date < end_date:
            total_volume += entry['volume']
            
    return total_volume / settings.avg_daily_volume_window

def _get_item_profit_index(item: Item) -> tuple[float, float, float, float]:
    sell_price = _get_lowest_order_price(item.type_id, "sell")
    if not sell_price:
        return 0, 0, 0, 0
        
    production_cost = 0
    for material in item.materials:
        material_price = material_prices.get(material.type_id)
        if not material_price:
            material_price = _get_lowest_order_price(material.type_id, "sell")
            material_prices[material.type_id] = material_price
        production_cost += material_price * material.quantity
        
    margin = sell_price - production_cost
    if not margin:
        return 0, 0, 0, 0
        
    daily_avg_volume = _get_item_daily_avg_volume(item)
    if not daily_avg_volume:
        return 0, 0, 0, 0
    
    return margin * daily_avg_volume, sell_price, production_cost, daily_avg_volume

def _calculate_profit_indexes(items: list[Item]) -> list[ProfitIndex]:
    profit_indexes: list[ProfitIndex] = []
    for item in items:
        profit_index, sell_price, production_cost, daily_avg_volume = _get_item_profit_index(item)
        if not profit_index or profit_index < 0 or profit_index < settings.min_profit_threshold:
            continue
        blueprint_cost = _get_lowest_order_price(item.blueprint_id, "sell")
        return_time_seconds = (blueprint_cost / profit_index) * 24 * 60 * 60

        profit_indexes.append(ProfitIndex(
            item_name=item.name, 
            item_id=item.type_id, 
            profit_index=profit_index,
            sell_price=sell_price,
            production_cost=production_cost,
            avg_volume=daily_avg_volume,
            blueprint_cost=blueprint_cost,
            return_time_seconds=return_time_seconds
        ))

    profit_indexes = sorted(profit_indexes, key=lambda x: x.profit_index, reverse=True)[:settings.max_profit_indexes-1]
    
    with open(PROFIT_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump([pi.model_dump() for pi in profit_indexes], f, indent=4)

    return profit_indexes

async def get_profit_indexes(refresh: bool = False) -> list[ProfitIndex]:
    if not refresh and os.path.exists(PROFIT_INDEX_PATH):
        with open(PROFIT_INDEX_PATH, "r", encoding="utf-8") as f:
            profit_indexes = [ProfitIndex.model_validate(pi) for pi in json.load(f)]
        return profit_indexes

    items = await get_items()
    loop = asyncio.get_event_loop()
    print("[MARKET] Calculating profit indexes")
    profit_indexes = await loop.run_in_executor(executor, _calculate_profit_indexes, items)
    print("[MARKET] Profit indexes calculated")
    return profit_indexes

    