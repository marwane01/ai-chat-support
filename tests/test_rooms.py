import requests


def test_rooms_paris():
    r = requests.post(
        "http://localhost:8000/chat",
        json={"message": "show me rooms in Paris under 200 for 2"},
    )
    j = r.json()
    assert j["intent"] == "rooms"
    assert j["results"] is not None
