import logging
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory

logger = logging.getLogger(__name__)

# Enforce consistent results from langdetect
DetectorFactory.seed = 0

def translate_prompt(text: str) -> str:
    """
    Detects the language of the prompt and translates RU/UZ prompts to English.
    Returns the original text on EN, unknown, or failure.
    """
    if not text or not text.strip():
        return text
        
    try:
        lang = detect(text)
        if lang in ('ru', 'uz'):
            translated = GoogleTranslator(source='auto', target='en').translate(text)
            if translated:
                return translated
    except Exception as e:
        logger.warning(f"Translation failed or language could not be detected: {e}")
        
    return text
