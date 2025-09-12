from .state import GraphState

def fallback_node(state: GraphState) -> GraphState:
    state.answer = "Sorry, I didn’t catch that. You can ask about rooms (city/budget/guests) or hotel FAQs (parking, breakfast, check-in, wifi)."
    return state