import random
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from fastapi import Response
from fastapi import APIRouter

wallet_balance = Gauge("wallet_balance", "Wallet balance")

router = APIRouter(prefix="/metrics")

@router.get("/")
def metrics():
    wallet_balance.set(random.randint(0, 1000000))
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
