import json
from database import db

class Finding(db.Model):
    __tablename__ = "findings"

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.String(36), db.ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False)
    threat_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # High, Medium, Safe
    description = db.Column(db.Text, nullable=False)
    bbox_json = db.Column(db.Text, nullable=True)  # Stores [x, y, width, height] array

    def to_dict(self):
        bbox = None
        if self.bbox_json:
            try:
                bbox = json.loads(self.bbox_json)
            except Exception:
                bbox = None

        res = {
            "type": self.threat_type,
            "severity": self.severity,
            "description": self.description,
        }
        if bbox is not None:
            res["bbox"] = bbox
        return res
