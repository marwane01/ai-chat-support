import requests


def test_faq_checkin():
    r = requests.post(
        "http://localhost:8000/chat", json={"message": "what is the check-in time?"}
    )
    j = r.json()
    assert j["intent"] == "faq"
    assert j["citations"] is not None
    assert len(j["citations"]) > 0
