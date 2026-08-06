# AI Privacy Risk Simulator - Production-Grade Flask Backend

Production-ready, asynchronous Python/Flask backend for the **AI Privacy Risk Simulator**. Performs multi-stage automated image analysis (EXIF metadata, EasyOCR text recognition with PII regex matching, MediaPipe facial biometrics, OpenCV/pyzbar QR code scanning, privacy risk scoring, and Google Gemini AI summary generation).

---

## 🚀 Key Architecture & Performance Highlights

1. **Non-Blocking Background Processing**:
   - `POST /api/upload` saves the image, initializes the scan record with status `"pending"`, and returns immediately ($\le$100ms).
   - Analysis executes asynchronously in a background thread, updating scan lifecycle status (`pending` $\rightarrow$ `processing` $\rightarrow$ `completed` / `failed`), progress percentage (0–100%), and active step (`"Metadata Extraction"`, `"OCR Analysis"`, `"Face Detection"`, `"QR Scanning"`, `"Scoring & Gemini AI"`).

2. **Real-time Status Polling**:
   - `GET /api/status/<scanId>` allows the frontend scanning animation to display live progress and current processing steps.

3. **Image Overlay Coordinates**:
   - Bounding boxes `[x, y, width, height]` are returned for all faces, recognized OCR strings, and QR codes inside `report_json`, enabling frontend visual risk highlighting overlays.

4. **Instant Report Caching**:
   - Completed reports are stored directly in SQLite (`report_json`). `GET /api/report/<scanId>` serves cached reports instantly.

5. **Pre-Warmed AI Singletons**:
   - `EasyOCR Reader` and `MediaPipe Face Detector` are loaded ONCE globally to prevent per-request startup overhead.

6. **Image Preview Endpoint**:
   - `GET /api/image/<scanId>` serves the original uploaded image file.

7. **Gemini Failsafe Guarantee**:
   - Gemini API calls are wrapped in robust exception handlers. If the API key is omitted or the network fails, an intelligent fallback summary template is returned — ensuring analysis **never** fails.

8. **Structured File Logging**:
   - All server events and step timings are written to `backend/logs/app.log` and stdout.

---

## 🛠️ Tech Stack

- **Python**: 3.11+
- **Framework**: Flask, Flask-CORS, Flask-SQLAlchemy
- **Database**: SQLite with SQLAlchemy ORM
- **Computer Vision & AI**:
  - **EXIF Metadata**: `Pillow` (PIL)
  - **OCR**: `EasyOCR` (Single global instance)
  - **Biometrics & Faces**: `MediaPipe Face Detection` (Single global instance, with OpenCV Haar Cascade fallback)
  - **QR Code Scanning**: OpenCV `QRCodeDetector` (Primary) + `pyzbar` (Fallback)
  - **AI Summaries**: Google Gemini API (`google-generativeai`)

---

## 📁 Project Structure

```
backend/
├── app.py                     # App factory, file logger, error handlers
├── config.py                  # Storage paths, 20MB limit, mime types
├── database.py                # SQLAlchemy DB setup
├── .env                       # Environment variables
├── requirements.txt           # Dependency manifest
├── README.md                  # Complete documentation
│
├── logs/
│   └── app.log                # Rotating structured app log file
│
├── models/
│   ├── scan.py                # Scan status lifecycle & JSON caching schema
│   └── finding.py             # Finding threat schema with bbox JSON
│
├── routes/
│   ├── upload.py              # POST /api/upload (Instant return & async task)
│   ├── status.py              # GET /api/status/<scanId> (Polling)
│   ├── report.py              # GET /api/report/<scanId> (Instant cached JSON)
│   ├── image.py               # GET /api/image/<scanId> (Original image file)
│   └── history.py             # GET /api/history & DELETE endpoints
│
└── services/
    ├── metadata_service.py    # EXIF GPS and camera parsing
    ├── ocr_service.py         # EasyOCR singleton & PII regex matcher with bboxes
    ├── face_service.py        # MediaPipe face landmarking singleton with bboxes
    ├── qr_service.py          # OpenCV primary + pyzbar fallback QR scanner
    ├── scoring_service.py     # 0-100 privacy scoring & threat engine with bboxes
    ├── gemini_service.py      # Google Gemini summary generation with failsafe
    └── analysis_service.py    # Async pipeline orchestrator & status reporter
```

---

## 🏃 Quick Setup & Run Instructions

### 1. Create Virtual Environment & Install Dependencies

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

Copy or edit `.env`:

```env
FLASK_ENV=development
PORT=5000
SECRET_KEY=dev-secret-key-392810
DATABASE_URL=sqlite:///privacy_simulator.db
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Start Server

```bash
python app.py
```

Server runs on **`http://localhost:5000`**.

---

## 📡 API Endpoint Reference

### 1. Health Check
`GET /api/health`
```json
{
  "status": "healthy",
  "database": "connected",
  "gemini": "configured"
}
```

### 2. Upload Image (Instant Non-Blocking Response)
`POST /api/upload`
- **Form Data**: `image` (file, max 20MB), `scanMode` (`deep`/`quick`), `privacyLevel` (`high`/`standard`/`minimal`)
- **Response**: `201 Created`
```json
{
  "scanId": "3f8290a1-94bd-4c55-b771-46e28ef9019d",
  "status": "pending",
  "targetName": "photo.jpg"
}
```

### 3. Check Real-Time Scan Status (Polling)
`GET /api/status/<scanId>`
- **Response**: `200 OK`
```json
{
  "scanId": "3f8290a1-94bd-4c55-b771-46e28ef9019d",
  "status": "processing",
  "progress": 65,
  "currentStep": "Face Detection",
  "errorMessage": null
}
```

### 4. Get Final Report (Cached Instant Response)
`GET /api/report/<scanId>`
- **Response**: `200 OK`
```json
{
  "scanId": "3f8290a1-94bd-4c55-b771-46e28ef9019d",
  "targetName": "photo.jpg",
  "scanMode": "deep",
  "privacyLevel": "high",
  "status": "completed",
  "progress": 100,
  "currentStep": "Completed",
  "privacyScore": 65,
  "riskLevel": "Medium",
  "summary": "This image contains 2 visible face(s) and a visible phone number. Review sensitive areas before posting online.",
  "metrics": {
    "facesDetected": 2,
    "textBlocks": 3,
    "qrCodes": 0,
    "gpsMetadata": false
  },
  "threats": [
    {
      "type": "Phone Number",
      "severity": "High",
      "description": "Visible phone number detected: +919876543210",
      "bbox": [100, 200, 250, 40]
    },
    {
      "type": "Face Detected",
      "severity": "High",
      "description": "2 human face(s) identified in image.",
      "bbox": [120, 55, 80, 80]
    }
  ],
  "recommendations": [
    "Blur or redact phone numbers in the image.",
    "Apply biometric face blur or anonymization if sharing publicly."
  ],
  "analysisDetails": {
    "ocrText": [
      { "text": "Call +919876543210", "bbox": [100, 200, 250, 40] }
    ],
    "decodedQRCodes": [],
    "faceLocations": [
      { "x": 120, "y": 55, "width": 80, "height": 80, "confidence": 0.95 }
    ],
    "metadata": {
      "cameraMake": "Apple",
      "cameraModel": "iPhone 15",
      "dateTimeOriginal": "2025:07:24 14:32:00",
      "gps": null
    }
  }
}
```

### 5. Fetch Original Image File (Preview)
`GET /api/image/<scanId>`
- **Response**: Binary image stream (`image/jpeg`, `image/png`, etc.)

### 6. Audit History
- `GET /api/history`: List all scan history items.
- `DELETE /api/history/<scanId>`: Delete scan item and uploaded file.
- `DELETE /api/history`: Clear all history and uploaded files.

---

## 🔒 Privacy & Scoring Rules

| Category | Score Deduction | Severity |
| :--- | :--- | :--- |
| **GPS Metadata Present** | **-25** | High |
| **Phone Number Detected** | **-20** | High |
| **Street Address Detected** | **-15** | High |
| **Email Address Detected** | **-10** | Medium |
| **Face Detected** | **-10 per face** | High (>1 face) / Medium |
| **QR Code Detected** | **-10** | Medium |

### Privacy Remediation (Redaction Engine)

Transform the risk simulator into a privacy protection tool by automatically removing discovered threats.

**1. Auto-Redact Detected PII:**
```http
POST /api/v1/redact/<scanId>
Content-Type: application/json

{
  "mode": "blur" // Supported: blur, pixelate, blackbox, solid
}
```

**2. Check Redaction Status:**
```http
GET /api/v1/redact/redaction-status/<scanId>
```
*Note: Background redaction typically finishes in <2 seconds.*

**3. Get the Safe Image (No Metadata, PII Redacted):**
```http
GET /api/v1/redacted-image/<scanId>
```

**4. Compare Before vs After:**
```http
GET /api/v1/comparison/<scanId>
```
*Returns scores, image URLs, and risk reduction metrics for frontend visualization.*

### Risk Tiers
- **`0 – 25`**: Critical Risk
- **`26 – 50`**: High Risk
- **`51 – 75`**: Medium Risk
- **`76 – 100`**: Safe
