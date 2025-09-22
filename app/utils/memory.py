# app/utils/memory.py
import os
import json
from typing import Any, Dict, Optional, List
import redis

# --- Slot memory (structured fields) ---
TTL_SECONDS = int(os.getenv("SLOT_TTL_SECONDS", "7200"))  # 2h default


def _client() -> "redis.Redis":
    return redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )


def session_key(session_id: str) -> str:
    return f"chatbi:slots:{session_id}"


DEFAULT_SLOTS: Dict[str, Any] = {
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
    out.update({k2: v for k2, v in slots.items() if k2 in out})
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


# --- Chat history (unstructured short transcript) ---
# Stored as a Redis LIST of JSON messages (newest-first).
# Each item: {"role": "user"|"assistant", "content": "text"}
HIST_TTL_SECONDS = int(os.getenv("HIST_TTL_SECONDS", "7200"))  # 2h default
HIST_MAX_TURNS = int(os.getenv("HIST_MAX_TURNS", "8"))  # 8 turns ~ 16 messages


def history_key(session_id: str) -> str:
    return f"chatbi:history:{session_id}"


def get_history(session_id: str) -> List[Dict[str, str]]:
    """
    Return history as a list of messages ordered oldest -> newest.
    """
    r = _client()
    k = history_key(session_id)
    raw = r.lrange(k, 0, -1) or []
    # We store newest-first; reverse to oldest-first for LLM context
    try:
        msgs = [json.loads(x) for x in reversed(raw)]
    except Exception:
        msgs = []
    # refresh TTL
    if raw:
        r.expire(k, HIST_TTL_SECONDS)
    return msgs


def append_history(session_id: str, role: str, content: str) -> None:
    """
    Append a single turn to the history (newest-first).
    Trims list to ~2*HIST_MAX_TURNS messages (user+assistant per turn).
    """
    if not content:
        return
    if role not in ("user", "assistant"):
        return
    r = _client()
    k = history_key(session_id)
    r.lpush(k, json.dumps({"role": role, "content": content}))
    # keep last N*2 messages
    r.ltrim(k, 0, HIST_MAX_TURNS * 2 - 1)
    r.expire(k, HIST_TTL_SECONDS)


def clear_history(session_id: str) -> None:
    """
    Remove the chat history for a given session.
    """
    r = _client()
    r.delete(history_key(session_id))


def reset_session(session_id: str) -> None:
    """
    Clear both slots and history for a clean conversation.
    """
    r = _client()
    r.delete(session_key(session_id))
    r.delete(history_key(session_id))
