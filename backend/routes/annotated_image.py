from flask import Blueprint, jsonify, send_file
import os
from models.scan import Scan

annotated_bp = Blueprint("annotated", __name__)

@annotated_bp.route("/<scan_id>", methods=["GET"])
def get_annotated_image(scan_id):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    
    if not scan:
        return jsonify({"success": False, "error": "Scan not found"}), 404
        
    if not scan.annotated_path or not os.path.exists(scan.annotated_path):
        return jsonify({"success": False, "error": "Annotated image not found or not generated yet"}), 404
        
    return send_file(scan.annotated_path, mimetype="image/png")
