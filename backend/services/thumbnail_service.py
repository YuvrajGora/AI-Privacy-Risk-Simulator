import os
import logging
from PIL import Image

logger = logging.getLogger(__name__)

def generate_thumbnail(image_path: str, scan_id: str, thumbnail_folder: str) -> str:
    """
    Generate a 300x300 preview thumbnail for an uploaded image.
    Returns the absolute path to the generated thumbnail file.
    """
    try:
        os.makedirs(thumbnail_folder, exist_ok=True)
        thumb_filename = f"{scan_id}_thumb.png"
        thumb_path = os.path.join(thumbnail_folder, thumb_filename)

        with Image.open(image_path) as img:
            img_copy = img.copy()
            img_copy.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Convert RGBA/P to RGB for PNG/JPEG saving
            if img_copy.mode in ("RGBA", "P"):
                img_copy = img_copy.convert("RGB")

            img_copy.save(thumb_path, "PNG", optimize=True)
            logger.info(f"Generated thumbnail for scan {scan_id} at {thumb_path}")
            return thumb_path

    except Exception as e:
        logger.error(f"Thumbnail generation error for {image_path}: {e}")
        return None
