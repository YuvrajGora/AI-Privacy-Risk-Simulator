import logging
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)

def _convert_to_degrees(value):
    """Helper to convert the GPS coordinates stored in EXIF to decimal degrees."""
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return 0.0

def extract_metadata(image_path: str) -> dict:
    """Extract EXIF metadata including GPS coordinates, camera details, and timestamps."""
    metadata_result = {
        "hasGps": False,
        "gps": None,
        "cameraMake": None,
        "cameraModel": None,
        "dateTimeOriginal": None,
        "rawTagsCount": 0
    }

    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if not exif_data:
                return metadata_result

            exif = {
                ExifTags.TAGS[k]: v
                for k, v in exif_data.items()
                if k in ExifTags.TAGS
            }
            metadata_result["rawTagsCount"] = len(exif)

            # Camera Make & Model
            metadata_result["cameraMake"] = str(exif.get("Make", "")).strip() or None
            metadata_result["cameraModel"] = str(exif.get("Model", "")).strip() or None
            metadata_result["dateTimeOriginal"] = str(exif.get("DateTimeOriginal", exif.get("DateTime", ""))).strip() or None

            # GPS Processing
            gps_info = exif.get("GPSInfo")
            if gps_info:
                gps_tags = {}
                for key in gps_info.keys():
                    decode_key = ExifTags.GPSTAGS.get(key, key)
                    gps_tags[decode_key] = gps_info[key]

                lat_ref = gps_tags.get("GPSLatitudeRef")
                lat = gps_tags.get("GPSLatitude")
                lon_ref = gps_tags.get("GPSLongitudeRef")
                lon = gps_tags.get("GPSLongitude")

                if lat and lon and lat_ref and lon_ref:
                    latitude = _convert_to_degrees(lat)
                    if lat_ref != "N":
                        latitude = -latitude

                    longitude = _convert_to_degrees(lon)
                    if lon_ref != "E":
                        longitude = -longitude

                    metadata_result["hasGps"] = True
                    metadata_result["gps"] = {
                        "latitude": round(latitude, 6),
                        "longitude": round(longitude, 6),
                        "latRef": lat_ref,
                        "lonRef": lon_ref
                    }

    except Exception as e:
        logger.warning(f"Metadata extraction warning for {image_path}: {e}")

    return metadata_result


def analyze_image_quality(image_path: str) -> dict:
    """Detect blur level (Laplacian), exposure level, resolution, and warn if poor."""
    import cv2
    import numpy as np
    
    quality = {
        "blurLevel": 0.0,
        "exposureLevel": "Normal",
        "resolution": "Unknown",
        "qualityAssessment": "Good",
        "warning": None
    }
    try:
        img = cv2.imread(image_path)
        if img is None:
            return quality
        h, w = img.shape[:2]
        quality["resolution"] = f"{w}x{h}"
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Blur detection (Laplacian variance)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        quality["blurLevel"] = round(lap_var, 2)
        
        # 2. Exposure check
        mean_bright = float(np.mean(gray))
        if mean_bright > 220:
            quality["exposureLevel"] = "Overexposed"
        elif mean_bright < 45:
            quality["exposureLevel"] = "Underexposed"
        else:
            quality["exposureLevel"] = "Normal"
            
        # 3. Quality Assessment
        reasons = []
        if lap_var < 80:
            reasons.append("blurry")
        if quality["exposureLevel"] in ("Overexposed", "Underexposed"):
            reasons.append(quality["exposureLevel"].lower())
        if max(h, w) < 800:
            reasons.append("low resolution")
            
        if reasons:
            quality["qualityAssessment"] = "Poor"
            quality["warning"] = f"Results may be incomplete due to {', '.join(reasons)} image quality."
        else:
            quality["qualityAssessment"] = "Good"
            quality["warning"] = None
    except Exception as e:
        logger.warning(f"Error in image quality analysis: {e}")
    return quality


def calculate_scan_reliability(quality: dict, avg_ocr_conf: float) -> int:
    """Calculate overall scan reliability score from 20 to 100 based on image factors."""
    score = 100
    if quality["qualityAssessment"] == "Poor":
        w = quality["warning"] or ""
        if "blurry" in w:
            score -= 20
        if "exposed" in w or "overexposed" in w or "underexposed" in w:
            score -= 15
        if "low resolution" in w:
            score -= 15
    # Factor in average OCR confidence
    score -= int((1.0 - avg_ocr_conf) * 15)
    return max(20, min(100, score))

