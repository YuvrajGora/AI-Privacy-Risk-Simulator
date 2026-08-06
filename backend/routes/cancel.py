from flask import Blueprint, jsonify
from services.job_manager import job_manager
from models.scan import Scan

cancel_bp = Blueprint("cancel", __name__)

@cancel_bp.route("/<scan_id>", methods=["POST"])
def cancel_scan(scan_id):
    scan = Scan.query.filter_by(scan_id=scan_id).first()
    
    if not scan:
        return jsonify({"success": False, "error": "Scan not found"}), 404
        
    if scan.status in ["completed", "failed", "cancelled"]:
        return jsonify({
            "success": False,
            "error": f"Cannot cancel scan in '{scan.status}' state"
        }), 400
        
    # Cancel the job in job_manager
    cancelled = job_manager.cancel_job(scan_id)
    
    # If it wasn't running but was queued/pending, it will be cancelled when it starts
    # update status right away
    if scan.status in ["queued", "pending"]:
        scan.status = "cancelled"
        scan.current_step = "Cancelled"
        from database import db
        db.session.commit()
        cancelled = True
        
    if cancelled:
        return jsonify({"success": True, "status": "cancelled"}), 200
    else:
        # Fallback if job is already processing and can't be easily stopped
        return jsonify({"success": False, "error": "Failed to cancel job"}), 500
