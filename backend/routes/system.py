import psutil
from flask import Blueprint, jsonify
from database import db
from config import Config
from services.job_manager import job_manager

system_bp = Blueprint("system", __name__)

@system_bp.route("/health", methods=["GET"])
def health_check():
    db_ok = True
    try:
        db.session.execute('SELECT 1')
    except Exception:
        db_ok = False
        
    return jsonify({
        "status": "healthy" if db_ok else "unhealthy",
        "components": {
            "database": "connected" if db_ok else "disconnected",
            "geminiApi": "configured" if Config.GEMINI_API_KEY else "missing"
        }
    }), 200 if db_ok else 503

@system_bp.route("/metrics", methods=["GET"])
def system_metrics():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return jsonify({
        "success": True,
        "metrics": {
            "cpuPercent": psutil.cpu_percent(interval=1),
            "memoryUsagePercent": memory.percent,
            "memoryAvailableMb": memory.available / (1024 * 1024),
            "diskUsagePercent": disk.percent,
            "jobsActive": len(job_manager.futures),
            "jobsCancelled": len(job_manager.cancelled_scans)
        }
    })
