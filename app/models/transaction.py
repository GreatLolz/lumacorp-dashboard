from sqlalchemy import Boolean, Column, DateTime, Float, Integer, BigInteger, func, UniqueConstraint, Index

from app.db import Base


class CorpTransaction(Base):
    __tablename__ = "corp_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(BigInteger, unique=True, index=True, nullable=False)
    division = Column(Integer, nullable=False)
    type_id = Column(Integer, index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    is_buy = Column(Boolean, nullable=False)
    unit_price = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("transaction_id", name="uq_corp_transactions_transaction_id"),
        Index("idx_corp_transactions_type_date", "type_id", "date"),
    )
