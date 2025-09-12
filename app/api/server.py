# app/api/server.py
from typing import Any, Optional
import os
import time

from fastapi import FastAPI, Request
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, make_asgi_app

from ..graph.graph import build_graph
from ..graph.state import GraphState
from ..db import init_db
from ..utils.pii import scrub_in, scrub_out, redact
from ..utils.memory import get_slots, update_slots

# --- Feature flags ---
GUARDRAILS_ON = os.getenv("GUARDRAILS", "on") == "on"
MEMORY_ON = os.getenv("PHASE3_MEMORY", "off") == "on"
OBS_ON = os.getenv("OBS_ON", "on") == "on"  # turn off if metrics cause issues

# --- Metrics (safe to call behind OBS_ON) ---
requests_total = Counter("chat_requests_total", "Total chat requests")
latency_seconds = Histogram("chat_request_latency_seconds", "Chat request latency")

app = FastAPI(title="Chatbi")
workflow = build_graph()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[Any] = None
    results: Optional[Any] = None
    citations: Optional[Any] = None


@app.on_event("startup")
def on_start() -> None:
    # initialize DB connections, etc.
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
        #    - user_text: safe/redacted (for LLM/tools)
        #    - user_text_raw: original (so router can use it if needed)
        state = GraphState(
            user_text=redacted_text,
            user_text_raw=raw_text,
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
