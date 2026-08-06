import os
from flask import Blueprint, jsonify, send_file
from models.scan import Scan
from services.pdf_service import generate_pdf_report
from config import Config

export_bp = Blueprint("export", __name__)

@export_bp.route("/pdf/<scan_id>", methods=["GET"])
def export_pdf(scan_id):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    
    if not scan:
        return jsonify({"success": False, "error": "Scan not found"}), 404
        
    if scan.status != "completed":
        return jsonify({
            "success": False, 
            "error": "Scan is not completed. PDF export is only available for completed scans."
        }), 400
        
    # Ensure export directory exists
    export_dir = os.path.join(Config.UPLOAD_FOLDER, "exports")
    os.makedirs(export_dir, exist_ok=True)
    
    pdf_path = os.path.join(export_dir, f"{scan_id}_report.pdf")
    
    # Generate the PDF if it doesn't exist
    if not os.path.exists(pdf_path):
        try:
            generate_pdf_report(scan, pdf_path)
        except Exception as e:
            return jsonify({"success": False, "error": f"Failed to generate PDF: {str(e)}"}), 500
            
    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"privacy_report_{scan_id}.pdf"
    )
