# app/utils/memory.py
import os, json, time
from typing import Any, Dict, Optional
import redis

TTL_SECONDS = int(os.getenv("SLOT_TTL_SECONDS", "7200"))  # 2h default


def _client() -> "redis.Redis":
    return redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True
    )


def session_key(session_id: str) -> str:
    return f"chatbi:slots:{session_id}"


DEFAULT_SLOTS = {
    "city": None,
    "budget": None,
    "occupancy": None,
    "check_in": None,
    "check_out": None,
    "currency": None,
    "lang": None,
}


def get_slots(session_id: str) -> Dict[str, Any]:
    r = _client()
    k = session_key(session_id)
    data = r.get(k)
    if not data:
        return DEFAULT_SLOTS.copy()
    try:
        slots = json.loads(data)
    except Exception:
        slots = {}
    # ensure keys exist
    out = DEFAULT_SLOTS.copy()
    out.update({k: v for k, v in slots.items() if k in out})
    # refresh TTL
    r.expire(k, TTL_SECONDS)
    return out


def update_slots(session_id: str, **updates) -> Dict[str, Any]:
    r = _client()
    k = session_key(session_id)
    cur = get_slots(session_id)
    for k2, v in updates.items():
        if k2 in cur and v is not None:
            cur[k2] = v
    r.set(k, json.dumps(cur), ex=TTL_SECONDS)
    return cur
