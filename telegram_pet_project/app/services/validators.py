import re

PHONE_RE = re.compile(r'^\+?[0-9\-\s()]{10,20}$')


def validate_phone(phone: str) -> bool:
    return bool(PHONE_RE.match(phone.strip()))


def normalize_phone(phone: str) -> str:
    return re.sub(r'\s+', ' ', phone.strip())
