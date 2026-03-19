import os
from aiogram import F, Router
from aiogram.types import Message

from bot.services.db_session import get_db_session
from backend.models.user import User
from backend.models.generation_job import GenerationJob

router = Router()

@router.message(F.text == "/admin")
async def cmd_admin(message: Message) -> None:
    admin_ids_env = os.getenv("ADMIN_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_env.split(",") if x.strip().isdigit()]
    
    if message.from_user.id not in admin_ids:
        return
        
    db = get_db_session()
    try:
        users_count = db.query(User).count()
        jobs_count = db.query(GenerationJob).count()
        
        lines = [
            "📊 <b>Статистика Бота</b>",
            "",
            f"👤 Пользователей: {users_count}",
            f"✅ Генераций: {jobs_count}",
        ]
        await message.answer("\n".join(lines), parse_mode="HTML")
    finally:
        db.close()
