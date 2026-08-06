import os
import cv2
import logging
import numpy as np

logger = logging.getLogger(__name__)

COLOR_MAP = {
    "Critical": (0, 0, 255),      # Red (BGR)
    "High": (0, 165, 255),        # Orange (BGR)
    "Medium": (0, 255, 255),      # Yellow (BGR)
    "Low": (255, 0, 0),           # Blue (BGR)
    "Safe": (255, 0, 0),          # Blue (BGR)
    "Text": (255, 0, 0)           # Blue (BGR)
}

def generate_annotated_image(image_path: str, scan_id: str, threats: list, analysis_details: dict, annotated_folder: str) -> str:
    """
    Generate a high-end visual overlay risk heatmap on the target image.
    High-risk regions (Critical/High) = Red translucent overlay
    Medium-risk = Orange translucent overlay
    Low-risk = Yellow translucent overlay
    Informational/Text = Blue translucent overlay
    """
    try:
        os.makedirs(annotated_folder, exist_ok=True)
        out_filename = f"{scan_id}_annotated.png"
        out_path = os.path.join(annotated_folder, out_filename)

        img = cv2.imread(image_path)
        if img is None:
            logger.warning(f"Could not read image for annotation: {image_path}")
            return None

        h, w, _ = img.shape
        overlay = img.copy()

        # 1. Draw Informational General OCR Text Blocks (Blue Overlay)
        ocr_blocks = analysis_details.get("ocrText", [])
        for block in ocr_blocks:
            bbox = block.get("bbox")
            txt = block.get("text", "")
            if bbox and len(bbox) == 4:
                bx, by, bw, bh = bbox
                if bw > 0 and bh > 0:
                    # Draw filled translucent block on overlay
                    cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (255, 0, 0), -1)
                    # Small thin boundary on main image
                    cv2.rectangle(img, (bx, by), (bx + bw, by + bh), (255, 0, 0), 1)

        # 2. Draw Face Locations (Yellow/Blue Overlay - Low/Informational)
        face_locations = analysis_details.get("faceLocations", [])
        for fl in face_locations:
            x, y, width, height = fl.get("x", 0), fl.get("y", 0), fl.get("width", 0), fl.get("height", 0)
            if width > 0 and height > 0:
                cv2.rectangle(overlay, (x, y), (x + width, y + height), (0, 255, 255), -1) # Yellow
                cv2.rectangle(img, (x, y), (x + width, y + height), (0, 255, 255), 2)
                cv2.putText(img, "FACE DETECTED", (x + 4, y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        # 3. Draw Active Audited Threats (High/Medium/Low Risk Heatmaps)
        for threat in threats:
            # Skip if user has dismissed the threat
            if threat.get("dismissed", False):
                continue
                
            bbox = threat.get("bbox")
            severity = threat.get("severity", "High")
            threat_color = COLOR_MAP.get(severity, (0, 0, 255))
            threat_type = threat.get("type", "RISK")

            if bbox and len(bbox) == 4:
                bx, by, bw, bh = bbox
                if bw > 0 and bh > 0:
                    cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), threat_color, -1)
                    cv2.rectangle(img, (bx, by), (bx + bw, by + bh), threat_color, 2)
                    label = f"[{threat_type.upper()}]"
                    cv2.putText(img, label, (bx + 4, by + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, threat_color, 2)

        # 4. Draw QR Codes (Orange/Yellow Overlay)
        qr_codes = analysis_details.get("decodedQRCodes", [])
        for qr in qr_codes:
            q_bbox = qr.get("bbox") if isinstance(qr, dict) else None
            if q_bbox and len(q_bbox) == 4:
                qx, qy, qw, qh = q_bbox
                if qw > 0 and qh > 0:
                    cv2.rectangle(overlay, (qx, qy), (qx + qw, qy + qh), (0, 165, 255), -1) # Orange
                    cv2.rectangle(img, (qx, qy), (qx + qw, qy + qh), (0, 165, 255), 2)
                    cv2.putText(img, "QR CODE", (qx + 4, qy + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 2)

        # Blend the translucent overlay (alpha = 0.28 for high transparency glass look)
        alpha = 0.28
        cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0, img)

        cv2.imwrite(out_path, img)
        logger.info(f"Generated audited heatmap overlay for scan {scan_id} at {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"Error generating heatmap overlay image for {image_path}: {e}")
        return None
