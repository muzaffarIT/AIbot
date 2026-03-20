"""
Ready-made prompt library categorized by style.
Used for the "Surprise Me" feature.
"""
import random

PROMPTS: dict[str, list[str]] = {
    "portrait": [
        "a beautiful young woman with blue eyes, soft studio lighting, 4k, photorealistic",
        "a wise old man with a long beard, dramatic cinematic lighting, detailed",
        "an elegant asian woman in traditional dress, golden hour light, 8k",
        "a mysterious girl with red hair and green eyes, dark background, bokeh",
        "a handsome man in suit, confidence portrait, sharp focus, studio lighting",
    ],
    "landscape": [
        "a magical forest with glowing mushrooms at night, fantasy art, 8k",
        "dramatic mountain peaks at sunset, golden clouds, aerial view, cinematic",
        "a cozy japanese village in autumn, maple trees, soft light, anime style",
        "a tropical beach at sunrise, crystal clear water, paradise, 4k",
        "the milky way galaxy over a dark desert, long exposure, astro photography",
    ],
    "fantasy": [
        "a powerful dragon flying over a burning castle, dark fantasy, epic, 4k",
        "a futuristic cyberpunk city at night, neon lights, rain, blade runner style",
        "an ancient wizard casting a spell, magical particles, detailed, fantasy art",
        "a beautiful fairy in a glowing enchanted forest, ethereal light",
        "a knight in shining armor standing on a cliff at dawn, epic fantasy",
    ],
    "anime": [
        "a cute anime girl with pink hair in a flower field, studio ghibli style",
        "a heroic anime warrior with glowing sword, epic battle scene, detailed",
        "an anime cityscape at night with neon lights, rain reflections, makoto shinkai style",
        "a cool anime boy with blue eyes and silver hair, dramatic pose",
        "a magical anime school girl surrounded by cherry blossoms, spring",
    ],
    "video": [
        "a person walking slowly on a beach at sunset, slow motion, cinematic",
        "a dragon flying through clouds, epic scale, cinematic 4k, slow motion",
        "cherry blossoms falling in the wind, slow motion, dreamy, soft light",
        "waves crashing on rocky shore at golden hour, drone shot, slow motion",
        "a city timelapse from dusk to night, lights turning on, time-lapse",
    ],
}

CATEGORY_LABELS_RU = {
    "portrait": "🧑 Портреты",
    "landscape": "🌄 Пейзажи",
    "fantasy": "🐉 Фэнтези",
    "anime": "🎌 Аниме",
    "video": "🎬 Видео",
}

CATEGORY_LABELS_UZ = {
    "portrait": "🧑 Portretlar",
    "landscape": "🌄 Manzaralar",
    "fantasy": "🐉 Fantaziya",
    "anime": "🎌 Anime",
    "video": "🎬 Video",
}

VIDEO_CATEGORIES = {"video"}


def get_random_prompt(category: str | None = None) -> tuple[str, str]:
    """Returns (category, prompt) — category may be random if not specified."""
    if category and category in PROMPTS:
        cat = category
    else:
        cat = random.choice(list(PROMPTS.keys()))
    prompt = random.choice(PROMPTS[cat])
    return cat, prompt
