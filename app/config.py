from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    eve_client_id: str
    eve_client_secret: str
    eve_callback_url: str = "http://localhost:8000/callback"

    esi_client_useragent: str = "lumacorp-api/0.1.0"
    scopes: list[str] = [
        "esi-wallet.read_corporation_wallets.v1",
        "esi-corporations.read_divisions.v1",
        "esi-skills.read_skills.v1",
    ]

    database_url: str = "sqlite:///./data/lumacorp.db"
    refresh_token_secret: str

    character_id: str | None = None
    corp_id: str | None = None
    region_id: int = 10000043
    avg_daily_volume_window: int = 5
    max_profit_indexes: int = 50
    min_profit_threshold: float = 10000000
    
    class Config:
        case_sensitive = False

settings = Settings()