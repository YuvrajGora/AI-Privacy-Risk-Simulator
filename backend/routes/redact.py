from flask import Blueprint, request, jsonify, current_app
import logging
from database import db
from models.scan import Scan
from services.job_manager import job_manager
from services.redaction_service import run_async_redaction

redact_bp = Blueprint("redact", __name__)
logger = logging.getLogger(__name__)

VALID_MODES = ["blur", "pixelate", "blackbox", "solid"]


@redact_bp.route("/redact/<string:scan_id>", methods=["POST"])
def trigger_redaction(scan_id):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found."}), 404

    if scan.status != "completed":
        return jsonify({"success": False, "error": "Cannot redact an incomplete scan."}), 400

    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "blur").lower()

    if mode not in VALID_MODES:
        return jsonify({"success": False, "error": f"Invalid mode. Supported: {', '.join(VALID_MODES)}"}), 400

    import os
    # If this mode is already cached, skip queuing a new job — just mark as completed
    cached_path = scan.get_redacted_path_for_mode(mode)
    if cached_path and os.path.exists(cached_path):
        logger.info(f"[REDACT ROUTE] Mode={mode} is cached for scan {scan_id}. Returning instantly.")
        scan.redacted_image_path = cached_path
        scan.redaction_mode = mode
        scan.redaction_status = "completed"
        scan.redaction_progress = 100
        scan.redaction_current_step = "Completed (Cached)"
        db.session.commit()
        return jsonify({
            "success": True,
            "status": "completed",
            "cached": True,
            "mode": mode
        }), 200

    # Not cached — queue a new redaction job
    scan.redaction_status = "queued"
    scan.redaction_progress = 0
    scan.redaction_mode = mode
    scan.redaction_current_step = "Queued"
    db.session.commit()

    job_manager.submit_job(
        current_app._get_current_object(),
        scan_id,
        run_async_redaction,
        mode=mode
    )

    return jsonify({
        "success": True,
        "status": "processing",
        "cached": False,
        "mode": mode
    }), 202


@redact_bp.route("/redaction-status/<string:scan_id>", methods=["GET"])
def get_redaction_status(scan_id):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found."}), 404

    return jsonify({
        "scanId": scan.scan_id,
        "status": scan.redaction_status,
        "progress": scan.redaction_progress,
        "currentStep": scan.redaction_current_step,
        "mode": scan.redaction_mode,
        "cachedModes": scan.get_cached_modes()
    }), 200


@redact_bp.route("/redaction-options/<string:scan_id>", methods=["GET"])
def get_redaction_options(scan_id):
    """
    Returns all available redaction modes and which ones are already cached
    (can be served instantly without regeneration).
    """
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found."}), 404

    return jsonify({
        "scanId": scan_id,
        "availableModes": VALID_MODES,
        "cachedModes": scan.get_cached_modes()
    }), 200
