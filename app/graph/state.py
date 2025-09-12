from pydantic import BaseModel
from typing import Optional, List, Literal, Dict, Any


def _norm_city(x: Optional[str]) -> Optional[str]:
    if not x:
        return None
    x = x.strip()
    if not x:
        return None
    return x.title()  # Qdrant string-match is case-sensitive


class GraphState(BaseModel):
    # Text seen by generators/tools (redacted/safe)
    user_text: str

    # Raw text for routing only (optional; use carefully)
    user_text_raw: Optional[str] = None

    # High-level intent for routing
    intent: Optional[Literal["rooms", "faq", "unknown"]] = None

    # Extracted slots
    city: Optional[str] = None
    budget: Optional[float] = None
    occupancy: Optional[int] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None

    # Outputs
    reply: Optional[str] = None
    answer: Optional[str] = None
    results: Optional[list] = None
    citations: Optional[List[Dict[str, Any]]] = None

    def normalize(self) -> None:
        """Normalize slot values so downstream nodes are consistent."""
        self.city = _norm_city(self.city)
