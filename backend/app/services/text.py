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


# What a transaction is when there is no shop or person: shown as its heading.
_KINDS = [
    (re.compile(r"cash withdrawal|\batm\b", re.I), "Cash withdrawal"),
    (re.compile(r"mobile bundle|mobile package", re.I), "Mobile bundle"),
    (re.compile(r"top(?:ped)?[ -]?up|mobile (?:balance|load)|easyload", re.I), "Mobile top-up"),
    (re.compile(r"\bfee\b", re.I), "Bank fee"),
    (re.compile(r"\b(?:bill|utility)\b", re.I), "Bill payment"),
    (re.compile(r"\bprofit\b", re.I), "Profit credited"),
]


def transaction_kind(subject: str) -> str:
    """A heading for transactions without a shop or person ("Cash withdrawal", "Mobile top-up" ...)."""
    return next((label for rx, label in _KINDS if rx.search(subject or "")), "")


def transaction_title(merchant: str, description: str) -> str:
    """What a transaction is called in lists: the shop or person, else what kind of transaction it was."""
    return merchant or transaction_kind(description)
