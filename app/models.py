from sqlmodel import SQLModel, Field
from typing import Optional


class Hotel(SQLModel, table=True):
    hotel_id: int | None = Field(default=None, primary_key=True)
    name: str
    city: str
    country: str
    stars: Optional[int] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    amenities_json: Optional[str] = None


class RoomRate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hotel_id: int = Field(foreign_key="hotel.hotel_id")
    room_type: str
    occupancy: int
    currency: str
    base_rate: float
    refundable: bool
    breakfast_included: bool


class Policy(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hotel_id: int = Field(foreign_key="hotel.hotel_id")
    key: str
    value: str
