from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shared.utils.i18n import I18n

i18n = I18n()

def get_quality_keyboard(provider: str, lang: str) -> InlineKeyboardMarkup:
    """Returns inline keyboard for quality selection based on provider and language."""
    buttons = []
    
    if provider == "nano_banana":
        buttons = [
            [InlineKeyboardButton(text=i18n.t(lang, "quality.nano.standard"), callback_data="q:nano:std")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.nano.hd"), callback_data="q:nano:hd")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.nano.pro_hd"), callback_data="q:nano:pro_hd")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.nano.4k"), callback_data="q:nano:4k")],
        ]
    elif provider == "gpt_image":
        buttons = [
            [InlineKeyboardButton(text=i18n.t(lang, "quality.gpt.std"), callback_data="q:gpt:std")],
        ]
    elif provider == "veo":
        buttons = [
            [InlineKeyboardButton(text=i18n.t(lang, "quality.veo.fast"), callback_data="q:veo:fast")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.veo.quality"), callback_data="q:veo:quality")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.veo.4k"), callback_data="q:veo:4k")],
        ]
    elif provider == "kling":
        buttons = [
            [InlineKeyboardButton(text=i18n.t(lang, "quality.kling.std5"), callback_data="q:kling:std5")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.kling.pro5"), callback_data="q:kling:pro5")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.kling.pro10"), callback_data="q:kling:pro10")],
        ]
    
    back_text = "← Orqaga" if lang == "uz" else "← Назад"
    buttons.append([InlineKeyboardButton(text=back_text, callback_data="menu_create")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Margin note: 1 user credit ≈ $0.056 (PACKAGES: ~705 UZS/cr, ~12 500 UZS/$).
# All margins below comfortably clear provider + Telegram/infra overhead.
QUALITY_DATA = {
    # Nano Banana — 4 tiers, 3 kie.ai models:
    # google/nano-banana  (Gemini 2.5 Flash) ≈ $0.02   → 10 cr  · 28× margin
    # nano-banana-2       (Gemini 3.1 Flash) ≈ $0.06   → 20 cr  · 18× margin
    # nano-banana-pro@2K  (Gemini 3.0 Pro)   ≈ $0.12   → 30 cr  · 14× margin
    # nano-banana-pro@4K  (Gemini 3.0 Pro)   ≈ $0.12   → 50 cr  · 23× margin
    "nano:std":    {"cost": 10, "payload": {"image_size": "1:1", "_nano_model": "nano-banana"}},
    "nano:hd":     {"cost": 20, "payload": {"image_size": "1:1", "_nano_model": "nano-banana-2",   "image_resolution": "2K"}},
    "nano:pro_hd": {"cost": 30, "payload": {"image_size": "1:1", "_nano_model": "nano-banana-pro", "image_resolution": "2K"}},
    "nano:4k":     {"cost": 50, "payload": {"image_size": "1:1", "_nano_model": "nano-banana-pro", "image_resolution": "4K"}},

    # GPT Image 2 (OpenAI via kie.ai) — $0.06/gen (t2i and i2i same price)
    # 30 cr = $1.68 → 28× margin
    "gpt:std": {"cost": 30, "payload": {"_gpt_model": "gpt-image-2"}},

    # Veo 3 — veo3_fast ≈ 60-80 kie cr ($0.30-0.40), veo3_quality = 400 kie cr ($2.00)
    # 4K tier = veo3_fast generation + 4K upscale endpoint (~160 kie cr extra)
    #          total kie cost ≈ $1.20 → 90 user cr = 4.2× margin
    "veo:fast":    {"cost": 30, "payload": {"model": "veo3_fast"}},
    "veo:quality": {"cost": 80, "payload": {"model": "veo3_quality"}},
    "veo:4k":      {"cost": 90, "payload": {"model": "veo3_fast", "upscale_4k": True}},

    # Kling 3.0 — std=14 kie cr/s, pro=18 kie cr/s
    "kling:std5":  {"cost": 40,  "payload": {"mode": "std", "duration": "5"}},
    "kling:pro5":  {"cost": 70,  "payload": {"mode": "pro", "duration": "5"}},
    "kling:pro10": {"cost": 120, "payload": {"mode": "pro", "duration": "10"}},
}
