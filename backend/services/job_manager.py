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
    def __init__(self, max_workers=2):
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
                        self._update_scan_status(app, scan_id, "completed")
                        
                except Exception as e:
                    logger.error(f"Job {scan_id} failed: {e}\n{traceback.format_exc()}")
                    self._update_scan_status(app, scan_id, "failed", str(e))
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

# Global singleton
job_manager = JobManager(max_workers=Config.MAX_CONCURRENT_SCANS if hasattr(Config, 'MAX_CONCURRENT_SCANS') else 2)
