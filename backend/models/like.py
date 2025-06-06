# backend/models/like.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    liker_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    liked_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    liker = relationship("User", foreign_keys=[liker_id], backref="likes_given")
    liked = relationship("User", foreign_keys=[liked_id], backref="likes_received")

    def __repr__(self):
        return f"<Like {self.liker_id}→{self.liked_id}>"
