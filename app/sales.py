from datetime import datetime, timedelta, timezone
from typing import List

from requests import HTTPError

from app.config import settings
from app.db import SessionLocal
from app.esi import esi_manager
from app.models.transaction import CorpTransaction
from app.crud.transactions import (
    get_latest_transaction_id,
    upsert_transactions,
    prune_transactions_before,
    get_sales_sums_since,
)
from app.sde import get_type_name


class CorpSoldAverage:
    def __init__(self, item_id: int, item_name: str, avg_volume: float):
        self.item_id = item_id
        self.item_name = item_name
        self.avg_volume = avg_volume


def _fetch_transactions_for_division(division: int, last_seen: int | None) -> list[CorpTransaction]:
    esi = esi_manager.get_client()
    all_new: list[CorpTransaction] = []
    from_id = None
    seen = 0
    pages = 0
    last_from_id = None

    while True:
        try:
            params = dict(
                corporation_id=settings.corp_id,
                division=division,
            )
            if from_id:
                params["from_id"] = from_id

            batch = esi.get_op(
                "get_corporations_corporation_id_wallets_division_transactions",
                **params,
                _request_options={"timeout": 15},
            )
        except HTTPError as e:
            if e.response.status_code in (401, 403):
                print(f"[SALES] Unauthorized for division {division}; check roles/scope")
                return []
            raise

        if not batch:
            print(f"[SALES] Division {division}: no more transactions (pages={pages}, seen={seen})", flush=True)
            break

        # ESI returns most recent first; stop when we hit older/equal to last_seen
        stop = False
        for row in batch:
            txn_id = row["transaction_id"]
            if last_seen and txn_id <= last_seen:
                stop = True
                continue
            all_new.append(
                CorpTransaction(
                    transaction_id=txn_id,
                    division=division,
                    type_id=row["type_id"],
                    quantity=row["quantity"],
                    is_buy=row["is_buy"],
                    unit_price=row["unit_price"],
                    date=datetime.fromisoformat(row["date"].replace("Z", "+00:00")),
                )
            )
            seen += 1

        if stop:
            break

        pages += 1
        new_from_id = min(row["transaction_id"] for row in batch)
        if last_from_id is not None and new_from_id == last_from_id:
            print(f"[SALES] Division {division}: no progress on paging (from_id {new_from_id}); stopping", flush=True)
            break

        from_id = new_from_id
        last_from_id = new_from_id

        # Safety guard to avoid runaway loops
        if pages > 500:
            print(f"[SALES] Division {division}: paging stopped after {pages} pages", flush=True)
            break

    print(f"[SALES] Division {division}: fetched {seen} new transactions", flush=True)
    return all_new


def ingest_corp_sales() -> None:
    if not settings.corp_id:
        print("[SALES] Skipping ingest; corp_id not set")
        return

    with SessionLocal() as db:
        divisions = []
        try:
            divisions = [
                div["division"]
                for div in esi_manager.get_client().get_op(
                    "get_corporations_corporation_id_divisions",
                    corporation_id=settings.corp_id,
                )["wallet"]
            ]
        except HTTPError as e:
            print(f"[SALES] Unable to fetch divisions: {e}")
            return

        print(f"[SALES] Divisions detected: {divisions}", flush=True)
        total_new = 0
        for division in divisions:
            last_seen = get_latest_transaction_id(db, division)
            print(f"[SALES] Division {division}: last_seen={last_seen}", flush=True)
            new_txns = _fetch_transactions_for_division(division, last_seen)
            if new_txns:
                inserted = upsert_transactions(db, new_txns)
                total_new += inserted
                print(f"[SALES] Division {division}: inserted {inserted} rows", flush=True)

        print(f"[SALES] Ingested {total_new} new corp transactions", flush=True)

        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.corp_sales_window_days)
        pruned = prune_transactions_before(db, cutoff)
        print(f"[SALES] Pruned {pruned} old transactions (cutoff {cutoff.isoformat()})", flush=True)


def get_corp_average_sold_volume() -> List[CorpSoldAverage]:
    window_days = settings.corp_sales_window_days
    if window_days <= 0:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    with SessionLocal() as db:
        sums = get_sales_sums_since(db, cutoff)

    averages: list[CorpSoldAverage] = []
    for type_id, total_qty in sums:
        avg = total_qty / window_days if window_days else 0
        averages.append(
            CorpSoldAverage(
                item_id=type_id,
                item_name=get_type_name(type_id),
                avg_volume=avg,
            )
        )
    return averages
