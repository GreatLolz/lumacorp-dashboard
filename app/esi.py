from preston import Preston
from app.config import settings

_preston = Preston(
    client_id=settings.eve_client_id,
    client_secret=settings.eve_client_secret,
    callback_url=settings.eve_callback_url,
    user_agent=settings.esi_client_useragent,
    scopes=settings.scopes,
)

esi: Preston | None = None

def get_auth_url():
    return _preston.get_authorize_url()

def authenticate(code: str):
    global esi
    esi = _preston.authenticate(code)
    settings.character_id = esi.whoami().get("character_id")
    settings.corp_id = esi.get_op("get_characters_character_id", character_id=settings.character_id).get("corporation_id")

def get_client() -> Preston:
    if esi is None:
        raise RuntimeError("Client not authenticated.")
    return esi

