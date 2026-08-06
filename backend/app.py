import os
# Limit PyTorch / BLAS / OpenMP threads to reduce memory footprint on Render free tier
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

try:
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except Exception:
    pass

import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from config import Config
from database import db
from routes.upload import upload_bp
from routes.report import report_bp
from routes.history import history_bp
from routes.status import status_bp
from routes.image import image_bp

# Load environment variables
load_dotenv()

def setup_logging(app):
    """Configure structured logging to file (backend/logs/app.log) and console."""
    log_file = app.config.get("LOG_FILE")
    os.makedirs(app.config.get("LOG_FOLDER"), exist_ok=True)

    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(threadName)s): %(message)s"
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)

    # Logging setup
    setup_logging(app)
    logger = logging.getLogger(__name__)

    # Initialize Extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["10000 per hour"],
        storage_uri="memory://"
    )

    # Register Blueprints with v1 prefix
    from routes.cancel import cancel_bp
    from routes.export import export_bp
    from routes.annotated_image import annotated_bp
    from routes.analytics import analytics_bp
    from routes.system import system_bp
    from routes.redact import redact_bp
    from routes.redacted_image import redacted_image_bp
    from routes.comparison import comparison_bp

    app.register_blueprint(upload_bp, url_prefix="/api/v1")
    app.register_blueprint(report_bp, url_prefix="/api/v1/report")
    app.register_blueprint(history_bp, url_prefix="/api/v1/history")
    app.register_blueprint(status_bp, url_prefix="/api/v1/status")
    app.register_blueprint(image_bp, url_prefix="/api/v1/image")
    app.register_blueprint(cancel_bp, url_prefix="/api/v1/cancel")
    app.register_blueprint(export_bp, url_prefix="/api/v1/export")
    app.register_blueprint(annotated_bp, url_prefix="/api/v1/annotated-image")
    app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")
    app.register_blueprint(system_bp, url_prefix="/api/v1/system")
    app.register_blueprint(redact_bp, url_prefix="/api/v1")
    app.register_blueprint(redacted_image_bp, url_prefix="/api/v1")
    app.register_blueprint(comparison_bp, url_prefix="/api/v1")

    # Apply specific limits
    if os.environ.get("FLASK_ENV") == "development" or app.config.get("ENV") == "development" or app.debug:
        limiter.limit("1000 per hour")(upload_bp)
        limiter.limit("1000 per hour")(report_bp)
        limiter.limit("1000 per hour")(history_bp)
        limiter.limit("1000 per hour")(redact_bp)
    else:
        limiter.limit("10 per hour")(upload_bp)
        limiter.limit("100 per hour")(report_bp)
        limiter.limit("100 per hour")(history_bp)
        limiter.limit("20 per hour")(redact_bp)

    # Centralized Error Handlers (Uniform JSON Format)
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"success": False, "error": str(error.description if hasattr(error, 'description') else "Bad Request")}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "error": "Requested API resource not found."}), 404

    @app.errorhandler(429)
    def ratelimit_handler(error):
        return jsonify({"success": False, "error": "Rate limit exceeded. Please try again later."}), 429

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({"success": False, "error": "File size exceeds maximum allowed limit of 20MB."}), 413

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {error}", exc_info=True)
        return jsonify({"success": False, "error": "An unexpected internal server error occurred."}), 500

    # Ensure Database Tables Exist & Auto-Migrate missing columns for SQLite
    with app.app_context():
        try:
            db.create_all()
            # Inspect scans table columns
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if inspector.has_table("scans"):
                existing_cols = {col["name"] for col in inspector.get_columns("scans")}
                required_cols = {
                    "original_path": "VARCHAR(255)",
                    "redacted_blur_path": "VARCHAR(255)",
                    "redacted_pixelate_path": "VARCHAR(255)",
                    "redacted_blackbox_path": "VARCHAR(255)",
                    "redacted_solid_path": "VARCHAR(255)"
                }
                with db.engine.begin() as conn:
                    for col_name, col_type in required_cols.items():
                        if col_name not in existing_cols:
                            conn.execute(text(f"ALTER TABLE scans ADD COLUMN {col_name} {col_type}"))
                            logger.info(f"Auto-migrated missing DB column: scans.{col_name}")
        except Exception as mig_err:
            logger.warning(f"DB Auto-migration warning: {mig_err}")
        logger.info("Database tables verified & initialized.")


    # Start background cleanup thread
    import threading
    from services.cleanup_service import run_cleanup_job
    import time
    
    def cleanup_worker():
        while True:
            try:
                run_cleanup_job(app, max_age_hours=24)
            except Exception as e:
                app.logger.error(f"Cleanup job error: {e}")
            time.sleep(3600)  # Run every hour
            
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()

    # Enhanced Health Check Endpoint
    @app.route("/api/v1/health", methods=["GET"])
    def health_check():
        db_status = "connected"
        try:
            db.session.execute(db.select(1))
        except Exception:
            db_status = "disconnected"

        gemini_key = app.config.get("GEMINI_API_KEY", "")
        gemini_status = "configured" if (gemini_key and gemini_key != "your_gemini_api_key_here") else "not_configured"

        return jsonify({
            "status": "healthy",
            "database": db_status,
            "gemini": gemini_status
        }), 200

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.logger.info(f"Starting AI Privacy Risk Simulator backend on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
