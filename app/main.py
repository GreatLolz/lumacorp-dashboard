from fastapi import FastAPI
from app.db import engine, Base
from app.models.token import RefreshToken

app = FastAPI()

Base.metadata.create_all(bind=engine)

from app.routes import auth, metrics

app.include_router(auth.router)
app.include_router(metrics.router)