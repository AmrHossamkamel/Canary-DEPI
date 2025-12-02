from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "healthy"

def test_api_info_endpoint():
    resp = client.get("/api")
    assert resp.status_code == 200
    data = resp.json()
    assert "endpoints" in data
    assert "/scrape" in data["endpoints"]

def test_scrape_single_invalid_url_schema():
    resp = client.post("/scrape-single", params={"url": "ftp://example.com", "timeout": 10})
    assert resp.status_code == 400

def test_scrape_single_missing_url():
    resp = client.post("/scrape-single")
    assert resp.status_code == 422

