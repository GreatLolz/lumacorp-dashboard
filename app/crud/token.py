from sqlalchemy.orm import Session
from app.models.token import RefreshToken
from app.utils.encrypt import encrypt, decrypt

def get_refresh_token(db: Session):
    token = db.query(RefreshToken).first()
    if token:
        token.refresh_token = decrypt(token.refresh_token)
    return token

def save_refresh_token(db: Session, refresh_token: str, character_id: str):
    encrypted_token = encrypt(refresh_token)

    token = get_refresh_token(db)
    if token:
        token.refresh_token = encrypted_token
        token.character_id = character_id
    else:
        token = RefreshToken(id=1, refresh_token=encrypted_token, character_id=character_id)
        db.add(token)
    db.commit()
    