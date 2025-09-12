from typing import List, Optional
from sqlmodel import select
from sqlalchemy import cast, Numeric, func, String
from ..db import get_session
from ..models import RoomRate, Hotel

class RoomsRepo:
    def search(
        self,
        city: str,
        max_price: Optional[float] = None,
        occupancy: Optional[int] = None,
        topk: int = 5,
    ) -> List[dict]:
        with get_session() as session:
            # Safe for NUMERIC or TEXT columns:
            # cast -> strip -> nullif -> cast back to NUMERIC
            price_expr = cast(
                func.nullif(
                    func.regexp_replace(cast(RoomRate.base_rate, String), r"[^0-9.]", "", "g"),
                    ""
                ),
                Numeric
            )

            q = (
                select(RoomRate, Hotel, price_expr.label("price_num"))
                .join(Hotel, Hotel.hotel_id == RoomRate.hotel_id)
                .where(Hotel.city.ilike(f"%{city}%"))
            )
            if max_price is not None:
                q = q.where(price_expr <= max_price)
            if occupancy is not None:
                q = q.where(RoomRate.occupancy >= occupancy)

            q = q.order_by(price_expr.asc()).limit(topk)
            rows = session.exec(q).all()

            results: List[dict] = []
            for rr, h, price_num in rows:
                price_out = float(price_num) if price_num is not None else float(rr.base_rate)
                results.append(
                    {
                        "hotel": h.name,
                        "city": h.city,
                        "room_type": rr.room_type,
                        "occupancy": rr.occupancy,
                        "price": price_out,
                        "currency": rr.currency,
                        "refundable": rr.refundable,
                        "breakfast_included": rr.breakfast_included,
                    }
                )
            return results
