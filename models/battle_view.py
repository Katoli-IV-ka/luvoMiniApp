from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func

from .base import Base


class BattleView(Base):
    __tablename__ = "battle_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<BattleView user={self.user_id}>"
