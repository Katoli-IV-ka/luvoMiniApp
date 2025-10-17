from sqlalchemy import Column, Integer, DateTime, ForeignKey, Date
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


class BattleSession(Base):
    __tablename__ = "battle_sessions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    completed_rounds = Column(Integer, nullable=False, default=0)
    left_profile_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    right_profile_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    final_winner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    battle_date = Column(Date, nullable=False, default=func.current_date())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", foreign_keys=[owner_id])
    left_profile = relationship("User", foreign_keys=[left_profile_id])
    right_profile = relationship("User", foreign_keys=[right_profile_id])
    final_winner = relationship("User", foreign_keys=[final_winner_id])

    def __repr__(self) -> str:
        return (
            "<BattleSession owner="
            f"{self.owner_id} rounds={self.completed_rounds} "
            f"final={self.final_winner_id}>"
        )
