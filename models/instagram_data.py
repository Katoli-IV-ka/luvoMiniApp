# backend/models/instagram_data.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class InstagramData(Base):
    __tablename__ = "instagram_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    ig_username = Column(String(length=150), nullable=False, unique=True)
    last_sync = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    subscriptions = Column(JSON, nullable=True)
    # subscriptions: JSON-список объектов или ID подписок, получаемый через instagrapi

    user = relationship("User", backref="instagram_data")

    def __repr__(self):
        return f"<InstagramData user_id={self.user_id} username={self.ig_username}>"
