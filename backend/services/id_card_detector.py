import os
import cv2
import logging
import numpy as np

logger = logging.getLogger(__name__)

# ============================================================
# Configurable Detection Thresholds
# ============================================================
CONFIDENCE_THRESHOLD = 0.75   # Raised from 0.65 per spec
IOU_NMS_THRESHOLD = 0.45
MIN_CARD_WIDTH = 120           # Raised from 80 per spec
MIN_CARD_HEIGHT = 70           # Raised from 50 per spec
FACE_IN_CARD_AREA_MIN = 0.05  # Face must be at least 5% of card area
FACE_IN_CARD_AREA_MAX = 0.40  # Face must be at most 40% of card area

# Aspect Ratio Boundaries (CR80 standard ~1.58)
LANDSCAPE_RATIO_MIN = 1.35
LANDSCAPE_RATIO_MAX = 1.85
PORTRAIT_RATIO_MIN = 0.54
PORTRAIT_RATIO_MAX = 0.74

# ID card content keyword list
ID_CARD_PATTERNS = [
    "id", "identity", "card", "licence", "license", "driver", "aadhaar",
    "aadhar", "pan", "passport", "student", "employee", "badge", "vips",
    "republic", "govt", "india", "name", "dob", "number", "holder",
    "government", "authority", "uidai", "income tax", "transport", "voter",
    "election", "membership", "enroll", "issue", "expiry", "valid"
]


def calculate_iou(boxA, boxB):
    """Calculate Intersection over Union (IoU) of two bounding boxes [x, y, w, h]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH
    unionArea = float(boxA[2] * boxA[3] + boxB[2] * boxB[3] - interArea)
    return interArea / unionArea if unionArea > 0 else 0.0


def apply_nms(candidates, iou_threshold=IOU_NMS_THRESHOLD):
    """Non-Maximum Suppression — keeps highest confidence box, removes overlapping duplicates."""
    if not candidates:
        return []
    sorted_cands = sorted(candidates, key=lambda c: c["confidence"], reverse=True)
    selected = []
    while sorted_cands:
        best = sorted_cands.pop(0)
        selected.append(best)
        sorted_cands = [c for c in sorted_cands if calculate_iou(best["bbox"], c["bbox"]) < iou_threshold]
    return selected


def is_valid_aspect_ratio(w, h):
    """Enforce CR80 standard: landscape 1.35–1.85 or portrait 0.54–0.74."""
    ratio = float(w) / max(1, float(h))
    return (LANDSCAPE_RATIO_MIN <= ratio <= LANDSCAPE_RATIO_MAX) or \
           (PORTRAIT_RATIO_MIN <= ratio <= PORTRAIT_RATIO_MAX)


def face_is_inside_card(face, card_bbox):
    """
    STRICT check: face bounding box must be COMPLETELY inside the card bounding box.
    face = {x, y, width, height}
    card_bbox = [x, y, w, h]

    Requirements (per spec):
      face_x >= card_x
      face_y >= card_y
      face_x + face_width <= card_x + card_width
      face_y + face_height <= card_y + card_height

    Returns (True, area_ratio) if inside and area ratio is 0.05–0.40, else (False, 0).
    """
    cx, cy, cw, ch = card_bbox
    fx = face.get("x", 0)
    fy = face.get("y", 0)
    fw = face.get("width", 0)
    fh = face.get("height", 0)

    # Strict containment check
    fully_inside = (fx >= cx) and (fy >= cy) and \
                   (fx + fw <= cx + cw) and (fy + fh <= cy + ch)

    if not fully_inside:
        return False, 0.0

    face_area = fw * fh
    card_area = max(1, cw * ch)
    area_ratio = face_area / card_area

    # ID card photo should be 5%–40% of card area
    if not (FACE_IN_CARD_AREA_MIN <= area_ratio <= FACE_IN_CARD_AREA_MAX):
        logger.debug(f"[ID DETECTOR] Face area ratio {area_ratio:.2f} outside [0.05, 0.40]. Rejected.")
        return False, 0.0

    return True, area_ratio


def validate_card_candidate(img, cand, text_blocks, face_locations, qr_codes, reader=None):
    """
    Strict multi-stage validation.
    An Identity Card should only be detected if:
      - Rectangular card region exists with valid dimensions (landscape 1.35-1.85 or portrait 0.54-0.74, w>=120, h>=70)
      - OCR finds multiple text fields (len(roi_texts) >= 2)
      - If face(s) exist in image, at least one face must be completely inside the card boundary.
        If a face is present but none are inside the card, we reject the identity card.
      - Never classifies a face alone as a card (card IoU with any face must be low).
      - Card confidence > 0.75
    """
    x, y, w, h = cand["bbox"]
    debug = {"bbox": [x, y, w, h], "signals": [], "reason": "", "detectionType": "Identity Badge Visible"}

    # 1. Size check
    if w < MIN_CARD_WIDTH or h < MIN_CARD_HEIGHT:
        debug["reason"] = f"Card too small ({w}x{h}px, min {MIN_CARD_WIDTH}x{MIN_CARD_HEIGHT}px)"
        return False, 0.0, debug

    # 2. Aspect ratio check
    if not is_valid_aspect_ratio(w, h):
        ratio = round(float(w) / max(1, float(h)), 2)
        debug["reason"] = f"Invalid aspect ratio {ratio}"
        return False, 0.0, debug

    # 3. Eliminate face overlap (prevent face alone classified as card)
    card_box = [x, y, w, h]
    for face in face_locations:
        fx, fy, fw, fh = face.get("x", 0), face.get("y", 0), face.get("width", 0), face.get("height", 0)
        face_box = [fx, fy, fw, fh]
        iou = calculate_iou(card_box, face_box)
        if iou > 0.5:
            debug["reason"] = "Rejected: Face overlaps too much with card region (likely a face alone)"
            return False, 0.0, debug

    img_h, img_w = img.shape[:2]
    crop_x = max(0, x)
    crop_y = max(0, y)
    crop_w = min(img_w - crop_x, w)
    crop_h = min(img_h - crop_y, h)
    roi = img[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]

    # 4. OCR text inside card ROI
    roi_texts = []
    for tb in text_blocks:
        bx, by, bw, bh = tb.get("bbox", [0, 0, 0, 0])
        text_cx = bx + bw / 2
        text_cy = by + bh / 2
        if (crop_x <= text_cx <= crop_x + crop_w) and (crop_y <= text_cy <= crop_y + crop_h):
            roi_texts.append(tb.get("text", ""))

    if not roi_texts and reader and reader is not False and roi.size > 0:
        try:
            roi_results = reader.readtext(roi)
            for pts, text, prob in roi_results:
                if prob > 0.10 and text.strip():
                    roi_texts.append(text.strip())
        except Exception as e:
            logger.debug(f"[ID DETECTOR] ROI crop OCR error: {e}")

    # Require multiple text fields
    if len(roi_texts) < 2:
        debug["reason"] = f"Rejected: Insufficient text fields in card (found {len(roi_texts)}, need >=2)"
        return False, 0.0, debug

    # 5. Face Containment Check (Required Small Photo Inside Card)
    face_inside = False
    for fl in face_locations:
        is_inside, area_ratio = face_is_inside_card(fl, [crop_x, crop_y, crop_w, crop_h])
        if is_inside:
            face_inside = True
            break
    if not face_inside:
        debug["reason"] = "Rejected: No small photo (face) detected inside the card boundary"
        return False, 0.0, debug

    # 6. Signals check
    signals = ["valid_dimensions", "multiple_ocr_texts"]
    if face_inside:
        signals.append("face_inside_card")

    # Final validation check
    final_conf = min(0.98, round(0.70 + (len(signals) * 0.08), 2))
    if final_conf <= CONFIDENCE_THRESHOLD:
        debug["reason"] = f"Confidence {final_conf} <= {CONFIDENCE_THRESHOLD}"
        return False, final_conf, debug

    debug["reason"] = f"Validated card with {', '.join(signals)}"
    debug["ocrTextInCard"] = roi_texts
    debug["faceInsideCard"] = face_inside
    debug["governmentIdDetected"] = True

    return True, final_conf, debug



def detect_and_validate_id_cards(image_path_or_img, text_blocks: list, face_locations: list, qr_codes: list, reader=None) -> list:
    """
    Precision ID Card Detection Pipeline.
    """
    validated_cards = []

    if isinstance(image_path_or_img, str):
        img = cv2.imread(image_path_or_img)
    else:
        img = image_path_or_img
    if img is None:
        return validated_cards

    img_h, img_w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 140)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    raw_candidates = []
    for c in contours:
        bx, by, bw, bh = cv2.boundingRect(c)

        # Minimum size filter (120x70 per spec)
        if bw < MIN_CARD_WIDTH or bh < MIN_CARD_HEIGHT:
            continue

        # Aspect ratio filter
        if not is_valid_aspect_ratio(bw, bh):
            continue

        # Area sanity: card should be 2%–50% of image area
        area_ratio = (bw * bh) / float(img_w * img_h)
        if not (0.02 <= area_ratio <= 0.50):
            continue

        raw_candidates.append({
            "label": "Identity Badge Visible",
            "confidence": 0.75,  # baseline; refined in validate_card_candidate
            "bbox": [bx, by, bw, bh]
        })

    # Confidence filter (>0.75)
    conf_filtered = [c for c in raw_candidates if c["confidence"] >= CONFIDENCE_THRESHOLD]

    # NMS (IoU 0.45) — removes overlapping duplicates
    nms_candidates = apply_nms(conf_filtered)

    # Strict multi-stage validation
    for cand in nms_candidates:
        is_valid, final_conf, debug_info = validate_card_candidate(
            img, cand, text_blocks, face_locations, qr_codes, reader=reader
        )
        if is_valid and final_conf >= CONFIDENCE_THRESHOLD:
            validated_cards.append({
                "label": "Identity Badge Visible",
                "confidence": final_conf,
                "bbox": cand["bbox"],
                "validated": True,
                "reason": debug_info.get("reason", ""),
                "ocrTextInCard": debug_info.get("ocrTextInCard", []),
                "faceInsideCard": debug_info.get("faceInsideCard", False)
            })

    # Return only the single best result (highest confidence)
    validated_cards.sort(key=lambda c: c["confidence"], reverse=True)
    return validated_cards[:1]
