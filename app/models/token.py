from app.db import Base
from sqlalchemy import Column, String, Integer

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, default=1)
    refresh_token = Column(String)
    character_id = Column(String)
