import cv2
import re
import logging
from PIL import Image

logger = logging.getLogger(__name__)

# ── QR Content Classifiers ────────────────────────────────────────────────────
_PAYMENT_PATTERN = re.compile(
    r'(?:upi://|upi=|paytm|phonepe|gpay|googlepay|bhim|razorpay|@(okaxis|okicici|oksbi|okhdfcbank|ybl|ibl|paytm|upi|kotak|sbi|mahb))',
    re.IGNORECASE
)
_WEBSITE_PATTERN = re.compile(r'^https?://', re.IGNORECASE)
_CONTACT_PATTERN = re.compile(r'^(?:BEGIN:VCARD|MECARD:|BEGIN:VEVENT)', re.IGNORECASE)
_LOGIN_PATTERN   = re.compile(r'(?:login|signin|auth|token|oauth|session)', re.IGNORECASE)


def classify_qr(content: str) -> dict:
    """Classify QR code content into a type with risk level."""
    content_upper = content.upper()
    if "PRINTLETTERBARCODEDATA" in content_upper or "UIDAI" in content_upper or "<AADH" in content_upper or (content.isdigit() and len(content) > 100):
        return {"qrType": "Aadhaar QR", "severity": "Critical",
                "description": "Aadhaar secure QR code containing highly sensitive demographic info."}
    if _PAYMENT_PATTERN.search(content):
        return {"qrType": "Payment QR", "severity": "High",
                "description": "Payment or UPI QR code — can initiate financial transactions."}
    if _CONTACT_PATTERN.match(content):
        return {"qrType": "Contact QR", "severity": "Medium",
                "description": "QR encodes contact/vCard information."}
    if _LOGIN_PATTERN.search(content):
        return {"qrType": "Login/Auth QR", "severity": "High",
                "description": "QR contains login token or authentication URL."}
    if _WEBSITE_PATTERN.match(content):
        return {"qrType": "Website QR", "severity": "Low",
                "description": f"QR links to: {content[:80]}"}
    return {"qrType": "Unknown QR", "severity": "Medium",
            "description": "QR code with unknown content type."}


def detect_qr_codes(image_path_or_img) -> dict:
    """
    Detect and decode QR codes and 1D Barcodes from an image.
    Primary: OpenCV QRCodeDetector (Optimal Windows compatibility)
    Fallback: pyzbar
    Returns: qrCount, decodedQRCodes list of { value, bbox: [x, y, w, h] }.
    """
    result = {
        "qrCount": 0,
        "decodedQRCodes": []
    }

    opencv_success = False
    img = None

    try:
        if isinstance(image_path_or_img, str):
            img = cv2.imread(image_path_or_img)
        else:
            img = image_path_or_img

        if img is not None:
            detector = cv2.QRCodeDetector()
            retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)

            if retval and decoded_info:
                valid_codes = [info for info in decoded_info if info.strip()]
                if valid_codes:
                    opencv_success = True
                    result["qrCount"] = len(valid_codes)
                    for i, info in enumerate(valid_codes):
                        bbox = None
                        if points is not None and i < len(points):
                            pts = points[i]
                            xs = [int(pt[0]) for pt in pts]
                            ys = [int(pt[1]) for pt in pts]
                            bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]

                        result["decodedQRCodes"].append({
                            "value": info.strip(),
                            "bbox": bbox,
                            **classify_qr(info.strip())
                        })
            elif not retval:
                val, pts, _ = detector.detectAndDecode(img)
                if val and val.strip():
                    opencv_success = True
                    result["qrCount"] = 1
                    bbox = None
                    if pts is not None and len(pts) > 0:
                        xs = [int(pt[0]) for pt in pts[0]] if len(pts.shape) == 3 else [int(pt[0]) for pt in pts]
                        ys = [int(pt[1]) for pt in pts[0]] if len(pts.shape) == 3 else [int(pt[1]) for pt in pts]
                        bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
                    result["decodedQRCodes"].append({
                        "value": val.strip(),
                        "bbox": bbox,
                        **classify_qr(val.strip())
                    })
    except Exception as cv_err:
        logger.debug(f"OpenCV QR Detection debug info: {cv_err}")

    # Fallback: pyzbar if OpenCV found nothing or to extract 1D barcodes
    try:
        from pyzbar.pyzbar import decode
        if isinstance(image_path_or_img, str):
            img_pil = Image.open(image_path_or_img)
        elif img is not None:
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        else:
            img_pil = None

        if img_pil is not None:
            decoded = decode(img_pil)
            if decoded:
                for item in decoded:
                    content = item.data.decode("utf-8", errors="replace").strip()
                    # Check if we already have this exact detection to avoid duplicates
                    if any(c["value"] == content for c in result["decodedQRCodes"]):
                        continue
                        
                    rect = item.rect
                    bbox = [rect.left, rect.top, rect.width, rect.height]
                    
                    if item.type == 'QRCODE':
                        result["decodedQRCodes"].append({
                            "value": content,
                            "bbox": bbox,
                            **classify_qr(content)
                        })
                    else:
                        # 1D Barcode detected
                        result["decodedQRCodes"].append({
                            "value": content,
                            "bbox": bbox,
                            "qrType": "Barcode",
                            "severity": "High",
                            "description": f"1D Barcode ({item.type}) detected."
                        })
                result["qrCount"] = len(result["decodedQRCodes"])
    except Exception as pyzbar_err:
        logger.debug(f"pyzbar scanner debug info: {pyzbar_err}")

    return result
