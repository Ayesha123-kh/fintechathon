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


_UNREACHABLE = ("fetch failed", "timeout", "timed out", "econn", "enotfound", "unreachable", "network")


def assistant_failure_message(raw: str) -> str:
    """What the person reads when an assistant turn fails: a refused step is not the same as a model that cannot be reached."""
    low = (raw or "").lower()
    if "tool operation" in low or "denied" in low:
        return ("Your assistant couldn't finish that just now: one of the steps it tried was rejected, so nothing "
                "may have been saved. Please check the details (names, amounts, dates) and try again.")
    if any(word in low for word in _UNREACHABLE):
        return "Your assistant couldn't reply just now (the AI service is unreachable). Please try again in a moment."
    return "Your assistant couldn't reply just now. Please try again in a moment."
