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

import hashlib
import hmac
import urllib.parse
from fastapi import HTTPException
from backend.core.config import settings

def verify_telegram_data(init_data: str) -> dict:
    if not settings.bot_token:
        raise HTTPException(500, "BOT_TOKEN not configured")
        
    bot_token = settings.bot_token.strip()

    parsed_data = dict(urllib.parse.parse_qsl(init_data.strip()))
    if 'hash' not in parsed_data:
        raise HTTPException(401, "Missing hash in initData")
    
    received_hash = parsed_data.pop('hash')
    
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items(), key=lambda x: x[0]))
    
    secret_key = hmac.new(b"WebAppData", bot_token.encode('utf-8'), hashlib.sha256).digest()
    
    calculated_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
    
    if calculated_hash != received_hash:
        raise HTTPException(401, "Invalid Signature")
        
    return parsed_data
