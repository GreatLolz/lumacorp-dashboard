import random
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from fastapi import Response
from fastapi import APIRouter

from app.wallet import get_wallet_balance

wallet_balance_gauge = Gauge("wallet_balance", "Wallet balance per division", ["division"])

router = APIRouter(prefix="/metrics")

@router.get("/")
def metrics():
    balances = get_wallet_balance()
    for name, balance in balances.items():
        wallet_balance_gauge.labels(division=name).set(balance)

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
