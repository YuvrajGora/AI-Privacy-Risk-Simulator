import os
import json
import pytest
from app import create_app
from database import db
from models.scan import Scan
from services.scoring_service import calculate_privacy_score

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

def test_explainable_scoring():
    # Construct typical scan inputs
    metadata = {"hasGps": True}
    ocr_data = {
        "extractedText": "My phone number is 9876543210 and Aadhaar: 1234 5678 9012",
        "detectedPii": {
            "aadhaarNumbers": [{"value": "1234 5678 9012", "bbox": [10, 20, 100, 30]}],
            "phoneNumbers": [{"value": "9876543210", "bbox": [50, 60, 80, 25]}]
        },
        "textBlocks": []
    }
    face_data = {"faceCount": 1, "faceLocations": [[100, 100, 50, 50]]}
    qr_data = {"qrCount": 0}

    res = calculate_privacy_score(metadata, ocr_data, face_data, qr_data)

    assert "privacyScore" in res
    assert "scoreBreakdown" in res
    assert "scanReliability" in res
    assert "scanQuality" in res

    # Ensure all threats got unique IDs and explainability properties
    threats = res["threats"]
    assert len(threats) > 0
    for i, t in enumerate(threats):
        assert t["id"] == f"threat_{i}"
        assert t["dismissed"] is False
        assert "whatWasDetected" in t
        assert "whyIsItRisky" in t
        assert "howSeriousIsIt" in t
        assert "howCanItBeFixed" in t
        assert "confidenceLabel" in t
        assert "deduction" in t

    # Ensure Aadhaar (-30) and GPS (-25) and Phone (-20) are present in breakdown
    breakdown = res["scoreBreakdown"]
    assert breakdown.get("Personal Identifier Visible") == -30
    assert breakdown.get("GPS Location Metadata") == -25
    assert breakdown.get("Phone Number Exposed") == -20

def test_scan_and_actions(client):
    # 1. Manually insert a mock Scan object into the test SQLite database
    scan_id = "test-scan-123"
    mock_report = {
        "scanId": scan_id,
        "targetName": "test.jpg",
        "privacyScore": 50,
        "riskLevel": "High",
        "threats": [
            {
                "id": "threat_0",
                "type": "Phone Number Exposed",
                "severity": "High",
                "confidence": 0.85,
                "confidenceLabel": "High Confidence",
                "description": "Phone number found.",
                "deduction": 20,
                "dismissed": False
            },
            {
                "id": "threat_1",
                "type": "GPS Location Metadata",
                "severity": "High",
                "confidence": 0.90,
                "confidenceLabel": "High Confidence",
                "description": "GPS metadata found.",
                "deduction": 25,
                "dismissed": False
            }
        ],
        "recommendations": []
    }
    
    with client.application.app_context():
        scan = Scan(
            scan_id=scan_id,
            filename="test.jpg",
            target_name="test.jpg",
            status="completed",
            progress=100,
            current_step="Analysis complete",
            privacy_score=50,
            risk_level="High",
            report_json=json.dumps(mock_report)
        )
        db.session.add(scan)
        db.session.commit()

    # 2. Dismiss threat_0 (Phone Number Exposed, -20 pts)
    res_action = client.post(f"/api/v1/report/{scan_id}/action", json={
        "threatId": "threat_0",
        "action": "dismiss"
    })
    assert res_action.status_code == 200
    action_res = res_action.json
    assert action_res["success"] is True
    # Initial score was 50 (deductions: -20, -25. Remaining active deductions: -25).
    # New score should be 100 - 25 = 75
    assert action_res["privacyScore"] == 75
    assert action_res["riskLevel"] == "Medium"
    assert action_res["threats"][0]["dismissed"] is True

    # 3. Retrieve report from GET endpoint to confirm SQLite update persisted
    res_report = client.get(f"/api/v1/report/{scan_id}")
    assert res_report.status_code == 200
    report = res_report.json
    assert report["privacyScore"] == 75
    assert report["threats"][0]["dismissed"] is True
