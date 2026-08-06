import os
import uuid
import shutil
import logging
import hashlib
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from PIL import Image

from database import db
from models.scan import Scan
from services.analysis_service import run_async_analysis
from services.job_manager import job_manager
from services.thumbnail_service import generate_thumbnail

upload_bp = Blueprint("upload", __name__)
logger = logging.getLogger(__name__)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

def hash_image(file_stream):
    """Calculates SHA256 hash of the image stream without moving the cursor permanently."""
    hasher = hashlib.sha256()
    buf = file_stream.read(65536)
    while len(buf) > 0:
        hasher.update(buf)
        buf = file_stream.read(65536)
    file_stream.seek(0)
    return hasher.hexdigest()

@upload_bp.route("/upload", methods=["POST"])
@upload_bp.route("/upload/", methods=["POST"])
@upload_bp.route("/analyze", methods=["POST"])
@upload_bp.route("/analyze/", methods=["POST"])
@upload_bp.route("/", methods=["POST"])
def upload_image():
    logger.info("Upload request received.")

    if "image" not in request.files and "file" not in request.files:
        return jsonify({"success": False, "error": "No image file provided in request form-data."}), 400

    file = request.files.get("image") or request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    original_filename = secure_filename(file.filename)
    if not allowed_file(original_filename):
        return jsonify({
            "success": False,
            "error": "Unsupported file format. Allowed formats: PNG, JPG, JPEG, WEBP."
        }), 400

    # MIME type check
    if file.mimetype and file.mimetype.lower() not in current_app.config["ALLOWED_MIME_TYPES"]:
        return jsonify({
            "success": False,
            "error": f"Invalid MIME type '{file.mimetype}'. Only images are allowed."
        }), 400

    scan_mode = request.form.get("scanMode", "deep").strip().lower()
    privacy_level = request.form.get("privacyLevel", "high").strip().lower()

    image_hash = hash_image(file)

    scan_id = str(uuid.uuid4())
    saved_filename = f"{scan_id}_{original_filename}"
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], saved_filename)

    try:
        file.save(file_path)

        # Save immutable original copy — this file is NEVER modified
        original_folder = current_app.config.get("ORIGINAL_FOLDER",
            os.path.join(current_app.config["UPLOAD_FOLDER"], "originals"))
        os.makedirs(original_folder, exist_ok=True)
        ext = original_filename.rsplit(".", 1)[-1].lower()
        original_copy_path = os.path.join(original_folder, f"{scan_id}_original.{ext}")
        shutil.copy2(file_path, original_copy_path)

        # Image integrity check & Thumbnail generation
        try:
            thumbnail_path = generate_thumbnail(file_path, current_app.config["THUMBNAIL_FOLDER"], scan_id)
        except Exception:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"success": False, "error": "Uploaded file is corrupted or not a valid image."}), 400

        # Save initial pending Scan record in DB
        scan_record = Scan(
            scan_id=scan_id,
            filename=file_path,
            original_path=original_copy_path,   # immutable copy
            target_name=original_filename,
            scan_mode=scan_mode,
            privacy_level=privacy_level,
            image_hash=image_hash,
            thumbnail_path=thumbnail_path,
            status="queued",
            progress=0,
            current_step="Upload Received"
        )
        db.session.add(scan_record)
        db.session.commit()


        logger.info(f"Scan record created ({scan_id}). Submitting to job manager...")

        # Start background processing asynchronously via job manager
        job_manager.submit_job(
            current_app._get_current_object(),
            scan_id,
            run_async_analysis,
            image_path=file_path,
            target_name=original_filename,
            scan_mode=scan_mode,
            privacy_level=privacy_level
        )

        return jsonify({
            "scanId": scan_id,
            "status": "queued",
            "targetName": original_filename
        }), 201

    except Exception as e:
        logger.error(f"Error handling upload: {e}", exc_info=True)
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"success": False, "error": f"Failed to upload image: {str(e)}"}), 500
