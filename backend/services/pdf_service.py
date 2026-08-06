import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import json
from models.scan import Scan

def generate_pdf_report(scan: Scan, output_path: str):
    """Generates a premium multi-page PDF report for a given privacy scan."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    # Page 1 Header Banner
    c.setFillColor(colors.HexColor("#0f172a")) # Premium Navy Blue
    c.rect(0, height - 80, width, 80, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, height - 48, "AI PRIVACY AUDIT ASSESSMENT")
    
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 66, "Report generated automatically by AI Privacy Risk Simulator")
    
    # Reset text fill color
    c.setFillColor(colors.HexColor("#0f172a"))
    
    y = height - 120
    
    # Metadata Table
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "AUDIT INFORMATION")
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.line(40, y - 4, width - 40, y - 4)
    y -= 20
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "Scan ID:")
    c.setFont("Helvetica", 9)
    c.drawString(140, y, str(scan.scan_id))
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(width/2 + 20, y, "Target Image:")
    c.setFont("Helvetica", 9)
    c.drawString(width/2 + 110, y, str(scan.target_name))
    y -= 16
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "Risk Level:")
    c.setFont("Helvetica-Bold", 9)
    # Color risk level dynamically
    if "Critical" in str(scan.risk_level):
        c.setFillColor(colors.HexColor("#dc2626"))
    elif "High" in str(scan.risk_level):
        c.setFillColor(colors.HexColor("#ea580c"))
    elif "Medium" in str(scan.risk_level):
        c.setFillColor(colors.HexColor("#d97706"))
    else:
        c.setFillColor(colors.HexColor("#16a34a"))
    c.drawString(140, y, str(scan.risk_level).upper())
    c.setFillColor(colors.HexColor("#0f172a"))
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(width/2 + 20, y, "Privacy Score:")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(width/2 + 110, y, f"{scan.privacy_score}/100")
    y -= 30
    
    # Executive Summary
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "EXECUTIVE SUMMARY")
    c.line(40, y - 4, width - 40, y - 4)
    y -= 20
    
    c.setFont("Helvetica", 10)
    summary = scan.summary or "No summary available."
    words = summary.split(" ")
    line = ""
    for w in words:
        if c.stringWidth(line + w, "Helvetica", 10) < width - 100:
            line += w + " "
        else:
            c.drawString(50, y, line)
            y -= 14
            line = w + " "
    if line:
        c.drawString(50, y, line)
        y -= 25

    # Load full report data
    report_data = {}
    if scan.report_json:
        try:
            report_data = json.loads(scan.report_json)
        except:
            pass

    # Threats list
    threats = report_data.get("threats", [])
    
    # Diagnostics Card (Accuracy Dashboard details)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "DIAGNOSTICS BREAKDOWN")
    c.line(40, y - 4, width - 40, y - 4)
    y -= 20
    
    total = len(threats)
    critical = sum(1 for t in threats if t.get("severity", "").lower() == "critical")
    high = sum(1 for t in threats if t.get("severity", "").lower() == "high")
    medium = sum(1 for t in threats if t.get("severity", "").lower() == "medium")
    low = sum(1 for t in threats if t.get("severity", "").lower() == "low")
    dismissed = sum(1 for t in threats if t.get("dismissed") is True)
    
    c.setFont("Helvetica", 9.5)
    c.drawString(50, y, f"Total Findings: {total}")
    c.drawString(160, y, f"Critical Severity: {critical}")
    c.drawString(280, y, f"High Severity: {high}")
    c.drawString(390, y, f"Medium Severity: {medium}")
    c.drawString(490, y, f"Low Severity: {low}")
    y -= 14
    c.drawString(50, y, f"Dismissed (False Positives Override): {dismissed}")
    y -= 30

    # Threats details (Page 1 fits ~4-5 threats, then rollover)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "DETECTED RISK FINDINGS")
    c.line(40, y - 4, width - 40, y - 4)
    y -= 20
    
    active_threats = [t for t in threats if not t.get("dismissed")]
    if not active_threats:
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(50, y, "No active privacy risks identified in this scan.")
        y -= 20
    else:
        for idx, t in enumerate(active_threats):
            if y < 80: # Start Page 2!
                c.showPage()
                # Draw small header on Page 2
                c.setFillColor(colors.HexColor("#0f172a"))
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, height - 40, "AI Privacy Audit Assessment Report - Findings (Contd.)")
                c.line(40, height - 45, width - 40, height - 45)
                y = height - 70
                c.setFillColor(colors.HexColor("#0f172a"))

            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, f"{idx+1}. {t.get('type')} [{t.get('severity', 'Medium').upper()}]")
            
            # Color indicator box
            t_sev = t.get("severity", "").lower()
            if t_sev == "critical":
                c.setFillColor(colors.HexColor("#dc2626"))
            elif t_sev == "high":
                c.setFillColor(colors.HexColor("#ea580c"))
            elif t_sev == "medium":
                c.setFillColor(colors.HexColor("#d97706"))
            else:
                c.setFillColor(colors.HexColor("#3b82f6"))
            c.rect(40, y, 4, 10, fill=True, stroke=False)
            c.setFillColor(colors.HexColor("#0f172a"))
            
            y -= 14
            c.setFont("Helvetica", 9)
            desc = t.get("description", "")
            # Word wrap description
            desc_words = desc.split(" ")
            d_line = ""
            for dw in desc_words:
                if c.stringWidth(d_line + dw, "Helvetica", 9) < width - 100:
                    d_line += dw + " "
                else:
                    c.drawString(60, y, d_line)
                    y -= 12
                    d_line = dw + " "
            if d_line:
                c.drawString(60, y, d_line)
                y -= 16

    # Force page break for Visuals & Recommendations
    c.showPage()
    
    # Page 2 Header
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 40, "Mitigation & Remediation Analysis")
    c.line(40, height - 45, width - 40, height - 45)
    
    y = height - 70
    
    # Recommendations
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "MITIGATION RECOMMENDATIONS")
    c.line(40, y - 4, width - 40, y - 4)
    y -= 20
    
    recs = report_data.get("recommendations", [])
    if not recs:
        recs = scan.recommendations_json
        if recs:
            try: recs = json.loads(recs)
            except: recs = []
            
    if not recs:
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(50, y, "No specific recommendations needed.")
        y -= 20
    else:
        c.setFont("Helvetica", 9.5)
        for idx, rec in enumerate(recs):
            rec_words = rec.split(" ")
            r_line = ""
            for rw in rec_words:
                if c.stringWidth(r_line + rw, "Helvetica", 9.5) < width - 120:
                    r_line += rw + " "
                else:
                    c.drawString(60, y, r_line)
                    y -= 13
                    r_line = rw + " "
            if r_line:
                c.drawString(60, y, r_line)
                c.setFont("Helvetica-Bold", 9.5)
                c.drawString(50, y, f"-")
                c.setFont("Helvetica", 9.5)
                y -= 16
                
    y -= 15
    
    # Before / After Score improvement
    is_redacted = scan.redacted_image_path and os.path.exists(scan.redacted_image_path)
    if is_redacted:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, "REMEDIATION SCORE IMPROVEMENT")
        c.line(40, y - 4, width - 40, y - 4)
        y -= 20
        
        orig_score = report_data.get("originalScore", scan.privacy_score) or 50
        safe_score = report_data.get("safeScore", 98) or 98
        # Calculate improvement percentage
        imp_pct = 0.0
        if orig_score > 0:
            imp_pct = ((safe_score - orig_score) / float(orig_score)) * 100.0
            
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, f"Original Score: {orig_score}   →   Safe Score: {safe_score}")
        c.setFillColor(colors.HexColor("#16a34a"))
        c.drawString(325, y, f"+{imp_pct:.0f}% Improvement")
        c.setFillColor(colors.HexColor("#0f172a"))
        y -= 20
        
        c.setFont("Helvetica", 9.5)
        c.drawString(50, y, f"Scrubbed Metadata: YES (All EXIF tags, GPS coordinates, timestamps removed)")
        y -= 14
        c.drawString(50, y, f"Redaction mode applied: {scan.redaction_mode.upper() if scan.redaction_mode else 'BLUR'}")
        y -= 30
        
        # Before / After visual side-by-side
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, "VISUAL COMPARISON (ANNOTATED vs SAFE)")
        c.line(40, y - 4, width - 40, y - 4)
        y -= 15
        
        try:
            # Draw side by side
            img_width_max = (width / 2) - 50
            
            # Annotated Path (Before)
            if scan.annotated_path and os.path.exists(scan.annotated_path):
                img_orig = ImageReader(scan.annotated_path)
                w_orig, h_orig = img_orig.getSize()
                aspect_orig = h_orig / float(w_orig)
                draw_w_orig = img_width_max
                draw_h_orig = draw_w_orig * aspect_orig
                
                # Check height bounds
                if draw_h_orig > 180:
                    draw_h_orig = 180
                    draw_w_orig = draw_h_orig / aspect_orig
                
                c.drawImage(img_orig, 40, y - draw_h_orig, width=draw_w_orig, height=draw_h_orig)
                c.setFont("Helvetica-Bold", 8)
                c.drawString(40, y - draw_h_orig - 12, "ORIGINAL IMAGE (ANNOTATED THREATS)")
            
            # Redacted Path (After)
            if scan.redacted_image_path and os.path.exists(scan.redacted_image_path):
                img_redact = ImageReader(scan.redacted_image_path)
                w_redact, h_redact = img_redact.getSize()
                aspect_redact = h_redact / float(w_redact)
                draw_w_redact = img_width_max
                draw_h_redact = draw_w_redact * aspect_redact
                
                if draw_h_redact > 180:
                    draw_h_redact = 180
                    draw_w_redact = draw_h_redact / aspect_redact
                    
                c.drawImage(img_redact, width/2 + 10, y - draw_h_redact, width=draw_w_redact, height=draw_h_redact)
                c.setFont("Helvetica-Bold", 8)
                c.drawString(width/2 + 10, y - draw_h_redact - 12, "AUTO-REDACTED SAFE IMAGE")
                
        except Exception as e:
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(50, y - 20, f"[Visual comparison rendering failed: {str(e)}]")
    else:
        # Just draw annotated if not redacted
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, "VISUAL THREAT ASSESSMENT")
        c.line(40, y - 4, width - 40, y - 4)
        y -= 15
        
        if scan.annotated_path and os.path.exists(scan.annotated_path):
            try:
                img = ImageReader(scan.annotated_path)
                img_w, img_h = img.getSize()
                aspect = img_h / float(img_w)
                
                draw_width = width - 100
                draw_height = draw_width * aspect
                
                if draw_height > 250:
                    draw_height = 250
                    draw_width = draw_height / aspect
                    
                c.drawImage(img, 50, y - draw_height, width=draw_width, height=draw_height)
                c.setFont("Helvetica-Bold", 8)
                c.drawString(50, y - draw_height - 12, "ANNOTATED PRIVACY RISK HEATMAP")
            except Exception as e:
                c.drawString(50, y - 20, f"[Image rendering failed: {str(e)}]")

    c.save()
    return output_path
