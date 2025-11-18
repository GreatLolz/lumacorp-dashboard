from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    eve_client_id: str
    eve_client_secret: str
    eve_callback_url: str = "http://localhost:8000/callback"

    esi_client_useragent: str = "lumacorp-api/0.1.0"
    
    token_file_path: str = "./data/tokens.json"
    
    class Config:
        case_sensitive = False

settings = Settings()