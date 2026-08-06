import os
import cv2
import logging

logger = logging.getLogger(__name__)

CASCADE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "haarcascade_frontalface_default.xml")
if not os.path.exists(CASCADE_PATH):
    CASCADE_PATH = os.path.join(os.path.dirname(__file__), "haarcascade_frontalface_default.xml")

_face_cascade = None


def get_cascade_classifier():
    global _face_cascade
    if _face_cascade is None:
        if os.path.exists(CASCADE_PATH):
            try:
                _face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
                if _face_cascade.empty():
                    _face_cascade = False
            except Exception as e:
                logger.warning(f"Failed to load Haar Cascade from {CASCADE_PATH}: {e}")
                _face_cascade = False
        else:
            _face_cascade = False
    return _face_cascade


def detect_faces(image_path_or_img) -> dict:
    """
    Sub-second OpenCV face detection using bundled Haar Cascade.

    Returns:
        faceCount, faceLocations, isGroupPhoto, photoType
    """
    result = {
        "faceCount": 0,
        "faceLocations": [],
        "isGroupPhoto": False,
        "photoType": "No Face"
    }

    try:
        if isinstance(image_path_or_img, str):
            img = cv2.imread(image_path_or_img)
        else:
            img = image_path_or_img

        if img is None:
            logger.warning("Could not read image for face detection")
            return result

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        cascade = get_cascade_classifier()
        if cascade and cascade != False and not cascade.empty():
            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(int(w * 0.04), int(h * 0.04))
            )
            if len(faces) == 0:
                faces = cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2, minSize=(30, 30))

            if len(faces) > 0:
                result["faceCount"] = len(faces)

                for (fx, fy, fw, fh) in faces:
                    result["faceLocations"].append({
                        "x": int(fx),
                        "y": int(fy),
                        "width": int(fw),
                        "height": int(fh),
                        "confidence": 0.92
                    })

                face_count = len(faces)

                # Photo type classification
                if face_count >= 4:
                    result["isGroupPhoto"] = True
                    result["photoType"] = "Group Photo"
                elif face_count >= 2:
                    result["photoType"] = "Multiple Faces"
                else:
                    result["photoType"] = "Single Face"

                logger.info(
                    f"Face detection: {face_count} face(s), type={result['photoType']}, "
                    f"group={result['isGroupPhoto']}"
                )
                return result

    except Exception as e:
        logger.error(f"Error during face detection on {image_path}: {e}")

    return result
