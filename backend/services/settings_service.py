from sqlalchemy.orm import Session
from backend.models.setting import Setting

class SettingsService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str, default: any = None) -> any:
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        if not setting:
            return default
        return setting.value

    def get_int(self, key: str, default: int = 0) -> int:
        val = self.get(key)
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def set(self, key: str, value: any):
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = Setting(key=key, value=str(value))
            self.db.add(setting)
        self.db.commit()
