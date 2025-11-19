from app.esi import esi_manager
from app.config import settings

wallet_divisions: dict[int, str] | None = None

def get_wallet_divisions():
    global wallet_divisions
    if wallet_divisions is None:
        esi = esi_manager.get_client()
        wallet_divisions = esi.get_op("get_corporations_corporation_id_divisions", corporation_id=settings.corp_id)["wallet"]
    return wallet_divisions

def get_wallet_balance():
    divisions: dict[str, float] = {}

    for div in get_wallet_divisions():
        division = div["division"]
        name = div.get("name", "Master")
        esi = esi_manager.get_client()
        divisions[name] = esi.get_op("get_corporations_corporation_id_wallets", corporation_id=settings.corp_id)[division-1]["balance"]

    return divisions
