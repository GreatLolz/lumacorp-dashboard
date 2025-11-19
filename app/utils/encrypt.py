from cryptography.fernet import Fernet
from app.config import settings

def encrypt(text: str):
    return Fernet(settings.refresh_token_secret).encrypt(text.encode()).decode()

def decrypt(text: str):
    return Fernet(settings.refresh_token_secret).decrypt(text.encode()).decode()