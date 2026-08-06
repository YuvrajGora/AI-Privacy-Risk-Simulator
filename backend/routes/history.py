import os
import logging
from flask import Blueprint, jsonify
from database import db
from models.scan import Scan

history_bp = Blueprint("history", __name__)
logger = logging.getLogger(__name__)

@history_bp.route("/", methods=["GET"])
def get_all_history():
    scans = Scan.query.order_by(Scan.created_at.desc()).all()
    return jsonify([scan.to_dict() for scan in scans]), 200

@history_bp.route("/<string:scan_id>", methods=["DELETE"])
def delete_single_scan(scan_id: str):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan:
        return jsonify({"success": False, "error": f"Scan with ID '{scan_id}' not found."}), 404

    # Delete local image file
    if scan.filename and os.path.exists(scan.filename):
        try:
            os.remove(scan.filename)
        except Exception as e:
            logger.warning(f"Failed to delete file {scan.filename}: {e}")

    db.session.delete(scan)
    db.session.commit()

    return jsonify({"success": True, "message": f"Scan '{scan_id}' and associated file deleted successfully."}), 200

@history_bp.route("/", methods=["DELETE"])
def clear_all_history():
    scans = Scan.query.all()
    count = len(scans)

    for scan in scans:
        if scan.filename and os.path.exists(scan.filename):
            try:
                os.remove(scan.filename)
            except Exception as e:
                logger.warning(f"Failed to delete file {scan.filename}: {e}")
        db.session.delete(scan)

    db.session.commit()

    return jsonify({"success": True, "message": f"Successfully cleared all {count} scan records and associated files."}), 200
