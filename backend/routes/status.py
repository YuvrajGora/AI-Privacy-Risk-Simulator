from flask import Blueprint, jsonify
from models.scan import Scan

status_bp = Blueprint("status", __name__)

@status_bp.route("/<string:scan_id>", methods=["GET"])
def get_scan_status(scan_id: str):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan:
        return jsonify({"success": False, "error": f"Scan with ID '{scan_id}' not found."}), 404

    return jsonify(scan.to_status_dict()), 200
