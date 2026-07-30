"""
sms_client.py

Sends SMS alerts via Africa's Talking when a complaint is marked resolved.
Falls back to a printed mock message if credentials are missing or the
send fails, so the rest of the app never breaks because of SMS issues.
"""

import os
from dotenv import load_dotenv

load_dotenv()

AT_USERNAME = os.getenv("AT_USERNAME")
AT_API_KEY = os.getenv("AT_API_KEY")

_sms_service = None


def _get_sms_service():
    global _sms_service
    if _sms_service is not None:
        return _sms_service
    if not AT_USERNAME or not AT_API_KEY:
        return None
    try:
        import africastalking
        africastalking.initialize(AT_USERNAME, AT_API_KEY)
        _sms_service = africastalking.SMS
        return _sms_service
    except Exception as e:
        print(f"[sms_client] Could not init Africa's Talking, SMS will be mocked: {e}")
        return None


def _normalize_phone(phone: str) -> str:
    """Converts common Kenyan phone formats to E.164 (+254...)."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+254"):
        return phone
    if phone.startswith("254"):
        return "+" + phone
    if phone.startswith("0"):
        return "+254" + phone[1:]
    return phone


def send_resolution_alert(phone: str, category: str, ward: str) -> bool:
    """
    Sends an SMS telling the citizen their complaint was resolved.
    Returns True if a real send was attempted, False if mocked (no phone
    or no credentials).
    """
    if not phone or not phone.strip():
        print("[sms_client] No phone number on file for this complaint — skipping SMS.")
        return False

    message = (
        f"sauti-yetu: Your {category} report in {ward} ward has been marked "
        f"resolved. Reply on the portal if this isn't fixed."
    )
    to = _normalize_phone(phone)

    service = _get_sms_service()
    if service is None:
        print(f"[sms_client] MOCK SMS to {to}: {message}")
        return False

    try:
        response = service.send(message, [to])
        print(f"[sms_client] SMS sent to {to}: {response}")
        return True
    except Exception as e:
        print(f"[sms_client] Live SMS send failed, falling back to mock: {e}")
        print(f"[sms_client] MOCK SMS to {to}: {message}")
        return False