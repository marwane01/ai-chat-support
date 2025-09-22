# app/utils/lang.py
from langdetect import detect, DetectorFactory

# make results reproducible
DetectorFactory.seed = 0


def detect_lang(text: str, default: str = "en") -> str:
    """
    Detect the language of a given text.
    Returns an ISO 639-1 code like 'en', 'es', 'fr'.
    Falls back to 'en' if detection fails.
    """
    try:
        code = (detect(text or "") or default).split("-")[0].lower()
        return code or default
    except Exception:
        return default
