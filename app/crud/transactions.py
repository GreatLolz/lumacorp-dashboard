from datetime import datetime
from typing import Iterable, Sequence

from sqlalchemy import func, select, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.models.transaction import CorpTransaction


def get_latest_transaction_id(db: Session, division: int) -> int | None:
    stmt = select(func.max(CorpTransaction.transaction_id)).where(
        CorpTransaction.division == division
    )
    result = db.execute(stmt).scalar_one_or_none()
    return result


def upsert_transactions(db: Session, txns: Iterable[CorpTransaction]) -> int:
    """Insert transactions, ignoring duplicates by transaction_id."""
    tx_dicts = [
        dict(
            transaction_id=txn.transaction_id,
            division=txn.division,
            type_id=txn.type_id,
            quantity=txn.quantity,
            is_buy=txn.is_buy,
            unit_price=txn.unit_price,
            date=txn.date,
        )
        for txn in txns
    ]
    if not tx_dicts:
        return 0

    stmt = insert(CorpTransaction).prefix_with("OR IGNORE")
    result = db.execute(stmt, tx_dicts)
    db.commit()
    try:
        count = result.rowcount  # may be None for some dialects
        if count is None or count < 0:
            raise AttributeError
        return count
    except AttributeError:
        return len(tx_dicts)


def prune_transactions_before(db: Session, cutoff: datetime) -> int:
    stmt = delete(CorpTransaction).where(CorpTransaction.date < cutoff)
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


def get_sales_sums_since(
    db: Session, since: datetime
) -> Sequence[tuple[int, int]]:
    stmt = (
        select(CorpTransaction.type_id, func.sum(CorpTransaction.quantity))
        .where(
            CorpTransaction.is_buy.is_(False),
            CorpTransaction.date >= since,
        )
        .group_by(CorpTransaction.type_id)
    )
    return db.execute(stmt).all()
