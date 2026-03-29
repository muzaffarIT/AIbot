import json
from fastapi import Header, HTTPException
from backend.core.security import verify_telegram_data
from backend.db.session import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_tma_auth(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Missing or invalid TMA auth header")
    
    init_data = authorization[4:]
    try:
        parsed_data = verify_telegram_data(init_data)
        if 'user' in parsed_data:
            user_data = json.loads(parsed_data['user'])
            return user_data
        raise HTTPException(status_code=400, detail="No user data in initData")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=401, detail=f"Invalid Telegram WebApp auth: {str(e)}")
