import os
import logging
from flask import Blueprint, jsonify, send_file
from models.scan import Scan

image_bp = Blueprint("image", __name__)
logger = logging.getLogger(__name__)

@image_bp.route("/<string:scan_id>", methods=["GET"])
def get_scan_image(scan_id: str):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan or not scan.filename:
        return jsonify({"success": False, "error": f"Image for scan '{scan_id}' not found."}), 404

    if not os.path.exists(scan.filename):
        return jsonify({"success": False, "error": "Image file no longer exists on server storage."}), 404

    return send_file(scan.filename)
