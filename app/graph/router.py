import re
from .state import GraphState

ROOMS_KW = re.compile(r"\b(room|rooms|book|price|rate)\b", re.I)
FAQ_KW = re.compile(
    r"\b(check[- ]?in|policy|refund|breakfast|parking|wifi|faq|question)\b", re.I
)
CITY_RE = re.compile(r"in\s+([A-Za-z][A-Za-z\s]+)$", re.I)
PRICE_RE = re.compile(r"under\s+(\d+(?:\.\d+)?)|max\s+(\d+(?:\.\d+)?)", re.I)
OCC_RE = re.compile(r"for\s+(\d+)\s*(?:people|guests)?", re.I)


def router_node(state: GraphState) -> GraphState:
    text = state.user_text.strip()
    if ROOMS_KW.search(text):
        state.intent = "rooms"
    elif FAQ_KW.search(text):
        state.intent = "faq"
    else:
        state.intent = "unknown"
    # naive slot extraction
    if m := CITY_RE.search(text):
        state.city = m.group(1).strip()
    if m := PRICE_RE.search(text):
        state.budget = float(next(g for g in m.groups() if g))
    if m := OCC_RE.search(text):
        state.occupancy = int(m.group(1))
    return state
