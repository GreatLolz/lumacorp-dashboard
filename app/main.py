from fastapi import FastAPI, Depends
from app.esi import get_client
from app.routes import auth, metrics
from app.config import settings
from preston import Preston

app = FastAPI()

app.include_router(auth.router)
app.include_router(metrics.router)