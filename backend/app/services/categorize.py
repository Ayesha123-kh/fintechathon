"""Spending categories: merchant directory first, keyword rules second, LLM last."""

import re

from app.core.llm import complete_json

RULES: list[tuple[str, str]] = [
    (r"\b(kfc|mcdonald|pizza|burger|hardee|domino|subway|cafe|coffee|restaurant|dhaba|biryani|bakery|foodpanda|"
     r"food ?panda|cheezious|savour|nando|tea|chai|kitchen|grill|bbq|karahi)\b", "food"),
    (r"\b(imtiaz|carrefour|naheed|metro cash|al[- ]?fatah|chase up|hyperstar|grocery|mart|super ?market|"
     r"utility store|green valley|springs|panda mart|pandamart)\b", "grocery"),
    (r"\b(pso|shell|total ?parco|aramco|attock|byco|go petroleum|hascol|petrol|fuel|filling station|cng)\b", "fuel"),
    (r"\b(pharma|pharmacy|watson|servaid|clinic|hospital|lab|chughtai|shaukat khanum|aga khan|medical|"
     r"dawaai|sehat|marham)\b", "medicine"),
    (r"\b(careem|uber|indrive|in drive|bykea|yango|daewoo|faisal movers|railway|parking|toll|motorway)\b",
     "transport"),
    (r"\b(k-?electric|lesco|iesco|fesco|mepco|pesco|hesco|ssgc|sngpl|water board|wasa|electricity|gas bill|"
     r"bill payment)\b", "utilities"),
    (r"\b(jazz|zong|telenor|ufone|ptcl|nayatel|stormfiber|storm fiber|wateen|internet|mobile load|mobile bundle|top ?up|topped up)\b",
     "telecom"),
    (r"\b(khaadi|sapphire|outfitters|bata|servis|daraz|gul ahmed|alkaram|j\.|junaid jamshed|limelight|"
     r"breakout|ndure|stylo|zellbury|bonanza|nishat|shopping|mall)\b", "shopping"),
    (r"\b(cinema|cinepax|nueplex|netflix|spotify|youtube|steam|playstation|amazon prime|tapmad)\b",
     "entertainment"),
    (r"\b(school|university|college|academy|tuition|school fee|tuition fee|admission fee|beaconhouse|city school|lums|nust|fast)\b", "education"),
    (r"\b(pia|airblue|serene|airsial|fly jinnah|booking\.com|hotel|airbnb|travel)\b", "travel"),
    (r"\b(rent|landlord|maintenance charges|society)\b", "housing"),
    (r"\b(edhi|chhipa|saylani|akhuwat|shaukat khanum donation|donation|zakat|sadqa|sadqah|charity|"
     r"alkhidmat)\b", "charity"),
    (r"\b(salary|payroll|stipend|profit credit|dividend)\b", "income"),
    (r"\b(ibft|raast|fund transfer|funds transfer|transfer to|transfer from|1link)\b", "transfer"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), c) for p, c in RULES]
VALID = {"food", "grocery", "fuel", "medicine", "transport", "utilities", "shopping", "entertainment",
         "education", "travel", "housing", "telecom", "charity", "transfer", "income", "misc"}


_MEANINGS = """food: restaurants, cafes, food delivery
grocery: supermarkets, daily groceries
fuel: petrol pumps
medicine: pharmacies, clinics, hospitals, labs
transport: ride hailing, buses, parking, tolls
utilities: electricity, gas, water bills
telecom: mobile load, mobile bundles, internet
shopping: clothes, shoes, online stores (Daraz, Shopify stores), electronics
entertainment: streaming, cinema, games, app and software subscriptions
education: schools, universities, courses, tuition
travel: airlines, hotels, travel bookings
housing: rent, society maintenance
charity: donations, zakat, sadqah
transfer: money sent to or received from a person (a personal name) or another own account
income: ONLY salary, business income or profit paid to the person
misc: anything else"""


def rule_category(text: str) -> str | None:
    for regex, cat in _COMPILED:
        if regex.search(text):
            return cat
    return None


async def llm_category(merchant: str, description: str = "") -> tuple[str, str | None]:
    """Returns (category, subcategory such as 'fast food restaurant')."""
    result = await complete_json(
        "You classify a payment's merchant or payee for a Pakistani budgeting app. Categories:\n" + _MEANINGS +
        '\nReply as JSON: {"category": one of the names above, "subcategory": short type like '
        '"fast food restaurant", "software subscription", "online store", "pharmacy" or null}',
        f"Merchant / payee: {merchant}\nDetails: {description}",
        max_tokens=100,
    )
    if not result:
        return "misc", None
    cat = str(result.get("category", "misc")).lower()
    sub = result.get("subcategory")
    return (cat if cat in VALID else "misc"), (str(sub)[:80] if sub else None)


async def categorize(merchant: str, description: str = "") -> tuple[str, str | None]:
    cat = rule_category(f"{merchant} {description}")
    if cat:
        return cat, None
    if not merchant.strip():
        return "misc", None
    return await llm_category(merchant, description)
