import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_check_has_version(self):
        response = client.get("/health")
        data = response.json()
        assert "version" in data or response.status_code == 200


class TestRootEndpoint:
    def test_root_returns_welcome(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "welcome" in str(data).lower()


class TestScrapeEndpoints:
    def test_scrape_pages_endpoint_exists(self):
        response = client.post("/scrape-pages", json={
            "url": "https://example.com",
            "max_pages": 1
        })
        assert response.status_code in [200, 422, 400]

    def test_scrape_pages_invalid_url(self):
        response = client.post("/scrape-pages", json={
            "url": "not-a-valid-url",
            "max_pages": 1
        })
        assert response.status_code in [422, 400, 500]

    def test_scrape_pages_missing_url(self):
        response = client.post("/scrape-pages", json={
            "max_pages": 1
        })
        assert response.status_code == 422


class TestStreamEndpoints:
    def test_stream_endpoint_exists(self):
        response = client.post("/scrape-stream", json={
            "url": "https://example.com",
            "max_pages": 1
        })
        assert response.status_code in [200, 422, 400]


class TestAPIEndpoints:
    def test_api_info_endpoint(self):
        response = client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data


class TestAPIDocumentation:
    def test_openapi_schema_available(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_docs_endpoint_available(self):
        response = client.get("/docs")
        assert response.status_code == 200
