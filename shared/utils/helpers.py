from uuid import uuid4


def generate_order_number() -> str:
    return uuid4().hex[:12].upper()