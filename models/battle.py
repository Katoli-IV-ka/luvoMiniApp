from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Battle(Base):
    __tablename__ = "battles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    opponent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    winner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    opponent = relationship("User", foreign_keys=[opponent_id])
    winner = relationship("User", foreign_keys=[winner_id])

    def __repr__(self) -> str:
        return f"<Battle {self.user_id} vs {self.opponent_id} winner={self.winner_id}>"
