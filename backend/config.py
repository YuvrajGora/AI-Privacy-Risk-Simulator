import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # Storage settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ORIGINAL_FOLDER = os.path.join(UPLOAD_FOLDER, "originals")   # IMMUTABLE — never modified
    THUMBNAIL_FOLDER = os.path.join(UPLOAD_FOLDER, "thumbnails")
    ANNOTATED_FOLDER = os.path.join(UPLOAD_FOLDER, "annotated")
    REDACTED_FOLDER = os.path.join(UPLOAD_FOLDER, "redacted")
    # Per-mode redacted caches
    REDACTED_BLUR_FOLDER    = os.path.join(REDACTED_FOLDER, "blur")
    REDACTED_PIXELATE_FOLDER= os.path.join(REDACTED_FOLDER, "pixelate")
    REDACTED_BLACKBOX_FOLDER= os.path.join(REDACTED_FOLDER, "blackbox")
    REDACTED_SOLID_FOLDER   = os.path.join(REDACTED_FOLDER, "solid")

    LOG_FOLDER = os.path.join(BASE_DIR, "logs")
    LOG_FILE = os.path.join(LOG_FOLDER, "app.log")

    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB max file size
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/pjpeg", "image/webp"}

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'privacy_simulator.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Gemini API Key
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    # Job Manager Settings
    MAX_CONCURRENT_JOBS = 3

    # All valid redaction modes
    REDACTION_MODES = ["blur", "pixelate", "blackbox", "solid"]
    REDACTED_MODE_FOLDERS = {
        "blur":     REDACTED_BLUR_FOLDER,
        "pixelate": REDACTED_PIXELATE_FOLDER,
        "blackbox": REDACTED_BLACKBOX_FOLDER,
        "solid":    REDACTED_SOLID_FOLDER,
    }

    @staticmethod
    def init_app(app):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.ORIGINAL_FOLDER, exist_ok=True)
        os.makedirs(Config.THUMBNAIL_FOLDER, exist_ok=True)
        os.makedirs(Config.ANNOTATED_FOLDER, exist_ok=True)
        os.makedirs(Config.REDACTED_FOLDER, exist_ok=True)
        os.makedirs(Config.REDACTED_BLUR_FOLDER, exist_ok=True)
        os.makedirs(Config.REDACTED_PIXELATE_FOLDER, exist_ok=True)
        os.makedirs(Config.REDACTED_BLACKBOX_FOLDER, exist_ok=True)
        os.makedirs(Config.REDACTED_SOLID_FOLDER, exist_ok=True)
        os.makedirs(Config.LOG_FOLDER, exist_ok=True)

