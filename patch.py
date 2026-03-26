import os
import json
import re

def inplace_replace(path, old, new):
    with open(path, 'r') as f:
        text = f.read()
    with open(path, 'w') as f:
        f.write(text.replace(old, new))

# ----------------- БЛОК 1 и 2 ----------------- #
gen_path = "worker/tasks/generation_tasks.py"
with open(gen_path, 'r') as f:
    text = f.read()

text = re.sub(
    r'payload = \{\s*"model": "nano-banana-pro",[^}]*"image_input"[^}]*\}\s*\}',
    '''payload = {
                "model": "nano-banana-pro",
                "input": {
                    "prompt": job.prompt,
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                    "output_format": "png",
                    "image_input": [job.source_image_url] if job.source_image_url else []
                }
            }''', text
)

text = re.sub(
    r'payload = \{\s*"model": "veo-3",[^}]*"image_input"[^}]*\}\s*\}',
    '''payload = {
                "model": "veo-3",
                "input": {
                    "prompt": job.prompt,
                    "duration": 8,
                    "resolution": "720p" if quality == "fast" else "1080p"
                }
            }''', text
)

text = re.sub(
    r'payload = \{\s*"model": "kling-v3",[^}]*"image_input"[^}]*\}\s*\}',
    '''payload = {
                "model": "kling-3.0/video",
                "input": {
                    "prompt": job.prompt,
                    "duration": str(duration),
                    "mode": mode,
                    "aspect_ratio": "16:9",
                    "sound": False,
                    "image_urls": [job.source_image_url] if job.source_image_url else []
                }
            }''', text
)

text = re.sub(
    r'code = resp\.get\("code", 0\).*?if not task_id:.*?raise ValueError\(f"Нет taskId: \{resp\}"\)',
    '''code = resp.get("code", 0)
        msg = resp.get("msg", "")

        if code == 402:
            raise ValueError(f"KIE: недостаточно кредитов: {msg}")
        if code == 401:
            raise ValueError(f"KIE: неверный ключ: {msg}")
        if code == 422:
            raise ValueError(f"KIE: неверная модель: {msg}")
        if code != 200:
            raise ValueError(f"KIE error {code}: {msg}")

        data = resp.get("data") or {}
        task_id = (data.get("taskId")
                   or data.get("task_id")
                   or data.get("recordId"))
        if not task_id:
            raise ValueError(f"Нет taskId в ответе: {resp}")''', text, flags=re.DOTALL
)

notify_old = re.search(r'async def _notify\(telegram_id.*?finally:\n        await bot\.session\.close\(\)', text, flags=re.DOTALL).group(0)
notify_new = '''async def _notify_user(telegram_id: int, url: str,
                       provider: str, prompt: str,
                       credits: int, bot_token: str):
    if not bot_token:
        logger.error("[NOTIFY] BOT_TOKEN не задан!")
        return
    from aiogram import Bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.exceptions import TelegramForbiddenError
    bot = Bot(token=bot_token)
    try:
        caption = (
            f"✅ Готово!\\n"
            f"💬 {prompt[:100]}\\n"
            f"💰 Потрачено: {credits} кр."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🔄 Ещё раз",
                callback_data=f"gen_again:{provider}"
            ),
            InlineKeyboardButton(
                text="🏠 Меню",
                callback_data="start_menu"
            )
        ]])
        is_video = provider in (
            "veo", "veo-3", "kling", "kling-3.0/video"
        )
        if is_video:
            await bot.send_video(
                chat_id=telegram_id,
                video=url,
                caption=caption,
                reply_markup=kb
            )
        else:
            await bot.send_photo(
                chat_id=telegram_id,
                photo=url,
                caption=caption,
                reply_markup=kb
            )
        logger.info(f"[NOTIFY] ✅ Отправлено {telegram_id}")
    except TelegramForbiddenError:
        logger.warning(f"[NOTIFY] {telegram_id} заблокировал бота")
    except Exception as e:
        logger.error(f"[NOTIFY] Ошибка: {e}")
    finally:
        await bot.session.close()'''
text = text.replace(notify_old, notify_new)

loop_old = re.search(r'if chat_id:\n\s*loop = asyncio\.new_event_loop\(\)\n\s*try:\n\s*loop\.run_until_complete\(_notify\(.*?\)\)\n\s*finally:\n\s*loop\.close\(\)', text, flags=re.DOTALL).group(0)
loop_new = '''if chat_id:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_notify_user(
                        chat_id,
                        final_result_url,
                        job.provider,
                        job.prompt,
                        job.credits_reserved,
                        settings.bot_token
                    ))
                finally:
                    loop.close()'''
text = text.replace(loop_old, loop_new)

with open(gen_path, 'w') as f:
    f.write(text)


# ----------------- БЛОК 3 ----------------- #
reply_menu_path = "bot/keyboards/reply_menu.py"
with open(reply_menu_path, "w") as f:
    f.write('''from aiogram.types import (ReplyKeyboardMarkup,
                            KeyboardButton, WebAppInfo)
from backend.core.config import settings

def main_reply_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎨 Yaratish"),
                 KeyboardButton(text="💎 Tariflar")],
                [KeyboardButton(text="❓ Yordam")],
                [KeyboardButton(
                    text="🌐 Shaxsiy kabinet",
                    web_app=WebAppInfo(url=(settings.miniapp_url or "").rstrip("/"))
                )],
            ],
            resize_keyboard=True,
            persistent=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎨 Создать"),
             KeyboardButton(text="💎 Тарифы")],
            [KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(
                text="🌐 Открыть кабинет",
                web_app=WebAppInfo(url=(settings.miniapp_url or "").rstrip("/"))
            )],
        ],
        resize_keyboard=True,
        persistent=True
    )
''')


# ----------------- БЛОК 4 ----------------- #
ru_json_path = "locales/ru/messages.json"
uz_json_path = "locales/uz/messages.json"

with open(ru_json_path, 'r') as f:
    ru_data = json.load(f)

ru_data["common"] = {
    "cancel": "❌ Отмена",
    "back": "← Назад",
    "yes": "✅ Да",
    "no": "❌ Нет"
}
ru_data["errors"]["rate_limit"] = "⏳ Слишком много запросов. Подожди минуту."
ru_data["prompt_hint"] = "✏️ Опиши что хочешь создать:\\nМожно на русском, узбекском или английском!\\n\\nПример: неоновый город ночью, кинематографично"

with open(ru_json_path, 'w') as f:
    json.dump(ru_data, f, ensure_ascii=False, indent=4)

with open(uz_json_path, 'r') as f:
    uz_data = json.load(f)

uz_data["common"] = {
    "cancel": "❌ Bekor qilish",
    "back": "← Orqaga",
    "yes": "✅ Ha",
    "no": "❌ Yo'q"
}
uz_data["errors"]["rate_limit"] = "⏳ Juda ko'p so'rov. Bir daqiqa kuting."
uz_data["prompt_hint"] = "✏️ Nima yaratmoqchiliginizni tasvirlab bering:\\nRus, o'zbek yoki ingliz tilida yozsa bo'ladi!\\n\\nMisol: tungi neon shahar, kinematografik"

with open(uz_json_path, 'w') as f:
    json.dump(uz_data, f, ensure_ascii=False, indent=4)


# ----------------- БЛОК 8 ----------------- #
config_path = "backend/core/config.py"
with open(config_path, "r") as f:
    text = f.read()

text = re.sub(
    r'@property\n\s*def admin_ids_list\(self\) -> list\[int\]:.*?(?=    welcome_credits: int)',
    '''@property
    def admin_ids_list(self) -> list[int]:
        if not self.admin_ids:
            return []
        return [
            int(x.strip())
            for x in self.admin_ids.replace(";",",").split(",")
            if x.strip().isdigit()
        ]

''', text, flags=re.DOTALL
)

with open(config_path, "w") as f:
    f.write(text)
    
print("Settings patched successfully.")
