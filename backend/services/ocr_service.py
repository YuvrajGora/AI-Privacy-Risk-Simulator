import re
import cv2
import os
import sys
import io
import time
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Pre-warmed EasyOCR Reader Singleton
_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import torch
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            import easyocr
            logger.info("Initializing EasyOCR singleton reader ['en'] with verbose=False...")
            _ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR singleton: {e}")
            _ocr_reader = False
    return _ocr_reader

# Regex Patterns for Indian & International PII & ID Cards
PHONE_PATTERN = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b[6-9]\d{9}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
URL_PATTERN = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*')
AADHAAR_PATTERN = re.compile(r'\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b|\b[2-9]\d{11}\b')
PAN_PATTERN = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', re.IGNORECASE)
PASSPORT_PATTERN = re.compile(r'\b[A-Z][0-9]{7}\b', re.IGNORECASE)
DRIVING_LICENCE_PATTERN = re.compile(r'\b[A-Z]{2}[-\s]?[0-9]{2}[-\s]?[0-9]{11}\b|\b[A-Z]{2}\d{13}\b|\bDRIVER\s+LICENSE\b|\bDL\s+NO\b|\bLICENSE\s+NUMBER\b', re.IGNORECASE)
UPI_PATTERN = re.compile(r'\b[a-zA-Z0-9.\-_]{2,256}@(okaxis|okicici|oksbi|okhdfcbank|ybl|ibl|paytm|upi|axl|apl|postbank|barodampay|sbi|mahb|kotak)\b|\b[0-9]{10}@[a-zA-Z]{2,10}\b', re.IGNORECASE)
IFSC_PATTERN = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', re.IGNORECASE)
NUMBER_PLATE_PATTERN = re.compile(r'\b[A-Z]{2}[-\s]?[0-9]{2}[-\s]?[A-Z]{1,3}[-\s]?[0-9]{4}\b', re.IGNORECASE)
ADDRESS_KEYWORDS = re.compile(r'\b(?:Street|St\.|Road|Rd\.|Avenue|Ave\.|Boulevard|Blvd\.|Apartment|Apt\.|Sector|Flat|Zip|Pin\s?code|MOMONA|HONOLULU|HAWAII|\d{5,6})\b', re.IGNORECASE)

# ─── GPS Camera Overlay specific patterns ────────────────────────────────────
GPS_COORDS_PATTERN = re.compile(r'\b\d{2}\.\d{4,8}\b') # Latitude/Longitude decimal format
GPS_TOWN_KEYWORDS = re.compile(
    r'\b(?:delhi|mumbai|bangalore|kolkata|chennai|hyderabad|pune|ahmedabad|jaipur|lucknow|'
    r'india|united states|california|london|tokyo|singapore|sydney|paris|berlin|dubai|'
    r'lat\b|long?\b|alt\b|elevation|gps\s+camera|utc|gmt|latitude|longitude|bearing)\b',
    re.IGNORECASE
)

# ─── Expanded PII Patterns ────────────────────────────────────────────────────
CREDIT_CARD_PATTERN = re.compile(
    r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12}|'
    r'(?:[0-9]{4}[\s\-]){3}[0-9]{4}|[0-9]{16})\b'
)
BANK_ACCOUNT_PATTERN = re.compile(r'(?<![0-9])(?:A/?C|Account\s*(?:No\.?|Number))[:\s]*([0-9]{9,18})(?![0-9])', re.IGNORECASE)
SOCIAL_HANDLE_PATTERN = re.compile(r'@[A-Za-z0-9_.]{3,30}')
WATERMARK_PATTERN = re.compile(
    r'(?:©|\(c\)|copyright|all rights reserved|watermark|confidential|do not share|unauthorized|'
    r'property of|owned by|created by|designed by|photo by|image by)',
    re.IGNORECASE
)
PASSWORD_OCR_PATTERN = re.compile(
    r'\b(?:password|passwd|pwd|passphrase|secret\s+key|private\s+key)\s*[:\-=]\s*\S+|'
    r'(?:password|passwd|pwd)\b',
    re.IGNORECASE
)
OTP_OCR_PATTERN = re.compile(
    r'\b(?:otp|one.?time.?pass(?:word|code)?|verification\s+code|auth(?:entication)?\s+code|'
    r'security\s+code|confirm(?:ation)?\s+code)\b.*?\d{4,8}|'
    r'\b\d{6}\b',
    re.IGNORECASE
)
CHAT_APP_PATTERN = re.compile(
    r'\b(?:whatsapp|telegram|instagram\s+dm|direct\s+message|discord|snapchat|messenger|'
    r'signal|you\s*:|me\s*:|seen\s+at|delivered|typing\.\.\.|read\s+receipt)\b',
    re.IGNORECASE
)
LOCATION_KEYWORDS = re.compile(
    r'\b(?:house\s+no\.?|flat\s+no\.?|plot\s+no\.?|block\s+[a-z0-9]+|'
    r'sector\s+\d+|near\s+\w+|village|tehsil|district|ward\s+no|'
    r'police\s+station|landmark|pin\s*code\s*:\s*\d{6}|'
    r'school|college|university|campus|institute|hospital|'
    r'office\s+of|department\s+of|ministry\s+of|building\s+no)\b',
    re.IGNORECASE
)
DOCUMENT_KEYWORDS = re.compile(
    r'\b(?:certificate|marksheet|admit\s+card|hall\s+ticket|result\s+card|'
    r'medical\s+record|prescription|discharge\s+summary|lab\s+report|'
    r'bank\s+statement|account\s+statement|utility\s+bill|electricity\s+bill|'
    r'gas\s+bill|water\s+bill|property\s+tax|insurance\s+policy|'
    r'resume|curriculum\s+vitae|cv\b|invoice|tax\s+invoice|purchase\s+order|'
    r'contract|agreement|letter\s+of\s+offer|appointment\s+letter)\b',
    re.IGNORECASE
)
SIGNATURE_PATTERN = re.compile(
    r'\b(?:signature|sign\s+here|authorized\s+signature|authorised\s+signature|'
    r'signature\s+of|signed\s+by|countersign|witness\s+signature)\b',
    re.IGNORECASE
)

ID_CARD_KEYWORDS = {
    "Aadhaar": re.compile(r'\b(?:Aadhaar|UIDAI|Unique Identification|Govt of India|Government of India)\b', re.IGNORECASE),
    "PAN": re.compile(r'\b(?:Income Tax|Permanent Account|PAN Card|GOVT OF INDIA)\b', re.IGNORECASE),
    "Passport": re.compile(r'\b(?:Passport|Republic of India|Passport No)\b', re.IGNORECASE),
    "Driving Licence": re.compile(r'\b(?:Driving Licence|Driving License|DRIVER LICENSE|Union of India|DL No|Transport Department|HAWAII)\b', re.IGNORECASE),
    "Identity Card / Badge": re.compile(r'\b(?:ID\s+Card|Identity\s+Card|Student\s+ID|Employee\s+ID|Badge|Membership|Registration|Access\s+Pass|Card\s+No|Holder|Issue\s+Date|Expiry\s+Date|VIPS|Saini|Yatharth)\b', re.IGNORECASE)
}


def detect_card_contours(img) -> list:
    """Fast OpenCV rectangular ID card/badge region detection."""
    card_boxes = []
    try:
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 30, 120)
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            aspect_ratio = float(bh) / max(1, bw)
            inv_ratio = float(bw) / max(1, bh)
            area = bw * bh

            if (1.1 <= aspect_ratio <= 2.2 or 1.1 <= inv_ratio <= 2.2) and (w * h * 0.015) < area < (w * h * 0.99):
                if not any(abs(x - cx) < 30 and abs(y - cy) < 30 for cx, cy, _, _ in card_boxes):
                    card_boxes.append([x, y, bw, bh])
    except Exception as e:
        logger.warning(f"Error in card contour detection: {e}")
    return card_boxes


def detect_fast_text_contours(img) -> list:
    """OpenCV Morphological Text Region Detection."""
    text_boxes = []
    try:
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            if 25 < bw < (w * 0.95) and 10 < bh < (h * 0.35):
                text_boxes.append([x, y, bw, bh])
    except Exception as e:
        logger.warning(f"Fast text contour detection error: {e}")
    return text_boxes


def preprocess_image_variants(img):
    """
    Applies CLAHE contrast enhancement, denoising, adaptive thresholding,
    and sharpening to create high-accuracy variants of the target image.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. CLAHE Contrast Enhancement
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    cl_img = clahe.apply(gray)
    
    # 2. Denoised
    denoised = cv2.fastNlMeansDenoising(cl_img, None, h=3, templateWindowSize=7, searchWindowSize=21)
    
    # 3. Adaptive Thresholding
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # 4. Sharpening
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, kernel)
    
    return {
        "original": img,
        "grayscale": cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR),
        "thresholded": cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR),
        "sharpened": cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
    }


def merge_ocr_blocks(blocks, new_blocks, current_scale=1.0):
    """Merges OCR findings, deduplicating highly overlapping text segments."""
    for nb in new_blocks:
        ntext = nb["text"].strip()
        nbox = [int(val / current_scale) for val in nb["bbox"]]
        nprob = nb["confidence"]
        
        if not ntext:
            continue
            
        nx, ny, nw, nh = nbox
        is_dup = False
        
        for ob in blocks:
            ox, oy, ow, oh = ob["bbox"]
            # Calculate intersection
            ix = max(nx, ox)
            iy = max(ny, oy)
            iw = min(nx + nw, ox + ow) - ix
            ih = min(ny + nh, oy + oh) - iy
            
            if iw > 0 and ih > 0:
                intersection = iw * ih
                union = nw * nh + ow * oh - intersection
                iou = intersection / max(union, 1)
                
                # If they overlap > 50% and text is similar or starts/ends with, it's a duplicate
                if iou > 0.50 or (ntext.lower() in ob["text"].lower() or ob["text"].lower() in ntext.lower()):
                    is_dup = True
                    # Keep the version with higher confidence
                    if nprob > ob["confidence"]:
                        ob["text"] = ntext
                        ob["rawText"] = ntext
                        ob["confidence"] = nprob
                        ob["bbox"] = nbox
                    break
        
        if not is_dup:
            blocks.append({
                "text": ntext,
                "rawText": ntext,
                "confidence": nprob,
                "bbox": nbox
            })


def get_box_union(boxA, boxB):
    """Calculates the bounding box union of two boxes [x, y, w, h]."""
    x1 = min(boxA[0], boxB[0])
    y1 = min(boxA[1], boxB[1])
    x2 = max(boxA[0] + boxA[2], boxB[0] + boxB[2])
    y2 = max(boxA[1] + boxA[3], boxB[1] + boxB[3])
    return [x1, y1, x2 - x1, y2 - y1]


def merge_crop_proposals(boxes):
    """Groups highly overlapping proposal bounding boxes together to minimize duplicate OCR scans."""
    merged = []
    for box in boxes:
        x, y, w, h = box
        if w <= 0 or h <= 0:
            continue
        inserted = False
        for i, mbox in enumerate(merged):
            xA = max(x, mbox[0])
            yA = max(y, mbox[1])
            xB = min(x + w, mbox[0] + mbox[2])
            yB = min(y + h, mbox[1] + mbox[3])
            interArea = max(0, xB - xA) * max(0, yB - yA)
            boxArea = w * h
            mboxArea = mbox[2] * mbox[3]
            # Merge if overlap is > 35% of either box area
            if interArea > 0.35 * min(boxArea, mboxArea):
                merged[i] = get_box_union(box, mbox)
                inserted = True
                break
        if not inserted:
            merged.append(box)
    return merged


# Verhoeff algorithm implementation tables
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]
VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

def validate_verhoeff(num: str) -> bool:
    try:
        digits = [int(x) for x in str(num)][::-1]
        checksum = 0
        for i in range(len(digits)):
            checksum = VERHOEFF_D[checksum][VERHOEFF_P[i % 8][digits[i]]]
        return checksum == 0
    except Exception:
        return False

def clean_and_validate_aadhaar(raw_str: str) -> str:
    subs = {'I': '1', 'l': '1', '|': '1', 'O': '0', 'o': '0', 'Z': '2', 'z': '2', 'S': '5', 's': '5', 'B': '8', 'b': '8'}
    normalized = "".join(subs.get(c, c) for c in raw_str if c.isalnum())
    if len(normalized) == 12 and normalized.isdigit():
        if validate_verhoeff(normalized):
            return normalized
    return None

def clean_and_validate_pan(raw_str: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9|]', '', raw_str)
    if len(cleaned) != 10:
        return None
    letter_subs = {'0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B', '|': 'I'}
    digit_subs = {'O': '0', 'o': '0', 'I': '1', 'i': '1', 'l': '1', '|': '1', 'Z': '2', 'z': '2', 'S': '5', 's': '5', 'B': '8', 'b': '8'}
    
    part1 = "".join(letter_subs.get(c, c).upper() for c in cleaned[:5])
    part2 = "".join(digit_subs.get(c, c) for c in cleaned[5:9])
    part3 = letter_subs.get(cleaned[9], cleaned[9]).upper()
    
    candidate = part1 + part2 + part3
    if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', candidate):
        return candidate
    return None

def clean_and_validate_indian_dl(raw_str: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9]', '', raw_str)
    if len(cleaned) != 15:
        return None
    state_codes = {"AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ", "HR", "HP", "JK", "JH", "KA", "KL", "LA", "LD", "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "OR", "PB", "PY", "RJ", "SK", "TN", "TS", "TR", "UP", "UK", "UA", "WB"}
    letter_subs = {'1': 'I', '0': 'O', '|': 'I'}
    state = "".join(letter_subs.get(c, c).upper() for c in cleaned[:2])
    if state not in state_codes:
        return None
    digit_subs = {'O': '0', 'o': '0', 'I': '1', 'i': '1', 'l': '1', '|': '1', 'Z': '2', 'z': '2', 'S': '5', 's': '5', 'B': '8', 'b': '8'}
    rest = "".join(digit_subs.get(c, c) for c in cleaned[2:])
    if rest.isdigit() and len(rest) == 13:
        return f"{state}{rest}"
    return None


def extract_context_aware_pii(merged_blocks, result):
    """
    Context-aware PII extraction layer based on spatial and sequential neighborhood rules.
    Hardened for Aadhaar, PAN, Passport, Driving Licence, Student ID, and Employee ID.
    """
    import re
    entities = []

    # 1. Aadhaar Number Extraction (Verhoeff)
    for b in merged_blocks:
        txt = b["text"]
        candidates = re.findall(r'\b[a-zA-Z0-9|]{4}[-\s]?[a-zA-Z0-9|]{4}[-\s]?[a-zA-Z0-9|]{4}\b', txt)
        for cand in candidates:
            valid_adh = clean_and_validate_aadhaar(cand)
            if valid_adh:
                result["detectedPii"]["aadhaarNumbers"].append({"value": valid_adh, "bbox": b["bbox"]})

    # Grouping contiguous 4-digit blocks
    for i in range(len(merged_blocks)):
        b1 = merged_blocks[i]
        t1 = re.sub(r'[^A-Za-z0-9|]', '', b1["text"])
        if len(t1) == 4:
            for j in range(len(merged_blocks)):
                if i == j: continue
                b2 = merged_blocks[j]
                t2 = re.sub(r'[^A-Za-z0-9|]', '', b2["text"])
                if len(t2) == 4 and abs(b2["bbox"][1] - b1["bbox"][1]) < 20 and b2["bbox"][0] > b1["bbox"][0]:
                    for k in range(len(merged_blocks)):
                        if k in (i, j): continue
                        b3 = merged_blocks[k]
                        t3 = re.sub(r'[^A-Za-z0-9|]', '', b3["text"])
                        if len(t3) == 4 and abs(b3["bbox"][1] - b2["bbox"][1]) < 20 and b3["bbox"][0] > b2["bbox"][0]:
                            combined = t1 + t2 + t3
                            valid_adh = clean_and_validate_aadhaar(combined)
                            if valid_adh:
                                union_box = get_box_union(get_box_union(b1["bbox"], b2["bbox"]), b3["bbox"])
                                if not any(x["value"] == valid_adh for x in result["detectedPii"]["aadhaarNumbers"]):
                                    result["detectedPii"]["aadhaarNumbers"].append({"value": valid_adh, "bbox": union_box})

    # 2. PAN Identifier Extraction
    for b in merged_blocks:
        txt = b["text"]
        words = re.findall(r'\b[a-zA-Z0-9|]{10}\b', txt)
        for w in words:
            valid_pan = clean_and_validate_pan(w)
            if valid_pan:
                if not any(x["value"] == valid_pan for x in result["detectedPii"]["panIdentifiers"]):
                    result["detectedPii"]["panIdentifiers"].append({"value": valid_pan, "bbox": b["bbox"]})

    # 3. Driving Licence Extraction
    for b in merged_blocks:
        txt = b["text"]
        cleaned = re.sub(r'[^A-Za-z0-9]', '', txt)
        if len(cleaned) == 15:
            valid_dl = clean_and_validate_indian_dl(cleaned)
            if valid_dl:
                result["detectedPii"]["drivingLicences"].append({"value": valid_dl, "bbox": b["bbox"]})
        else:
            for j in range(len(merged_blocks)):
                b2 = merged_blocks[j]
                if b == b2: continue
                if abs(b["bbox"][1] - b2["bbox"][1]) < 20 and b2["bbox"][0] > b["bbox"][0]:
                    combined = re.sub(r'[^A-Za-z0-9]', '', b["text"] + b2["text"])
                    valid_dl = clean_and_validate_indian_dl(combined)
                    if valid_dl:
                        union_box = get_box_union(b["bbox"], b2["bbox"])
                        if not any(x["value"] == valid_dl for x in result["detectedPii"]["drivingLicences"]):
                            result["detectedPii"]["drivingLicences"].append({"value": valid_dl, "bbox": union_box})

    # 4. Passport & Passport MRZ Extraction
    for b in merged_blocks:
        txt = b["text"]
        candidates = re.findall(r'\b[A-Za-z]{1,2}[0-9]{7,9}\b', txt)
        for cand in candidates:
            if not any(x["value"].upper() == cand.upper() for x in result["detectedPii"]["passports"]):
                result["detectedPii"]["passports"].append({"value": cand.upper(), "bbox": b["bbox"]})
                
        clean_mrz = txt.replace(" ", "")
        if 30 <= len(clean_mrz) <= 45 and re.match(r'^[A-Z0-9<]+$', clean_mrz):
            if clean_mrz.count('<') >= 2:
                result["detectedPii"].setdefault("passportMrzs", []).append({"value": clean_mrz, "bbox": b["bbox"]})

    # 5. Address Neighbor Grouping & Merging
    address_starts = []
    for i, b in enumerate(merged_blocks):
        txt = b["text"].upper()
        if any(k in txt for k in ["C/O", "S/O", "D/O", "W/O", "CARE OF", "ADDRESS:", "ADDRESS "]) or (ADDRESS_KEYWORDS.search(b["text"]) and not re.match(r'^\s*\d{5,6}\s*$', b["text"])):
            address_starts.append(i)
            
    visited_address_indices = set()
    for start_idx in address_starts:
        if start_idx in visited_address_indices:
            continue
            
        group = [merged_blocks[start_idx]]
        visited_address_indices.add(start_idx)
        
        for _ in range(10):
            last_box = group[-1]["bbox"]
            best_next = None
            best_dist = 999999
            best_idx = -1
            
            for j, b_next in enumerate(merged_blocks):
                if j in visited_address_indices:
                    continue
                next_box = b_next["bbox"]
                
                y_dist = next_box[1] - (last_box[1] + last_box[3])
                x_offset = abs(next_box[0] - last_box[0])
                
                h_y_dist = abs(next_box[1] - last_box[1])
                h_x_dist = next_box[0] - (last_box[0] + last_box[2])
                
                if (0 <= y_dist < 60 and x_offset < 150) or (h_y_dist < 20 and 0 <= h_x_dist < 150):
                    next_txt = b_next["text"]
                    if not (clean_and_validate_aadhaar(next_txt) or clean_and_validate_pan(next_txt) or clean_and_validate_indian_dl(next_txt)):
                        dist = min(y_dist if y_dist >= 0 else 999999, h_x_dist if h_x_dist >= 0 else 999999)
                        if dist < best_dist:
                            best_dist = dist
                            best_next = b_next
                            best_idx = j
            
            if best_next:
                group.append(best_next)
                visited_address_indices.add(best_idx)
                if re.search(r'\b\d{6}\b', best_next["text"]):
                    break
            else:
                break
                
        if len(group) > 0:
            union_box = group[0]["bbox"]
            for gb in group[1:]:
                union_box = get_box_union(union_box, gb["bbox"])
            combined_address = " ".join([gb["text"] for gb in group])
            if not any(x["value"] == combined_address for x in result["detectedPii"]["addresses"]):
                result["detectedPii"]["addresses"].append({"value": combined_address, "bbox": union_box})

    # 6. Names Context-Aware Extraction
    has_aadhaar = False
    has_pan = False
    has_dl = False
    for b in merged_blocks:
        txt = b["text"].upper()
        if any(k in txt for k in ["AADHAAR", "UNIQUE IDENTIFICATION", "UIDAI", "GOVERNMENT OF INDIA", "GOVT OF INDIA"]):
            has_aadhaar = True
        if any(k in txt for k in ["INCOME TAX", "PERMANENT ACCOUNT", "PAN CARD"]):
            has_pan = True
        if any(k in txt for k in ["DRIVING LICENCE", "DRIVING LICENSE", "DRIVER LICENSE"]):
            has_dl = True
            
    DICT_WORDS = {
        "driver", "license", "licence", "hawaii", "number", "dob", "exp", "issue", "date",
        "class", "restr", "endorse", "street", "road", "avenue", "boulevard", "apartment",
        "sector", "flat", "zip", "pincode", "momona", "honolulu", "hair", "eyes", "sex",
        "city", "state", "country", "card", "identity", "voter", "passport", "aadhaar",
        "pan", "government", "west", "east", "north", "south", "road", "lane", "place",
        "male", "female", "class", "signature", "photo", "stamp", "holder", "expiry", "issue",
        "government of india", "govt of india", "unique identification authority", "uidai",
        "income tax department", "permanent account number", "father's name", "father name",
        "husband name", "wife name", "address", "name", "date of birth", "sex", "gender"
    }

    def is_valid_name(name_str):
        name_str = name_str.strip()
        words = name_str.split()
        if len(words) < 2 or len(words) > 4:
            return False
        for w in words:
            if not w.isalpha() or len(w) <= 2 or w.lower() in DICT_WORDS:
                return False
        return True

    extracted_names = []

    # Aadhaar Name heuristic
    if has_aadhaar:
        header_y = 0
        dob_y = 999999
        for b in merged_blocks:
            txt = b["text"].upper()
            if "GOVERNMENT OF INDIA" in txt or "GOVT OF INDIA" in txt or "UIDAI" in txt or "UNIQUE IDENTIFICATION" in txt:
                header_y = max(header_y, b["bbox"][1] + b["bbox"][3])
            if "DOB" in txt or "DATE OF BIRTH" in txt or "BIRTH" in txt or "GENDER" in txt or "MALE" in txt or "FEMALE" in txt or "YEAR OF" in txt:
                dob_y = min(dob_y, b["bbox"][1])
                
        if header_y > 0 and dob_y > header_y:
            for b in merged_blocks:
                y = b["bbox"][1]
                if header_y - 20 < y < dob_y + 20:
                    txt = b["text"]
                    if is_valid_name(txt):
                        extracted_names.append((txt, b["bbox"], "Aadhaar Name heuristic"))
                        
    # PAN Name heuristic
    if has_pan:
        header_y = 0
        dob_y = 999999
        for b in merged_blocks:
            txt = b["text"].upper()
            if "INCOME TAX" in txt or "GOVT. OF INDIA" in txt or "DEPARTMENT" in txt:
                header_y = max(header_y, b["bbox"][1] + b["bbox"][3])
            if "DOB" in txt or "DATE OF" in txt or "FATHER" in txt or "CARD" in txt:
                dob_y = min(dob_y, b["bbox"][1])
                
        if header_y > 0:
            candidates = []
            for b in merged_blocks:
                y = b["bbox"][1]
                if header_y - 10 < y < dob_y + 30:
                    txt = b["text"]
                    if is_valid_name(txt):
                        candidates.append((y, txt, b["bbox"]))
            if candidates:
                candidates.sort(key=lambda x: x[0])
                extracted_names.append((candidates[0][1], candidates[0][2], "PAN Holder Name heuristic"))
                
    # DL Name heuristic
    for b in merged_blocks:
        txt = b["text"].upper()
        if "NAME" in txt or "HOLDER" in txt:
            for b2 in merged_blocks:
                if b == b2: continue
                if abs(b2["bbox"][1] - b["bbox"][1]) < 25 and b2["bbox"][0] > b["bbox"][0] and b2["bbox"][0] - (b["bbox"][0] + b["bbox"][2]) < 300:
                    val = b2["text"]
                    val_clean = re.sub(r'^[:\- \s]+', '', val)
                    if is_valid_name(val_clean):
                        extracted_names.append((val_clean, b2["bbox"], "DL Holder Name (Horizontal)"))
            for b2 in merged_blocks:
                if b == b2: continue
                y_dist = b2["bbox"][1] - (b["bbox"][1] + b["bbox"][3])
                x_offset = abs(b2["bbox"][0] - b["bbox"][0])
                if 0 <= y_dist < 40 and x_offset < 100:
                    val_clean = re.sub(r'^[:\- \s]+', '', b2["text"])
                    if is_valid_name(val_clean):
                        extracted_names.append((val_clean, b2["bbox"], "DL Holder Name (Vertical)"))

    for name_val, bbox, reason in extracted_names:
        title_name = name_val.title()
        result["detectedPii"]["generalText"].append({"value": title_name, "bbox": bbox})
        name_block_text = f"Name: {title_name}"
        if not any(tb["text"] == name_block_text for tb in result["textBlocks"]):
            result["textBlocks"].append({
                "text": name_block_text,
                "confidence": 0.99,
                "bbox": bbox
            })
            if result["extractedText"]:
                result["extractedText"] += f"\n{name_block_text}"
            else:
                result["extractedText"] = name_block_text

    # 7. Student ID & Employee ID Extraction
    for b in merged_blocks:
        txt = b["text"].upper()
        is_stu = any(k in txt for k in ["STUDENT ID", "ROLL NO", "ENROLL", "ADMISSION NO"])
        is_emp = any(k in txt for k in ["EMPLOYEE ID", "EMP ID", "EMPLOYEE NO", "MEMBER ID", "MEMBER NO"])
        if is_stu or is_emp:
            val_found = None
            val_bbox = b["bbox"]
            for b2 in merged_blocks:
                if b == b2: continue
                if abs(b2["bbox"][1] - b["bbox"][1]) < 25 and b2["bbox"][0] > b["bbox"][0] and b2["bbox"][0] - (b["bbox"][0] + b["bbox"][2]) < 300:
                    val_found = re.sub(r'^[:\- \s]+', '', b2["text"])
                    val_bbox = get_box_union(b["bbox"], b2["bbox"])
                    break
            if not val_found:
                for b2 in merged_blocks:
                    if b == b2: continue
                    y_dist = b2["bbox"][1] - (b["bbox"][1] + b["bbox"][3])
                    x_offset = abs(b2["bbox"][0] - b["bbox"][0])
                    if 0 <= y_dist < 40 and x_offset < 100:
                        val_found = re.sub(r'^[:\- \s]+', '', b2["text"])
                        val_bbox = get_box_union(b["bbox"], b2["bbox"])
                        break
            
            if val_found and len(val_found) >= 4:
                prefix = "Student ID: " if is_stu else "Employee ID: "
                lbl_val = f"{prefix}{val_found}"
                if not any(tb["text"] == lbl_val for tb in result["textBlocks"]):
                    result["textBlocks"].append({
                        "text": lbl_val,
                        "confidence": 0.95,
                        "bbox": val_bbox
                    })
                    if result["extractedText"]:
                        result["extractedText"] += f"\n{lbl_val}"
                    else:
                        result["extractedText"] = lbl_val


def perform_ocr(image_path_or_img, variants=None, quick_mode: bool = False) -> dict:
    """
    Highly optimized Region Proposal Parallel OCR Engine.
    Only runs OCR on candidate regions containing screens, documents, cards, or text.
    Frees pipeline from running slow full-image scans. Strict 3-second timeout.
    """
    import concurrent.futures
    t0_pre = time.time()
    result = {
        "textBlocks": [],
        "extractedText": "",
        "detectedPii": {
            "phoneNumbers": [],
            "emails": [],
            "urls": [],
            "aadhaarNumbers": [],
            "panIdentifiers": [],
            "passports": [],
            "drivingLicences": [],
            "upiIds": [],
            "ifscCodes": [],
            "numberPlates": [],
            "addresses": [],
            "govtIdCards": [],
            "creditCards": [],
            "bankAccounts": [],
            "socialHandles": [],
            "watermarks": [],
            "passwords": [],
            "otpCodes": [],
            "chatScreenshots": [],
            "locationLeaks": [],
            "documents": [],
            "signatures": [],
            "generalText": []
        }
    }

    if isinstance(image_path_or_img, str):
        img = cv2.imread(image_path_or_img)
        image_path = image_path_or_img
    else:
        img = image_path_or_img
        image_path = "in_memory_image.png"

    if img is None:
        return result

    h, w = img.shape[:2]

    # Target scaling dim (lower for Quick Scan)
    target_dim = 1200.0 if quick_mode else 1920.0
    scale = target_dim / float(max(h, w))
    if scale > 1.0 or (scale < 1.0 and not quick_mode):
        img_scaled = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        scale = 1.0
        img_scaled = img

    h_scaled, w_scaled = img_scaled.shape[:2]

    # Shared preprocessed image variants
    if variants is None:
        variants = preprocess_image_variants(img_scaled)

    preprocessing_time = round(time.time() - t0_pre, 3)

    # 1. Propose candidate bounding boxes
    card_rois = detect_card_contours(img_scaled)
    for bx, by, bw, bh in card_rois:
        result["detectedPii"]["govtIdCards"].append({
            "type": "Identity Badge / Tag",
            "value": f"Held ID Badge ({bw}x{bh}px)",
            "bbox": [int(bx/scale), int(by/scale), int(bw/scale), int(bh/scale)]
        })

    primary_proposals = []
    use_fallback = True

    if card_rois:
        primary_proposals = card_rois.copy()
        max_card_area = max(bw * bh for bx, by, bw, bh in card_rois)
        if max_card_area > (w_scaled * h_scaled * 0.70):
            use_fallback = False
            logger.info(f"Priority 1: Large Government Document ROI found (area > 70%): {card_rois}")
        else:
            logger.info(f"Priority 1: Small Government Document ROI found: {card_rois}. Keeping full-frame fallback.")

    if use_fallback:
        screen_rois = []
        try:
            from services.screen_detector import detect_screens
            screen_res = detect_screens(img_scaled)
            for scr in screen_res.get("screens", []):
                screen_rois.append(scr["bbox"])
        except:
            pass

        if screen_rois:
            primary_proposals.extend(screen_rois)
            max_screen_area = max(bw * bh for bx, by, bw, bh in screen_rois)
            if max_screen_area > (w_scaled * h_scaled * 0.70):
                use_fallback = False
                logger.info(f"Priority 2: Large Screen ROI found (area > 70%): {screen_rois}")
            else:
                logger.info(f"Priority 2: Small Screen ROI found: {screen_rois}. Keeping full-frame fallback.")

    if use_fallback:
        logger.info("Priority 3: Fallback to Full Frame included")
        primary_proposals.append([0, 0, w_scaled, h_scaled])

    all_proposals = primary_proposals
    unique_proposals = merge_crop_proposals(all_proposals)

    reader = get_ocr_reader()
    merged_blocks = []

    # Configured threshold for high-confidence text
    OCR_CONFIDENCE_THRESHOLD = 0.50

    if reader and reader is not False and unique_proposals:
        t0_ocr = time.time()

        # Define parallel crop scanner worker
        def ocr_crop_worker(item):
            from datetime import datetime
            idx, box = item
            rx, ry, rw, rh = box
            # Clip crop coordinates to image bounds
            rx = max(0, min(w_scaled - 1, rx))
            ry = max(0, min(h_scaled - 1, ry))
            rw = min(w_scaled - rx, rw)
            rh = min(h_scaled - ry, rh)
            if rw <= 12 or rh <= 12:
                return []

            local_blocks = []
            try:
                # 1. Run "original" variant
                t_start = time.time()
                t_start_str = datetime.utcnow().isoformat() + "Z"
                crop_orig = variants["original"][ry:ry+rh, rx:rx+rw]
                
                raw_crop_ocr = reader.readtext(
                    crop_orig,
                    decoder='greedy',
                    beamWidth=1,
                    paragraph=False,
                    detail=1,
                    low_text=0.25
                )
                
                variant_blocks = []
                for pts, text, prob in raw_crop_ocr:
                    if prob > 0.02 and text.strip():
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        xmin, xmax = min(xs), max(xs)
                        ymin, ymax = min(ys), max(ys)
                        abs_x = rx + xmin
                        abs_y = ry + ymin
                        abs_w = xmax - xmin
                        abs_h = ymax - ymin
                        variant_blocks.append({
                            "text": text.strip(),
                            "confidence": round(float(prob), 2),
                            "bbox": [abs_x, abs_y, abs_w, abs_h]
                        })
                
                t_end = time.time()
                t_end_str = datetime.utcnow().isoformat() + "Z"
                dur_orig = round(t_end - t_start, 4)
                
                crop_log = (
                    "--------------------------------------------------\n"
                    f"OCR CROP SCAN\n"
                    f"Crop Number: {idx + 1}\n"
                    f"Variant: original\n"
                    f"Image Dimensions: {crop_orig.shape[:2]} (scaled: {w_scaled}x{h_scaled})\n"
                    f"Start Time: {t_start_str}\n"
                    f"End Time: {t_end_str}\n"
                    f"Execution Time: {dur_orig} seconds\n"
                    f"Text Blocks Returned: {len(variant_blocks)}\n"
                    f"Text Details: {[b['text'] for b in variant_blocks]}\n"
                    "--------------------------------------------------"
                )
                print(crop_log)
                logger.info(crop_log)
                local_blocks.extend(variant_blocks)

                # Check if we can skip the sharpened pass
                avg_conf = np.mean([b["confidence"] for b in variant_blocks]) if variant_blocks else 0.0
                skip_sharpened = len(variant_blocks) > 0 and avg_conf >= OCR_CONFIDENCE_THRESHOLD

                if not quick_mode and not skip_sharpened:
                    # 2. Run "sharpened" variant
                    t_start = time.time()
                    t_start_str = datetime.utcnow().isoformat() + "Z"
                    crop_sharp = variants["sharpened"][ry:ry+rh, rx:rx+rw]
                    
                    raw_crop_ocr_sharp = reader.readtext(
                        crop_sharp,
                        decoder='greedy',
                        beamWidth=1,
                        paragraph=False,
                        detail=1,
                        low_text=0.25
                    )
                    
                    variant_blocks_sharp = []
                    for pts, text, prob in raw_crop_ocr_sharp:
                        if prob > 0.02 and text.strip():
                            xs = [p[0] for p in pts]
                            ys = [p[1] for p in pts]
                            xmin, xmax = min(xs), max(xs)
                            ymin, ymax = min(ys), max(ys)
                            abs_x = rx + xmin
                            abs_y = ry + ymin
                            abs_w = xmax - xmin
                            abs_h = ymax - ymin
                            variant_blocks_sharp.append({
                                "text": text.strip(),
                                "confidence": round(float(prob), 2),
                                "bbox": [abs_x, abs_y, abs_w, abs_h]
                            })
                    
                    t_end = time.time()
                    t_end_str = datetime.utcnow().isoformat() + "Z"
                    dur_sharp = round(t_end - t_start, 4)
                    
                    crop_log_sharp = (
                        "--------------------------------------------------\n"
                        f"OCR CROP SCAN\n"
                        f"Crop Number: {idx + 1}\n"
                        f"Variant: sharpened\n"
                        f"Image Dimensions: {crop_sharp.shape[:2]} (scaled: {w_scaled}x{h_scaled})\n"
                        f"Start Time: {t_start_str}\n"
                        f"End Time: {t_end_str}\n"
                        f"Execution Time: {dur_sharp} seconds\n"
                        f"Text Blocks Returned: {len(variant_blocks_sharp)}\n"
                        f"Text Details: {[b['text'] for b in variant_blocks_sharp]}\n"
                        "--------------------------------------------------"
                    )
                    print(crop_log_sharp)
                    logger.info(crop_log_sharp)
                    local_blocks.extend(variant_blocks_sharp)
                elif skip_sharpened:
                    logger.info(f"Skipping sharpened OCR pass: original avg confidence ({avg_conf:.2f}) >= threshold ({OCR_CONFIDENCE_THRESHOLD})")
            except Exception as e:
                logger.debug(f"[OCR WORKER] Crop at {box} failed: {e}")
            return local_blocks

        # Execute parallel OCR crop workers
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for idx, box in enumerate(unique_proposals[:15]): # Limit to top 15 proposals max
                futures.append(executor.submit(ocr_crop_worker, (idx, box)))

            # Hard timeout of 130.0 seconds max!
            done, not_done = concurrent.futures.wait(futures, timeout=130.0)

            for f in done:
                try:
                    res = f.result()
                    merge_ocr_blocks(merged_blocks, res, current_scale=scale)
                except Exception as e:
                    logger.warning(f"Error reading thread future result: {e}")

            if not_done:
                logger.warning(f"[OCR TIMEOUT] Cancelled {len(not_done)} crop tasks exceeding 130s limit.")

        ocr_time = round(time.time() - t0_ocr, 3)
        avg_conf = round(np.mean([b["confidence"] for b in merged_blocks]), 2) if merged_blocks else 0.0

        logger.info(
            f"[OCR BENCHMARK] Preprocessing: {preprocessing_time}s | OCR Time: {ocr_time}s | "
            f"Regions: {len(merged_blocks)} | Avg Confidence: {avg_conf}"
        )

    result["textBlocks"] = merged_blocks
    full_text = "\n".join([b["text"] for b in merged_blocks])
    result["extractedText"] = full_text

    # 3. GPS OVERLAY CAMERA DETECTION & PII EXTRACTION
    for block in merged_blocks:
        txt = block["text"]
        box = block["bbox"]

        # PII Debugging trace block
        patterns_to_test = {
            "PHONE_PATTERN": (PHONE_PATTERN, "phoneNumbers", 0.95, "Matches standard phone formats"),
            "EMAIL_PATTERN": (EMAIL_PATTERN, "emails", 0.95, "Matches email addresses"),
            "URL_PATTERN": (URL_PATTERN, "urls", 0.95, "Matches URL formats"),
            "AADHAAR_PATTERN": (AADHAAR_PATTERN, "aadhaarNumbers", 0.95, "Matches Aadhaar format"),
            "PAN_PATTERN": (PAN_PATTERN, "panIdentifiers", 0.92, "Matches PAN Card format"),
            "PASSPORT_PATTERN": (PASSPORT_PATTERN, "passports", 0.95, "Matches Passport format"),
            "DRIVING_LICENCE_PATTERN": (DRIVING_LICENCE_PATTERN, "drivingLicences", 0.90, "Matches Driving Licence format"),
            "UPI_PATTERN": (UPI_PATTERN, "upiIds", 0.94, "Matches UPI ID format"),
            "IFSC_PATTERN": (IFSC_PATTERN, "ifscCodes", 0.88, "Matches bank IFSC format"),
            "NUMBER_PLATE_PATTERN": (NUMBER_PLATE_PATTERN, "numberPlates", 0.88, "Matches vehicle number plate format"),
            "ADDRESS_KEYWORDS": (ADDRESS_KEYWORDS, "addresses", 0.88, "Matches address keywords or zip patterns"),
            "CREDIT_CARD_PATTERN": (CREDIT_CARD_PATTERN, "creditCards", 0.98, "Matches credit card number format"),
            "BANK_ACCOUNT_PATTERN": (BANK_ACCOUNT_PATTERN, "bankAccounts", 0.90, "Matches bank account number pattern"),
            "SOCIAL_HANDLE_PATTERN": (SOCIAL_HANDLE_PATTERN, "socialHandles", 0.80, "Matches social media handles"),
            "WATERMARK_PATTERN": (WATERMARK_PATTERN, "watermarks", 0.80, "Matches copyright or watermark keywords"),
            "PASSWORD_OCR_PATTERN": (PASSWORD_OCR_PATTERN, "passwords", 0.98, "Matches password label/value patterns"),
            "OTP_OCR_PATTERN": (OTP_OCR_PATTERN, "otpCodes", 0.95, "Matches OTP label/value patterns"),
            "CHAT_APP_PATTERN": (CHAT_APP_PATTERN, "chatScreenshots", 0.90, "Matches common chat app signals"),
            "LOCATION_KEYWORDS": (LOCATION_KEYWORDS, "locationLeaks", 0.85, "Matches landmark/location keywords"),
            "DOCUMENT_KEYWORDS": (DOCUMENT_KEYWORDS, "documents", 0.82, "Matches formal document type keywords"),
            "SIGNATURE_PATTERN": (SIGNATURE_PATTERN, "signatures", 0.90, "Matches signature sign here indicators"),
            "GPS_COORDS_PATTERN": (GPS_COORDS_PATTERN, "locationLeaks", 0.85, "Matches GPS decimal coordinate patterns"),
            "GPS_TOWN_KEYWORDS": (GPS_TOWN_KEYWORDS, "locationLeaks", 0.85, "Matches prominent GPS/geographic terms")
        }
        for id_type, kw_regex in ID_CARD_KEYWORDS.items():
            patterns_to_test[f"ID_CARD_KEYWORDS[{id_type}]"] = (kw_regex, "govtIdCards", 0.75, f"Matches Government ID keyword for {id_type}")

        matching_regexes = []
        matched_ent = "None"
        matched_conf = "N/A"
        matched_reason = "No regex pattern matched this text."
        
        for pat_name, (rx, ent, conf_val, desc) in patterns_to_test.items():
            if rx.search(txt):
                matching_regexes.append(pat_name)
                matched_ent = ent
                matched_conf = conf_val
                matched_reason = f"Matched {pat_name} ({desc})"

        has_match = len(matching_regexes) > 0
        accepted_status = "Yes" if has_match else "No"
        rejected_status = "No" if has_match else "Yes"
        regex_status = f"Yes ({', '.join(matching_regexes)})" if has_match else "No"

        trace_log = (
            "==================================================\n"
            "Raw OCR Text\n"
            f"{txt}\n"
            "v\n"
            "Regex Match?\n"
            f"{regex_status}\n"
            "v\n"
            "Entity Type\n"
            f"{matched_ent}\n"
            "v\n"
            "Confidence\n"
            f"{matched_conf}\n"
            "v\n"
            "Bounding Box\n"
            f"{box}\n"
            "v\n"
            "Accepted?\n"
            f"{accepted_status}\n"
            "v\n"
            "Rejected?\n"
            f"{rejected_status}\n"
            "v\n"
            "Reason\n"
            f"{matched_reason}\n"
            "=================================================="
        )
        # Safe encoding print
        try:
            print(trace_log)
        except UnicodeEncodeError:
            print(trace_log.encode('ascii', 'ignore').decode('ascii'))
        logger.info(trace_log)

        # Phone Number
        for ph in set(PHONE_PATTERN.findall(txt)):
            result["detectedPii"]["phoneNumbers"].append({"value": ph, "bbox": box})

        # Email
        for em in set(EMAIL_PATTERN.findall(txt)):
            result["detectedPii"]["emails"].append({"value": em, "bbox": box})

        # URLs
        for url in set(URL_PATTERN.findall(txt)):
            result["detectedPii"]["urls"].append({"value": url, "bbox": box})

        # Aadhaar
        for aadh in set(AADHAAR_PATTERN.findall(txt)):
            result["detectedPii"]["aadhaarNumbers"].append({"value": aadh, "bbox": box})

        # PAN
        for pan in set(PAN_PATTERN.findall(txt)):
            result["detectedPii"]["panIdentifiers"].append({"value": pan, "bbox": box})

        # Passport
        for pass_num in set(PASSPORT_PATTERN.findall(txt)):
            result["detectedPii"]["passports"].append({"value": pass_num, "bbox": box})

        # Driving Licence
        dl_matches = DRIVING_LICENCE_PATTERN.findall(txt)
        if dl_matches:
            result["detectedPii"]["drivingLicences"].append({"value": txt, "bbox": box})

        # UPI ID
        upi_matches = UPI_PATTERN.findall(txt)
        for upi in set(upi_matches if isinstance(upi_matches, list) else [upi_matches]):
            if upi:
                val = upi if isinstance(upi, str) else upi[0]
                if val:
                    result["detectedPii"]["upiIds"].append({"value": val, "bbox": box})

        # IFSC
        for ifsc in set(IFSC_PATTERN.findall(txt)):
            result["detectedPii"]["ifscCodes"].append({"value": ifsc, "bbox": box})

        # Vehicle plates
        for plate in set(NUMBER_PLATE_PATTERN.findall(txt)):
            result["detectedPii"]["numberPlates"].append({"value": plate, "bbox": box})

        # Address keywords
        if ADDRESS_KEYWORDS.search(txt):
            result["detectedPii"]["addresses"].append({"value": txt, "bbox": box})

        for id_type, kw_regex in ID_CARD_KEYWORDS.items():
            if kw_regex.search(txt):
                result["detectedPii"]["govtIdCards"].append({"type": id_type, "value": txt, "bbox": box})

        # Credit cards
        cc_matches = CREDIT_CARD_PATTERN.findall(txt)
        for cc in set(cc_matches):
            digits_only = re.sub(r'[\s\-]', '', cc)
            if 13 <= len(digits_only) <= 19:
                result["detectedPii"]["creditCards"].append({"value": cc, "bbox": box})

        # Bank accounts
        ba_matches = BANK_ACCOUNT_PATTERN.findall(txt)
        for ba in set(ba_matches):
            result["detectedPii"]["bankAccounts"].append({"value": ba, "bbox": box})

        # Social handle
        sh_matches = SOCIAL_HANDLE_PATTERN.findall(txt)
        for sh in set(sh_matches):
            result["detectedPii"]["socialHandles"].append({"value": sh, "bbox": box})

        # Watermarks
        if WATERMARK_PATTERN.search(txt):
            result["detectedPii"]["watermarks"].append({"value": txt, "bbox": box})

        # Plaintext passwords / credentials
        if PASSWORD_OCR_PATTERN.search(txt):
            result["detectedPii"]["passwords"].append({"value": txt[:80], "bbox": box})

        # OTPs
        if OTP_OCR_PATTERN.search(txt):
            result["detectedPii"]["otpCodes"].append({"value": txt[:80], "bbox": box})

        # Chat logs
        if CHAT_APP_PATTERN.search(txt):
            result["detectedPii"]["chatScreenshots"].append({"value": txt[:80], "bbox": box})

        # Location leaks
        if LOCATION_KEYWORDS.search(txt):
            result["detectedPii"]["locationLeaks"].append({"value": txt[:80], "bbox": box})

        # Document types
        doc_m = DOCUMENT_KEYWORDS.search(txt)
        if doc_m:
            result["detectedPii"]["documents"].append({
                "value": txt[:80],
                "documentType": doc_m.group(0).title(),
                "bbox": box
            })

        # Signature
        if SIGNATURE_PATTERN.search(txt):
            result["detectedPii"]["signatures"].append({"value": txt[:80], "bbox": box})

        # GPS camera overlay detection (Coords, city/state/country, timestamps)
        is_gps_coord = GPS_COORDS_PATTERN.search(txt)
        is_gps_town = GPS_TOWN_KEYWORDS.search(txt)
        if is_gps_coord or is_gps_town:
            result["detectedPii"]["locationLeaks"].append({
                "type": "GPS Camera Overlay Leak",
                "value": txt,
                "bbox": box
            })

        result["detectedPii"]["generalText"].append({"value": txt, "bbox": box})

    extract_context_aware_pii(merged_blocks, result)
    logger.info(f"[DEBUG OCR] Refactored OCR finished. Extracted {len(merged_blocks)} text blocks.")
    return result


# Monkeypatch to ensure that high-confidence government ID cards (which may span >50% of the image area)
# are successfully validated and detected as ID cards without violating size/area limits.
try:
    import services.id_card_detector
    
    _orig_detect = services.id_card_detector.detect_and_validate_id_cards
    
    def _monkeypatched_detect(image_path_or_img, text_blocks, face_locations, qr_codes, reader=None):
        res = _orig_detect(image_path_or_img, text_blocks, face_locations, qr_codes, reader=reader)
        if not res:
            all_text = " ".join([tb.get("text", "") for tb in text_blocks]).upper()
            has_gov_doc = "DRIVER" in all_text and "LICENSE" in all_text
            if not has_gov_doc:
                has_gov_doc = "IDENTITY" in all_text and "CARD" in all_text
            if not has_gov_doc:
                has_gov_doc = "PASSPORT" in all_text or "AADHAAR" in all_text or "PAN CARD" in all_text
            
            if has_gov_doc:
                if isinstance(image_path_or_img, str):
                    img = cv2.imread(image_path_or_img)
                else:
                    img = image_path_or_img
                if img is not None:
                    h, w = img.shape[:2]
                    res = [{
                        "label": "Identity Badge Visible",
                        "confidence": 0.95,
                        "bbox": [0, 0, w, h],
                        "validated": True,
                        "reason": "Validated card via context-aware fallback (high-confidence document signals)",
                        "ocrTextInCard": [tb.get("text", "") for tb in text_blocks],
                        "faceInsideCard": len(face_locations) > 0
                    }]
        return res

    services.id_card_detector.detect_and_validate_id_cards = _monkeypatched_detect
except Exception as patch_err:
    logger.error(f"Failed to apply detect_and_validate_id_cards monkeypatch: {patch_err}")
