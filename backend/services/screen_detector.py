import cv2
import logging
import re
import numpy as np

logger = logging.getLogger(__name__)

# Common UI and Presentation Patterns for content validation
UI_PATTERNS = re.compile(
    r'(?:windows|menu|icon|document|presentation|web|chat|app|slide|agenda|topic|project|summary|meeting|workshop|title|bhim|upi|netbank|login|signin|sign-in|user|pass|otp|code)',
    re.IGNORECASE
)

# Generic ignore list keyword check on text (to help reject signs, backdrops, doors)
IGNORE_OCR_KEYWORDS = re.compile(
    r'\b(?:door|cupboard|table|cabinet|wall|wardrobe|air conditioner|ac|panel)\b',
    re.IGNORECASE
)

PASSWORD_PATTERN = re.compile(
    r'\b(?:password|passwd|pwd|secret|pin|passcode)\s*[:\-]?\s*\S+|'
    r'[*•●]{4,}|'               # masked password fields
    r'\bpassword\b',
    re.IGNORECASE
)
OTP_PATTERN = re.compile(
    r'\b(?:otp|one.?time.?password|verification\s+code|auth\s+code)\b.*?(\d{4,8})|'
    r'\b\d{4,8}\b(?=.*(?:otp|verify|code|confirm))',
    re.IGNORECASE
)
CHAT_PATTERN = re.compile(
    r'(?:whatsapp|telegram|instagram|discord|messenger|snapchat|signal|dm|'
    r'direct\s+message|you\s*:\s*|me\s*:\s*|seen|delivered|typing)',
    re.IGNORECASE
)
BANKING_PATTERN = re.compile(
    r'(?:net\s*banking|internet\s*banking|bank\s*login|hdfc|icici|sbi|axis\s*bank|'
    r'kotak|paytm|phonepe|googlepay|gpay|bhim|upi|account\s*balance|transaction\s*history)',
    re.IGNORECASE
)
LOGIN_PATTERN = re.compile(
    r'(?:login|sign\s*in|log\s*in|username|email\s*address|forgot\s*password|'
    r'remember\s*me|create\s*account)',
    re.IGNORECASE
)
MEDICAL_PATTERN = re.compile(
    r'(?:patient|diagnosis|prescription|medicine|dosage|hospital|clinic|'
    r'medical\s+record|health\s+report|blood\s+report|lab\s+result)',
    re.IGNORECASE
)


def detect_screens(image_path_or_img) -> dict:
    """
    Overhauled Screen & Projection Screen Detector with multi-signal validation.

    Conditions for validation (need at least TWO of):
      1. Bright display region (mean brightness >= 95)
      2. Visible UI/Presentation elements (keywords in text)
      3. Meaningful displayed text (OCR length >= 6 chars)
      4. Valid screen dimensions & aspect ratios
      5. Upper room projection surface placement

    Strict confidence score (> 0.75 required, otherwise rejected).
    """
    result = {
        "screenCount": 0,
        "screens": [],
        "sensitiveContentFound": False,
        "sensitiveItems": []
    }

    try:
        if isinstance(image_path_or_img, str):
            img = cv2.imread(image_path_or_img)
        else:
            img = image_path_or_img

        if img is None:
            return result

        h_img, w_img = img.shape[:2]
        img_area = h_img * w_img
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Edge & Contour Analysis
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 40, 130)
        dilated = cv2.dilate(edges, None, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        for cnt in contours:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

            # Accept 4-corner polygons or bounding boxes of tight contours
            if len(approx) == 4 or True:
                x, y, w, h = cv2.boundingRect(cnt)
                area = w * h
                ratio = w / max(h, 1)

                # Size bounds: must be at least 2.5% of image area, aspect ratio 0.25 to 4.0
                if area < img_area * 0.025:
                    continue
                if ratio < 0.22 or ratio > 4.5:
                    continue

                candidates.append({
                    "bbox": [x, y, w, h],
                    "area": area,
                    "ratio": ratio
                })

        # Keep largest candidates first to prevent inner boundaries duplication
        candidates.sort(key=lambda c: c["area"], reverse=True)
        filtered_cands = []
        for cand in candidates[:6]:
            bx, by, bw, bh = cand["bbox"]
            overlaps = False
            for existing in filtered_cands:
                ex, ey, ew, eh = existing["bbox"]
                # IoU overlap > 30% check
                ix = max(bx, ex)
                iy = max(by, ey)
                iw = min(bx+bw, ex+ew) - ix
                ih = min(by+bh, ey+eh) - iy
                if iw > 0 and ih > 0:
                    intersection = iw * ih
                    union = bw*bh + ew*eh - intersection
                    if intersection / max(union, 1) > 0.30:
                        overlaps = True
                        break
            if not overlaps:
                filtered_cands.append(cand)

        validated_screens = []
        from services.ocr_service import get_ocr_reader
        reader = get_ocr_reader()

        for cand in filtered_cands:
            x, y, w, h = cand["bbox"]
            roi = gray[y:y+h, x:x+w]
            if roi.size == 0:
                continue

            # ── Check Validation Signals ──
            signals = []

            # Signal 1: Bright Display Region
            mean_brightness = float(np.mean(roi))
            if mean_brightness >= 95:
                signals.append("bright_display")

            # Run OCR on ROI
            roi_img = img[y:y+h, x:x+w]
            screen_text = ""
            if reader and reader is not False:
                try:
                    # Upscale if too small
                    if w < 180:
                        scale = 180.0 / w
                        roi_img = cv2.resize(roi_img, None, fx=scale, fy=scale)
                    raw_text = reader.readtext(roi_img, detail=0, paragraph=True)
                    screen_text = " ".join(raw_text).strip()
                except Exception as e:
                    logger.debug(f"ROI OCR failed: {e}")

            # Signal 2: Displayed Text
            if len(screen_text) >= 6 and not IGNORE_OCR_KEYWORDS.search(screen_text):
                signals.append("displayed_text")

            # Signal 3: Visible UI or Presentation Elements
            if UI_PATTERNS.search(screen_text):
                signals.append("ui_or_presentation_elements")

            # Signal 4: Screen Bezel / Border (tight contour fit)
            # Checked via valid rectangular aspect ratio bounds
            if 0.5 <= cand["ratio"] <= 2.2:
                signals.append("screen_bezel")

            # Signal 5: Projection surface placement
            # Large screen occupying upper half of the room
            is_upper = (y + h/2) < (h_img * 0.65)
            is_large = w >= (w_img * 0.35)
            if is_upper and is_large:
                signals.append("projection_surface_placement")

            # ── Confidence System ──
            # Baseline confidence based on brightness and matched signals
            base_conf = 0.60 + (len(signals) * 0.08)

            # Reduce confidence significantly if no meaningful text exists
            if "displayed_text" not in signals:
                base_conf -= 0.30

            final_conf = min(0.98, round(base_conf, 2))

            # Strictly reject if confidence is <= 0.75 or satisfied signals < 2
            if final_conf <= 0.75 or len(signals) < 2:
                logger.info(f"[SCREEN DETECTOR] Rejected screen candidate at [{x},{y},{w},{h}] due to low confidence ({final_conf}) or signals ({len(signals)})")
                continue

            # Classify Projection Screen vs regular Monitor/Display screen
            if "projection_surface_placement" in signals and mean_brightness >= 120:
                stype = "Projection Screen"
            else:
                ratio = cand["ratio"]
                if 1.5 <= ratio <= 2.0:
                    stype = "Laptop/Monitor Screen"
                elif 0.45 <= ratio <= 0.65:
                    stype = "Mobile Phone Screen"
                elif 1.2 <= ratio <= 1.5:
                    stype = "Tablet Screen"
                else:
                    stype = "Screen Detected"

            # Check sensitive content type for threat analysis
            has_sensitive = False
            content_type = "blank"
            detail = ""

            if PASSWORD_PATTERN.search(screen_text):
                has_sensitive = True
                content_type = "credentials"
                detail = "Password field or login credentials exposed on screen"
            elif OTP_PATTERN.search(screen_text):
                has_sensitive = True
                content_type = "credentials"
                detail = "One-time password or authorization code visible on screen"
            elif CHAT_PATTERN.search(screen_text):
                has_sensitive = True
                content_type = "private_chat"
                detail = "Private chat messaging app visible on screen"
            elif BANKING_PATTERN.search(screen_text) or any(k in screen_text.lower() for k in ["credit card", "bank account", "account no", "ifsc"]):
                has_sensitive = True
                content_type = "financial"
                detail = "Banking, credit card, or financial details exposed on screen"
            elif MEDICAL_PATTERN.search(screen_text):
                has_sensitive = True
                content_type = "personal_info"
                detail = "Medical record or patient health document visible on screen"
            elif UI_PATTERNS.search(screen_text) or len(screen_text) > 10:
                # Regular presentation slide or document
                content_type = "presentation"
                detail = "Presentation slide or document page visible on screen"

            reason = f"{stype} identified. Content: {content_type}."
            if not has_sensitive and content_type == "blank":
                reason = f"{stype} identified but no sensitive content detected"

            validated_screens.append({
                "type": stype,
                "confidence": final_conf,
                "bbox": [x, y, w, h],
                "containsSensitiveData": has_sensitive,
                "contentType": content_type,
                "detail": detail,
                "reason": reason,
                "text": screen_text
            })

        result["screenCount"] = len(validated_screens)
        result["screens"] = validated_screens

        # Map to sensitiveItems for backwards compatibility and scoring service
        for vs in validated_screens:
            if vs["containsSensitiveData"] or vs["contentType"] == "presentation":
                tname = "Screen Content Exposed"
                if vs["contentType"] == "credentials":
                    tname = "Password Visible on Screen"
                elif vs["contentType"] == "private_chat":
                    tname = "Private Chat Visible on Screen"
                elif vs["contentType"] == "financial":
                    tname = "Banking/Financial Screen Visible"
                elif vs["contentType"] == "presentation":
                    tname = "Presentation Slide on Screen"

                result["sensitiveItems"].append({
                    "type": tname,
                    "detail": vs["detail"],
                    "contentType": vs["contentType"],
                    "bbox": vs["bbox"]
                })

    except Exception as e:
        logger.error(f"[SCREEN] Screen detection failed: {e}", exc_info=True)

    return result
