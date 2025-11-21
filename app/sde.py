from fastapi import HTTPException
from pydantic import BaseModel
from requests import HTTPError
from app.esi import esi_manager
from app.utils.parse import parse_jsonl
import os
import json
from app.config import settings

TYPES_PATH = "./data/sde/types.jsonl"
BLUEPRINTS_PATH = "./data/sde/blueprints.jsonl"
PARSED_PATH = "./data/sde/parsed/items.json"

class Material(BaseModel):
    type_id: int
    name: str
    quantity: int

class Item(BaseModel):
    blueprint_id: int
    type_id: int
    name: str
    materials: list[Material]

items_cache: list[Item] = []
market_order_type_ids: set[int] = set()

def _get_market_order_type_ids() -> set[int]:
    global market_order_type_ids
    if market_order_type_ids:
        return market_order_type_ids

    esi = esi_manager.get_client()

    page = 1
    type_ids = set()

    while True:
        try:
            orders = esi.get_op("get_markets_region_id_orders", region_id=settings.region_id, page=page)
        except HTTPError as e:
            if e.response.status_code == 404:
                break

        for order in orders:
            type_ids.add(order["type_id"])

        page += 1

    market_order_type_ids = type_ids
    return type_ids

def _is_blueprint_available(blueprint_id: int) -> bool:
    return blueprint_id in _get_market_order_type_ids()

def _parse_sde_files() -> list[Item]:
    item_names = {}
    for item in parse_jsonl(TYPES_PATH):
        item_names[item.get("_key")] = item.get("name").get("en")

    items: list[Item] = []
    for blueprint in parse_jsonl(BLUEPRINTS_PATH):
        blueprint_id = blueprint.get("blueprintTypeID")

        manufacturing = blueprint.get("activities").get("manufacturing")
        if not manufacturing:
            continue

        products = manufacturing.get("products")
        if not products or len(products) > 1:
            continue
        
        type_id = products[0].get("typeID")
        name = item_names.get(type_id)
        if not name:
            continue
        
        materials = manufacturing.get("materials")
        if not materials:
            continue
        
        materials_list: list[Material] = []
        for material in materials:
            type_id = material.get("typeID")
            quantity = material.get("quantity")
            material_name = item_names.get(type_id)
            if not material_name:
                continue
            materials_list.append(Material(type_id=type_id, name=material_name, quantity=quantity))

        items.append(Item(blueprint_id=blueprint_id, type_id=type_id, name=name, materials=materials_list))
    return items

def get_items() -> list[Item]:
    global items_cache
    if items_cache:
        return items_cache

    if os.path.exists(PARSED_PATH):
        with open(PARSED_PATH, "r", encoding="utf-8") as f:
            items_cache = json.load(f)
        return items_cache

    items = _parse_sde_files()
    print("Total items: ", len(items))
    items = [item for item in items if _is_blueprint_available(item.blueprint_id)]
    print("Items with available blueprint: ", len(items))
    
    items_cache = items
    with open(PARSED_PATH, "w", encoding="utf-8") as f:
        json.dump([i.model_dump() for i in items], f, indent=4)

    return items

