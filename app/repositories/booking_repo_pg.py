from datetime import date, datetime, timezone
import os

from fastapi import HTTPException
from sqlalchemy import create_engine, text

DSN = (
    os.getenv("POSTGRES_DSN")
    or os.getenv("DATABASE_URL")
    or "postgresql+psycopg://chatbi:chatbi@postgres:5432/chatbi"
)
engine = create_engine(DSN, pool_pre_ping=True)


def create_hold_pg(
    hotel_id: int,
    room_type: str,
    check_in: date,
    check_out: date,
    contact_name: str,
    contact_phone: str,
) -> str:
    if check_out <= check_in:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")

    with engine.begin() as conn:
        # Lock inventory rows
        conn.execute(
            text(
                """
                SELECT 1
                  FROM room_inventory
                 WHERE hotel_id=:hid AND room_type=:rt
                   AND day >= :cin AND day < :cout
                 FOR UPDATE
            """
            ),
            {"hid": hotel_id, "rt": room_type, "cin": check_in, "cout": check_out},
        )

        # Check availability across all days
        ok = conn.execute(
            text(
                """
                SELECT CASE WHEN MIN(total_qty - held_qty - booked_qty) >= 1
                           THEN TRUE ELSE FALSE END AS ok
                  FROM room_inventory
                 WHERE hotel_id=:hid AND room_type=:rt
                   AND day >= :cin AND day < :cout
            """
            ),
            {"hid": hotel_id, "rt": room_type, "cin": check_in, "cout": check_out},
        ).scalar()

        if not ok:
            raise HTTPException(
                status_code=400,
                detail="Sorry, all rooms are booked for the selected dates.",
            )

        # Hold one room across the range
        conn.execute(
            text(
                """
                UPDATE room_inventory
                   SET held_qty = held_qty + 1,
                       is_held  = TRUE
                 WHERE hotel_id=:hid AND room_type=:rt
                   AND day >= :cin AND day < :cout
            """
            ),
            {"hid": hotel_id, "rt": room_type, "cin": check_in, "cout": check_out},
        )

        booking_id = "hold_" + os.urandom(6).hex()
        conn.execute(
            text(
                """
                INSERT INTO bookings
                    (booking_id, hotel_id, room_type, check_in, check_out,
                     contact_name, contact_phone, status, hold_expires_at)
                VALUES
                    (:bid, :hid, :rt, :cin, :cout,
                     :cname, :cphone, 'hold', NOW() + INTERVAL '15 minutes')
            """
            ),
            {
                "bid": booking_id,
                "hid": hotel_id,
                "rt": room_type,
                "cin": check_in,
                "cout": check_out,
                "cname": contact_name,
                "cphone": contact_phone,
            },
        )
        return booking_id


def confirm_hold_pg(booking_id: str) -> None:
    with engine.begin() as conn:
        b = (
            conn.execute(
                text("SELECT * FROM bookings WHERE booking_id=:bid FOR UPDATE"),
                {"bid": booking_id},
            )
            .mappings()
            .first()
        )
        if not b:
            raise HTTPException(404, "Booking not found")
        if b["status"] == "confirmed":
            return  # idempotent
        if b["status"] != "hold":
            raise HTTPException(409, "Only holds can be confirmed")
        if b["hold_expires_at"] and datetime.now(timezone.utc) > b["hold_expires_at"]:
            raise HTTPException(409, "Hold expired")
        # ...inventory move...
        conn.execute(
            text("UPDATE bookings SET status='confirmed' WHERE booking_id=:bid"),
            {"bid": booking_id},
        )


def cancel_booking_pg(booking_id: str) -> None:
    """Cancel a hold or a confirmed booking (→ status='cancelled')."""
    with engine.begin() as conn:
        b = (
            conn.execute(
                text(
                    """
                SELECT booking_id, hotel_id, room_type, check_in, check_out, status
                  FROM bookings
                 WHERE booking_id=:bid
                 FOR UPDATE
            """
                ),
                {"bid": booking_id},
            )
            .mappings()
            .first()
        )

        if not b:
            raise HTTPException(status_code=404, detail="Booking not found")
        if b["status"] in ("cancelled", "expired"):
            return

        if b["status"] == "hold":
            conn.execute(
                text(
                    """
                    UPDATE room_inventory
                       SET held_qty = GREATEST(held_qty - 1, 0),
                           is_held  = CASE WHEN held_qty - 1 <= 0 THEN FALSE ELSE is_held END
                     WHERE hotel_id=:hid AND room_type=:rt
                       AND day >= :cin AND day < :cout
                """
                ),
                {
                    "hid": b["hotel_id"],
                    "rt": b["room_type"],
                    "cin": b["check_in"],
                    "cout": b["check_out"],
                },
            )
        elif b["status"] == "confirmed":
            conn.execute(
                text(
                    """
                    UPDATE room_inventory
                       SET booked_qty = GREATEST(booked_qty - 1, 0),
                           is_booked  = CASE WHEN booked_qty - 1 <= 0 THEN FALSE ELSE is_booked END
                     WHERE hotel_id=:hid AND room_type=:rt
                       AND day >= :cin AND day < :cout
                """
                ),
                {
                    "hid": b["hotel_id"],
                    "rt": b["room_type"],
                    "cin": b["check_in"],
                    "cout": b["check_out"],
                },
            )

        conn.execute(
            text("""UPDATE bookings SET status='cancelled' WHERE booking_id=:bid"""),
            {"bid": booking_id},
        )


def get_booking_pg(booking_id: str) -> dict | None:
    with engine.begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                SELECT booking_id, hotel_id, room_type, check_in, check_out,
                       contact_name, contact_phone, status, hold_expires_at, created_at
                  FROM bookings
                 WHERE booking_id=:bid
            """
                ),
                {"bid": booking_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None


def expire_holds_pg() -> int:
    """Mark past-due holds as expired and release inventory."""
    with engine.begin() as conn:
        rows = (
            conn.execute(
                text(
                    """
                SELECT booking_id, hotel_id, room_type, check_in, check_out
                  FROM bookings
                 WHERE status='hold' AND hold_expires_at < NOW()
                 FOR UPDATE SKIP LOCKED
            """
                )
            )
            .mappings()
            .all()
        )

        for b in rows:
            conn.execute(
                text(
                    """
                    UPDATE room_inventory
                       SET held_qty = GREATEST(held_qty - 1, 0),
                           is_held  = CASE WHEN held_qty - 1 <= 0 THEN FALSE ELSE is_held END
                     WHERE hotel_id=:hid AND room_type=:rt
                       AND day >= :cin AND day < :cout
                """
                ),
                {
                    "hid": b["hotel_id"],
                    "rt": b["room_type"],
                    "cin": b["check_in"],
                    "cout": b["check_out"],
                },
            )
            conn.execute(
                text("""UPDATE bookings SET status='expired' WHERE booking_id=:bid"""),
                {"bid": b["booking_id"]},
            )
        return len(rows)
