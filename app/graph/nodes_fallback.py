from .state import GraphState


def fallback_node(state: GraphState) -> GraphState:
    state.answer = (
        "Sorry, I didn't understand. You can ask about rooms or hotel policies."
    )
    return state
