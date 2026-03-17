import json
from pathlib import Path
from typing import Any


class I18n:
    def __init__(self, locales_dir: str = "locales") -> None:
        self.locales_dir = Path(locales_dir)
        self.messages: dict[str, dict[str, str]] = {}
        self.load()

    def load(self) -> None:
        if not self.locales_dir.exists():
            return

        for lang_dir in self.locales_dir.iterdir():
            if not lang_dir.is_dir():
                continue

            messages_file = lang_dir / "messages.json"
            if not messages_file.exists():
                continue

            with messages_file.open("r", encoding="utf-8") as f:
                self.messages[lang_dir.name] = json.load(f)

    def t(self, lang: str, key: str, **kwargs: Any) -> str:
        lang_messages = self.messages.get(lang) or self.messages.get("ru", {})
        template = lang_messages.get(key, key)

        if kwargs:
            try:
                return template.format(**kwargs)
            except Exception:
                return template

        return template