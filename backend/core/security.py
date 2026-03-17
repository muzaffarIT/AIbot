from hmac import compare_digest


def is_secret_valid(secret: str | None, candidate: str | None) -> bool:
    if not secret or not candidate:
        return False
    return compare_digest(secret, candidate)


def extract_bearer_token(header_value: str | None) -> str | None:
    if not header_value:
        return None

    prefix = "bearer "
    if header_value.lower().startswith(prefix):
        return header_value[len(prefix):].strip()
    return None
