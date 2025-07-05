from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from core.id_generator import generate_random_id

# Общий Base для всех моделей
Base = declarative_base()


@event.listens_for(Base, "before_insert", propagate=True)
def assign_random_id(mapper, connection, target):
    if getattr(target, "id", None) is None:
        entity = target.__tablename__
        target.id = generate_random_id(entity)