from fastapi import HTTPException
from pydantic import BaseModel
from requests import HTTPError
from app.cache import get_json, set_json
from app.esi import esi_manager
from app.utils.parse import parse_jsonl
import os
import json
from app.config import settings
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

TYPES_PATH = "./data/sde/types.jsonl"
BLUEPRINTS_PATH = "./data/sde/blueprints.jsonl"
PARSED_PATH = "./data/sde/parsed/items.json"
MARKET_TYPE_CACHE_KEY = "sde:market_order_type_ids"
CORP_BLUEPRINT_CACHE_KEY = "sde:corp_blueprint_type_ids"
CHARACTER_SKILLS_CACHE_KEY = "sde:character_skills"

MARKET_CACHE_TTL = 6 * 60 * 60
CORP_BP_CACHE_TTL = 60 * 60
SKILL_CACHE_TTL = 12 * 60 * 60

executor = ThreadPoolExecutor(max_workers=4)

class Material(BaseModel):
    type_id: int
    name: str
    quantity: int

class Skills(BaseModel):
    skill_id: int
    level: int

class Item(BaseModel):
    blueprint_id: int
    type_id: int
    name: str
    materials: list[Material]
    blueprint_skills: list[Skills]


def _get_market_order_type_ids() -> set[int]:
    cached = get_json(MARKET_TYPE_CACHE_KEY)
    if cached:
        return set(cached)

    esi = esi_manager.get_client()

    page = 1
    type_ids = set()

    while True:
        try:
            orders = esi.get_op(
                "get_markets_region_id_orders",
                region_id=settings.region_id,
                page=page,
                order_type="sell",
            )
        except HTTPError as e:
            if e.response.status_code == 404:
                break
            raise

        if not orders:
            break

        for order in orders:
            type_ids.add(order["type_id"])

        page += 1

    set_json(MARKET_TYPE_CACHE_KEY, list(type_ids), ex=MARKET_CACHE_TTL)
    return type_ids


def _get_corp_blueprint_type_ids(refresh: bool = False) -> set[int]:
    cached = get_json(CORP_BLUEPRINT_CACHE_KEY)
    if cached and not refresh:
        return set(cached)

    if not settings.corp_id:
        return set()

    esi = esi_manager.get_client()

    page = 1
    type_ids = set()

    while True:
        try:
            blueprints = esi.get_op(
                "get_corporations_corporation_id_blueprints",
                corporation_id=settings.corp_id,
                page=page,
            )
        except HTTPError as e:
            if e.response.status_code == 404:
                break
            raise

        if not blueprints:
            break

        for bp in blueprints:
            type_ids.add(bp["type_id"])

        page += 1

    set_json(CORP_BLUEPRINT_CACHE_KEY, list(type_ids), ex=CORP_BP_CACHE_TTL)
    print("[SDE] Corp blueprint types: ", len(type_ids))
    return type_ids


def _get_character_skills() -> list[Skills]:
    cache_key = f"{CHARACTER_SKILLS_CACHE_KEY}:{settings.character_id}"
    cached = get_json(cache_key)
    if cached:
        return [Skills(**skill) for skill in cached]

    if not settings.character_id:
        return []

    esi = esi_manager.get_client()
    skills = esi.get_op(
        "get_characters_character_id_skills",
        character_id=settings.character_id,
    )["skills"]
    parsed = [
        Skills(skill_id=skill.get("skill_id"), level=skill.get("active_skill_level"))
        for skill in skills
    ]
    set_json(cache_key, [skill.model_dump() for skill in parsed], ex=SKILL_CACHE_TTL)
    print("Discoverd skills: ", len(parsed))
    return parsed

def _character_has_skills(item: Item, skills: list[Skills] | None = None) -> bool:
    character_skills = skills or _get_character_skills()

    for blueprint_skill in item.blueprint_skills:
        if blueprint_skill.skill_id not in [s.skill_id for s in character_skills]:
            return False

        if blueprint_skill.level > [s.level for s in character_skills if s.skill_id == blueprint_skill.skill_id][0]:
            return False
    return True

def _is_blueprint_available(item: Item) -> bool:
    return item.blueprint_id in _get_market_order_type_ids() and _character_has_skills(item)

def _is_corp_blueprint_owned(item: Item) -> bool:
    return item.blueprint_id in _get_corp_blueprint_type_ids() and _character_has_skills(item)

def _parse_sde_raw_items() -> list[Item]:
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
            material_type_id = material.get("typeID")
            quantity = material.get("quantity")
            material_name = item_names.get(material_type_id)
            if not material_name:
                continue
            materials_list.append(Material(type_id=material_type_id, name=material_name, quantity=quantity))

        skills = manufacturing.get("skills")
        if not skills:
            continue

        skills_list: list[Skills] = []
        for skill in skills:
            skills_list.append(Skills(skill_id=skill.get("typeID"), level=skill.get("level")))

        items.append(Item(
            blueprint_id=blueprint_id, 
            type_id=type_id, 
            name=name, 
            materials=materials_list,
            blueprint_skills=skills_list
        ))

    return items

def _filter_market_available_items(items: list[Item]) -> list[Item]:
    print("[SDE] Total items: ", len(items))
    available_ids = _get_market_order_type_ids()
    skills = _get_character_skills()
    available_items = [
        item
        for item in items
        if item.blueprint_id in available_ids and _character_has_skills(item, skills)
    ]
    print("[SDE] Items with available blueprint: ", len(available_items))
    return available_items

def _filter_corp_owned_items(items: list[Item]) -> list[Item]:
    print("[SDE] Total items: ", len(items))
    owned_ids = _get_corp_blueprint_type_ids(refresh=True)
    skills = _get_character_skills()
    corp_items = [
        item for item in items if item.blueprint_id in owned_ids and _character_has_skills(item, skills)
    ]
    print("[SDE] Items with corp-owned blueprint: ", len(corp_items))
    return corp_items

async def get_items() -> list[Item]:
    loop = asyncio.get_event_loop()
    print("[SDE] Processing SDE files")
    raw_items = await loop.run_in_executor(executor, _parse_sde_raw_items)
    items = await loop.run_in_executor(executor, _filter_market_available_items, raw_items)
    print("[SDE] SDE files processed")    

    return items

async def get_corp_blueprint_items() -> list[Item]:
    loop = asyncio.get_event_loop()
    print("[SDE] Processing SDE files for corp blueprints")
    raw_items = await loop.run_in_executor(executor, _parse_sde_raw_items)
    items = await loop.run_in_executor(executor, _filter_corp_owned_items, raw_items)
    print("[SDE] Corp blueprint SDE processed")
    return items


@lru_cache(maxsize=1)
def _type_name_map() -> dict[int, str]:
    names: dict[int, str] = {}
    for item in parse_jsonl(TYPES_PATH):
        names[item.get("_key")] = item.get("name").get("en")
    return names


def get_type_name(type_id: int) -> str:
    return _type_name_map().get(type_id, str(type_id))
