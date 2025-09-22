def test_it_localizes_answer(client):
    r = client.post(
        "/chat", json={"message": "Quali sono gli orari di check-in?"}
    ).json()
    assert "check-in" in r["reply"].lower()
    assert any(c.get("meta", {}).get("collection") == "faqs_v2" for c in r["citations"])
