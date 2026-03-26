import os

import_block = """from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton, WebAppInfo,
)
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
"""

def patch_file(path):
    with open(path, "r") as f:
        content = f.read()

    if "InlineKeyboardMarkup" not in content and "WebAppInfo" not in content:
        return

    lines = content.split('\\n')
    new_lines = []
    skip = False
    has_injected = False
    
    for line in lines:
        if line.startswith("from aiogram.types import") or line.startswith("from aiogram.exceptions import"):
            if "(" in line and ")" not in line:
                skip = True
            continue
        if skip:
            if ")" in line:
                skip = False
            continue
            
        if not has_injected and not line.startswith("import") and not line.startswith("from") and line.strip() != "":
            # We are past imports
            new_lines.append(import_block)
            has_injected = True
            
        new_lines.append(line)
        
    if not has_injected:
        new_lines.insert(0, import_block)

    with open(path, "w") as f:
        f.write("\\n".join(new_lines))


for root, _, fs in os.walk("bot"):
    for f in fs:
        if f.endswith(".py"):
            patch_file(os.path.join(root, f))

print("Imports patched successfully.")
