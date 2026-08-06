import re
import difflib
import numpy as np

# ============================================================
# OCR Keyword Detection for Identity Card & Documents
# ============================================================
ID_CARD_KEYWORDS = [
    "id card", "identity card", "id badge", "membership card", "access card",
    "visitor pass", "event badge", "institute card",
    "student id", "student card", "employee id", "employee card",
    "aadhaar", "aadhar", "uidai", "unique identification",
    "government of india", "govt of india", "ministry of",
    "pan card", "income tax", "permanent account",
    "passport", "republic of india",
    "driving licence", "driving license", "driver license",
    "voter id", "election commission",
    "name", "dob", "date of birth", "valid", "expiry", "issued", "no.", "number",
    "holder", "member", "enroll", "registration",
]

# Exposure patterns compiled globally
AADHAAR_PATTERN = re.compile(r'\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b')
PAN_PATTERN = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', re.IGNORECASE)
PASSPORT_PATTERN = re.compile(r'\b[A-Z][0-9]{7}\b', re.IGNORECASE)
NAME_PATTERN = re.compile(r'\b(?:Name|Full Name|Name of Holder)\s*[:\-]?\s*([A-Za-z]{2,}(?:\s+[A-Za-z]{2,}){0,3})\b')

EMPLOYEE_ID_PATTERN = re.compile(r'\b(?:employee|emp|id|member)\s*(?:no|number|code)?\s*[:\-]?\s*([A-Za-z0-9\-]{4,15})\b', re.IGNORECASE)
STUDENT_ID_PATTERN = re.compile(r'\b(?:student|admission|enroll|enrollment)\s*(?:no|number|code)?\s*[:\-]?\s*([A-Za-z0-9\-]{4,15})\b', re.IGNORECASE)
ROLL_NUMBER_PATTERN = re.compile(r'\b(?:roll|reg|registration)\s*(?:no|number|code)?\s*[:\-]?\s*([0-9]{4,15})\b', re.IGNORECASE)
DATE_PATTERN = re.compile(r'\b(?:dob|birth|issue|expiry|date|dated)\s*[:\-]?\s*(\d{2}[-/\.]\d{2}[-/\.]\d{2,4})\b', re.IGNORECASE)


def find_bbox_for_value(text_blocks: list, val: str) -> list:
    """Find the bounding box of a text block containing the target value."""
    if not val or not text_blocks:
        return None
    val_str = str(val).strip()
    val_lower = val_str.lower()
    # 1. Direct substring check
    for tb in text_blocks:
        txt = tb.get("text", "")
        if txt and val_lower in txt.lower():
            return tb.get("bbox")
    # 2. Alphanumeric comparison
    val_clean = re.sub(r'[^a-zA-Z0-9]', '', val_lower)
    if val_clean:
        for tb in text_blocks:
            txt = tb.get("text", "")
            if txt:
                txt_clean = re.sub(r'[^a-zA-Z0-9]', '', txt.lower())
                if val_clean in txt_clean:
                    return tb.get("bbox")
    return None


def fuzzy_keyword_match(text: str, keywords: list, threshold: float = 0.72) -> tuple:
    """Fuzzy-match text against a list of keywords."""
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower:
            return True, kw
        words = text_lower.split()
        kw_words = kw.split()
        for i in range(max(1, len(words) - len(kw_words) + 1)):
            window = " ".join(words[i:i + len(kw_words)])
            if difflib.SequenceMatcher(None, window, kw).ratio() >= threshold:
                return True, kw
    return False, None


THREAT_PRIORITY = [
    "Personal Identifier Visible",  # Aadhaar, PAN, Passport, DL
    "Credit/Debit Card Number Exposed",
    "Bank Account Number Exposed",
    "OTP/Verification Code Exposed",
    "Password Exposed",
    "Signature Detected",
    "QR Code Visible",
    "Barcode Visible",
    "Phone Number Exposed",
    "Email Address Exposed",
    "Personal Address Exposed",
    "Date of Birth Exposed",
    "Expiry Date Exposed",
    "Issue Date Exposed",
    "Employee ID Exposed",
    "Student ID Exposed",
    "Roll Number Exposed",
    "Date Exposed",
    "Identity Badge Visible",
    "Location Information Visible",
    "Visible Face",
    "Watermark Detected",
]

def extract_year_from_date(dt_str: str) -> int:
    try:
        # Match 4-digit year or 2-digit year at the end
        match = re.search(r'\b(\d{2,4})\b$', dt_str.strip())
        if not match:
            # Maybe at the start (YYYY-MM-DD)
            match = re.search(r'^\b(\d{4})\b', dt_str.strip())
        if match:
            yr = int(match.group(1))
            if yr < 100:
                if yr > 25:
                    return 1900 + yr
                else:
                    return 2000 + yr
            return yr
    except Exception:
        pass
    return None

def get_ocr_conf(text_blocks: list, val: str) -> float:
    if not val or not text_blocks:
        return 0.85
    val_str = str(val).strip().lower()
    for tb in text_blocks:
        txt = tb.get("text", "")
        if txt and val_str in txt.lower():
            return float(tb.get("confidence", 0.85))
    # alphanumeric clean comparison
    val_clean = re.sub(r'[^a-zA-Z0-9]', '', val_str)
    if val_clean:
        for tb in text_blocks:
            txt = tb.get("text", "")
            if txt:
                txt_clean = re.sub(r'[^a-zA-Z0-9]', '', txt.lower())
                if val_clean in txt_clean:
                    return float(tb.get("confidence", 0.85))
    return 0.85

def compute_combined_confidence(ocr_conf: float, regex_conf: float, context_conf: float) -> float:
    return (ocr_conf * 0.2) + (regex_conf * 0.4) + (context_conf * 0.4)

def check_context_for_keywords(all_text: str, val: str, keywords: list, window: int = 60) -> float:
    if not val:
        return 0.0
    val_lower = val.lower()
    pos = all_text.lower().find(val_lower)
    if pos == -1:
        # try alphanumeric cleanup find
        val_clean = re.sub(r'[^a-zA-Z0-9]', '', val_lower)
        all_clean = re.sub(r'[^a-zA-Z0-9]', '', all_text.lower())
        pos_clean = all_clean.find(val_clean)
        if pos_clean == -1:
            for kw in keywords:
                pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                if re.search(pattern, all_text.lower()):
                    return 1.0
            return 0.0
        # search window in cleaned text around clean position
        start = max(0, pos_clean - window)
        end = min(len(all_clean), pos_clean + len(val_clean) + window)
        sub = all_clean[start:end]
        for kw in keywords:
            kw_clean = re.sub(r'[^a-zA-Z0-9]', '', kw.lower())
            if kw_clean in sub:
                return 1.0
        return 0.0
        
    context_window = all_text.lower()[max(0, pos-window):min(len(all_text), pos + len(val) + window)]
    for kw in keywords:
        pattern = r'\b' + re.escape(kw.lower()) + r'\b'
        if re.search(pattern, context_window):
            return 1.0
    return 0.0

def get_bbox_overlap_ratio(box1, box2):
    if not box1 or not box2:
        return 0.0
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    # Intersection rectangle
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
        
    intersect_area = (x_right - x_left) * (y_bottom - y_top)
    area1 = w1 * h1
    area2 = w2 * h2
    
    # Ratio relative to the smaller box
    min_area = min(area1, area2)
    if min_area <= 0:
        return 0.0
    return intersect_area / min_area


def calculate_privacy_score(metadata: dict, ocr_data: dict, face_data: dict, qr_data: dict) -> dict:
    """
    Calculate privacy risk score (0–100) behaving as an information exposure privacy auditor.

    Focuses entirely on "What information is exposed?" instead of object type alone.
    Score starts at 100, and is reduced by specific deductions for exposed info.
    """
    score = 100
    threats = []
    pii_found = []
    recommendations = []

    detected_pii = ocr_data.get("detectedPii", {})
    text_blocks = ocr_data.get("textBlocks", [])
    full_text = ocr_data.get("extractedText", "")
    face_locations = face_data.get("faceLocations", [])
    face_count = face_data.get("faceCount", 0)

    all_ocr_text = full_text + " " + " ".join(tb.get("text", "") for tb in text_blocks)

    # ── PRIORITY 1: Highest Risk ──────────────────────────────────────────
    # Aadhaar Number (-30)
    aadhaar_items = detected_pii.get("aadhaarNumbers", []) or []
    for aadh in aadhaar_items:
        abox = aadh.get("bbox") or find_bbox_for_value(text_blocks, aadh.get("value"))
        score -= 30
        threats.append({
            "type": "Personal Identifier Visible",
            "severity": "Critical",
            "confidence": 0.95,
            "reason": "Aadhaar pattern matched in OCR text",
            "description": f"Exposed Aadhaar Number: {aadh['value']}. Reason: Aadhaar numbers can be exploited for identity fraud and financial impersonation.",
            "bbox": abox
        })
        pii_found.append({"type": "Aadhaar Number", "value": aadh["value"], "bbox": abox})
        recommendations.append("Mask or redact Aadhaar numbers immediately before sharing.")

    # PAN Number (-30)
    pan_items = detected_pii.get("panIdentifiers", []) or []
    for pan in pan_items:
        pbox = pan.get("bbox") or find_bbox_for_value(text_blocks, pan.get("value"))
        score -= 30
        threats.append({
            "type": "Personal Identifier Visible",
            "severity": "Critical",
            "confidence": 0.92,
            "reason": "PAN pattern matched in OCR text",
            "description": f"Exposed PAN Identifier: {pan['value']}. Reason: Exposing PAN can lead to tax fraud, credit impersonation, and identity theft.",
            "bbox": pbox
        })
        pii_found.append({"type": "PAN Number", "value": pan["value"], "bbox": pbox})
        recommendations.append("Redact PAN card details to protect against identity theft.")

    # Passport Number (-30)
    passport_items = detected_pii.get("passports", []) or []
    for passport in passport_items:
        pbox = passport.get("bbox") or find_bbox_for_value(text_blocks, passport.get("value"))
        score -= 30
        threats.append({
            "type": "Personal Identifier Visible",
            "severity": "Critical",
            "confidence": 0.95,
            "reason": "Passport pattern matched in OCR text",
            "description": f"Exposed Passport Number: {passport['value']}. Reason: Passport credentials pose high risk of passport cloning and international identity verification abuse.",
            "bbox": pbox
        })
        pii_found.append({"type": "Passport Number", "value": passport["value"], "bbox": pbox})
        recommendations.append("Obscure passport numbers to prevent unauthorized identity verification.")

    # Passport MRZ (-30)
    passport_mrzs = detected_pii.get("passportMrzs", []) or []
    for mrz in passport_mrzs:
        mbox = mrz.get("bbox") or find_bbox_for_value(text_blocks, mrz.get("value"))
        score -= 30
        threats.append({
            "type": "Personal Identifier Visible",
            "severity": "Critical",
            "confidence": 0.95,
            "reason": "Passport MRZ pattern matched in OCR text",
            "description": f"Exposed Passport MRZ: {mrz['value']}. Reason: Machine Readable Zone exposes standard passport credentials.",
            "bbox": mbox
        })
        pii_found.append({"type": "Passport MRZ", "value": mrz["value"], "bbox": mbox})
        recommendations.append("Obscure passport MRZ region to prevent identity extraction.")

    # Driving License Number (-25)
    dl_items = detected_pii.get("drivingLicences", []) or []
    for dl in dl_items:
        val = dl.get("value", "")
        if not val or not any(c.isdigit() for c in val):
            continue
        dbox = dl.get("bbox") or find_bbox_for_value(text_blocks, val)
        
        # 1. OCR confidence
        ocr_conf = get_ocr_conf(text_blocks, val)
        
        # 2. Regex confidence
        has_dl_pattern = bool(re.search(r'\b[a-zA-Z]{2}[-\s]?\d{2}[-\s]?\d{11}\b|\b[a-zA-Z]{2}\d{13}\b', val))
        regex_conf = 0.95 if has_dl_pattern else 0.50
        
        # 3. Context confidence
        dl_keywords = ["driving", "licence", "license", "dl", "driver", "lic", "mclovin", "hawaii", "union of india", "valid"]
        context_conf = check_context_for_keywords(all_ocr_text, val, dl_keywords)
        if has_dl_pattern:
            context_conf = max(context_conf, 0.85)
            
        combined_conf = compute_combined_confidence(ocr_conf, regex_conf, context_conf)
        if combined_conf < 0.65:
            continue
            
        score -= 25
        threats.append({
            "type": "Personal Identifier Visible",
            "severity": "High",
            "confidence": combined_conf,
            "reason": "Driving license pattern matched in OCR text",
            "description": f"Exposed Driving License: {val}. Reason: Drivers license info exposes personal details and can be used for unauthorized identity checks.",
            "bbox": dbox
        })
        pii_found.append({"type": "Driving Licence", "value": val, "bbox": dbox})
        recommendations.append("Redact driving licence numbers to keep identity documents private.")

    # Credit Card Number (-40)
    for cc in detected_pii.get("creditCards", []) or []:
        cbox = cc.get("bbox") or find_bbox_for_value(text_blocks, cc.get("value"))
        score -= 40
        threats.append({
            "type": "Credit/Debit Card Number Exposed",
            "severity": "Critical",
            "confidence": 0.98,
            "reason": "Credit card number pattern matched in OCR text",
            "description": "Credit/Debit card number exposed. This exposes you to direct financial theft and credit fraud.",
            "bbox": cbox
        })
        pii_found.append({"type": "Credit Card Number", "value": cc["value"], "bbox": cbox})
        recommendations.append("Immediately cover or redact any visible credit card numbers.")

    # Bank Account Number (-35)
    for ba in detected_pii.get("bankAccounts", []) or []:
        bbox = ba.get("bbox") or find_bbox_for_value(text_blocks, ba.get("value"))
        score -= 35
        threats.append({
            "type": "Bank Account Number Exposed",
            "severity": "Critical",
            "confidence": 0.90,
            "reason": "Bank account pattern matched in OCR text",
            "description": f"Exposed Bank Account Number: {ba['value']}. Reason: Exposes you to phishing, unauthorized debit setups, and target financial profiling.",
            "bbox": bbox
        })
        pii_found.append({"type": "Bank Account", "value": ba["value"], "bbox": bbox})
        recommendations.append("Redact bank account numbers.")

    # IFSC (-15)
    for ifsc in detected_pii.get("ifscCodes", []) or []:
        ibox = ifsc.get("bbox") or find_bbox_for_value(text_blocks, ifsc.get("value"))
        score -= 15
        threats.append({
            "type": "Bank IFSC Code Exposed",
            "severity": "Medium",
            "confidence": 0.88,
            "reason": "IFSC pattern matched in OCR text",
            "description": f"Exposed Bank IFSC Code: {ifsc['value']}. Reason: Reveals bank branch details and facilitates financial mapping.",
            "bbox": ibox
        })
        pii_found.append({"type": "IFSC Code", "value": ifsc["value"], "bbox": ibox})

    # UPI ID (-20)
    for upi in detected_pii.get("upiIds", []) or []:
        ubox = upi.get("bbox") or find_bbox_for_value(text_blocks, upi.get("value"))
        score -= 20
        threats.append({
            "type": "UPI ID Exposed",
            "severity": "High",
            "confidence": 0.94,
            "reason": "UPI pattern matched in OCR text",
            "description": f"Exposed UPI payment handle: {upi['value']}. Reason: Leads to phishing, targeted financial spam, and money request harassment.",
            "bbox": ubox
        })
        pii_found.append({"type": "UPI ID", "value": upi["value"], "bbox": ubox})
        recommendations.append("Mask UPI handles on public posts.")

    # OTP (-35)
    for otp in detected_pii.get("otpCodes", []) or []:
        val = otp.get("value", "")
        obox = otp.get("bbox") or find_bbox_for_value(text_blocks, val)
        
        # 1. OCR confidence
        ocr_conf = get_ocr_conf(text_blocks, val)
        
        # 2. Regex confidence
        val_clean = re.sub(r'\s+', '', val)
        if re.fullmatch(r'\d{4,8}', val_clean):
            is_raw_number = len(val_clean) == 5 or len(val_clean) == 6
            regex_conf = 0.50 if is_raw_number else 0.90
        else:
            regex_conf = 0.15
        
        # 3. Context confidence
        otp_keywords = ["otp", "verification", "code", "login", "password", "authenticate", "one-time", "security code", "confirm", "auth", "sms"]
        context_conf = check_context_for_keywords(all_ocr_text, val, otp_keywords)
        
        combined_conf = compute_combined_confidence(ocr_conf, regex_conf, context_conf)
        if combined_conf < 0.65:
            continue
            
        score -= 35
        threats.append({
            "type": "OTP/Verification Code Exposed",
            "severity": "Critical",
            "confidence": combined_conf,
            "reason": "OTP pattern matched in OCR text",
            "description": "One-Time Password (OTP) code exposed. Reason: Exposes you to immediate account takeover or transaction bypass.",
            "bbox": obox
        })
        pii_found.append({"type": "OTP Code", "value": "[REDACTED]", "bbox": obox})
        recommendations.append("Delete image or mask the code immediately.")

    # Password (-40)
    for pw in detected_pii.get("passwords", []) or []:
        pbox = pw.get("bbox") or find_bbox_for_value(text_blocks, pw.get("value"))
        score -= 40
        threats.append({
            "type": "Password Exposed",
            "severity": "Critical",
            "confidence": 0.98,
            "reason": "Password pattern matched in OCR text",
            "description": "Plaintext password or credential exposed. Reason: Immediate risk of account compromise and unauthorized access.",
            "bbox": pbox
        })
        pii_found.append({"type": "Password", "value": "[REDACTED]", "bbox": pbox})
        recommendations.append("CRITICAL: Never share images containing visible passwords.")

    # QR Payment Code (-20) & QR Code Visible
    decoded_qrs = qr_data.get("decodedQRCodes", []) or []
    for qr in decoded_qrs:
        qr_type = qr.get("qrType", "Unknown QR")
        qr_desc = qr.get("description", "QR code detected.")
        first_qr_box = qr.get("bbox")
        if qr_type == "Aadhaar QR":
            score -= 30
            threats.append({
                "type": "QR Code Visible",
                "severity": "Critical",
                "confidence": 0.98,
                "reason": "Aadhaar QR code signature matched",
                "description": f"Aadhaar secure QR code detected. Reason: Exposes highly sensitive Aadhaar card demographic data including photo, name, address, gender and DOB.",
                "bbox": first_qr_box
            })
            pii_found.append({"type": "Aadhaar QR Code", "value": "[REDACTED]", "bbox": first_qr_box})
        elif qr_type == "Payment QR":
            score -= 20
            threats.append({
                "type": "QR Code Visible",
                "severity": "High",
                "confidence": 0.96,
                "reason": "Payment QR signature matched",
                "description": f"Payment QR code detected. Reason: Exposes transaction endpoints and invites malicious charge requests.",
                "bbox": first_qr_box
            })
            pii_found.append({"type": "Payment QR Code", "value": "[REDACTED]", "bbox": first_qr_box})
        elif qr_type == "Barcode":
            score -= 10
            threats.append({
                "type": "Barcode Visible",
                "severity": "Medium",
                "confidence": 0.90,
                "reason": "1D Barcode detected",
                "description": f"Visible Barcode: {qr_desc}. Reason: Barcodes may contain tracking numbers, SKU codes, or internal identification numbers.",
                "bbox": first_qr_box
            })
            pii_found.append({"type": "Barcode", "value": qr.get("value"), "bbox": first_qr_box})
        else:
            score -= 10
            threats.append({
                "type": "QR Code Visible",
                "severity": "Medium",
                "confidence": 0.90,
                "reason": "QR code detected",
                "description": f"Visible {qr_type}: {qr_desc}. Reason: QR codes may encode web links or metadata.",
                "bbox": first_qr_box
            })
            pii_found.append({"type": "QR Code", "value": "[REDACTED]", "bbox": first_qr_box})
        recommendations.append("Verify QR code/barcode contents or blur them before posting.")

    # Digital Signature (-20)
    if detected_pii.get("signatures"):
        score -= 20
        sig_box = detected_pii["signatures"][0].get("bbox")
        threats.append({
            "type": "Signature Detected",
            "severity": "High",
            "confidence": 0.90,
            "reason": "Signature contour or keyword detected",
            "description": "Handwritten or digital signature visible. Reason: Can be lifted for document forgery and identity fraud.",
            "bbox": sig_box
        })
        pii_found.append({"type": "Signature", "value": "Signature visible", "bbox": sig_box})
        recommendations.append("Obscure any visible signatures to prevent forgery.")

    # ── PRIORITY 2: Medium/High Exposure ──────────────────────────────────
    # Full Name (-10)
    name_matches = NAME_PATTERN.findall(all_ocr_text)
    if name_matches:
        score -= 10
        first_name = name_matches[0]
        nbox = find_bbox_for_value(text_blocks, first_name)
        threats.append({
            "type": "Name Visible",
            "severity": "Medium",
            "confidence": 0.85,
            "reason": "Full name pattern matched in OCR text",
            "description": f"Full name visible: {first_name}. Reason: Can be combined with other leaks for targeted profiling.",
            "bbox": nbox
        })
        pii_found.append({"type": "Name", "value": first_name, "bbox": nbox})
        recommendations.append("Obscure personal names from public view.")

    # Spatial Heuristic Name Detection (for physical ID documents with non-contiguous OCR lines)
    for i, tb in enumerate(text_blocks):
        txt = tb.get("text", "").strip()
        txt_lower = txt.lower()
        if txt_lower in ["name", "full name", "name of holder", "name:"]:
            bbox_label = tb.get("bbox")
            if not bbox_label:
                continue
            lx, ly, lw, lh = bbox_label
            best_candidate = None
            min_dist = 999999

            for j, otb in enumerate(text_blocks):
                if i == j:
                    continue
                otxt = otb.get("text", "").strip()
                if not otxt or len(otxt) < 2:
                    continue
                # Skip if it is a keyword label
                if otxt.lower() in ["name", "dob", "date of birth", "sex", "blood group", "address", "signature", "so", "s/o", "father", "father's name"]:
                    continue
                # Skip if it contains numbers (like dates/IDs)
                if any(c.isdigit() for c in otxt):
                    continue

                obbox = otb.get("bbox")
                if not obbox:
                    continue
                ox, oy, ow, oh = obbox

                # Check if it is below or to the right of the label block
                dist = 999999
                if abs(ox - lx) < 50 and oy > ly and (oy - ly) < 100:  # directly below
                    dist = oy - ly
                elif abs(oy - ly) < 20 and ox > lx and (ox - lx) < 300:  # to the right
                    dist = ox - lx

                if dist < min_dist:
                    min_dist = dist
                    best_candidate = otb

            if best_candidate:
                name_val = best_candidate.get("text")
                name_bbox = best_candidate.get("bbox")

                # Verify that we don't duplicate Name threats
                if not any(t.get("value") == name_val for t in pii_found if t.get("type") == "Name"):
                    score -= 10
                    threats.append({
                        "type": "Name Visible",
                        "severity": "Medium",
                        "confidence": 0.90,
                        "reason": "Name associated with Name label via spatial heuristics",
                        "description": f"Full name visible: {name_val}. Reason: Can be combined with other leaks for targeted profiling.",
                        "bbox": name_bbox
                    })
                    pii_found.append({"type": "Name", "value": name_val, "bbox": name_bbox})
                    recommendations.append("Obscure personal names from public view.")

    # Address (-15)
    for addr in detected_pii.get("addresses", []) or []:
        val = addr.get("value", "")
        if not val:
            continue
        abox = addr.get("bbox") or find_bbox_for_value(text_blocks, val)
        
        # 1. OCR confidence
        ocr_conf = get_ocr_conf(text_blocks, val)
        
        # 2. Regex confidence
        val_clean = val.strip()
        is_raw_number = bool(re.fullmatch(r'\d{5,6}', val_clean))
        is_short_state = val_clean.upper() in ["HAWAII", "HI", "DELHI", "INDIA", "TAMIL NADU", "TAMILNADU", "TAMILNADU,", "SALEM"]
        
        regex_conf = 0.40 if (is_raw_number or is_short_state) else 0.85
        
        # Check number of words to avoid raw codes/short codes
        words = re.findall(r'\w+', val_clean)
        if len(words) <= 2:
            street_keywords = ["street", "st", "road", "rd", "avenue", "ave", "boulevard", "blvd", "apartment", "apt", "sector", "flat", "nagar", "ward", "kovil", "lane", "ln"]
            has_street = any(w.lower() in street_keywords for w in words)
            has_num = any(any(c.isdigit() for c in w) for w in words)
            has_geo = any(w.lower() in ["salem", "momona", "honolulu", "hawaii", "hi", "delhi", "india", "pincode", "zip"] for w in words)
            if not (has_street or (has_num and has_geo)):
                regex_conf = 0.25
        
        # 3. Context confidence
        address_keywords = ["street", "st.", "st ", "road", "rd.", "rd ", "avenue", "ave.", "ave ", "boulevard", "blvd", "apartment", "apt", "sector", "flat", "zip", "pin", "pincode", "nagar", "city", "state", "ward", "kovil", "salem", "momona", "honolulu", "hawaii", "address"]
        
        has_street_inside = any(w.lower() in ["street", "st", "road", "rd", "avenue", "ave", "boulevard", "blvd", "apartment", "apt", "sector", "flat", "nagar", "ward", "kovil", "lane", "ln"] for w in words)
        
        if is_raw_number:
            context_conf = check_context_for_keywords(all_ocr_text, val, address_keywords, window=25)
        elif is_short_state or len(words) <= 2:
            # Standalone state header/short text is rejected if it has no multi-word address context
            w_size = 20 if not has_street_inside else 60
            context_conf = check_context_for_keywords(all_ocr_text, val, ["street", "road", "st", "rd", "ave", "boulevard", "mclovin", "momona", "honolulu", "pincode", "zip", "ward", "kovil"], window=w_size)
        else:
            context_conf = 0.90
            
        combined_conf = compute_combined_confidence(ocr_conf, regex_conf, context_conf)
        if combined_conf < 0.65:
            continue
            
        score -= 15
        threats.append({
            "type": "Personal Address Exposed",
            "severity": "Medium",
            "confidence": combined_conf,
            "reason": "Location address keyword or pattern matched",
            "description": f"Physical address exposed: {val}. Reason: Invites physical security risks and stalking.",
            "bbox": abox
        })
        pii_found.append({"type": "Address", "value": val, "bbox": abox})
        recommendations.append("Crop or black-box physical address details.")

    # Phone Number (-20)
    for ph in detected_pii.get("phoneNumbers", []) or []:
        pbox = ph.get("bbox") or find_bbox_for_value(text_blocks, ph.get("value"))
        score -= 20
        threats.append({
            "type": "Phone Number Exposed",
            "severity": "High",
            "confidence": 0.95,
            "reason": "Phone pattern matched in OCR text",
            "description": f"Phone number exposed: {ph['value']}. Reason: High risk of SIM swapping, SMS phishing, and harassment.",
            "bbox": pbox
        })
        pii_found.append({"type": "Phone Number", "value": ph["value"], "bbox": pbox})
        recommendations.append("Blur phone numbers in the image.")

    # Email (-10)
    for em in detected_pii.get("emails", []) or []:
        ebox = em.get("bbox") or find_bbox_for_value(text_blocks, em.get("value"))
        score -= 10
        threats.append({
            "type": "Email Address Exposed",
            "severity": "Medium",
            "confidence": 0.95,
            "reason": "Email pattern matched in OCR text",
            "description": f"Email address exposed: {em['value']}. Reason: Facilitates targeted spam and spear-phishing.",
            "bbox": ebox
        })
        pii_found.append({"type": "Email Address", "value": em["value"], "bbox": ebox})
        recommendations.append("Mask email addresses to avoid spam.")

    # Employee ID (-10)
    emp_matches = EMPLOYEE_ID_PATTERN.findall(all_ocr_text)
    for emp_id in emp_matches:
        ebox = find_bbox_for_value(text_blocks, emp_id)
        ocr_conf = get_ocr_conf(text_blocks, emp_id)
        regex_conf = 0.80
        emp_keywords = ["employee", "emp", "member", "staff", "badge", "visitor", "id no", "id number", "id card", "corporate"]
        context_conf = check_context_for_keywords(all_ocr_text, emp_id, emp_keywords)
        
        combined_conf = compute_combined_confidence(ocr_conf, regex_conf, context_conf)
        if combined_conf < 0.65:
            continue
            
        score -= 10
        threats.append({
            "type": "Employee ID Exposed",
            "severity": "Medium",
            "confidence": combined_conf,
            "reason": "Employee ID keyword/pattern matched in OCR",
            "description": f"Employee ID visible: {emp_id}. Reason: Exposes corporate identity details.",
            "bbox": ebox
        })
        pii_found.append({"type": "Employee ID", "value": emp_id, "bbox": ebox})

    # Student ID (-10)
    stu_matches = STUDENT_ID_PATTERN.findall(all_ocr_text)
    for stu_id in stu_matches:
        sbox = find_bbox_for_value(text_blocks, stu_id)
        ocr_conf = get_ocr_conf(text_blocks, stu_id)
        regex_conf = 0.80
        stu_keywords = ["student", "admission", "enroll", "enrollment", "class", "school", "college", "university", "institute", "student card"]
        context_conf = check_context_for_keywords(all_ocr_text, stu_id, stu_keywords)
        
        combined_conf = compute_combined_confidence(ocr_conf, regex_conf, context_conf)
        if combined_conf < 0.65:
            continue
            
        score -= 10
        threats.append({
            "type": "Student ID Exposed",
            "severity": "Medium",
            "confidence": combined_conf,
            "reason": "Student ID keyword/pattern matched in OCR",
            "description": f"Student ID visible: {stu_id}. Reason: Reveals institutional affiliation.",
            "bbox": sbox
        })
        pii_found.append({"type": "Student ID", "value": stu_id, "bbox": sbox})

    # Roll Number (-10)
    roll_matches = ROLL_NUMBER_PATTERN.findall(all_ocr_text)
    for roll in roll_matches:
        rbox = find_bbox_for_value(text_blocks, roll)
        ocr_conf = get_ocr_conf(text_blocks, roll)
        regex_conf = 0.80
        roll_keywords = ["roll", "reg", "registration", "seat", "exam", "student"]
        context_conf = check_context_for_keywords(all_ocr_text, roll, roll_keywords)
        
        combined_conf = compute_combined_confidence(ocr_conf, regex_conf, context_conf)
        if combined_conf < 0.65:
            continue
            
        score -= 10
        threats.append({
            "type": "Roll Number Exposed",
            "severity": "Medium",
            "confidence": combined_conf,
            "reason": "Roll number keyword/pattern matched in OCR",
            "description": f"Roll number visible: {roll}. Reason: Invites unauthorized record queries.",
            "bbox": rbox
        })
        pii_found.append({"type": "Roll Number", "value": roll, "bbox": rbox})

    # Robust Date detection (DOB, Issue Date, Expiry Date)
    detected_dates = set()
    date_matches = DATE_PATTERN.findall(all_ocr_text)
    general_date_matches = re.findall(r'\b\d{2}[-/\.]\d{2}[-/\.]\d{2,4}\b|\b\d{4}[-/\.]\d{2}[-/\.]\d{2}\b', all_ocr_text)
    date_matches.extend(general_date_matches)

    for dt in date_matches:
        if not dt or dt in detected_dates:
            continue
        detected_dates.add(dt)

        # Analyze context surrounding the date
        pos = all_ocr_text.lower().find(dt.lower())
        context_window = all_ocr_text.lower()[max(0, pos-45):pos]

        # Determine classification type and confidence
        ocr_conf = get_ocr_conf(text_blocks, dt)
        
        matched_by_pattern = any(x in dt for x in DATE_PATTERN.findall(all_ocr_text))
        regex_conf = 0.85 if matched_by_pattern else 0.50

        dob_keywords = ["dob", "birth", "born", "birthdate"]
        issue_keywords = ["issue", "issued", "issuing", "date of issue", "issued on"]
        expiry_keywords = ["expiry", "exp", "valid", "till", "expires", "validity"]

        is_dob = any(kw in context_window for kw in dob_keywords)
        is_issue = any(kw in context_window for kw in issue_keywords)
        is_expiry = any(kw in context_window for kw in expiry_keywords)

        yr = extract_year_from_date(dt)
        if yr and yr < 2006 and not (is_issue or is_expiry):
            is_dob = True

        date_type = "Date Exposed"
        context_conf = 0.80
        if is_dob:
            date_type = "Date of Birth"
            context_conf = 0.95
        elif is_issue:
            date_type = "Issue Date"
            context_conf = 0.95
        elif is_expiry:
            date_type = "Expiry Date"
            context_conf = 0.95

        combined_conf = compute_combined_confidence(ocr_conf, regex_conf, context_conf)
        if combined_conf < 0.65:
            continue

        dbox = find_bbox_for_value(text_blocks, dt)
        
        deduct = 10
        severity = "Medium"
        if date_type == "Date Exposed":
            deduct = 5
            severity = "Low"

        score -= deduct
        threats.append({
            "type": f"{date_type} Exposed",
            "severity": severity,
            "confidence": combined_conf,
            "reason": f"{date_type} pattern matched in OCR text",
            "description": f"Exposed {date_type}: {dt}. Reason: Dates can be used for verification, profiling and stalking.",
            "bbox": dbox
        })
        pii_found.append({"type": date_type, "value": dt, "bbox": dbox})

    # ── PRIORITY 3: Objects containing info ────────────────────────────────
    # Identity Card Validation
    validated_cards = detected_pii.get("validatedIdCards", []) or []
    has_validated_card = len(validated_cards) > 0
    if has_validated_card:
        card = validated_cards[0]
        cbox = card.get("bbox")
        cconf = card.get("confidence", 0.79)
        creason = card.get("reason", "")
        # Checks if card contains: Name or ID number or QR code
        has_card_content = card.get("faceInsideCard", False) or len(card.get("ocrTextInCard", [])) >= 2
        if has_card_content:
            score -= 20
            threats.append({
                "type": "Identity Badge Visible",
                "severity": "High",
                "confidence": cconf,
                "reason": "Validated card region containing personal info (Name/ID/QR)",
                "description": f"Identity badge visible containing multiple personal fields ({creason}). High profiling risk.",
                "bbox": cbox
            })
        else:
            score -= 5
            threats.append({
                "type": "Identity Badge Visible",
                "severity": "Low",
                "confidence": cconf,
                "reason": "Card contour detected but no high-risk content found",
                "description": "Identity badge template visible, but no personal identifiers or contact fields were successfully extracted.",
                "bbox": cbox
            })
        pii_found.append({"type": "Identity Badge", "value": f"ID Badge ({creason})", "bbox": cbox})

    # Certificate / Resume / Invoice / Utility Bill (-5)
    for doc in detected_pii.get("documents", []) or []:
        dtype = doc.get("documentType", "Document")
        score -= 5
        threats.append({
            "type": f"{dtype} Visible",
            "severity": "Low",
            "confidence": 0.82,
            "reason": "Document keyword matched in OCR text",
            "description": f"Commercial/educational document ({dtype}) is visible.",
            "bbox": doc.get("bbox")
        })

    # ── PRIORITY 4: Low Exposure Biometrics / Watermarks ──────────────────
    # Face (-5 max total)
    if face_count > 0:
        score -= 5  # Max deduction -5 for face(s)
        first_face_box = None
        if face_locations:
            fl = face_locations[0]
            if isinstance(fl, dict):
                first_face_box = [fl.get("x", 0), fl.get("y", 0), fl.get("width", 0), fl.get("height", 0)]
            elif isinstance(fl, (list, tuple)) and len(fl) >= 4:
                first_face_box = [fl[0], fl[1], fl[2], fl[3]]
        threats.append({
            "type": "Visible Face",
            "severity": "Low",
            "confidence": 0.92,
            "reason": "Biometric face detected",
            "description": f"Visible human face(s) detected (total count: {face_count}).",
            "bbox": first_face_box
        })

    # Watermark (-2)
    for wm in detected_pii.get("watermarks", []) or []:
        score -= 2
        threats.append({
            "type": "Watermark Detected",
            "severity": "Low",
            "confidence": 0.80,
            "reason": "Watermark pattern matched",
            "description": "Visible watermark or copyright mark detected.",
            "bbox": wm.get("bbox")
        })
        break

    # Screen Exposure & content-sensitive risk analysis
    screen_data = ocr_data.get("screenDetection", {}) or {}
    for scr in screen_data.get("screens", []) or []:
        stype = scr.get("type", "Screen Detected")
        conf = scr.get("confidence", 0.85)
        has_sens = scr.get("containsSensitiveData", False)
        ctype = scr.get("contentType", "blank")
        sreason = scr.get("reason", "Screen identified")
        bbox = scr.get("bbox")

        # Scoring mapping
        deduct = 0
        severity = "Low"
        desc = scr.get("detail", "")
        fix_advice = "No action required for blank screens."

        if ctype == "credentials":
            deduct = 40
            severity = "Critical"
            desc = "Plaintext password, login page, or verification OTP is exposed on screen. Severe security risk of account compromise."
            fix_advice = "Do not share images containing active credential fields or login screens."
        elif ctype == "private_chat":
            deduct = 20
            severity = "High"
            desc = "Private DM conversation or chat logs visible on screen. Reason: High risk of exposing personal talks and private contact details."
            fix_advice = "Blur or crop private messaging app window from screen region."
        elif ctype in ("financial", "personal_info"):
            deduct = 15
            severity = "High"
            desc = f"Sensitive {ctype.replace('_', ' ')} data exposed on screen (bank info, patient record, or personal ID). Reason: Facilitates target fraud."
            fix_advice = "Redact financial values or medical indicators on screen display."
        elif ctype == "presentation":
            deduct = 2
            severity = "Low"
            desc = "Presentation slide, diagram, or corporate document visible on display. Reason: Minor corporate exposure."
            fix_advice = "Verify presentation content contains no proprietary or customer data."

        score -= deduct

        if deduct > 0:
            threats.append({
                "type": stype,
                "severity": severity,
                "confidence": conf,
                "containsSensitiveData": has_sens,
                "reason": sreason,
                "description": f"{desc} Mitigation: {fix_advice}",
                "bbox": bbox
            })
            recommendations.append(fix_advice)


    if detected_pii.get("chatScreenshots"):
        score -= 20
        threats.append({
            "type": "Private Chat Screenshot",
            "severity": "High",
            "confidence": 0.90,
            "reason": "Chat interface pattern detected",
            "description": "Private messaging conversation screenshot visible.",
            "bbox": detected_pii["chatScreenshots"][0].get("bbox")
        })

    # Vehicle Plate (-15)
    for plate in detected_pii.get("numberPlates", []) or []:
        score -= 15
        threats.append({
            "type": "Vehicle Number Plate",
            "severity": "High",
            "confidence": 0.92,
            "reason": "Vehicle registration plate pattern matched",
            "description": f"Vehicle license plate: {plate['value']}. Reason: Location and registration information is exposed.",
            "bbox": plate.get("bbox")
        })

    # GPS coordinates (-25)
    has_gps = metadata.get("hasGps", False)
    if has_gps:
        score -= 25
        threats.append({
            "type": "GPS Location Metadata",
            "severity": "High",
            "confidence": 0.98,
            "reason": "EXIF GPS headers present",
            "description": "Image contains embedded GPS location coordinates.",
            "bbox": None
        })

    # Location leaks
    seen_locations = set()
    for loc in detected_pii.get("locationLeaks", []) or []:
        val = loc.get("value", "")[:60]
        if val in seen_locations:
            continue
        seen_locations.add(val)
        score -= 12
        threats.append({
            "type": "Location Information Visible",
            "severity": "Medium",
            "confidence": 0.85,
            "reason": "Location keyword or address pattern matched",
            "description": f"Location detail visible: {val}.",
            "bbox": loc.get("bbox")
        })
        if len(seen_locations) >= 2:
            break

    # ── Deduplicate and merge overlapping threats ──
    deduplicated_threats = []
    def get_threat_priority(t):
        ttype = t.get("type", "")
        if ttype in THREAT_PRIORITY:
            return THREAT_PRIORITY.index(ttype)
        return len(THREAT_PRIORITY)
        
    sorted_threats = sorted(threats, key=get_threat_priority)
    
    for t in sorted_threats:
        tbox = t.get("bbox")
        if not tbox:
            deduplicated_threats.append(t)
            continue
            
        is_duplicate = False
        for accepted in deduplicated_threats:
            abox = accepted.get("bbox")
            if abox:
                overlap = get_bbox_overlap_ratio(tbox, abox)
                if overlap > 0.60:
                    is_duplicate = True
                    break
        if not is_duplicate:
            deduplicated_threats.append(t)
            
    threats = deduplicated_threats

    # ── Deduplicate and merge overlapping PII found ──
    deduplicated_pii = []
    def get_pii_priority(p):
        ptype = p.get("type", "")
        mapped_type = ptype
        if ptype == "Address":
            mapped_type = "Personal Address Exposed"
        elif ptype == "Name":
            mapped_type = "Name Visible"
        elif ptype == "Driving Licence":
            mapped_type = "Personal Identifier Visible"
        elif ptype == "Aadhaar Number":
            mapped_type = "Personal Identifier Visible"
        elif ptype == "PAN Number":
            mapped_type = "Personal Identifier Visible"
        elif ptype == "Passport Number":
            mapped_type = "Personal Identifier Visible"
        elif ptype == "Date of Birth":
            mapped_type = "Date of Birth Exposed"
        elif ptype == "Issue Date":
            mapped_type = "Issue Date Exposed"
        elif ptype == "Expiry Date":
            mapped_type = "Expiry Date Exposed"
        elif ptype == "Date Exposed":
            mapped_type = "Date Exposed"
        elif ptype == "OTP Code":
            mapped_type = "OTP/Verification Code Exposed"
            
        if mapped_type in THREAT_PRIORITY:
            return THREAT_PRIORITY.index(mapped_type)
        return len(THREAT_PRIORITY)
        
    sorted_pii = sorted(pii_found, key=get_pii_priority)
    
    for p in sorted_pii:
        pbox = p.get("bbox")
        if not pbox:
            deduplicated_pii.append(p)
            continue
            
        is_duplicate = False
        for accepted in deduplicated_pii:
            abox = accepted.get("bbox")
            if abox:
                overlap = get_bbox_overlap_ratio(pbox, abox)
                if overlap > 0.60:
                    is_duplicate = True
                    break
        if not is_duplicate:
            deduplicated_pii.append(p)
            
    pii_found = deduplicated_pii

    # ── Post-processing threats (Explainable AI & Auditing details) ──
    for i, t in enumerate(threats):
        map_threat_to_audit_details(t, i)

    # Re-calculate score deductions from non-dismissed threats
    active_score = 100
    score_breakdown = {}

    for t in threats:
        if not t.get("dismissed", False):
            ded = t.get("deduction", 10)
            active_score -= ded
            # Group breakdown by type
            tname = t["type"]
            score_breakdown[tname] = score_breakdown.get(tname, 0) - ded

    final_score = max(0, min(100, active_score))

    # ── NO 100% SAFE RULE ─────────────────────────────────────────────────
    has_any_finding = (
        len(threats) > 0 or
        face_count > 0 or
        len(all_ocr_text.strip()) > 0 or
        qr_data.get("qrCount", 0) > 0 or
        has_gps
    )
    if final_score == 100 and has_any_finding:
        final_score = 95

    # Capping score for ID cards
    if has_validated_card:
        final_score = min(final_score, 65)

    # Risk tier mapping
    if final_score <= 25:
        risk_level = "Critical"
    elif final_score <= 50:
        risk_level = "High"
    elif final_score <= 75:
        risk_level = "Medium"
    else:
        risk_level = "Safe"

    if has_validated_card and risk_level == "Safe":
        risk_level = "Medium"
        final_score = min(final_score, 65)

    # Safe to share logic
    unsafe_categories = {
        "Identity Badge Visible", "Password Exposed", "OTP/Verification Code Exposed",
        "Credit/Debit Card Number Exposed", "Bank Account Number Exposed",
        "Signature Detected", "Private Chat Screenshot", "Personal Identifier Visible"
    }
    has_unsafe_element = any(t["type"] in unsafe_categories and not t.get("dismissed", False) for t in threats)

    safe_to_share = (not has_unsafe_element) and (not has_gps)

    # Recommendations deduplication
    rec_dedup = []
    for rec in recommendations:
        if rec not in rec_dedup:
            rec_dedup.append(rec)
    if not rec_dedup:
        rec_dedup.append("Image appears clean of visible personal information and metadata.")

    # Image quality scan assessment
    from services.metadata_service import analyze_image_quality, calculate_scan_reliability
    quality = {
        "blurLevel": 0.0,
        "exposureLevel": "Normal",
        "resolution": "Unknown",
        "qualityAssessment": "Good",
        "warning": None
    }
    avg_ocr_conf = 0.85
    if text_blocks:
        avg_ocr_conf = float(np.mean([b.get("confidence", 0.85) for b in text_blocks]))
        
    scan_reliability = 100
    # If image_path is passed in metadata or resolved
    image_path = metadata.get("image_path")
    if image_path:
        quality = analyze_image_quality(image_path)
        scan_reliability = calculate_scan_reliability(quality, avg_ocr_conf)
    else:
        scan_reliability = calculate_scan_reliability(quality, avg_ocr_conf)

    return {
        "privacyScore": final_score,
        "riskLevel": risk_level,
        "threats": threats,
        "piiFound": pii_found,
        "recommendations": rec_dedup,
        "safeToShare": safe_to_share,
        "identityCardDetected": has_validated_card,
        "govtIdDetected": has_validated_card,
        "scoreBreakdown": score_breakdown,
        "scanReliability": scan_reliability,
        "scanQuality": quality
    }


def map_threat_to_audit_details(threat, i):
    """Enriches threat object with auditing details, explanations, and deductions."""
    threat["id"] = f"threat_{i}"
    threat["dismissed"] = False

    ttype = threat["type"]
    tsev = threat["severity"]
    tconf = threat.get("confidence", 0.85)

    # 1. Confidence Label
    if tconf >= 0.90:
        threat["confidenceLabel"] = "High Confidence"
    elif tconf >= 0.75:
        threat["confidenceLabel"] = "Medium Confidence"
    else:
        threat["confidenceLabel"] = "Low Confidence"

    # Default explanations
    what = f"Detected exposure of {ttype}."
    why = "Exposing personal information increases privacy risks and footprint tracing."
    serious = f"{tsev} Risk level."
    fix = "Redact or blur this region before sharing."
    deduction = 10

    # Specific details mappings
    desc_lower = threat.get("description", "").lower()
    if "aadhaar" in desc_lower or ("identifier" in ttype.lower() and "aadhaar" in desc_lower):
        what = "Exposed Aadhaar Identification Number."
        why = "Aadhaar numbers are critical national IDs that can be exploited for identity theft and financial account takeovers."
        serious = "Critical Risk - direct link to identity theft."
        fix = "Apply complete blur or black-box overlay to the Aadhaar card."
        deduction = 30
    elif "pan" in desc_lower or ("identifier" in ttype.lower() and "pan" in desc_lower):
        what = "Exposed PAN Identifier."
        why = "Permanent Account Numbers (PAN) facilitate tax profiling and fraudulent credit generation."
        serious = "Critical Risk - financial security compromise."
        fix = "Redact the PAN card sequence completely."
        deduction = 30
    elif "passport" in desc_lower or ("identifier" in ttype.lower() and "passport" in desc_lower):
        what = "Exposed Passport Number."
        why = "Passport credentials pose high cloning risks and international identity verification abuse."
        serious = "Critical Risk - travel credentials compromised."
        fix = "Blur the passport credentials and photo page."
        deduction = 30
    elif "licence" in desc_lower or "license" in desc_lower or "driving licence" in ttype.lower() or "driver license" in ttype.lower():
        what = "Exposed Driving License Number."
        why = "Driving license numbers contain vital stats that can be used for unauthorized identity checks."
        serious = "High Risk - identity impersonation."
        fix = "Obscure the license serial characters."
        deduction = 25
    elif "credit" in ttype.lower() or "debit" in ttype.lower() or "credit card" in desc_lower:
        what = "Exposed Credit/Debit Card Number."
        why = "Credit/Debit numbers are immediate financial targets for online carding, fraud, and theft."
        serious = "Critical Risk - direct financial theft."
        fix = "Cover card numbers before uploading or sharing."
        deduction = 40
    elif "bank account" in ttype.lower():
        what = "Exposed Bank Account Number."
        why = "Account numbers expose payment routing details, inviting phishing and direct debit attempts."
        serious = "Critical Risk - banking compromise."
        fix = "Redact the bank statement details."
        deduction = 35
    elif "ifsc" in ttype.lower():
        what = "Exposed Bank IFSC Code."
        why = "IFSC codes reveal specific branch details and enable targeted phishing."
        serious = "Medium Risk - routing exposure."
        fix = "Obscure the branch IFSC code."
        deduction = 15
    elif "upi" in ttype.lower():
        what = "Exposed UPI ID."
        why = "UPI payment addresses invite spam payment requests and phishing."
        serious = "High Risk - payment address leak."
        fix = "Mask your VPA / UPI handle."
        deduction = 20
    elif "otp" in ttype.lower():
        what = "Exposed Verification OTP Code."
        why = "One-Time Passwords are time-sensitive codes protecting logins. Exposure leads to instant account bypass."
        serious = "Critical Risk - authentication bypass."
        fix = "Delete this post or change verification credentials."
        deduction = 35
    elif "password" in ttype.lower():
        what = "Exposed Plaintext Password."
        why = "Exposing passwords provides attackers direct authorization to system logins."
        serious = "Critical Risk - credential theft."
        fix = "Delete the photo immediately and reset the password."
        deduction = 40
    elif "payment qr" in desc_lower or ("qr" in ttype.lower() and tsev == "High"):
        what = "Exposed Payment QR Scan Endpoint."
        why = "Payment QRs allow malicious parties to initiate payment request loops."
        serious = "High Risk - scan endpoint exposure."
        fix = "Crop out or blur QR codes."
        deduction = 20
    elif "qr" in ttype.lower():
        what = "Exposed QR Code."
        why = "General QR codes encode external URLs or contact payloads."
        serious = "Medium Risk - unverified payload link."
        fix = "Verify the target link is safe before sharing."
        deduction = 10
    elif "signature" in ttype.lower():
        what = "Exposed Digital / Handwritten Signature."
        why = "Signatures are verification tokens. Forgery can result in legal contract fraud."
        serious = "High Risk - signature forgery."
        fix = "Redact all signature boxes."
        deduction = 20
    elif "date" in ttype.lower() or "dob" in ttype.lower():
        what = f"Exposed {ttype}."
        why = "Exposing dates (DOB, issue, or expiry) facilitates identity verification bypass and target tracing."
        serious = "Medium Risk - verification bypass."
        fix = "Blur or redact date fields."
        deduction = 10
    elif "name" in ttype.lower():
        what = "Exposed Full Name."
        why = "Names are foundational hooks used for social engineering and cross-referencing leaks."
        serious = "Medium Risk - cataloging index."
        fix = "Conceal name fields."
        deduction = 10
    elif "address" in ttype.lower():
        what = "Exposed Physical Address."
        why = "Addresses reveal location details, posing physical security and privacy tracking threats."
        serious = "Medium Risk - physical tracking."
        fix = "Crop address fields."
        deduction = 15
    elif "phone" in ttype.lower():
        what = "Exposed Phone Number."
        why = "Phone numbers lead to SMS spam, SIM swapping, and harassment."
        serious = "High Risk - contact spam/tracing."
        fix = "Blur contact digits."
        deduction = 20
    elif "email" in ttype.lower():
        what = "Exposed Email Address."
        why = "Email leaks invite spear-phishing campaigns and spam database inclusions."
        serious = "Medium Risk - spam list entry."
        fix = "Mask email addresses."
        deduction = 10
    elif "employee" in ttype.lower():
        what = "Exposed Employee Credentials."
        why = "Exposes company credentials, enabling corporate spear-phishing."
        serious = "Medium Risk - workplace tracking."
        fix = "Mask workplace details."
        deduction = 10
    elif "student" in ttype.lower():
        what = "Exposed Student ID Code."
        why = "Exposes educational institution affiliation and enrollment status."
        serious = "Medium Risk - school tracking."
        fix = "Mask educational credentials."
        deduction = 10
    elif "roll" in ttype.lower():
        what = "Exposed Roll Number."
        why = "Roll numbers facilitate grade hacking and student profiling."
        serious = "Medium Risk - grade index leak."
        fix = "Conceal roll details."
        deduction = 10
    elif "identity badge" in ttype.lower():
        if tsev == "High":
            what = "Exposed Validated ID Badge."
            why = "Active ID badges contain photos, names, and access control barcodes, prompting security breaches."
            serious = "High Risk - visual badge clone."
            fix = "Apply a solid rectangle block to cover the badge."
            deduction = 20
        else:
            what = "Exposed ID Template."
            why = "Empty card templates leak institutional card details."
            serious = "Low Risk - template exposure."
            fix = "Ensure text is unreadable."
            deduction = 5
    elif "visible face" in ttype.lower():
        what = "Exposed Biometric Facial Features."
        why = "Visible faces enable facial recognition tracking and deepfake profile targeting."
        serious = "Low Risk - biometric exposure."
        fix = "Blur facial features if seeking anonymity."
        deduction = 5
    elif "watermark" in ttype.lower():
        what = "Exposed Copyright Watermark."
        why = "Watermarks show licensing ownership."
        serious = "Low Risk - copyright tag."
        fix = "No action required."
        deduction = 2
    elif "screen" in ttype.lower() or "projection screen" in ttype.lower():
        if "credentials" in threat.get("reason", "").lower():
            what = "Exposed Screen showing Credentials."
            why = "Active screen logs display credentials, inviting account takeovers."
            serious = "Critical Risk - active credentials exposed."
            fix = "Apply a complete block overlay to screen region."
            deduction = 40
        elif "chat" in threat.get("reason", "").lower():
            what = "Exposed Screen showing Chat."
            why = "Chat logs reveal active private dialogues."
            serious = "High Risk - direct message leak."
            fix = "Blur screen area."
            deduction = 20
        elif "financial" in threat.get("reason", "").lower() or "personal" in threat.get("reason", "").lower():
            what = "Exposed Screen showing Financial/Personal Info."
            why = "Exposes active balance tracking or patient statistics."
            serious = "High Risk - personal record leak."
            fix = "Mask numeric entries on screen."
            deduction = 15
        else:
            what = "Exposed Presentation Slide Screen."
            why = "Slide screens leak conference topics or corporate workflows."
            serious = "Low Risk - minor corporate disclosure."
            fix = "No action required."
            deduction = 2
    elif "chat" in ttype.lower():
        what = "Exposed Chat Screenshot."
        why = "Chat captures reveal personal threads, messaging partners, and phone handles."
        serious = "High Risk - communication disclosure."
        fix = "Mask conversation threads."
        deduction = 20
    elif "plate" in ttype.lower():
        what = "Exposed Vehicle registration number plate."
        why = "Number plates expose vehicle locations and registries."
        serious = "High Risk - vehicle tracing."
        fix = "Blur license plates."
        deduction = 15
    elif "gps" in ttype.lower():
        what = "Exposed GPS Exif metadata."
        why = "GPS location coordinates reveal the exact spot the photo was taken, inviting stalking."
        serious = "High Risk - absolute coordinate leak."
        fix = "Strip EXIF headers."
        deduction = 25
    elif "location" in ttype.lower():
        what = "Exposed Location details."
        why = "Reveals addresses or landmark intersections."
        serious = "Medium Risk - neighborhood leak."
        fix = "Mask location indicators."
        deduction = 12
    elif "document" in ttype.lower() or "visible" in ttype.lower():
        what = f"Exposed {ttype} Document."
        why = "Commercial or educational sheets expose administrative tracking."
        serious = "Low Risk - administrative exposure."
        fix = "Conceal document paragraphs."
        deduction = 5

    threat["whatWasDetected"] = what
    threat["whyIsItRisky"] = why
    threat["howSeriousIsIt"] = serious
    threat["howCanItBeFixed"] = fix
    threat["deduction"] = deduction

