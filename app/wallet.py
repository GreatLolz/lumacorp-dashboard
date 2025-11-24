import asyncio

from app.cache import get_json, set_json
from app.esi import esi_manager
from app.config import settings

WALLET_DIVISIONS_KEY = "wallet:divisions"
WALLET_BALANCES_KEY = "wallet:balances"


def get_wallet_divisions():
    cached = get_json(WALLET_DIVISIONS_KEY)
    if cached:
        return cached

    esi = esi_manager.get_client()
    divisions = esi.get_op(
        "get_corporations_corporation_id_divisions",
        corporation_id=settings.corp_id,
    )["wallet"]
    set_json(WALLET_DIVISIONS_KEY, divisions, ex=24 * 60 * 60)
    return divisions


def get_wallet_balance():
    cached = get_json(WALLET_BALANCES_KEY)
    if cached:
        return cached
    return _fetch_wallet_balance()


def _fetch_wallet_balance() -> dict[str, float]:
    divisions: dict[str, float] = {}

    for div in get_wallet_divisions():
        division = div["division"]
        name = div.get("name", "Master")
        esi = esi_manager.get_client()
        divisions[name] = esi.get_op(
            "get_corporations_corporation_id_wallets",
            corporation_id=settings.corp_id,
        )[division - 1]["balance"]

    set_json(
        WALLET_BALANCES_KEY,
        divisions,
        ex=max(settings.wallet_refresh_seconds * 2, 60),
    )
    return divisions


async def refresh_wallet_balances() -> dict[str, float]:
    """Refresh wallet balances in the background."""
    return await asyncio.to_thread(_fetch_wallet_balance)
