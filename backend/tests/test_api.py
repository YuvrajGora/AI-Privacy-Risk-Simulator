import os
import pytest
import io
from app import create_app
from database import db
from models.scan import Scan

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ANNOTATED_FOLDER = "uploads/annotated"
    UPLOAD_FOLDER = "uploads"
    LOG_FILE = "logs/app.log"
    LOG_FOLDER = "logs"
    @classmethod
    def init_app(cls, app):
        pass

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"

def test_system_metrics(client):
    response = client.get("/api/v1/system/metrics")
    assert response.status_code == 200
    assert "metrics" in response.json

def test_upload_missing_file(client):
    response = client.post("/api/v1/upload/")
    assert response.status_code == 400
    assert response.json["success"] is False

def test_get_analytics(client):
    response = client.get("/api/v1/analytics/")
    assert response.status_code == 200
    assert "metrics" in response.json
    assert response.json["metrics"]["totalScans"] == 0
