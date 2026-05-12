"""
Reusable form validation helpers for UniShare.

Each validator returns (value, error):
    - value: cleaned value (stripped, coerced to correct type, or None)
    - error: error message string, or None if valid

Routes use these together with a flat errors dict to collect all
problems in one pass, then flash them and re-render the form with
the user's previous inputs preserved.
"""

import re

# ─────────────────────────────────────────────────────────────
# Primitive validators
# ─────────────────────────────────────────────────────────────

def validate_required_text(raw, field_label, min_len=1, max_len=200):
    """Required string field. Strips whitespace. Enforces length."""
    value = (raw or '').strip()
    if len(value) < min_len:
        return value, f"{field_label} is required."
    if len(value) > max_len:
        return value, f"{field_label} must be {max_len} characters or fewer."
    return value, None


def validate_optional_text(raw, field_label, max_len=1000):
    """Optional string. Empty is OK but length still enforced."""
    value = (raw or '').strip()
    if len(value) > max_len:
        return value, f"{field_label} must be {max_len} characters or fewer."
    return value, None


def validate_unit_code(raw):
    """
    Unit code must look like 'CITS3403' or 'MATH1001'.
    We accept 2-4 letters followed by 3-5 digits, case insensitive.
    """
    value = (raw or '').strip().upper()
    if not value:
        return value, "Unit code is required."
    if not re.match(r'^[A-Z]{2,4}\d{3,5}$', value):
        return value, "Unit code must look like 'CITS3403' (2-4 letters + 3-5 digits)."
    return value, None


def validate_price(raw, field_label='Price', allow_zero=True, max_value=100000):
    """Non-negative number. Rejects empty, negative, and non-numeric."""
    raw_str = (raw or '').strip()
    if not raw_str:
        return None, f"{field_label} is required."
    try:
        value = float(raw_str)
    except ValueError:
        return None, f"{field_label} must be a number."
    if value < 0:
        return None, f"{field_label} cannot be negative."
    if value == 0 and not allow_zero:
        return None, f"{field_label} must be greater than 0."
    if value > max_value:
        return None, f"{field_label} cannot exceed {max_value}."
    return round(value, 2), None


def validate_positive_int(raw, field_label, min_value=1, max_value=1000):
    """Positive integer within range."""
    raw_str = (raw or '').strip()
    if not raw_str:
        return None, f"{field_label} is required."
    try:
        value = int(raw_str)
    except ValueError:
        return None, f"{field_label} must be a whole number."
    if value < min_value:
        return None, f"{field_label} must be at least {min_value}."
    if value > max_value:
        return None, f"{field_label} must be at most {max_value}."
    return value, None


def validate_email(raw):
    """Loose email format check. Good enough for a student project."""
    value = (raw or '').strip().lower()
    if not value:
        return value, "Email is required."
    if len(value) > 254:
        return value, "Email is too long."
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', value):
        return value, "Please enter a valid email address."
    return value, None


def validate_password(raw, min_len=8, max_len=128):
    """Password length check. We don't force character classes."""
    value = raw or ''
    if not value:
        return value, "Password is required."
    if len(value) < min_len:
        return value, f"Password must be at least {min_len} characters."
    if len(value) > max_len:
        return value, f"Password must be {max_len} characters or fewer."
    return value, None


def validate_session_date(raw):
    """
    Datetime-local input arrives as 'YYYY-MM-DDTHH:MM'.
    We just check it's non-empty and roughly that shape.
    """
    value = (raw or '').strip()
    if not value:
        return value, "Session date & time is required."
    if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', value):
        return value, "Session date must be a valid date and time."
    return value, None


def validate_choice(raw, field_label, allowed):
    """Value must be one of the allowed options."""
    value = (raw or '').strip()
    if not value:
        return value, f"{field_label} is required."
    if value not in allowed:
        return value, f"{field_label} must be one of: {', '.join(allowed)}."
    return value, None


# ─────────────────────────────────────────────────────────────
# Allowed choices (kept here so templates and routes agree)
# ─────────────────────────────────────────────────────────────

LISTING_CONDITIONS = ['New', 'Like New', 'Good', 'Fair', 'Poor']
