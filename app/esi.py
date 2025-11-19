from typing import Optional

from preston import Preston
from sqlalchemy.orm import Session

from app.config import settings
from app.crud.token import get_refresh_token, save_refresh_token
from app.db import SessionLocal


class EsiClientManager:
    def __init__(self):
        self._esi: Optional[Preston] = None

    def _create_client(self, refresh_token: Optional[str] = None) -> Preston:
        client = Preston(
            client_id=settings.eve_client_id,
            client_secret=settings.eve_client_secret,
            callback_url=settings.eve_callback_url,
            user_agent=settings.esi_client_useragent,
            scopes=settings.scopes,
            refresh_token=refresh_token,
            refresh_token_callback=self._on_refresh_token,
        )
        return client

    def _on_refresh_token(self, preston: Preston) -> None:
        info = preston.whoami()
        character_id = info.get("character_id")
        new_rt = preston.refresh_token
        if character_id is not None and new_rt is not None:
            with SessionLocal() as db:
                save_refresh_token(db, new_rt, character_id)

    def get_client(self) -> Preston:
        if self._esi is None:
            token = self._load_refresh_token()
            self._esi = self._create_client(token.refresh_token if token else None)

            if token and token.character_id:
                settings.character_id = token.character_id
                corp = self._esi.get_op(
                    "get_characters_character_id",
                    character_id=token.character_id,
                ).get("corporation_id")
                settings.corp_id = corp

        return self._esi

    def _load_refresh_token(self):
        with SessionLocal() as db:
            return get_refresh_token(db)

    def _save_refresh_token(self, refresh_token: str, character_id: int):
        with SessionLocal() as db:
            save_refresh_token(db, refresh_token, character_id)

    def get_auth_url(self) -> str:
        return self.get_client().get_authorize_url()

    def authenticate(self, code: str):
        new_esi = self.get_client().authenticate(code)
        self._esi = new_esi

        info = new_esi.whoami()
        cid = info.get("character_id")
        if cid is None:
            raise RuntimeError("Failed to retrieve character_id from whoami()")

        settings.character_id = cid

        corp = new_esi.get_op(
            "get_characters_character_id", character_id=cid
        ).get("corporation_id")
        settings.corp_id = corp

        rt = new_esi.refresh_token
        if rt is None:
            raise RuntimeError("Authenticate did not return a refresh token")

        self._save_refresh_token(rt, cid)

esi_manager = EsiClientManager()
