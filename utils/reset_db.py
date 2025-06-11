# scripts/reset_db.py
import logging
from core.database import engine
from models.base import Base

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def reset_database():
    log.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine, checkfirst=True)
    log.info("Recreating all tables...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    log.info("Database schema has been reset.")

if __name__ == "__main__":
    reset_database()
