from flask import Blueprint, jsonify
from models.scan import Scan
from database import db
from sqlalchemy import func

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/", methods=["GET"])
def get_analytics():
    total_scans = Scan.query.count()
    completed_scans = Scan.query.filter_by(status="completed").count()
    failed_scans = Scan.query.filter_by(status="failed").count()
    
    # Average score
    avg_score = db.session.query(func.avg(Scan.privacy_score)).filter_by(status="completed").scalar()
    
    # Group by risk level
    risk_distribution = db.session.query(Scan.risk_level, func.count(Scan.id)).filter_by(status="completed").group_by(Scan.risk_level).all()
    risk_counts = {level: count for level, count in risk_distribution}
    
    return jsonify({
        "success": True,
        "metrics": {
            "totalScans": total_scans,
            "completedScans": completed_scans,
            "failedScans": failed_scans,
            "averagePrivacyScore": round(avg_score, 2) if avg_score else 0,
            "riskDistribution": risk_counts
        }
    })
