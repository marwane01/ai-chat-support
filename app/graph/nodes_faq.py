from .state import GraphState
from ..rag.retriever import retrieve

def faq_node(state: GraphState) -> GraphState:
    # normalize slots once
    state.normalize()

    q = (state.user_text or "").strip()

    # First try WITH city (only if we actually have one)
    hits = retrieve(q, topk=5, city=state.city or None)

    # Fallback: retry WITHOUT city if empty
    if not hits:
        hits = retrieve(q, topk=5, city=None)

    state.citations = hits
    if hits:
        best = hits[0]
        # minimal answer for API; keep it simple
        state.answer = best["answer"]
        # If you want the “top related” list shown to the user, uncomment:
        # state.answer = f"{best['answer']}\n\nTop related:\n" + "\n".join(
        #     f"- {h['question']} (score {h['score']:.2f})" for h in hits[:3]
        # )
    else:
        state.answer = "I couldn't find an answer in FAQs."
    return state
