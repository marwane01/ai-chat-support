from pydantic import ValidationError
from .state import GraphState
from ..repositories.rooms_repo import RoomsRepo
from ..utils.schemas import RoomsQuery  # your existing schema

repo = RoomsRepo()


def rooms_node(state: GraphState) -> GraphState:
    try:
        q = RoomsQuery(
            city=(state.city or "").strip(),
            budget=float(state.budget) if state.budget is not None else None,
            occupancy=state.occupancy or 2,
            check_in=state.check_in,
            check_out=state.check_out,
        )
    except ValidationError:
        state.answer = "Please give a valid city (2+ letters)."
        state.results = None
        return state

    state.city = q.city
    state.budget = q.budget
    state.occupancy = q.occupancy
    state.check_in = q.check_in
    state.check_out = q.check_out

    if not q.city:
        state.answer = "Please tell me the city to search rooms."
        return state

    results = repo.search(
        city=q.city, max_price=q.budget, occupancy=q.occupancy, topk=5
    )
    state.results = results

    if results:
        bullets = [
            f"{r['hotel']} – {r['room_type']} (occ {r['occupancy']}) {r['currency']} {r['price']:.0f}"
            for r in results
        ]
        state.answer = "Here are some options:\n" + "\n".join(bullets)
    else:
        # nicer UX: suggest the cheapest available for the same occupancy
        cheapest = repo.search(
            city=q.city, max_price=None, occupancy=q.occupancy, topk=1
        )
        if cheapest:
            c = cheapest[0]
            state.answer = (
                f"No rooms under {q.budget:.0f} in {q.city}. "
                f"Cheapest is {c['hotel']} – {c['room_type']} at {c['currency']} {c['price']:.0f}."
            )
        else:
            state.answer = "No rooms found in that city."
    return state
