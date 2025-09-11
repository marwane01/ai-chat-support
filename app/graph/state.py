from pydantic import BaseModel
from typing import Optional, List, Literal


class GraphState(BaseModel):
    user_text: str
    intent: Optional[Literal["rooms", "faq", "unknown"]] = None
    city: Optional[str] = None
    budget: Optional[float] = None
    occupancy: Optional[int] = None
    answer: Optional[str] = None
    results: Optional[list] = None
    citations: Optional[List[dict]] = None
