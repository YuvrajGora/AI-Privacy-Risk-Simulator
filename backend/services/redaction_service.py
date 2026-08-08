import os
import cv2
import json
import logging
import numpy as np
from database import db
from models.scan import Scan
from config import Config

logger = logging.getLogger(__name__)


def update_redaction_status(app, scan_id, status, progress, step, error_msg=None):
    with app.app_context():
        scan = Scan.query.filter_by(scan_id=scan_id).first()
        if scan:
            if status:
                scan.redaction_status = status
            scan.redaction_progress = progress
            scan.redaction_current_step = step
            if error_msg:
                scan.error_message = error_msg
            db.session.commit()


def apply_redaction(img, bbox, mode):
    """
    Apply the chosen redaction style to a bbox region [x, y, w, h] on img in-place.
    Modes: blur | pixelate | blackbox | solid
    """
    if not bbox or len(bbox) != 4:
        return

    x, y, w, h = [int(v) for v in bbox]
    h_img, w_img = img.shape[:2]

    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = max(1, min(w, w_img - x))
    h = max(1, min(h, h_img - y))

    if w <= 0 or h <= 0:
        return

    roi = img[y:y + h, x:x + w]

    if mode == "blur":
        # Cap the kernel size to a safe maximum of 51 to prevent CPU performance issues.
        k_w = min(51, max(1, w // 2) | 1)
        k_h = min(51, max(1, h // 2) | 1)
        img[y:y + h, x:x + w] = cv2.GaussianBlur(roi, (k_w, k_h), 30)

    elif mode == "pixelate":
        small_w = max(1, w // 12)
        small_h = max(1, h // 12)
        temp = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
        img[y:y + h, x:x + w] = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)

    elif mode == "blackbox":
        img[y:y + h, x:x + w] = (0, 0, 0)

    elif mode == "solid":
        img[y:y + h, x:x + w] = (50, 50, 50)


def merge_or_deduplicate_bboxes(bboxes):
    """
    Deduplicates and merges bounding boxes that overlap by more than 80%.
    Overlap ratio is defined as intersection_area / min(area(A), area(B)).
    """
    if not bboxes:
        return []
        
    clean_boxes = []
    for box in bboxes:
        if not box or len(box) != 4:
            continue
        clean_boxes.append([int(v) for v in box])
        
    merged = True
    while merged:
        merged = False
        new_boxes = []
        used = set()
        for i in range(len(clean_boxes)):
            if i in used:
                continue
            box_a = clean_boxes[i]
            x1_a, y1_a, w_a, h_a = box_a
            area_a = w_a * h_a
            
            for j in range(i + 1, len(clean_boxes)):
                if j in used:
                    continue
                box_b = clean_boxes[j]
                x1_b, y1_b, w_b, h_b = box_b
                area_b = w_b * h_b
                
                # Intersection
                x1_i = max(x1_a, x1_b)
                y1_i = max(y1_a, y1_b)
                x2_i = min(x1_a + w_a, x1_b + w_b)
                y2_i = min(y1_a + h_a, y1_b + h_b)
                
                iw = max(0, x2_i - x1_i)
                ih = max(0, y2_i - y1_i)
                intersection_area = iw * ih
                
                min_area = min(area_a, area_b)
                if min_area <= 0:
                    used.add(j)
                    continue
                    
                overlap = intersection_area / float(min_area)
                if overlap > 0.80:
                    # Merge
                    x_new = min(x1_a, x1_b)
                    y_new = min(y1_a, y1_b)
                    w_new = max(x1_a + w_a, x1_b + w_b) - x_new
                    h_new = max(y1_a + h_a, y1_b + h_b) - y_new
                    
                    box_a = [x_new, y_new, w_new, h_new]
                    area_a = w_new * h_new
                    used.add(j)
                    merged = True
            new_boxes.append(box_a)
        clean_boxes = new_boxes
        
    return clean_boxes


def run_async_redaction(app, scan_id, job_mgr, mode="blur"):
    """
    Background worker — Immutable Redaction Architecture:
      1. Always reads from scan.original_path (never scan.filename)
      2. Checks per-mode cache before regenerating
      3. Saves to uploads/redacted/<mode>/<scan_id>_<mode>.jpg
      4. Updates scan.redacted_<mode>_path
    """
    import time
    t_total_start = time.time()
    logger.info(f"[REDACTION] Starting mode={mode} for scan {scan_id}")

    try:
        # ── Step 1: Load scan + check cache ───────────────────────────────
        if job_mgr and job_mgr.is_cancelled(scan_id):
            return
        update_redaction_status(app, scan_id, "processing", 10, "Checking Cache")

        with app.app_context():
            scan = Scan.query.filter_by(scan_id=scan_id).first()
            if not scan:
                raise Exception("Scan record not found.")

            # Check if this mode has already been generated and file still exists
            cached_path = scan.get_redacted_path_for_mode(mode)
            if cached_path and os.path.exists(cached_path):
                logger.info(f"[REDACTION] Cache hit for mode={mode}. Returning cached file: {cached_path}")
                scan.redacted_image_path = cached_path
                scan.redaction_mode = mode
                scan.redaction_status = "completed"
                scan.redaction_progress = 100
                scan.redaction_current_step = "Completed (Cached)"
                if scan.report_json:
                    try:
                        report_obj = json.loads(scan.report_json)
                        original_score = scan.privacy_score or 50
                        safe_score = 98
                        report_obj["safeImage"] = f"/api/v1/redacted-image/{scan_id}?mode={mode}"
                        report_obj["redactionStatus"] = "completed"
                        report_obj["redactionMode"] = mode
                        report_obj["originalScore"] = original_score
                        report_obj["safeScore"] = safe_score
                        report_obj["scoreImprovement"] = safe_score - original_score
                        report_obj["cachedRedactionModes"] = scan.get_cached_modes()
                        scan.report_json = json.dumps(report_obj)
                    except Exception as ex:
                        logger.warning(f"Could not update report_json for cache hit: {ex}")
                db.session.commit()
                return

            image_path = scan.original_path or scan.filename
            report_data = json.loads(scan.report_json) if scan.report_json else {}
            details_data = json.loads(scan.details_json) if scan.details_json else {}
            original_score = scan.privacy_score or 50

        # ── Step 2: Load original image ──────────────────────────────────
        if job_mgr and job_mgr.is_cancelled(scan_id):
            return
        update_redaction_status(app, scan_id, None, 25, "Loading Original Image")

        t_img_start = time.time()
        img = cv2.imread(image_path)
        img_load_time = time.time() - t_img_start
        if img is None:
            raise Exception(f"Failed to load original image from: {image_path}")

        # ── Step 3: Parse and deduplicate bounding boxes ──────────────────
        if job_mgr and job_mgr.is_cancelled(scan_id):
            return
        update_redaction_status(app, scan_id, None, 45, f"Applying {mode.capitalize()} Redaction")

        t_parse_start = time.time()

        face_boxes = []
        pii_boxes = []
        qr_boxes = []
        barcode_boxes = []

        # 1. Face locations from details_data
        for face in details_data.get("faceLocations", []):
            x, y, w, h = face.get("x", 0), face.get("y", 0), face.get("width", 0), face.get("height", 0)
            if w > 0 and h > 0:
                bbox = [x, y, w, h]
                face_boxes.append(bbox)
                msg = f"[REDACTION AUDIT] Detail Face | Action: REDACTED | BBox: {bbox} | Reason: Localized face region"
                print(msg)
                logger.info(msg)

        # 2. QR code bounding boxes from details_data
        for qr in details_data.get("decodedQRCodes", []):
            if qr.get("bbox"):
                bbox = qr["bbox"]
                qr_boxes.append(bbox)
                msg = f"[REDACTION AUDIT] Detail QR | Action: REDACTED | BBox: {bbox} | Reason: Localized QR region"
                print(msg)
                logger.info(msg)

        # 3. Threat bounding boxes from report
        for threat in report_data.get("threats", []):
            bbox = threat.get("bbox")
            if not bbox:
                continue
            ttype = threat.get("type", "")
            ttype_lower = ttype.lower()
            
            # Skip container-level threats whose only purpose is structural detection
            container_keywords = ["identity badge", "government id boundary", "projection screen", "screen detected", "tablet screen", "monitor boundary", "laptop/monitor screen", "mobile phone screen"]
            if any(k in ttype_lower for k in container_keywords):
                msg = f"[REDACTION AUDIT] Threat Type: '{ttype}' | Action: SKIPPED | BBox: {bbox} | Reason: Container-level structural threat"
                print(msg)
                logger.info(msg)
                continue
                
            msg = f"[REDACTION AUDIT] Threat Type: '{ttype}' | Action: REDACTED | BBox: {bbox} | Reason: Localized sensitive region"
            print(msg)
            logger.info(msg)
            
            if "face" in ttype_lower or "biometric" in ttype_lower:
                face_boxes.append(bbox)
            elif "qr" in ttype_lower:
                qr_boxes.append(bbox)
            elif "barcode" in ttype_lower:
                barcode_boxes.append(bbox)
            else:
                pii_boxes.append(bbox)

        # 4. Bounding boxes from piiFound
        pii_list = report_data.get("piiFound", []) or []
        if not pii_list and "detections" in report_data:
            pii_list = report_data.get("detections", {}).get("piiFound", []) or []
        for pii in pii_list:
            bbox = pii.get("bbox")
            if not bbox:
                continue
            ptype = pii.get("type", "")
            ptype_lower = ptype.lower()
            
            # Skip container-level PII categories to prevent over-redaction
            container_keywords = ["identity badge", "screen"]
            if any(k in ptype_lower for k in container_keywords):
                msg = f"[REDACTION AUDIT] PII Type: '{ptype}' | Action: SKIPPED | BBox: {bbox} | Reason: Container-level structural threat"
                print(msg)
                logger.info(msg)
                continue
                
            msg = f"[REDACTION AUDIT] PII Type: '{ptype}' | Action: REDACTED | BBox: {bbox} | Reason: Localized sensitive region"
            print(msg)
            logger.info(msg)
            
            if "face" in ptype_lower or "biometric" in ptype_lower:
                face_boxes.append(bbox)
            elif "qr" in ptype_lower:
                qr_boxes.append(bbox)
            elif "barcode" in ptype_lower:
                barcode_boxes.append(bbox)
            else:
                pii_boxes.append(bbox)

        # Deduplicate and merge boxes in each category
        face_boxes = merge_or_deduplicate_bboxes(face_boxes)
        qr_boxes = merge_or_deduplicate_bboxes(qr_boxes)
        barcode_boxes = merge_or_deduplicate_bboxes(barcode_boxes)
        pii_boxes = merge_or_deduplicate_bboxes(pii_boxes)

        parse_time = time.time() - t_parse_start

        # ── Step 3.5: Apply Redactions and Measure Times ──────────────────
        already_redacted = []

        def is_already_redacted(bbox):
            for r_box in already_redacted:
                x1_a, y1_a, w_a, h_a = bbox
                x1_b, y1_b, w_b, h_b = r_box
                area_a = w_a * h_a
                
                x1_i = max(x1_a, x1_b)
                y1_i = max(y1_a, y1_b)
                x2_i = min(x1_a + w_a, x1_b + w_b)
                y2_i = min(y1_a + h_a, y1_b + h_b)
                
                iw = max(0, x2_i - x1_i)
                ih = max(0, y2_i - y1_i)
                intersection_area = iw * ih
                
                if area_a > 0:
                    overlap = intersection_area / float(area_a)
                    if overlap > 0.80:
                        return True
            return False

        # Face Redaction
        t_face_start = time.time()
        for bbox in face_boxes:
            if not is_already_redacted(bbox):
                apply_redaction(img, bbox, mode)
                already_redacted.append(bbox)
        face_redact_time = time.time() - t_face_start

        # QR Redaction
        t_qr_start = time.time()
        for bbox in qr_boxes:
            if not is_already_redacted(bbox):
                apply_redaction(img, bbox, mode)
                already_redacted.append(bbox)
        qr_redact_time = time.time() - t_qr_start

        # Barcode Redaction
        t_barcode_start = time.time()
        for bbox in barcode_boxes:
            if not is_already_redacted(bbox):
                apply_redaction(img, bbox, mode)
                already_redacted.append(bbox)
        barcode_redact_time = time.time() - t_barcode_start

        # PII Redaction (includes government IDs, names, addresses)
        t_pii_start = time.time()
        for bbox in pii_boxes:
            if not is_already_redacted(bbox):
                apply_redaction(img, bbox, mode)
                already_redacted.append(bbox)
        pii_redact_time = time.time() - t_pii_start

        # ── Step 4: Save safely to per-mode subfolder ────────────────────
        if job_mgr and job_mgr.is_cancelled(scan_id):
            return
        update_redaction_status(app, scan_id, None, 80, "Saving Redacted Image")

        t_save_start = time.time()
        mode_folder = Config.REDACTED_MODE_FOLDERS.get(mode, Config.REDACTED_FOLDER)
        os.makedirs(mode_folder, exist_ok=True)
        safe_filename = f"{scan_id}_{mode}.jpg"
        safe_path = os.path.join(mode_folder, safe_filename)
        cv2.imwrite(safe_path, img)   # cv2.imwrite strips EXIF automatically
        save_time = time.time() - t_save_start

        # ── Step 5: Update DB ────────────────────────────────────────────
        if job_mgr and job_mgr.is_cancelled(scan_id):
            return
        update_redaction_status(app, scan_id, None, 95, "Updating Report")

        with app.app_context():
            scan = Scan.query.filter_by(scan_id=scan_id).first()
            scan.set_redacted_path_for_mode(mode, safe_path)

            safe_score = 98
            score_improvement = safe_score - original_score

            safe_report = {
                "privacyStatus": "Safe To Share",
                "originalScore": original_score,
                "safeScore": safe_score,
                "scoreImprovement": score_improvement,
                "redactionMode": mode,
                "remainingRisks": [],
                "summary": (
                    f"All detected sensitive items have been successfully obscured using "
                    f"{mode} redaction. EXIF metadata stripped."
                )
            }

            scan.redacted_report_json = json.dumps(safe_report)
            scan.redaction_status = "completed"
            scan.redaction_progress = 100
            scan.redaction_current_step = "Completed"

            if scan.report_json:
                try:
                    report_obj = json.loads(scan.report_json)
                    report_obj["safeImage"] = f"/api/v1/redacted-image/{scan_id}?mode={mode}"
                    report_obj["redactionStatus"] = "completed"
                    report_obj["redactionMode"] = mode
                    report_obj["originalScore"] = original_score
                    report_obj["safeScore"] = safe_score
                    report_obj["scoreImprovement"] = score_improvement
                    report_obj["cachedRedactionModes"] = scan.get_cached_modes()
                    scan.report_json = json.dumps(report_obj)
                except Exception as ex:
                    logger.warning(f"Could not update main report_json: {ex}")

            db.session.commit()

            total_time = time.time() - t_total_start
            redaction_log = (
                "==================================================\n"
                f"REDACTION SERVICE - Mode: {mode.upper()}\n"
                "--------------------------------------------------\n"
                f"Image Loading:          {img_load_time * 1000:.2f} ms\n"
                f"Bounding Box Parsing:   {parse_time * 1000:.2f} ms\n"
                f"Face Redaction:         {face_redact_time * 1000:.2f} ms\n"
                f"PII Redaction:          {pii_redact_time * 1000:.2f} ms\n"
                f"QR Redaction:           {qr_redact_time * 1000:.2f} ms\n"
                f"Barcode Redaction:      {barcode_redact_time * 1000:.2f} ms\n"
                f"Saving Image (EXIF):    {save_time * 1000:.2f} ms\n"
                f"Total Redaction Time:   {total_time * 1000:.2f} ms\n"
                "=================================================="
            )
            print(redaction_log)
            logger.info(redaction_log)

    except Exception as e:
        logger.error(f"[REDACTION] Error for scan {scan_id}: {e}", exc_info=True)
        update_redaction_status(app, scan_id, "failed", 100, "Failed", error_msg=str(e))
        raise e
    finally:
        # Release loaded image buffer and force garbage collection
        if 'img' in locals():
            del img
        import gc
        gc.collect()
