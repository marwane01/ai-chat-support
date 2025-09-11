from typing import List, Optional
from sqlmodel import select
from ..db import get_session
from ..models import RoomRate, Hotel


class RoomsRepo:
    def __init__(self):
        self.session = get_session()

    def search(
        self,
        city: str,
        max_price: Optional[float] = None,
        occupancy: Optional[int] = None,
        topk: int = 5,
    ) -> List[dict]:
        q = (
            select(RoomRate, Hotel)
            .join(Hotel, Hotel.hotel_id == RoomRate.hotel_id)
            .where(Hotel.city.ilike(city))
        )
        if max_price is not None:
            q = q.where(RoomRate.base_rate <= max_price)
        if occupancy is not None:
            q = q.where(RoomRate.occupancy >= occupancy)
        q = q.limit(topk)
        rows = self.session.exec(q).all()
        results = []
        for rr, h in rows:
            results.append(
                {
                    "hotel": h.name,
                    "city": h.city,
                    "room_type": rr.room_type,
                    "occupancy": rr.occupancy,
                    "price": rr.base_rate,
                    "currency": rr.currency,
                    "refundable": rr.refundable,
                    "breakfast_included": rr.breakfast_included,
                }
            )
        return results
