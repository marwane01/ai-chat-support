# app/utils/pii.py
import re

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+?\d{1,3}[ -]?)?(?:\(?\d{2,4}\)?[ -]?)?\d{3,4}[ -]?\d{4}")
CARD = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def scrub_in(text: str) -> str:
    """Mask PII in user input before logging/processing."""
    if not text:
        return text
    t = EMAIL.sub("[EMAIL]", text)
    t = CARD.sub("[CARD]", t)
    t = PHONE.sub("[PHONE]", t)
    return t


def scrub_out(text: str) -> str:
    """Double-check responses contain no raw PII."""
    return scrub_in(text)


def redact(text: str) -> tuple[str, bool]:
    """
    Return (redacted_text, pii_found).
    """
    if not text:
        return text, False

    pii_found = False
    if EMAIL.search(text) or CARD.search(text) or PHONE.search(text):
        pii_found = True

    t = EMAIL.sub("[EMAIL]", text)
    t = CARD.sub("[CARD]", t)
    t = PHONE.sub("[PHONE]", t)
    return t, pii_found
