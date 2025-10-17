import random

# Двухзначные коды сущностей
TYPE_POSTFIX = {
    "users": 1,
    "photos": 3,
    "likes": 4,
    "matches": 5,
    "feed_views": 6,
    "battles": 7,
    "battle_sessions": 8,
}


def generate_random_id(entity: str) -> int:
    """Возвращает 8-значный id: 6 случайных цифр + 2-значный постфикс."""
    if entity not in TYPE_POSTFIX:
        raise ValueError(f"Unknown entity for ID generation: {entity}")
    rand6 = random.randint(0, 999_999)
    postfix = TYPE_POSTFIX[entity]
    return rand6 * 100 + postfix
