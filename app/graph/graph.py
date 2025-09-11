# app/graph/graph.py
from langgraph.graph import StateGraph, END
from .state import GraphState
from .router import router_node
from .nodes_rooms import rooms_node
from .nodes_faq import faq_node
from .nodes_fallback import fallback_node


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
        return s.intent or "unknown"

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
