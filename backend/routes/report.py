import os
import json
from flask import Blueprint, jsonify, request, current_app
from models.scan import Scan
from database import db

report_bp = Blueprint("report", __name__)

@report_bp.route("/<string:scan_id>", methods=["GET"])
def get_report(scan_id: str):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan:
        return jsonify({"success": False, "error": f"Scan with ID '{scan_id}' not found."}), 404

    # If scan failed or is still in progress
    if scan.status in ["pending", "processing"]:
        return jsonify({
            "scanId": scan.scan_id,
            "status": scan.status,
            "progress": scan.progress,
            "currentStep": scan.current_step,
            "message": "Report analysis is currently processing. Please poll GET /api/status/<scanId>."
        }), 202

    if scan.status == "failed":
        return jsonify({
            "scanId": scan.scan_id,
            "status": "failed",
            "error": scan.error_message or "Analysis failed."
        }), 500

    # Return cached report instantly
    return jsonify(scan.to_dict()), 200


@report_bp.route("/<string:scan_id>/action", methods=["POST"])
def post_threat_action(scan_id: str):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan:
        return jsonify({"success": False, "error": f"Scan with ID '{scan_id}' not found."}), 404

    data = request.get_json() or {}
    threat_id = data.get("threatId")
    action = data.get("action") # "dismiss" or "confirm"

    if not threat_id or action not in ["dismiss", "confirm"]:
        return jsonify({"success": False, "error": "Invalid arguments. Provide threatId and action ('dismiss' or 'confirm')."}), 400

    if not scan.report_json:
        return jsonify({"success": False, "error": "Report data not ready."}), 400

    try:
        report = json.loads(scan.report_json)
        threats = report.get("threats", [])
        
        # Find the target threat
        target_threat = None
        for t in threats:
            if t.get("id") == threat_id:
                target_threat = t
                break

        if not target_threat:
            return jsonify({"success": False, "error": f"Threat with ID '{threat_id}' not found in report."}), 404

        # Apply action
        target_threat["dismissed"] = (action == "dismiss")

        # Recalculate score and breakdown
        active_score = 100
        score_breakdown = {}
        has_gps = report.get("metrics", {}).get("gpsMetadata", False)
        
        # Collect categories of active threats
        active_threat_types = set()
        for t in threats:
            if not t.get("dismissed", False):
                ded = t.get("deduction", 10)
                active_score -= ded
                tname = t["type"]
                score_breakdown[tname] = score_breakdown.get(tname, 0) - ded
                active_threat_types.add(tname)

        final_score = max(0, min(100, active_score))

        # "No 100% safe" rule: if any findings exist (even dismissed) or text exists, cap at 95
        has_any_finding = (
            len(threats) > 0 or
            report.get("metrics", {}).get("facesDetected", 0) > 0 or
            report.get("metrics", {}).get("textBlocks", 0) > 0 or
            report.get("metrics", {}).get("qrCodes", 0) > 0 or
            has_gps
        )
        if final_score == 100 and has_any_finding:
            final_score = 95

        # ID Card cap
        if report.get("identityCardDetected", False):
            final_score = min(final_score, 65)

        # Risk tier mapping
        if final_score <= 25:
            risk_level = "Critical"
        elif final_score <= 50:
            risk_level = "High"
        elif final_score <= 75:
            risk_level = "Medium"
        else:
            risk_level = "Safe"

        if report.get("identityCardDetected", False) and risk_level == "Safe":
            risk_level = "Medium"
            final_score = min(final_score, 65)

        # Recalculate safe to share
        unsafe_categories = {
            "Identity Badge Visible", "Password Exposed", "OTP/Verification Code Exposed",
            "Credit/Debit Card Number Exposed", "Bank Account Number Exposed",
            "Signature Detected", "Private Chat Screenshot", "Personal Identifier Visible"
        }
        has_unsafe_element = any(t in unsafe_categories for t in active_threat_types)
        safe_to_share = (not has_unsafe_element) and (not has_gps)

        # Update report dictionary
        report["privacyScore"] = final_score
        report["riskLevel"] = risk_level
        report["safeToShare"] = safe_to_share
        report["scoreBreakdown"] = score_breakdown
        report["threats"] = threats

        # Save to database
        scan.privacy_score = final_score
        scan.risk_level = risk_level
        scan.report_json = json.dumps(report)
        
        db.session.commit()

        # Re-generate the annotated heatmap image with the updated threat list (omitting dismissed threats)
        from services.annotation_service import generate_annotated_image
        details = report.get("analysisDetails", {})
        original_img = scan.original_path
        if original_img and os.path.exists(original_img):
            generate_annotated_image(
                image_path=original_img,
                scan_id=scan.scan_id,
                threats=threats,
                analysis_details=details,
                annotated_folder=current_app.config["ANNOTATED_FOLDER"]
            )

        return jsonify({
            "success": True,
            "privacyScore": final_score,
            "riskLevel": risk_level,
            "safeToShare": safe_to_share,
            "scoreBreakdown": score_breakdown,
            "threats": threats
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to perform action: {str(e)}"}), 500
