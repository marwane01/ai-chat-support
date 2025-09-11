from .state import GraphState
from ..repositories.rooms_repo import RoomsRepo

repo = RoomsRepo()


def rooms_node(state: GraphState) -> GraphState:
    if not state.city:
        state.answer = "Please tell me the city to search rooms."
        return state
    results = repo.search(
        city=state.city, max_price=state.budget, occupancy=state.occupancy, topk=5
    )
    state.results = results
    if results:
        bullets = [
            f"{r['hotel']} – {r['room_type']} (occ {r['occupancy']}) {r['currency']} {r['price']:.2f}"
            for r in results
        ]
        state.answer = "Here are some options:\n" + "\n".join(bullets)
    else:
        state.answer = "I couldn't find rooms matching your filters. Try adjusting budget or occupancy."
    return state
