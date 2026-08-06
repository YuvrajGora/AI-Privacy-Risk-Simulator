from flask import Blueprint, jsonify
from models.scan import Scan
import json

comparison_bp = Blueprint("comparison", __name__)

@comparison_bp.route("/comparison/<string:scan_id>", methods=["GET"])
def get_comparison(scan_id):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found."}), 404

    if scan.redaction_status != "completed":
        return jsonify({"success": False, "error": "Redaction must be completed to view comparison."}), 400

    # Build response with image URLs
    original_url = f"/api/v1/image/{scan_id}"
    redacted_url = f"/api/v1/redacted-image/{scan_id}"
    annotated_url = f"/api/v1/annotated-image/{scan_id}"

    # Parse safe report
    safe_score = 98
    improvement = 0

    if scan.redacted_report_json:
        try:
            safe_report = json.loads(scan.redacted_report_json)
            safe_score = safe_report.get("safeScore", 98)
            improvement = safe_report.get("scoreImprovement", safe_score - (scan.privacy_score or 50))
        except Exception:
            pass

    original_score = scan.privacy_score or 50

    return jsonify({
        "scanId": scan.scan_id,
        "originalImage": original_url,
        "annotatedImage": annotated_url,
        "redactedImage": redacted_url,
        "safeImage": redacted_url,
        "originalScore": original_score,
        "safeScore": safe_score,
        "scoreImprovement": improvement,
        "riskReductionPoints": max(0, improvement),
        "redactionMode": scan.redaction_mode or "blur"
    }), 200
