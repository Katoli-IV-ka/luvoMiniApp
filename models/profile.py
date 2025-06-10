# backend/models/profile.py
from sqlalchemy import Column, Integer, String, Date, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    instagram_username = Column(String(64), nullable=True)  # Instagram username
    telegram_username = Column(String(64), nullable=True)  # Telegram username
    birthdate = Column(Date, nullable=True)    # Можно хранить дату рождения
    gender = Column(String(length=10), nullable=True)  # Например: "male", "female", "other"
    about = Column(Text, nullable=True)
    # В будущем: latitude, longitude для геолокации
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связь с User (если понадобится)
    user = relationship("User", backref="profile", uselist=False)

    def __repr__(self):
        return f"<Profile user_id={self.user_id} instagram={self.instagram_username}>"
