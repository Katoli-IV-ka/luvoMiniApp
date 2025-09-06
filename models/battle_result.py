# models/battle_result.py
from sqlalchemy import Column, BigInteger, ForeignKey, DateTime
from sqlalchemy.sql import func

from .base import Base


class BattleResult(Base):
    __tablename__ = "battle_results"

    id = Column(BigInteger, primary_key=True, index=True)
    winner_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    loser_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<BattleResult winner={self.winner_id} loser={self.loser_id}>"
