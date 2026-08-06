from database import db
from datetime import datetime
import json

class Scan(db.Model):
    __tablename__ = "scans"

    __table_args__ = (
        db.Index("idx_scans_scan_id", "scan_id"),
        db.Index("idx_scans_created_at", "created_at"),
        db.Index("idx_scans_status", "status"),
        db.Index("idx_scans_risk_level", "risk_level"),
        db.Index("idx_scans_image_hash", "image_hash"),
    )

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    target_name = db.Column(db.String(255), nullable=False)
    scan_mode = db.Column(db.String(50), default="deep")
    privacy_level = db.Column(db.String(50), default="high")

    # Hashing & Storage Paths
    image_hash = db.Column(db.String(64), nullable=True, index=True)
    thumbnail_path = db.Column(db.String(255), nullable=True)
    annotated_path = db.Column(db.String(255), nullable=True)

    # Immutable original copy — never modified after upload
    original_path = db.Column(db.String(255), nullable=True)

    # Job Lifecycle: queued -> pending -> processing -> completed / failed / cancelled
    status = db.Column(db.String(20), default="queued", nullable=False, index=True)
    progress = db.Column(db.Integer, default=0, nullable=False)
    current_step = db.Column(db.String(100), default="Queued", nullable=False)
    error_message = db.Column(db.Text, nullable=True)

    privacy_score = db.Column(db.Integer, nullable=True, default=100)
    risk_level = db.Column(db.String(20), nullable=True, default="Safe", index=True)
    summary = db.Column(db.Text, nullable=True)

    # JSON Storage Columns
    metrics_json = db.Column(db.Text, nullable=True)
    details_json = db.Column(db.Text, nullable=True)
    report_json = db.Column(db.Text, nullable=True)
    recommendations_json = db.Column(db.Text, nullable=True)

    # Redaction Engine Fields — generic pointer to last used mode (backward compat)
    redacted_image_path = db.Column(db.String(255), nullable=True)
    redacted_report_json = db.Column(db.Text, nullable=True)
    redaction_status = db.Column(db.String(20), default="none", nullable=False)
    redaction_progress = db.Column(db.Integer, default=0, nullable=False)
    redaction_current_step = db.Column(db.String(100), default="", nullable=False)
    redaction_mode = db.Column(db.String(20), nullable=True)

    # Per-mode cached redacted image paths (immutable redaction architecture)
    redacted_blur_path     = db.Column(db.String(255), nullable=True)
    redacted_pixelate_path = db.Column(db.String(255), nullable=True)
    redacted_blackbox_path = db.Column(db.String(255), nullable=True)
    redacted_solid_path    = db.Column(db.String(255), nullable=True)

    # Job Timestamps
    queued_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    findings = db.relationship("Finding", backref="scan", cascade="all, delete-orphan", lazy=True)

    def get_redacted_path_for_mode(self, mode: str):
        """Return cached redacted image path for a given mode, or None if not yet generated."""
        return {
            "blur":     self.redacted_blur_path,
            "pixelate": self.redacted_pixelate_path,
            "blackbox": self.redacted_blackbox_path,
            "solid":    self.redacted_solid_path,
        }.get(mode)

    def set_redacted_path_for_mode(self, mode: str, path: str):
        """Store the cached redacted image path for a given mode."""
        if mode == "blur":
            self.redacted_blur_path = path
        elif mode == "pixelate":
            self.redacted_pixelate_path = path
        elif mode == "blackbox":
            self.redacted_blackbox_path = path
        elif mode == "solid":
            self.redacted_solid_path = path
        self.redacted_image_path = path
        self.redaction_mode = mode

    def get_cached_modes(self) -> list:
        """Return list of modes for which a redacted image already exists on disk."""
        import os
        cached = []
        for mode, path in {
            "blur":     self.redacted_blur_path,
            "pixelate": self.redacted_pixelate_path,
            "blackbox": self.redacted_blackbox_path,
            "solid":    self.redacted_solid_path,
        }.items():
            if path and os.path.exists(path):
                cached.append(mode)
        return cached

    def to_status_dict(self):
        return {
            "scanId": self.scan_id,
            "status": self.status,
            "progress": self.progress,
            "currentStep": self.current_step,
            "errorMessage": self.error_message,
            "queuedAt": self.queued_at.isoformat() if self.queued_at else None,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
        }

    def to_dict(self):
        if self.report_json:
            try:
                cached_report = json.loads(self.report_json)
                cached_report["status"] = self.status
                cached_report["progress"] = self.progress
                cached_report["currentStep"] = self.current_step
                cached_report["cachedRedactionModes"] = self.get_cached_modes()
                return cached_report
            except Exception:
                pass

        return {
            "scanId": self.scan_id,
            "targetName": self.target_name,
            "scanMode": self.scan_mode,
            "privacyLevel": self.privacy_level,
            "status": self.status,
            "progress": self.progress,
            "currentStep": self.current_step,
            "errorMessage": self.error_message,
            "privacyScore": self.privacy_score,
            "riskLevel": self.risk_level,
            "summary": self.summary or "",
            "metrics": json.loads(self.metrics_json) if self.metrics_json else {},
            "threats": [f.to_dict() for f in self.findings],
            "recommendations": json.loads(self.recommendations_json) if self.recommendations_json else [],
            "analysisDetails": json.loads(self.details_json) if self.details_json else {},
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "cachedRedactionModes": self.get_cached_modes(),
        }
