import os
import re

# Block 7 - Forbidden Error injection
# daily.py

path = "bot/handlers/daily.py"
with open(path, "r") as f:
    text = f.read()

old_send = '''        await message.answer(text, reply_markup=main_reply_keyboard(lang), parse_mode="HTML")
        logger.info(f"[Daily] user={telegram_id} claimed streak={streak} credits={result['credits']}")'''

new_send = '''        from aiogram.exceptions import TelegramForbiddenError
        try:
            await message.answer(text, reply_markup=main_reply_keyboard(lang), parse_mode="HTML")
            logger.info(f"[Daily] user={telegram_id} claimed streak={streak} credits={result['credits']}")
        except TelegramForbiddenError:
            logger.warning(f"User blocked bot: {telegram_id}")
            return'''

if old_send in text:
    text = text.replace(old_send, new_send)
    with open(path, "w") as f:
        f.write(text)

# notification_tasks.py
path2 = "worker/tasks/notification_tasks.py"
with open(path2, "r") as f:
    text2 = f.read()

old_except = '''            except Exception as e:
                logger.error(f"[Reminder] Failed to notify {user.telegram_user_id}: {e}")'''
new_except = '''            except TelegramForbiddenError:
                logger.warning(f"User blocked bot: {user.telegram_user_id}")
            except Exception as e:
                logger.error(f"[Reminder] Failed to notify {user.telegram_user_id}: {e}")'''

if old_except in text2 and "except TelegramForbiddenError" not in text2:
    text2 = text2.replace(old_except, new_except)
    text2 = text2.replace("from celery import shared_task", "from celery import shared_task\\nfrom aiogram.exceptions import TelegramForbiddenError")
    with open(path2, "w") as f:
        f.write(text2)
        
old_except2 = '''                except Exception as e:
                    logger.error(f"[Lifecycle] Day {day} failed for {user.telegram_user_id}: {e}")'''
new_except2 = '''                except TelegramForbiddenError:
                    logger.warning(f"User blocked bot: {user.telegram_user_id}")
                except Exception as e:
                    logger.error(f"[Lifecycle] Day {day} failed for {user.telegram_user_id}: {e}")'''

if old_except2 in text2:
    with open(path2, "r") as f:
        t = f.read()
    t = t.replace(old_except2, new_except2)
    with open(path2, "w") as f:
        f.write(t)

print("Patch 3 successful.")
