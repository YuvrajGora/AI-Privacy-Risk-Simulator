import os
import json
import logging

logger = logging.getLogger(__name__)

def generate_gemini_summary(metrics: dict, threats: list, privacy_score: int, risk_level: str) -> dict:
    """
    Generate plain-language privacy risk summary, recommendations, and social media sharing advice
    using Google Gemini API based on structured findings.
    Failsafe: Exception or missing key returns clean rule-based fallback dict.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if api_key and api_key != "your_gemini_api_key_here":
        try:
            import google.generativeai as genai
            import concurrent.futures

            def _call_gemini():
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                threat_types = [t.get("type", "") for t in threats]
                prompt = f"""
                Act as an expert AI privacy & cybersecurity auditor.
                I have performed technical computer vision & OCR scanning on an image and found the following structured findings:
                - Privacy Score: {privacy_score}/100 (Higher is safer)
                - Overall Risk Level: {risk_level}
                - Detected Threat Items: {threat_types}
                - Faces Detected: {metrics.get('facesDetected', 0)}
                - Text Blocks Found: {metrics.get('textBlocks', 0)}
                - QR Codes Found: {metrics.get('qrCodes', 0)}
                - GPS Metadata Present: {metrics.get('gpsMetadata', False)}

                Generate a valid JSON object with the following keys:
                1. "summary": A concise 2-sentence human-friendly explanation of why this image is at risk or safe.
                2. "recommendations": An array of 2-3 specific actionable bullet points to mitigate risks before sharing.
                3. "sharingAdvice": 1-2 sentences of specific advice for sharing this image on social media (Instagram, Twitter, LinkedIn, WhatsApp).

                Do NOT output markdown formatting like ```json. Return ONLY valid JSON text.
                """
                resp = model.generate_content(prompt)
                return resp

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini)
                response = future.result(timeout=10.0)  # 10s strict timeout

            if response and hasattr(response, 'text') and response.text:
                cleaned = response.text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("```")[1]
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:].strip()
                data = json.loads(cleaned)
                return {
                    "summary": data.get("summary", ""),
                    "recommendations": data.get("recommendations", []),
                    "sharingAdvice": data.get("sharingAdvice", "")
                }
        except concurrent.futures.TimeoutError:
            logger.warning("[GEMINI] API call exceeded 10-second timeout limit. Triggering fallback.")
        except Exception as e:
            logger.warning(f"Gemini API call warning/failsafe triggered: {e}. Using fallback generator.")

    # Rule-based Failsafe Summary Generator (No child/age elements)
    summary_parts = []
    recs = []

    if risk_level == "Safe":
        return {
            "summary": "Your image appears safe to share. No sensitive PII, location coordinates, or unmasked credentials were detected.",
            "recommendations": ["Image is clean and ready for sharing."],
            "sharingAdvice": "This image is safe to share across social media platforms without modification."
        }

    if metrics.get("gpsMetadata"):
        summary_parts.append("contains embedded GPS location coordinates")
        recs.append("Strip EXIF location metadata before uploading.")

    if metrics.get("facesDetected", 0) > 0:
        summary_parts.append(f"shows {metrics['facesDetected']} visible face(s)")
        recs.append("Apply face blur or sticker overlay to anonymize people.")

    if metrics.get("qrCodes", 0) > 0:
        summary_parts.append("includes a scannable QR code")
        recs.append("Verify QR code contents or blur QR code before posting.")

    if any("Identity" in t.get("type", "") for t in threats):
        summary_parts.append("exposes identity documents")
        recs.append("Black-box or pixelate identity card details immediately.")

    if any("Phone" in t.get("type", "") or "Email" in t.get("type", "") or "Address" in t.get("type", "") for t in threats):
        summary_parts.append("exposes personal contact details")
        recs.append("Redact phone numbers, emails, and address text.")

    details = ", ".join(summary_parts) if summary_parts else "contains visible sensitive elements"

    return {
        "summary": f"This image received a {privacy_score}/100 ({risk_level} Risk) score because it {details}.",
        "recommendations": recs or ["Review image content and redact sensitive areas before posting online."],
        "sharingAdvice": f"Do not post this image on social media without masking the detected sensitive items ({details})."
    }
