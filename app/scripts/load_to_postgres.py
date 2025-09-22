import os, csv, json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
pg = (
    f"postgresql://{os.getenv('POSTGRES_USER','chatbi')}:"
    f"{os.getenv('POSTGRES_PASSWORD','chatbi')}@"
    f"{os.getenv('POSTGRES_HOST','localhost')}:"
    f"{os.getenv('POSTGRES_PORT','5432')}/"
    f"{os.getenv('POSTGRES_DB','chatbi')}"
)
engine = create_engine(pg, future=True)


# -------- utils --------
def _norm_row(row: dict) -> dict:
    return {
        (k or "")
        .replace("\ufeff", "")
        .strip()
        .lower(): (v.strip() if isinstance(v, str) else v)
        for k, v in row.items()
    }


def _num(x, default=None):
    try:
        if x is None or x == "":
            return default
        return float(str(x).replace(",", ""))
    except Exception:
        return default


def _bool(x, default=False):
    if x is None:
        return default
    return str(x).strip().lower() in ("true", "1", "yes", "y")


# -------- loaders --------
def load_hotels(path):
    with engine.begin() as cx, open(path, newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            r = _norm_row(raw)
            cx.execute(
                text(
                    """
                INSERT INTO hotels (hotel_id,name,city,country,stars,lat,lon,amenities_json)
                VALUES (:hotel_id,:name,:city,:country,:stars,:lat,:lon,:amenities_json)
                ON CONFLICT (hotel_id) DO UPDATE SET
                  name=EXCLUDED.name, city=EXCLUDED.city, country=EXCLUDED.country,
                  stars=EXCLUDED.stars, lat=EXCLUDED.lat, lon=EXCLUDED.lon, amenities_json=EXCLUDED.amenities_json
                """
                ),
                {
                    "hotel_id": r.get("hotel_id") or r.get("hotelid"),
                    "name": r.get("name") or r.get("hotel_name"),
                    "city": r.get("city", ""),
                    "country": r.get("country", ""),
                    "stars": int(r["stars"]) if r.get("stars") else None,
                    "lat": _num(r.get("lat")),
                    "lon": _num(r.get("lon")),
                    "amenities_json": json.dumps(
                        json.loads(r.get("amenities_json", "{}"))
                        if r.get("amenities_json")
                        else {}
                    ),
                },
            )


def load_rates(path):
    with engine.begin() as cx, open(path, newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            r = _norm_row(raw)
            cx.execute(
                text(
                    """
                INSERT INTO room_rates (hotel_id,room_type,occupancy,currency,base_rate,refundable,breakfast_included)
                VALUES (:hotel_id,:room_type,:occupancy,:currency,:base_rate,:refundable,:breakfast_included)
                """
                ),
                {
                    "hotel_id": r.get("hotel_id") or r.get("hotelid"),
                    "room_type": r.get("room_type")
                    or r.get("roomtype")
                    or r.get("type"),
                    "occupancy": int(r.get("occupancy") or r.get("guests") or 2),
                    "currency": r.get("currency") or "USD",
                    "base_rate": _num(
                        r.get("base_rate")
                        or r.get("price_per_night")
                        or r.get("rate")
                        or 0.0,
                        0.0,
                    ),
                    "refundable": _bool(r.get("refundable")),
                    "breakfast_included": _bool(r.get("breakfast_included")),
                },
            )


def _resolve_hotel_id(cx, hotel_name: str, city: str | None = None):
    if not hotel_name:
        return None
    if city:
        row = cx.execute(
            text(
                "SELECT hotel_id FROM hotels "
                "WHERE lower(name)=lower(:n) AND lower(city)=lower(:c) LIMIT 1"
            ),
            {"n": hotel_name, "c": city},
        ).fetchone()
        if row:
            return row[0]
    row = cx.execute(
        text("SELECT hotel_id FROM hotels WHERE lower(name)=lower(:n) LIMIT 1"),
        {"n": hotel_name},
    ).fetchone()
    return row[0] if row else None


def load_policies(path):
    with engine.begin() as cx, open(path, newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            r = _norm_row(raw)
            # Accept multiple header variants
            hotel_id = r.get("hotel_id") or r.get("hotelid")
            if not hotel_id:
                hotel_id = _resolve_hotel_id(cx, r.get("hotel_name"), r.get("city"))
                if not hotel_id:
                    # Skip if we cannot resolve
                    continue
            key = (
                r.get("key") or r.get("policy_key") or r.get("policy") or r.get("name")
            )
            value = (
                r.get("value")
                or r.get("policy_value")
                or r.get("details")
                or r.get("text")
            )
            if not key or value is None:
                continue
            cx.execute(
                text(
                    "INSERT INTO policies (hotel_id,key,value) VALUES (:hotel_id,:key,:value)"
                ),
                {"hotel_id": hotel_id, "key": key, "value": value},
            )


if __name__ == "__main__":
    load_hotels("data/chatbi_hotels.csv")
    load_rates("data/room_rates.csv")
    load_policies("data/policy.csv")
    print("Loaded hotels, rates, policies.")
