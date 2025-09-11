import requests


def test_error_handles_missing_city():
    r = requests.post("http://localhost:8000/chat", json={"message": "show me rooms"})
    j = r.json()
    assert j["intent"] == "rooms"
    assert "city" in j["reply"].lower()
