"""
routes/receipts.py
Receipt scanning:
  POST /scan-receipt
  Accepts a multipart image upload, sends it to Google Cloud Vision TEXT_DETECTION,
  parses the response into a pre-filled transaction dict, and returns JSON.
  The frontend shows this to the user for review before they save it.
"""

import os
import re
import base64
import requests

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

receipts_bp = Blueprint("receipts", __name__)

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


@receipts_bp.route("/scan-receipt", methods=["POST"])
@login_required
def scan_receipt():
    api_key = os.environ.get("VISION_API_KEY")
    if not api_key:
        return jsonify({"error": "Receipt scanning is not configured on this server."}), 503

    if "image" not in request.files:
        return jsonify({"error": "No image file provided. Send a multipart field named 'image'."}), 400

    image_file = request.files["image"]
    image_bytes = image_file.read(MAX_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return jsonify({"error": "Image too large. Maximum size is 10 MB."}), 413

    # Determine MIME type
    content_type = image_file.content_type or "image/jpeg"
    if content_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        content_type = "image/jpeg"

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Call Vision API
    payload = {
        "requests": [{
            "image": {"content": b64_image},
            "features": [{"type": "TEXT_DETECTION", "maxResults": 1}],
            "imageContext": {"languageHints": ["en"]},
        }]
    }

    try:
        resp = requests.post(
            VISION_API_URL,
            params={"key": api_key},
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.Timeout:
        return jsonify({"error": "Vision API timed out. Please try again."}), 504
    except requests.HTTPError as e:
        return jsonify({"error": f"Vision API error: {e.response.status_code}"}), 502
    except requests.RequestException as e:
        return jsonify({"error": "Could not reach Vision API."}), 502

    vision_data = resp.json()

    try:
        raw_text = vision_data["responses"][0]["fullTextAnnotation"]["text"]
    except (KeyError, IndexError):
        return jsonify({
            "error": "No text detected in the image. Try a clearer photo.",
            "parsed": None,
        }), 200

    parsed = _parse_receipt_text(raw_text)
    return jsonify({"raw_text": raw_text, "parsed": parsed})


# ── Receipt text parser ──────────────────────────────────────────────────────

def _parse_receipt_text(text):
    """
    Heuristic parser for receipt OCR output.
    Returns a dict shaped like a transaction pre-fill:
    {
        "description": str,   # vendor name or first meaningful line
        "amount":      float, # best guess at the total
        "line_items":  [ {"name": str, "amount": float}, ... ]
    }
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return {"description": "", "amount": 0.0, "line_items": []}

    # Vendor name: usually the first non-trivial line
    description = _extract_vendor(lines)

    # Find all dollar amounts in the receipt
    amount_pattern = re.compile(r"\$?\s*(\d{1,6}[.,]\d{2})\b")
    all_amounts = []
    line_items = []

    for line in lines:
        matches = amount_pattern.findall(line)
        for m in matches:
            value = float(m.replace(",", ""))
            all_amounts.append(value)
            # Treat lines that look like "Item name ... $X.XX" as line items
            item_name = amount_pattern.sub("", line).strip().strip("-").strip()
            if item_name and 0.01 < value < 10000:
                line_items.append({"name": item_name, "amount": value})

    # The total is usually the largest amount, or a line explicitly labelled
    total = _find_total(lines, all_amounts)

    # Deduplicate line items by amount to avoid noise
    seen_amounts = set()
    unique_items = []
    for item in line_items:
        key = (item["name"].lower()[:20], item["amount"])
        if key not in seen_amounts:
            seen_amounts.add(key)
            unique_items.append(item)

    return {
        "description": description,
        "amount": total,
        "line_items": unique_items[:20],  # cap at 20 items for display
    }


def _extract_vendor(lines):
    """Return a best-guess vendor name from the top of the receipt."""
    skip_words = {"receipt", "welcome", "thank", "you", "invoice", "date", "time", "order"}
    for line in lines[:5]:
        words = line.lower().split()
        if not words:
            continue
        if any(w in skip_words for w in words):
            continue
        if re.search(r"\d{1,2}[/:]\d{2}", line):  # looks like a time
            continue
        if len(line) > 2:
            return line
    return lines[0] if lines else ""


def _find_total(lines, all_amounts):
    """
    Try to find the grand total from labelled lines first,
    then fall back to the largest amount seen.
    """
    total_pattern = re.compile(
        r"(total|grand\s*total|amount\s*due|balance\s*due|total\s*due)[^\d]*(\d{1,6}[.,]\d{2})",
        re.IGNORECASE,
    )
    for line in reversed(lines):  # totals usually appear near the bottom
        m = total_pattern.search(line)
        if m:
            try:
                return float(m.group(2).replace(",", ""))
            except ValueError:
                pass

    # Fallback: largest dollar amount on the receipt
    if all_amounts:
        return max(all_amounts)
    return 0.0