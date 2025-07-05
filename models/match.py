# backend/models/match.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user1 = relationship("User", foreign_keys=[user1_id], backref="matches_as_user1")
    user2 = relationship("User", foreign_keys=[user2_id], backref="matches_as_user2")

    def __repr__(self):
        return f"<Match {self.user1_id}↔{self.user2_id}>"
