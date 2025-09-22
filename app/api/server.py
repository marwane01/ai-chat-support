from typing import Any, Optional
import os
import time
from datetime import date

from fastapi import FastAPI, Request, APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, make_asgi_app

from ..graph.graph import build_graph
from ..graph.state import GraphState
from ..db import init_db
from ..utils.pii import scrub_in, scrub_out, redact
from ..utils.memory import get_slots, update_slots, get_history, append_history
from ..utils.lang import detect_lang
from app.repositories.booking_repo_pg import (
    create_hold_pg,
    confirm_hold_pg,
    cancel_booking_pg,
    get_booking_pg,
    expire_holds_pg,
)
from app.utils.schemas import BookingRequest, ConfirmRequest, CancelRequest


# --- Feature flags ---
GUARDRAILS_ON = os.getenv("GUARDRAILS", "on") == "on"
MEMORY_ON = os.getenv("PHASE3_MEMORY", "off") == "on"
OBS_ON = os.getenv("OBS_ON", "on") == "on"  # turn off if metrics cause issues

# --- Metrics ---
requests_total = Counter("chat_requests_total", "Total chat requests")
latency_seconds = Histogram("chat_request_latency_seconds", "Chat request latency")

# Booking metrics (optional)
booking_hold_ok = Counter("booking_hold_ok_total", "Successful booking hold requests")
booking_hold_fail = Counter("booking_hold_fail_total", "Failed booking hold requests")

# --- FastAPI App Setup ---
app = FastAPI(title="Chatbi", default_response_class=ORJSONResponse)


workflow = build_graph()


# Router for booking
router = APIRouter()


def _parse_iso_date(s: str, field: str) -> date:
    try:
        return date.fromisoformat(s)
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"{field} must be ISO date YYYY-MM-DD"
        )


@router.post("/booking/hold")
async def create_booking_hold(req: BookingRequest):
    try:
        check_in = _parse_iso_date(req.check_in, "check_in")
        check_out = _parse_iso_date(req.check_out, "check_out")

        booking_id = create_hold_pg(
            hotel_id=req.hotel_id,
            room_type=req.room_type,
            check_in=check_in,
            check_out=check_out,
            contact_name=req.contact.name,
            contact_phone=req.contact.phone,
        )
        booking_hold_ok.inc()
        return {"booking_id": booking_id, "status": "hold"}
    except HTTPException as e:
        booking_hold_fail.inc()
        raise e
    except Exception as e:
        booking_hold_fail.inc()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/booking/{booking_id}")
async def get_booking(booking_id: str):
    row = get_booking_pg(booking_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return row


@router.post("/booking/confirm")
async def confirm_booking(req: ConfirmRequest):
    # no payment_ref in your schema; confirm by id only
    confirm_hold_pg(req.booking_id)
    return {"booking_id": req.booking_id, "status": "confirmed"}


@router.post("/booking/cancel")
async def cancel_booking(req: CancelRequest):
    cancel_booking_pg(req.booking_id)
    return {"booking_id": req.booking_id, "status": "cancelled"}


@router.post("/booking/expire")
async def expire_holds(request: Request):
    if request.headers.get("X-Admin-Key") != os.getenv("ADMIN_KEY"):
        raise HTTPException(status_code=403, detail="forbidden")
    return {"released": expire_holds_pg()}


# Include the booking router in the FastAPI app
app.include_router(router)


# --- Existing Chatbot Logic ---


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[Any] = None
    results: Optional[Any] = None
    citations: Optional[Any] = None


@app.on_event("startup")
def on_start() -> None:
    # Initialize DB connections, etc.
    init_db()


def _session_id(req: Request) -> str:
    # Prefer explicit header; fallback to client host
    return (
        req.headers.get("X-Session-Id")
        or (req.client.host if req.client else None)
        or "anon"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    start = time.perf_counter()
    try:
        if OBS_ON:
            try:
                requests_total.inc()
            except Exception:
                pass

        session_id = _session_id(request)

        # 1) Load remembered slots
        slots = get_slots(session_id) if MEMORY_ON else {}
        history = get_history(session_id) if MEMORY_ON else []
        # 2) Guardrails: detect & redact PII
        raw_text = req.message
        redacted_text, has_pii = (scrub_in(raw_text), False)
        if GUARDRAILS_ON:
            redacted_text, has_pii = redact(raw_text)

        if has_pii:
            return ChatResponse(
                reply="For your safety, please don't share emails or card numbers. I can help with rooms or hotel policies.",
                intent="safety_block",
                results={},
                citations=[],
            )

        # 3) Build initial state (seed with memory)
        detected_lang = detect_lang(req.message)
        state = GraphState(
            user_text=redacted_text,
            user_text_raw=raw_text,
            lang=detected_lang,
            history=history,
            city=slots.get("city"),
            budget=slots.get("budget"),
            occupancy=slots.get("occupancy"),
            check_in=slots.get("check_in"),
            check_out=slots.get("check_out"),
        )

        # 4) Run graph
        out = workflow.invoke(state)

        # 5) Extract fields + collect updated slots
        if isinstance(out, dict):
            reply = out.get("reply") or out.get("answer") or out.get("text") or ""
            intent = out.get("intent")
            results = out.get("results")
            citations = out.get("citations")
            city = out.get("city") or state.city
            budget = out.get("budget") or state.budget
            occupancy = out.get("occupancy") or state.occupancy
            check_in = out.get("check_in") or state.check_in
            check_out = out.get("check_out") or state.check_out
        else:
            reply = (
                getattr(out, "reply", None)
                or getattr(out, "answer", None)
                or getattr(out, "text", "")
                or ""
            )
            intent = getattr(out, "intent", None)
            results = getattr(out, "results", None)
            citations = getattr(out, "citations", None)
            city = getattr(out, "city", None) or state.city
            budget = getattr(out, "budget", None) or state.budget
            occupancy = getattr(out, "occupancy", None) or state.occupancy
            check_in = getattr(out, "check_in", None) or state.check_in
            check_out = getattr(out, "check_out", None) or state.check_out

        # 6) Scrub outbound text
        if GUARDRAILS_ON:
            reply = scrub_out(reply)

        # 7) Save memory
        if MEMORY_ON:
            update_slots(
                session_id,
                city=city,
                budget=budget,
                occupancy=occupancy,
                check_in=check_in,
                check_out=check_out,
            )

            # Append both user and assistant turns
            try:
                append_history(session_id, "user", raw_text)
                append_history(session_id, "assistant", reply)
            except Exception:
                pass

        return ChatResponse(
            reply=reply or "Sorry, I couldn’t find an answer.",
            intent=intent,
            results=results or [],
            citations=(citations or [])[:3],
        )
    finally:
        if OBS_ON:
            try:
                latency_seconds.observe(time.perf_counter() - start)
            except Exception:
                pass


# 8) Expose /metrics for Prometheus (only if enabled)
if OBS_ON:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
