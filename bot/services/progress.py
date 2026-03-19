import asyncio
from aiogram import Bot
from backend.db.session import SessionLocal
from backend.models.generation_job import GenerationJob

async def track_generation_progress(bot: Bot, chat_id: int, message_id: int, job_id: int):
    """
    Asynchronous loop editing the waiting message every 30s.
    """
    elapsed = 0
    
    while True:
        await asyncio.sleep(30)
        elapsed += 30
        
        # Check DB to see if job is still processing
        db = SessionLocal()
        try:
            job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
            if not job or job.status != "processing":
                break
        finally:
            db.close()
            
        try:
            mins = elapsed // 60
            secs = elapsed % 60
            time_str = f"{mins} мин {secs} сек" if mins > 0 else f"{secs} сек"
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"⏳ Ваша генерация в процессе... ({time_str})"
            )
        except Exception:
            # Message might be deleted or no text changes made
            pass
