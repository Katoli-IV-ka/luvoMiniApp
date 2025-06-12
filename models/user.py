# backend/models/user.py
from sqlalchemy import Column, Integer, BigInteger, DateTime, Boolean, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    premium_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Изменено: используем back_populates вместо backref
    profile = relationship("Profile", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User id={self.id} telegram_id={self.telegram_user_id}>"