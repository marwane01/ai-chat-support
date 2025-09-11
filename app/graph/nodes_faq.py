from .state import GraphState
from ..rag.retriever import retrieve


def faq_node(state: GraphState) -> GraphState:
    hits = retrieve(state.user_text, topk=5, city=state.city, category=None)
    state.citations = hits
    if hits:
        best = hits[0]
        state.answer = f"{best['answer']}\n\nTop related questions:\n" + "\n".join(
            [f"- {h['question']} (score {h['score']:.2f})" for h in hits[:3]]
        )
    else:
        state.answer = "I couldn't find an answer in FAQs."
    return state
