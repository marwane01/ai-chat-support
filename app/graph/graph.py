# app/graph/graph.py
from langgraph.graph import StateGraph, END
from .state import GraphState
from .router import router_node
from .nodes_rooms import rooms_node
from .nodes_faq import faq_node
from .nodes_fallback import fallback_node

# --- build graph ---
def build_graph():
    sg = StateGraph(GraphState)

    # nodes
    sg.add_node("router", router_node)
    sg.add_node("rooms", rooms_node)
    sg.add_node("faq", faq_node)
    sg.add_node("fallback", fallback_node)

    # entry
    sg.set_entry_point("router")

    # conditional routing out of router
    def route_key(s: GraphState):
        # prefer explicit intent
        if s.intent and s.intent != "unknown":
            # DEBUG:
            print(f"[route_key] using intent={s.intent}")
            return s.intent
        # follow-up continuation: if we already have slots (from Redis/prior turns)
        if s.city or s.budget or s.occupancy:
            # DEBUG:
            return "rooms"
        # fallback
        print("[route_key] unknown")
        return "unknown"

    sg.add_conditional_edges(
        "router",
        route_key,
        {
            "rooms": "rooms",
            "faq": "faq",
            "unknown": "fallback",
        },
    )

    # terminate after each leaf node
    sg.add_edge("rooms", END)
    sg.add_edge("faq", END)
    sg.add_edge("fallback", END)

    return sg.compile()


# --- memory-aware wrapper ---
from app.utils.memory import get_slots, update_slots

_GRAPH = None
def _get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH

def run_chat_with_memory(session_id: str, message: str):
    # 1) hydrate slots from Redis
    slots = get_slots(session_id)
    state = GraphState(user_text=message, **slots)

    # 2) run the compiled graph
    graph = _get_graph()
    out = graph.invoke(state)

    # 3) persist updated slots
    update_slots(
        session_id,
        city=out.city,
        budget=out.budget,
        occupancy=out.occupancy,
        check_in=out.check_in,
        check_out=out.check_out,
    )
    return out
