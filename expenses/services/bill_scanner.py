import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from google import genai
from google.genai import types

from expenses.models import Expense, Category, User

ALLOWED_PAYMENT_METHODS = {"Cash", "Credit Card", "Debit Card", "UPI", "NetBanking"}


def _normalize_amount(raw_amount):
    if raw_amount in (None, ""):
        return ""
    if isinstance(raw_amount, (int, float)):
        return f"{Decimal(str(raw_amount)):.2f}"

    cleaned = str(raw_amount).strip().replace(",", "")
    # Keep only digits and one decimal point
    filtered = "".join(ch for ch in cleaned if ch.isdigit() or ch == ".")
    if not filtered:
        return ""
    try:
        return f"{Decimal(filtered):.2f}"
    except (InvalidOperation, ValueError):
        return ""


def _normalize_date(raw_date):
    """
    Normalize date to YYYY-MM-DD for HTML date input compatibility.
    """
    if not raw_date:
        return ""

    date_str = str(raw_date).strip()
    known_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%Y/%m/%d",
    ]
    for fmt in known_formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _normalize_payment_method(raw_method):
    if not raw_method:
        return ""
    method = str(raw_method).strip()
    mapping = {
        "credit": "Credit Card",
        "credit card": "Credit Card",
        "debit": "Debit Card",
        "debit card": "Debit Card",
        "upi": "UPI",
        "netbanking": "NetBanking",
        "net banking": "NetBanking",
        "cash": "Cash",
    }
    normalized = mapping.get(method.lower(), method)
    return normalized if normalized in ALLOWED_PAYMENT_METHODS else ""


def _extract_json_payload(text):
    """
    Extract JSON from model output. Handles plain JSON and markdown code fences.
    """
    if not text:
        return {}

    payload = text.strip()

    if payload.startswith("```"):
        payload = payload.strip("`")
        if payload.lower().startswith("json"):
            payload = payload[4:].strip()

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        start = payload.find("{")
        end = payload.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = payload[start : end + 1]
            return json.loads(snippet)
        raise


def scan_bill_image(image_bytes, mime_type, categories):
    """
    Scan a bill image and return normalized fields for expense form autofill.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return {
            "success": False,
            "error": "Gemini API key is not configured.",
            "data": {},
            "warnings": ["Set GEMINI_API_KEY in your environment."],
        }

    # Payment methods & categories are dynamic from database.
    payment_methods = Expense.PAYMENT_OPTIONS
    
    print("categories", categories)
    print("payment_methods", payment_methods)
    # categories <QuerySet [{'name': 'Bills', 'id': 4}, {'name': 'Entertainment', 'id': 5}, {'name': 'Food', 'id': 1}, {'name': 'Others', 'id': 6}, {'name': 'Shopping', 'id': 3}, {'name': 'Travel', 'id': 2}]>
    # payment_methods [('Cash', 'Cash'), ('Credit Card', 'Credit Card'), ('Debit Card', 'Debit Card'), ('UPI', 'UPI'), ('NetBanking', 'NetBanking')]

    # add categories and payment methods to the prompt, so can get the correct category id and payment method name
    prompt = f"""
    Extract bill details from this image. 
    Return ONLY valid JSON with these keys exactly: amount, date, description, merchant_name, payment_method, category_suggestion, currency, confidence. 
    Rules: 
    1) date must be YYYY-MM-DD if identifiable else empty string. It could be ordered date else the date of the bill or the date of the delivery of the product or service. 
    2) payment_method must be one of: {payment_methods}. 
    3) amount should be numeric string without currency symbols, else empty string. 
    4) description should be a short useful text from merchant + top items. 
    5) confidence should be a float 0-1.
    6) category_suggestion must be one of: {categories}.
    """
    # prompt = (
    #     "Extract bill details from this image. "
    #     "Return ONLY valid JSON with these keys exactly: "
    #     "amount, date, description, merchant_name, payment_method, category_suggestion, currency, confidence. "
    #     "Rules: "
    #     "1) date must be YYYY-MM-DD if identifiable else empty string. It could be ordered date else the date of the bill or the date of the delivery of the product or service. "
    #     "2) payment_method must be one of: Cash, Credit Card, Debit Card, UPI, NetBanking, else empty string. "
    #     "3) amount should be numeric string without currency symbols, else empty string. "
    #     "4) description should be a short useful text from merchant + top items. "
    #     "5) confidence should be a float 0-1."
    # )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                ),
                prompt,
            ],
        )
        raw_text = response.text or ""
    except Exception as exc:
        return {
            "success": False,
            "error": f"Bill scan request failed: {exc}",
            "data": {},
            "warnings": [],
        }

    try:
        parsed = _extract_json_payload(raw_text)
        print("raw_text", raw_text)
    except Exception:
        return {
            "success": False,
            "error": "Could not parse AI response for bill details.",
            "data": {},
            "warnings": ["Try another clearer image."],
        }

    amount = _normalize_amount(parsed.get("amount"))
    date_value = _normalize_date(parsed.get("date"))
    merchant = (parsed.get("merchant_name") or "").strip()
    description = (parsed.get("description") or "").strip()
    payment_method = _normalize_payment_method(parsed.get("payment_method"))
    category_suggestion = (parsed.get("category_suggestion") or "").strip()
    currency = (parsed.get("currency") or "").strip() or "INR"
    confidence = parsed.get("confidence")

    if not description and merchant:
        description = merchant

    data = {
        "amount": amount,
        "date": date_value,
        "description": description,
        "merchant_name": merchant,
        "payment_method": payment_method,
        "category_suggestion": category_suggestion,
        "currency": currency,
        "confidence": confidence,
    }

    warnings = []
    if not amount:
        warnings.append("Amount could not be confidently extracted.")
    if not date_value:
        warnings.append("Date could not be confidently extracted.")

    return {
        "success": True,
        "error": "",
        "data": data,
        "warnings": warnings,
    }
