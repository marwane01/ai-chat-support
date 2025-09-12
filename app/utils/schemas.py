# app/utils/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class RoomsQuery(BaseModel):
    city: str = Field(min_length=2, max_length=64)
    budget: Optional[float] = Field(default=None, ge=0)
    occupancy: Optional[int] = Field(default=2, ge=1, le=8)
    check_in: Optional[str] = None  # keep simple; format check optional
    check_out: Optional[str] = None

    @field_validator("city")
    @classmethod
    def strip_city(cls, v: str) -> str:
        return v.strip()


class FAQQuery(BaseModel):
    query: str = Field(min_length=2, max_length=512)
    city: Optional[str] = None
    category: Optional[str] = None
