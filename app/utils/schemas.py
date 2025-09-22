from pydantic import BaseModel, Field, field_validator
from typing import Optional


# -------- Rooms / FAQ --------


class RoomsQuery(BaseModel):
    city: str = Field(min_length=2, max_length=64)
    budget: Optional[float] = Field(default=None, ge=0)
    occupancy: Optional[int] = Field(default=2, ge=1, le=8)
    check_in: Optional[str] = None  # ISO date "YYYY-MM-DD"
    check_out: Optional[str] = None  # ISO date "YYYY-MM-DD"

    @field_validator("city")
    @classmethod
    def strip_city(cls, v: str) -> str:
        return v.strip()


class FAQQuery(BaseModel):
    query: str = Field(min_length=2, max_length=512)
    city: Optional[str] = None
    category: Optional[str] = None
    lang: Optional[str] = None


# -------- Booking --------


class ContactInfo(BaseModel):
    name: str
    phone: str


class BookingRequest(BaseModel):
    hotel_id: int
    room_type: str
    check_in: str  # ISO date
    check_out: str  # ISO date
    contact: ContactInfo


class ConfirmRequest(BaseModel):
    booking_id: str  # removed payment_ref (not in DB)


class CancelRequest(BaseModel):
    booking_id: str  # removed reason (not in DB)
