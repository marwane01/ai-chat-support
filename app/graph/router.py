import re
from .state import GraphState

# --- intent keywords ---
ROOMS_KW = re.compile(
    r"\b(room|rooms|book|price|rate|option|deal|availability)\b", re.I
)
FAQ_KW = re.compile(
    r"\b(check[- ]?in|policy|refund|breakfast|parking|wifi|faq|question)\b", re.I
)

# --- slot extractors ---
CITY_RE = re.compile(
    r"\b(?:in|at)\s+([A-Za-z][A-Za-z\s\-]+?)(?=\s+(?:under|below|max(?:imum)?|for|with|from|on|to|by)\b|[,.!?]|$)",
    re.I,
)
PRICE_RE = re.compile(r"\b(?:under|below|max(?:imum)?)\s+(\d+(?:\.\d+)?)\b", re.I)
OCC_RE = re.compile(r"\bfor\s+(\d+)\s*(?:people|guests)?\b", re.I)


def router_node(state: GraphState) -> GraphState:
    text = (state.user_text or "").strip()

    # 1) classify coarse intent
    if ROOMS_KW.search(text):
        state.intent = "rooms"
    elif FAQ_KW.search(text):
        state.intent = "faq"
    else:
        state.intent = "unknown"

    # 2) extract slots from THIS utterance (keep prior values if absent)
    if m := CITY_RE.search(text):
        state.city = m.group(1).strip(" ,.")
    if m := PRICE_RE.search(text):
        try:
            state.budget = float(m.group(1))
        except ValueError:
            pass
    if m := OCC_RE.search(text):
        try:
            state.occupancy = int(m.group(1))
        except ValueError:
            pass

    # normalize once here so downstream nodes get consistent values
    state.normalize()

    # 3) follow-up fix: if intent unknown BUT we already have room-like context, go to Rooms
    if (state.intent is None or state.intent == "unknown") and (
        state.city or state.budget or state.occupancy
    ):
        state.intent = "rooms"

    return state
