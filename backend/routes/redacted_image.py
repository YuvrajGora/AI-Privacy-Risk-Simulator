import os
from flask import Blueprint, jsonify, send_file, request
from models.scan import Scan

redacted_image_bp = Blueprint("redacted_image", __name__)


@redacted_image_bp.route("/redacted-image/<string:scan_id>", methods=["GET"])
def get_redacted_image(scan_id):
    """
    Serve a redacted image.
    Optional query param: ?mode=blur|pixelate|blackbox|solid
    Falls back to the most recently generated image if mode not specified.
    """
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found."}), 404

    mode = request.args.get("mode", "").lower().strip()

    # Try mode-specific cached path first
    image_path = None
    if mode:
        image_path = scan.get_redacted_path_for_mode(mode)

    # Fall back to the generic pointer
    if not image_path:
        image_path = scan.redacted_image_path

    if not image_path:
        return jsonify({"success": False, "error": "Redacted image not available yet."}), 404

    if not os.path.exists(image_path):
        return jsonify({"success": False, "error": "Redacted image file missing from server."}), 404

    return send_file(image_path)
