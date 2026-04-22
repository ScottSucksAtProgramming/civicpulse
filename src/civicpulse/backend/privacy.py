import re

REDACTION_TOKEN = "[REDACTED]"

_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?<!\w)(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(
        r"\b\d{1,6}\s+(?:[A-Z][a-zA-Z]*\s+){1,5}"
        r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|"
        r"Drive|Dr\.?|Lane|Ln\.?|Court|Ct\.?|Place|Pl\.?|Highway|Hwy\.?|"
        r"Parkway|Pkwy\.?|Way|Circle|Cir\.?)\b"
    ),
    re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr)\.\s+[A-Z][a-zA-Z]+\b"),
]


def redact(text: str) -> str:
    redacted = text
    for pattern in _PATTERNS:
        redacted = pattern.sub(REDACTION_TOKEN, redacted)
    return redacted
