from app.graph.router import router_node
from app.graph.state import GraphState

for msg in [
    "show rooms in Paris",
    "find rooms under 120",
    "show rooms in Paris under 120 for 2",
]:
    s = GraphState(user_text=msg)
    router_node(s)
    print(
        msg,
        "→",
        dict(intent=s.intent, city=s.city, budget=s.budget, occupancy=s.occupancy),
    )
