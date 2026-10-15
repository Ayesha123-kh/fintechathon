import re

_SUFFIXES = re.compile(
    r"\b(pvt|private|ltd|limited|pakistan|pk|co|inc|llc|store|restaurant|outlet|branch|smc)\b\.?", re.IGNORECASE
)


def normalize_name(name: str) -> str:
    """Normalize a merchant name so 'KFC PAKISTAN (PVT) LTD - DHA' and 'kfc' match."""
    s = name.lower()
    s = re.sub(r"[\(\)\[\]'’`.,]", " ", s)
    s = re.split(r"\s[-–|@#*]\s|\s\d{3,}", s)[0]
    s = _SUFFIXES.sub(" ", s)
    s = re.sub(r"[^a-z0-9&+ ]", " ", s)
    return re.sub(r"\s+", " ", s).strip() or name.lower().strip()
