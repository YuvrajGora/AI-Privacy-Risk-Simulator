import time
from datetime import datetime
import json
import logging
import concurrent.futures
import cv2
from database import db
from models.scan import Scan
from models.finding import Finding
from services.metadata_service import extract_metadata
from services.ocr_service import perform_ocr
from services.face_service import detect_faces
from services.qr_service import detect_qr_codes
from services.scoring_service import calculate_privacy_score
from services.gemini_service import generate_gemini_summary
from services.annotation_service import generate_annotated_image
from config import Config

logger = logging.getLogger(__name__)

def update_scan_status(app, scan_id: str, status: str, progress: int, current_step: str, error_msg: str = None):
    """Helper to update background scan status in database with application context."""
    with app.app_context():
        scan = Scan.query.filter_by(scan_id=scan_id).first()
        if scan:
            if status:
                scan.status = status
            scan.progress = progress
            scan.current_step = current_step
            if error_msg:
                scan.error_message = error_msg
            db.session.commit()

def run_async_analysis(app, scan_id: str, job_mgr, image_path: str, target_name: str, scan_mode: str, privacy_level: str):
    """
    Worker task executing high-performance parallel analysis pipeline.
    Profiles execution times, supports Quick Scan mode, and enforces 10s Gemini timeout.
    """
    t_start = time.time()
    is_quick_mode = (scan_mode.lower() == 'quick')

    print("\n==================================================")
    print(f"[PIPELINE DEBUG] Parallel Pipeline Started for Scan: {scan_id} ({target_name}, mode={scan_mode})")
    print("==================================================")

    timing_metrics = {
        "metadataTime": 0.0,
        "ocrTime": 0.0,
        "faceTime": 0.0,
        "qrTime": 0.0,
        "idCardTime": 0.0,
        "screenTime": 0.0,
        "geminiTime": 0.0,
        "totalTime": 0.0
    }

    try:
        # Load image once, scale once, preprocess once
        img = cv2.imread(image_path)
        if img is None:
            update_scan_status(app, scan_id, "failed", 0, "Failed to read image")
            return

        h, w = img.shape[:2]
        target_dim = 1200.0 if is_quick_mode else 1920.0
        scale = target_dim / float(max(h, w))
        if scale < 1.0:
            img_scaled = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        else:
            scale = 1.0
            img_scaled = img

        from services.ocr_service import preprocess_image_variants
        variants = preprocess_image_variants(img_scaled)

        # Mark initial status
        update_scan_status(app, scan_id, "processing", 10, "Initializing Sequential Scanners...")

        # ── SEQUENTIAL EXECUTION: Metadata → Face → QR → OCR → Screen → Gemini ─────────
        print("\n[PIPELINE DEBUG] Launching Sequential Pipeline (Metadata -> Face -> QR -> OCR -> Screen -> Gemini)...")

        metadata_res = {}
        ocr_res = {}
        face_res = {}
        qr_res = {}


        def _run_meta():
            t_start_meta = time.time()
            t_start_meta_str = datetime.utcnow().isoformat() + "Z"
            err = None
            res = {}
            try:
                res = extract_metadata(image_path)
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                print(f"[ERROR TRACEBACK] Metadata extraction failed:\n{err}")
                logger.error(f"[PIPELINE ERROR] Metadata extraction failed: {e}")
                res = {"hasGps": False, "exif": {}, "metadata_failed": True}
                raise e
            finally:
                t_end_meta = time.time()
                t_end_meta_str = datetime.utcnow().isoformat() + "Z"
                dur = round(t_end_meta - t_start_meta, 4)
                timing_metrics["metadataTime"] = dur
                
                gps_found = "Yes" if res.get("hasGps") else "No"
                gps_coords = res.get("gps") if res.get("hasGps") else None
                exif_tags_count = res.get("rawTagsCount", 0)
                camera_make = res.get("cameraMake")
                camera_model = res.get("cameraModel")
                date_time = res.get("dateTimeOriginal")
                
                log_block = (
                    "==================================================\n"
                    "METADATA EXTRACTION\n"
                    f"Started: {t_start_meta_str}\n"
                    f"Finished: {t_end_meta_str}\n"
                    f"Execution Time: {dur} seconds\n"
                    f"Input: image_path='{image_path}'\n"
                    f"Output: {res}\n"
                    f"Detections: GPS found? {gps_found} (coordinates: {gps_coords}), "
                    f"EXIF fields: rawTagsCount={exif_tags_count}, cameraMake={camera_make}, "
                    f"cameraModel={camera_model}, dateTimeOriginal={date_time}\n"
                    f"Errors: {err}\n"
                    "=================================================="
                )
                print(log_block)
                logger.info(log_block)
            return res

        def _run_ocr():
            t_start_ocr = time.time()
            t_start_ocr_str = datetime.utcnow().isoformat() + "Z"
            err = None
            res = {}
            try:
                res = perform_ocr(img_scaled, variants=variants, quick_mode=is_quick_mode)
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                print(f"[ERROR TRACEBACK] OCR scan failed:\n{err}")
                logger.error(f"[PIPELINE ERROR] OCR execution failed: {e}")
                res = {"extractedText": "", "textBlocks": [], "detectedPii": {}, "ocr_failed": True}
                raise e
            finally:
                t_end_ocr = time.time()
                t_end_ocr_str = datetime.utcnow().isoformat() + "Z"
                dur = round(t_end_ocr - t_start_ocr, 4)
                timing_metrics["ocrTime"] = dur
                
                text_blocks = res.get("textBlocks", [])
                num_blocks = len(text_blocks)
                extracted_text = res.get("extractedText", "")
                
                blocks_info = []
                for b in text_blocks:
                    blocks_info.append(f"Text: '{b.get('text')}', Conf: {b.get('confidence')}, BBox: {b.get('bbox')}")
                blocks_detail = "\n  - ".join(blocks_info) if blocks_info else "None"
                
                ocr_log = (
                    "==================================================\n"
                    "OCR SCAN\n"
                    f"Started: {t_start_ocr_str}\n"
                    f"Finished: {t_end_ocr_str}\n"
                    f"Execution Time: {dur} seconds\n"
                    f"Input: img_scaled (dimensions={img_scaled.shape[:2]}), quick_mode={is_quick_mode}\n"
                    f"Output: textBlocks count = {num_blocks}\n"
                    f"Detections:\n"
                    f"  - Number of text blocks: {num_blocks}\n"
                    f"  - Extracted text: {repr(extracted_text)}\n"
                    f"  - Text details:\n  - {blocks_detail}\n"
                    f"Errors: {err}\n"
                    "=================================================="
                )
                print(ocr_log)
                logger.info(ocr_log)
                
                detected_pii = res.get("detectedPii", {})
                pii_entities = []
                CONFIDENCES = {
                    "aadhaarNumbers": 0.95,
                    "panIdentifiers": 0.92,
                    "passports": 0.95,
                    "drivingLicences": 0.90,
                    "creditCards": 0.98,
                    "bankAccounts": 0.90,
                    "ifscCodes": 0.88,
                    "upiIds": 0.94,
                    "otpCodes": 0.95,
                    "passwords": 0.98,
                    "signatures": 0.90,
                    "socialHandles": 0.80,
                    "phoneNumbers": 0.95,
                    "emails": 0.95,
                    "addresses": 0.88,
                    "locationLeaks": 0.85,
                    "watermarks": 0.80,
                    "chatScreenshots": 0.90,
                    "documents": 0.82,
                    "govtIdCards": 0.75,
                }
                
                for entity_type, items in detected_pii.items():
                    if not items:
                        continue
                    for item in items:
                        val = item.get("value")
                        bbox = item.get("bbox")
                        conf = CONFIDENCES.get(entity_type, 0.85)
                        pii_entities.append(f"Value: '{val}', Type: '{entity_type}', Confidence: {conf}, BBox: {bbox}")
                        
                pii_detail = "\n  - ".join(pii_entities) if pii_entities else "None"
                
                pii_log = (
                    "==================================================\n"
                    "PII DETECTION\n"
                    f"Started: {t_start_ocr_str}\n"
                    f"Finished: {t_end_ocr_str}\n"
                    f"Execution Time: {dur} seconds\n"
                    f"Input: extractedText length = {len(extracted_text)}\n"
                    f"Output: detectedPii dictionary\n"
                    f"Detections:\n  - {pii_detail}\n"
                    f"Errors: {err}\n"
                    "=================================================="
                )
                print(pii_log)
                logger.info(pii_log)
                
            return res

        def _run_face():
            t_start_face = time.time()
            t_start_face_str = datetime.utcnow().isoformat() + "Z"
            err = None
            res = {}
            try:
                res = detect_faces(img)
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                print(f"[ERROR TRACEBACK] Face detection failed:\n{err}")
                logger.error(f"[PIPELINE ERROR] Face detection failed: {e}")
                res = {"faceCount": 0, "faceLocations": [], "face_failed": True}
                raise e
            finally:
                t_end_face = time.time()
                t_end_face_str = datetime.utcnow().isoformat() + "Z"
                dur = round(t_end_face - t_start_face, 4)
                timing_metrics["faceTime"] = dur
                
                face_count = res.get("faceCount", 0)
                face_locations = res.get("faceLocations", [])
                faces_info = []
                for f in face_locations:
                    faces_info.append(f"Coords: (x={f.get('x')}, y={f.get('y')}, w={f.get('width')}, h={f.get('height')}), Confidence: {f.get('confidence')}")
                faces_detail = "\n  - ".join(faces_info) if faces_info else "None"
                
                face_log = (
                    "==================================================\n"
                    "FACE DETECTION\n"
                    f"Started: {t_start_face_str}\n"
                    f"Finished: {t_end_face_str}\n"
                    f"Execution Time: {dur} seconds\n"
                    f"Input: img (dimensions={img.shape[:2]})\n"
                    f"Output: faceCount = {face_count}\n"
                    f"Detections:\n"
                    f"  - Number of faces: {face_count}\n"
                    f"  - Faces details:\n  - {faces_detail}\n"
                    f"Errors: {err}\n"
                    "=================================================="
                )
                print(face_log)
                logger.info(face_log)
            return res

        def _run_qr():
            t_start_qr = time.time()
            t_start_qr_str = datetime.utcnow().isoformat() + "Z"
            err = None
            res = {}
            try:
                res = detect_qr_codes(img)
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                print(f"[ERROR TRACEBACK] QR detection failed:\n{err}")
                logger.error(f"[PIPELINE ERROR] QR detection failed: {e}")
                res = {"qrCount": 0, "decodedQRCodes": [], "qr_failed": True}
                raise e
            finally:
                t_end_qr = time.time()
                t_end_qr_str = datetime.utcnow().isoformat() + "Z"
                dur = round(t_end_qr - t_start_qr, 4)
                timing_metrics["qrTime"] = dur
                
                qr_count = res.get("qrCount", 0)
                qr_codes = res.get("decodedQRCodes", [])
                qrs_info = []
                for q in qr_codes:
                    qrs_info.append(f"Content: '{q.get('value')}', BBox: {q.get('bbox')}, Type: {q.get('qrType')}, Severity: {q.get('severity')}")
                qrs_detail = "\n  - ".join(qrs_info) if qrs_info else "None"
                
                qr_log = (
                    "==================================================\n"
                    "QR DETECTION\n"
                    f"Started: {t_start_qr_str}\n"
                    f"Finished: {t_end_qr_str}\n"
                    f"Execution Time: {dur} seconds\n"
                    f"Input: img (dimensions={img.shape[:2]})\n"
                    f"Output: qrCount = {qr_count}\n"
                    f"Detections:\n"
                    f"  - Number of QR codes: {qr_count}\n"
                    f"  - QR codes details:\n  - {qrs_detail}\n"
                    f"Errors: {err}\n"
                    "=================================================="
                )
                print(qr_log)
                logger.info(qr_log)
            return res

        import gc

        # Execute stages sequentially to save thread scheduling memory and control peak memory usage
        if job_mgr and job_mgr.is_cancelled(scan_id): return
        metadata_res = _run_meta()
        update_scan_status(app, scan_id, "processing", 15, "Metadata Scan Complete")
        gc.collect()

        if job_mgr and job_mgr.is_cancelled(scan_id): return
        face_res = _run_face()
        update_scan_status(app, scan_id, "processing", 30, "Face Detection Complete")
        gc.collect()

        if job_mgr and job_mgr.is_cancelled(scan_id): return
        qr_res = _run_qr()
        update_scan_status(app, scan_id, "processing", 45, "QR Analysis Complete")
        gc.collect()

        if job_mgr and job_mgr.is_cancelled(scan_id): return
        ocr_res = _run_ocr()
        update_scan_status(app, scan_id, "processing", 65, "OCR Scan Complete")
        gc.collect()

        print(f"[PIPELINE DEBUG] Sequential Core Scanners Finished!")

        if job_mgr and job_mgr.is_cancelled(scan_id): return


        # ── Step 4.5: ID Card Candidate Validation & NMS ──────────────────────
        t0_id = time.time()
        t_start_id_str = datetime.utcnow().isoformat() + "Z"
        validated_id_cards = []
        err_id = None
        try:
            from services.id_card_detector import detect_and_validate_id_cards
            from services.ocr_service import get_ocr_reader

            validated_id_cards = detect_and_validate_id_cards(
                image_path_or_img=img_scaled, # Share the scaled cv2 image matrix
                text_blocks=ocr_res.get("textBlocks", []),
                face_locations=face_res.get("faceLocations", []),
                qr_codes=qr_res.get("decodedQRCodes", []),
                reader=get_ocr_reader()
            )
        except Exception as e:
            import traceback
            err_id = traceback.format_exc()
            print(f"[ERROR TRACEBACK] ID Card Validation failed:\n{err_id}")
            logger.error(f"[PIPELINE ERROR] ID Card validation failed: {e}")
            raise e
        finally:
            t_end_id = time.time()
            t_end_id_str = datetime.utcnow().isoformat() + "Z"
            dur_id = round(t_end_id - t0_id, 4)
            timing_metrics["idCardTime"] = dur_id
            
            cards_info = []
            for c in validated_id_cards:
                cards_info.append(f"Label: '{c.get('label')}', Confidence: {c.get('confidence')}, BBox: {c.get('bbox')}, Reason: '{c.get('reason')}'")
            cards_detail = "\n  - ".join(cards_info) if cards_info else "None"
            
            id_log = (
                "==================================================\n"
                "GOVERNMENT ID DETECTION\n"
                f"Started: {t_start_id_str}\n"
                f"Finished: {t_end_id_str}\n"
                f"Execution Time: {dur_id} seconds\n"
                f"Input: img_scaled (dimensions={img_scaled.shape[:2]}), textBlocks count={len(ocr_res.get('textBlocks', []))}, faceLocations count={len(face_res.get('faceLocations', []))}\n"
                f"Output: validatedIdCards count={len(validated_id_cards)}\n"
                f"Detections:\n  - {cards_detail}\n"
                f"Errors: {err_id}\n"
                "=================================================="
            )
            print(id_log)
            logger.info(id_log)

        ocr_res.setdefault("detectedPii", {})["validatedIdCards"] = validated_id_cards

        # ── Step 4.6: Screen Detection (Skipped in Quick Scan mode) ───────────
        t0_scr = time.time()
        t_start_scr_str = datetime.utcnow().isoformat() + "Z"
        err_scr = None
        if not is_quick_mode:
            try:
                from services.screen_detector import detect_screens
                screen_res = detect_screens(img_scaled)
                # Scale coordinates back to original image size
                for scr in screen_res.get("screens", []):
                    if scr.get("bbox"):
                        scr["bbox"] = [
                            int(scr["bbox"][0] / scale),
                            int(scr["bbox"][1] / scale),
                            int(scr["bbox"][2] / scale),
                            int(scr["bbox"][3] / scale)
                        ]
                for item in screen_res.get("sensitiveItems", []):
                    if item.get("bbox"):
                        item["bbox"] = [
                            int(item["bbox"][0] / scale),
                            int(item["bbox"][1] / scale),
                            int(item["bbox"][2] / scale),
                            int(item["bbox"][3] / scale)
                        ]
                ocr_res["screenDetection"] = screen_res
            except Exception as screen_err:
                import traceback
                err_scr = traceback.format_exc()
                print(f"[ERROR TRACEBACK] Screen detection failed:\n{err_scr}")
                logger.warning(f"Screen detection step failed: {screen_err}")
                ocr_res["screenDetection"] = {"screenCount": 0, "screens": [], "sensitiveContentFound": False, "sensitiveItems": []}
                raise screen_err
            finally:
                t_end_scr = time.time()
                t_end_scr_str = datetime.utcnow().isoformat() + "Z"
                dur_scr = round(t_end_scr - t0_scr, 4)
                timing_metrics["screenTime"] = dur_scr
                
                screen_log = (
                    "==================================================\n"
                    "SCREEN DETECTION\n"
                    f"Started: {t_start_scr_str}\n"
                    f"Finished: {t_end_scr_str}\n"
                    f"Execution Time: {dur_scr} seconds\n"
                    f"Input: image_path='{image_path}'\n"
                    f"Output: screenCount={ocr_res['screenDetection'].get('screenCount', 0)}\n"
                    f"Detections: screens={ocr_res['screenDetection'].get('screens')}\n"
                    f"Errors: {err_scr}\n"
                    "=================================================="
                )
                print(screen_log)
                logger.info(screen_log)
        else:
            ocr_res["screenDetection"] = {"screenCount": 0, "screens": [], "sensitiveContentFound": False, "sensitiveItems": []}

        update_scan_status(app, scan_id, "processing", 75, "Screen Detection Complete")
        gc.collect()

        # ── Step 5: Privacy Scoring & Threat Generation ───────────────────────

        if job_mgr and job_mgr.is_cancelled(scan_id): return
        update_scan_status(app, scan_id, "processing", 85, "Evaluating Privacy Risk Score")
        print("\n[PIPELINE DEBUG] Step 5: Privacy Classifier & Scoring Started...")

        metadata_res["image_path"] = image_path
        
        t0_score = time.time()
        t_start_score_str = datetime.utcnow().isoformat() + "Z"
        err_score = None
        score_res = {}
        try:
            score_res = calculate_privacy_score(metadata_res, ocr_res, face_res, qr_res)
        except Exception as e:
            import traceback
            err_score = traceback.format_exc()
            print(f"[ERROR TRACEBACK] Risk Scoring failed:\n{err_score}")
            logger.error(f"[PIPELINE ERROR] Risk Scoring failed: {e}")
            raise e
        finally:
            t_end_score = time.time()
            t_end_score_str = datetime.utcnow().isoformat() + "Z"
            dur_score = round(t_end_score - t0_score, 4)
            
            threats = score_res.get("threats", [])
            deductions_info = []
            for t in threats:
                deductions_info.append(f"Deduction: -{t.get('deduction')} for Type: '{t.get('type')}', Reason: '{t.get('reason')}', Desc: '{t.get('description')}'")
            deductions_detail = "\n  - ".join(deductions_info) if deductions_info else "None"
            
            score_log = (
                "==================================================\n"
                "RISK SCORING\n"
                f"Started: {t_start_score_str}\n"
                f"Finished: {t_end_score_str}\n"
                f"Execution Time: {dur_score} seconds\n"
                f"Input: Metadata, OCR, Face, QR results\n"
                f"Output: privacyScore={score_res.get('privacyScore')}, riskLevel='{score_res.get('riskLevel')}'\n"
                f"Detections:\n"
                f"  - Initial score: 100\n"
                f"  - Every deduction:\n  - {deductions_detail}\n"
                f"  - Final score: {score_res.get('privacyScore')}\n"
                f"  - Risk level: '{score_res.get('riskLevel')}'\n"
                f"Errors: {err_score}\n"
                "=================================================="
            )
            print(score_log)
            logger.info(score_log)

        metrics = {
            "facesDetected": face_res.get("faceCount", 0),
            "textBlocks": len(ocr_res.get("textBlocks", [])),
            "qrCodes": qr_res.get("qrCount", 0),
            "gpsMetadata": metadata_res.get("hasGps", False),
            "timingMetrics": timing_metrics
        }

        # ── Step 6: Gemini AI Advice Generation (with 10s timeout / quick mode skip) ─
        if job_mgr and job_mgr.is_cancelled(scan_id): return
        update_scan_status(app, scan_id, "processing", 95, "Generating AI Privacy Report")
        t0_gem = time.time()
        t_start_gem_str = datetime.utcnow().isoformat() + "Z"

        if is_quick_mode and score_res["privacyScore"] in (0, 100):
            # Fast static summary for obvious quick scans
            gemini_res = {
                "summary": f"Quick scan completed. Score: {score_res['privacyScore']}/100 ({score_res['riskLevel']} Risk).",
                "recommendations": score_res.get("recommendations", []),
                "sharingAdvice": "Review identified threats before sharing."
            }
            dur_gem = round(time.time() - t0_gem, 4)
            gemini_log = (
                "==================================================\n"
                "GEMINI SERVICE (STATIC QUICK MODE)\n"
                f"Started: {t_start_gem_str}\n"
                f"Finished: {datetime.utcnow().isoformat() + 'Z'}\n"
                f"Execution Time: {dur_gem} seconds\n"
                f"Input:\nPrompt sent: None (Fast static summary)\n"
                f"Output:\nResponse: {gemini_res}\n"
                f"Detections:\n"
                f"  - Response time: {dur_gem} seconds\n"
                f"  - Fallback triggered? No\n"
                f"Errors: None\n"
                "=================================================="
            )
            print(gemini_log)
            logger.info(gemini_log)
        else:
            gemini_res = generate_gemini_summary(
                metrics=metrics,
                threats=score_res["threats"],
                privacy_score=score_res["privacyScore"],
                risk_level=score_res["riskLevel"]
            )
        timing_metrics["geminiTime"] = round(time.time() - t0_gem, 3)

        # ── Step 7: Generate Annotated Overlay Image ──────────────────────────
        analysis_details = {
            "ocrText": [
                {"text": block["text"], "bbox": block.get("bbox")}
                for block in ocr_res.get("textBlocks", [])
            ],
            "decodedQRCodes": [
                {"value": code["value"], "bbox": code.get("bbox")}
                for code in qr_res.get("decodedQRCodes", [])
            ],
            "faceLocations": face_res.get("faceLocations", []),
            "metadata": {
                "cameraMake": metadata_res.get("cameraMake"),
                "cameraModel": metadata_res.get("cameraModel"),
                "dateTimeOriginal": metadata_res.get("dateTimeOriginal"),
                "gps": metadata_res.get("gps")
            }
        }

        annotated_path = generate_annotated_image(
            image_path=image_path,
            scan_id=scan_id,
            threats=score_res["threats"],
            analysis_details=analysis_details,
            annotated_folder=Config.ANNOTATED_FOLDER
        )

        timing_metrics["totalTime"] = round(time.time() - t_start, 3)
        metrics["timingMetrics"] = timing_metrics

        # SLA Performance Targets Check
        total_dur = timing_metrics["totalTime"]
        target_limit = 5.0 if is_quick_mode else 10.0
        if total_dur > target_limit:
            stages_timing = {k: v for k, v in timing_metrics.items() if k != "totalTime"}
            if stages_timing:
                max_step = max(stages_timing.items(), key=lambda x: x[1])
                logger.warning(
                    f"[PERFORMANCE SLA EXCEEDED] Scan {scan_id} ({scan_mode}) took {total_dur}s (limit: {target_limit}s). "
                    f"Primary bottleneck: {max_step[0]} took {max_step[1]}s."
                )

        # ── Step 8: Build Final Report Object ─────────────────────────────────
        safe_to_share = score_res.get("safeToShare", False)
        identity_card_detected = score_res.get("identityCardDetected", score_res.get("govtIdDetected", False))

        report_object = {
            "scanId": scan_id,
            "targetName": target_name,
            "scanMode": scan_mode,
            "privacyLevel": privacy_level,
            "status": "completed",
            "progress": 100,
            "currentStep": "Analysis complete",
            "privacyScore": score_res["privacyScore"],
            "riskLevel": score_res["riskLevel"],
            "summary": gemini_res.get("summary", ""),
            "recommendations": gemini_res.get("recommendations", score_res.get("recommendations", [])),
            "sharingAdvice": gemini_res.get("sharingAdvice", ""),
            "safeToShare": safe_to_share,
            "identityCardDetected": identity_card_detected,
            "govtIdDetected": identity_card_detected,
            "detections": {
                "facesDetected": face_res.get("faceCount", 0),
                "piiFound": score_res.get("piiFound", []),
                "qrCodesFound": qr_res.get("qrCount", 0),
                "gpsExposed": metadata_res.get("hasGps", False),
                "identityCardDetected": identity_card_detected,
                "govtIdDetected": identity_card_detected
            },
            "threats": score_res["threats"],
            "originalImage": f"/api/v1/image/{scan_id}",
            "annotatedImage": f"/api/v1/annotated-image/{scan_id}",
            "safeImage": None,
            "redactionStatus": "none",
            "redactionMode": None,
            "originalScore": score_res["privacyScore"],
            "safeScore": None,
            "scoreImprovement": 0,
            "timingMetrics": timing_metrics,
            "totalScanTime": total_dur,
            "scoreBreakdown": score_res.get("scoreBreakdown", {}),
            "scanReliability": score_res.get("scanReliability", 100),
            "scanQuality": score_res.get("scanQuality", {})
        }

        # ── Step 9: Save Final Results to DB & Mark Completed ─────────────────
        t0_db = time.time()
        t_start_db_str = datetime.utcnow().isoformat() + "Z"
        err_db = None
        db_saved = False
        try:
            with app.app_context():
                scan = Scan.query.filter_by(scan_id=scan_id).first()
                if scan:
                    scan.status = "completed"
                    scan.progress = 100
                    scan.current_step = "Analysis complete"
                    scan.privacy_score = score_res["privacyScore"]
                    scan.risk_level = score_res["riskLevel"]
                    scan.summary = gemini_res.get("summary", "")
                    scan.annotated_path = annotated_path
                    scan.metrics_json = json.dumps(metrics)
                    scan.details_json = json.dumps(analysis_details)
                    scan.recommendations_json = json.dumps(report_object["recommendations"])
                    scan.report_json = json.dumps(report_object)

                    for threat in score_res["threats"]:
                        finding = Finding(
                            scan_id=scan_id,
                            threat_type=threat["type"],
                            severity=threat["severity"],
                            description=threat["description"],
                            bbox_json=json.dumps(threat.get("bbox")) if threat.get("bbox") else None
                        )
                        db.session.add(finding)

                    db.session.commit()
                    db_saved = True
        except Exception as e:
            import traceback
            err_db = traceback.format_exc()
            print(f"[ERROR TRACEBACK] Database save failed:\n{err_db}")
            raise e
        finally:
            t_end_db = time.time()
            dur_db = round(t_end_db - t0_db, 4)
            db_log = (
                "==================================================\n"
                "DATABASE SAVE\n"
                f"Started: {t_start_db_str}\n"
                f"Finished: {datetime.utcnow().isoformat() + 'Z'}\n"
                f"Execution Time: {dur_db} seconds\n"
                f"Input: scan_id='{scan_id}', status='completed'\n"
                f"Output: db_saved={db_saved}\n"
                f"Detections:\n"
                f"  - Record successfully saved? {'Yes' if db_saved else 'No'}\n"
                f"  - Scan ID: '{scan_id}'\n"
                f"Errors: {err_db}\n"
                "=================================================="
            )
            print(db_log)
            logger.info(db_log)

        print("\n==================================================")
        print(f"[PIPELINE DEBUG] Scan {scan_id} Completed in {timing_metrics['totalTime']}s! Final Score: {score_res['privacyScore']}")
        print(f"Timing Metrics: {json.dumps(timing_metrics)}")
        print("==================================================\n")

    except Exception as e:
        logger.error(f"Error during async analysis for scan {scan_id}: {e}", exc_info=True)
        update_scan_status(app, scan_id, "failed", 100, "Analysis failed", error_msg=str(e))
        raise e
    finally:
        # Release heavy image arrays and trigger garbage collection immediately
        if 'img' in locals():
            del img
        if 'img_scaled' in locals():
            del img_scaled
        if 'variants' in locals():
            del variants
        import gc
        gc.collect()
