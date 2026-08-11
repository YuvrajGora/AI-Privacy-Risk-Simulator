import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
from datetime import datetime
from config import Config
from database import db
from models.scan import Scan
import logging

logger = logging.getLogger(__name__)

class JobManager:
    def __init__(self, max_workers=1):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures = {}  # Map scan_id to Future
        self.cancelled_scans = set()
        self.lock = threading.Lock()


    def _update_scan_status(self, app, scan_id, status, error_message=None):
        with app.app_context():
            scan = Scan.query.filter_by(scan_id=scan_id).first()
            if scan:
                scan.status = status
                if status == "processing":
                    scan.started_at = datetime.utcnow()
                elif status in ["completed", "failed", "cancelled"]:
                    scan.completed_at = datetime.utcnow()
                
                if error_message:
                    scan.error_message = error_message
                db.session.commit()

    def is_cancelled(self, scan_id):
        with self.lock:
            return scan_id in self.cancelled_scans

    def cancel_job(self, scan_id):
        with self.lock:
            self.cancelled_scans.add(scan_id)
        
        future = self.futures.get(scan_id)
        if future and not future.done():
            # ThreadPoolExecutor doesn't easily cancel running threads,
            # but we can set the flag so the worker thread can exit early.
            # We also try to cancel the future in case it hasn't started.
            future.cancel()
            return True
        return False

    def submit_job(self, app, scan_id, task_func, *args, **kwargs):
        with self.lock:
            if scan_id in self.cancelled_scans:
                self.cancelled_scans.remove(scan_id)
                
        def wrapped_task():
            # Run task within app context
            with app.app_context():
                try:
                    if self.is_cancelled(scan_id):
                        self._update_scan_status(app, scan_id, "cancelled")
                        return

                    self._update_scan_status(app, scan_id, "processing")
                    
                    # Execute the actual task
                    task_func(app, scan_id, self, *args, **kwargs)
                    
                    if self.is_cancelled(scan_id):
                        self._update_scan_status(app, scan_id, "cancelled")
                    else:
                        # Check current DB status to ensure we don't overwrite if task already set status
                        scan = Scan.query.filter_by(scan_id=scan_id).first()
                        if scan and scan.status not in ["completed", "failed", "cancelled"]:
                            self._update_scan_status(app, scan_id, "completed")
                        
                except BaseException as e:
                    logger.error(f"[SCAN {scan_id}] Job worker failed: {e}\n{traceback.format_exc()}")
                    self._update_scan_status(app, scan_id, "failed", f"Worker execution error: {str(e)}")
                finally:
                    with self.lock:
                        if scan_id in self.futures:
                            del self.futures[scan_id]
                        if scan_id in self.cancelled_scans:
                            self.cancelled_scans.remove(scan_id)

        future = self.executor.submit(wrapped_task)
        with self.lock:
            self.futures[scan_id] = future
        
        return True

def cleanup_orphaned_scans(app):
    """
    On application startup, identify any scans left in 'processing' or 'queued' status
    from a previous terminated/restarted worker process and mark them as failed.
    """
    try:
        with app.app_context():
            stale_scans = Scan.query.filter(Scan.status.in_(["processing", "queued"])).all()
            if stale_scans:
                logger.warning(f"[STARTUP RECOVERY] Found {len(stale_scans)} orphaned scans in database. Resetting status to failed...")
                for s in stale_scans:
                    s.status = "failed"
                    s.completed_at = datetime.utcnow()
                    s.error_message = "Scan worker process was restarted or terminated during analysis"
                db.session.commit()
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned scans on startup: {e}")

# Global singleton
job_manager = JobManager(max_workers=getattr(Config, 'MAX_CONCURRENT_SCANS', 1))


