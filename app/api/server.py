from typing import Any, Optional
from fastapi import FastAPI
from pydantic import BaseModel
from ..graph.graph import build_graph
from ..graph.state import GraphState
from ..db import init_db

app = FastAPI(title="Chatbi")
workflow = build_graph()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[Any] = None  # can be str/dict depending on node
    results: Optional[Any] = None  # list/dict/None
    citations: Optional[Any] = None


@app.on_event("startup")
def on_start():
    init_db()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    state = GraphState(user_text=req.message)
    out = workflow.invoke(state)

    if isinstance(out, dict):
        reply = out.get("reply") or out.get("answer") or out.get("text") or ""
        intent = out.get("intent")
        results = out.get("results")
        citations = out.get("citations")
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

    return ChatResponse(
        reply=reply, intent=intent, results=results, citations=citations
    )
