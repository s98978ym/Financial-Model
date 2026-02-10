"""Health & root endpoint tests."""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "PL Generator" in resp.json()["message"]
