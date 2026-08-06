import os
import time
import logging
from datetime import datetime, timedelta
from database import db
from models.scan import Scan
from config import Config

logger = logging.getLogger(__name__)

def delete_old_files(directory, max_age_hours):
    """Deletes files in a directory older than max_age_hours."""
    if not os.path.exists(directory):
        return
        
    current_time = time.time()
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            file_age = current_time - os.path.getmtime(filepath)
            if file_age > (max_age_hours * 3600):
                try:
                    os.remove(filepath)
                    logger.info(f"Deleted old file: {filepath}")
                except Exception as e:
                    logger.error(f"Error deleting file {filepath}: {e}")

def run_cleanup_job(app, max_age_hours=24):
    """Deletes old database records and orphaned files."""
    with app.app_context():
        logger.info(f"Running cleanup job for scans older than {max_age_hours} hours...")
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        old_scans = Scan.query.filter(Scan.created_at < cutoff_time).all()
        for scan in old_scans:
            try:
                # Delete files
                if scan.target_name:
                    file_path = os.path.join(Config.UPLOAD_FOLDER, scan.target_name)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                
                if scan.thumbnail_path and os.path.exists(scan.thumbnail_path):
                    os.remove(scan.thumbnail_path)
                    
                if scan.annotated_path and os.path.exists(scan.annotated_path):
                    os.remove(scan.annotated_path)
                
                db.session.delete(scan)
            except Exception as e:
                logger.error(f"Error cleaning up scan {scan.scan_id}: {e}")
                
        db.session.commit()
        
        # Also clean up any orphaned files in the directories
        delete_old_files(Config.UPLOAD_FOLDER, max_age_hours)
        delete_old_files(Config.THUMBNAIL_FOLDER, max_age_hours)
        delete_old_files(Config.ANNOTATED_FOLDER, max_age_hours)
        
        logger.info("Cleanup job completed.")
