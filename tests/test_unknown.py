import requests


def test_unknown():
    r = requests.post("http://localhost:8000/chat", json={"message": "tell me a joke"})
    j = r.json()
    assert j["intent"] == "unknown"
    assert "rooms" in j["reply"].lower()
