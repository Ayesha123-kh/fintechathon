"""Bank-alert email parsing, end to end through app.services.gmail.parse_email (regex first, live LLM fallback).
Inputs: every template the app's own test-alert generator can produce, plus OTP / promo emails and a few free-form
alerts in other banks' styles. Writes results/ingest.json."""
import asyncio, json, random, sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS

from app.services import gmail, test_alerts

HERE = Path(sys.argv[1])
results = []
def check(name, ok, detail="", warn=False):
    results.append({"section": "Bank-alert email parsing", "name": name, "status": "PASS" if ok else ("WARN" if warn else "FAIL"), "detail": str(detail)[:300]})
    print(results[-1]["status"], name, "" if ok else f"— {detail}")

async def main():
    random.seed(7)
    bank = NS(name="Habib Bank Limited", short_name="HBL")
    account = NS(balance=Decimal("85000.00"), last4="4321")
    card = NS(network="visa", card_type="debit")
    bad = []
    for merchant, low, high in test_alerts.DEBITS + test_alerts.CREDITS:
        direction = "debit" if (merchant, low, high) in test_alerts.DEBITS else "credit"
        test_alerts.random.choice = lambda seq, m=(merchant, low, high): m  # pin the template
        subject, text, _, meta = test_alerts.build_alert(bank, account, card, direction)
        got = await gmail.parse_email(subject, text)
        want_bal = float(account.balance) + (meta["amount"] if direction == "credit" else -meta["amount"])
        problems = []
        if not got: problems.append("not parsed")
        else:
            if abs(got["amount"] - meta["amount"]) > 0.01: problems.append(f"amount {got['amount']} != {meta['amount']}")
            if got["direction"] != direction: problems.append(f"direction {got['direction']}")
            if got.get("balance_after") is None or abs(got["balance_after"] - want_bal) > 0.01: problems.append(f"balance {got.get('balance_after')} != {want_bal}")
            name = (got.get("merchant") or "").lower()
            key = merchant.replace("IBFT FROM ", "").replace("RAAST TRANSFER FROM ", "").replace("REFUND ", "").split()[0].lower()
            if key not in name: problems.append(f"merchant {got.get('merchant')!r} for {merchant!r}")
            if got.get("last4") != "4321": problems.append(f"last4 {got.get('last4')}")
        if problems: bad.append(f"{merchant}: {', '.join(problems)}")
    n = len(test_alerts.DEBITS) + len(test_alerts.CREDITS)
    check(f"All {n} test-alert templates parse to the right amount, direction, merchant, balance and account", not bad, "; ".join(bad))

    otp = await gmail.parse_email("Your OTP for HBL Mobile", "Your one-time password is 482913. Do not share it.")
    check("OTP emails are never turned into transactions", otp is None, otp)

    samples = [
        ("Debit card purchase", "Dear Customer, You have made a purchase of PKR 2,450.00 at FOODPANDA PK using Debit Card ending 1234 on 18-Oct-2026. Avl Bal: PKR 45,210.33",
         {"amount": 2450.0, "direction": "debit", "merchant": "foodpanda", "balance_after": 45210.33}),
        ("JazzCash", "You have sent Rs. 1500 to Ali Khan via JazzCash Mobile Account. TID: 12345678. Your new balance is Rs. 3,250.00",
         {"amount": 1500.0, "direction": "debit", "merchant": "ali", "balance_after": 3250.0}),
        ("Meezan Bank Credit Alert", "Your A/C XX7788 has been credited with PKR 150,000.00 on 01-OCT-26 against SALARY ACME PVT LTD. Avail Bal PKR 210,500.00",
         {"amount": 150000.0, "direction": "credit", "merchant": "acme", "balance_after": 210500.0}),
        ("Cash Withdrawal Alert", "PKR 10,000.00 has been withdrawn from your A/C ****5678 at ATM UBL SADDAR KARACHI on 19-Oct-2026 14:05. Available balance PKR 31,000.00",
         {"amount": 10000.0, "direction": "debit", "balance_after": 31000.0}),
    ]
    for subject, text, want in samples:
        got = await gmail.parse_email(subject, text) or {}
        problems = [f"{k}={got.get(k)!r}" for k, v in want.items()
                    if (k == "merchant" and v not in (got.get(k) or "").lower()) or (k != "merchant" and got.get(k) != v)]
        check(f"Free-form alert '{subject}' is understood", not problems and got.get("is_transaction", True), f"wanted {want}, got {got}" if problems else got, warn=True)

    promo = await gmail.parse_email("Weekend deal: 20% off at KFC with HBL cards", "Enjoy 20% off at KFC every Saturday and Sunday when you pay with your HBL Debit Card. Max discount PKR 1,000. T&Cs apply.")
    check("Promotional emails aren't recorded as spending", not promo or not promo.get("is_transaction"), promo, warn=True)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "ingest.json").write_text(json.dumps(results, indent=1))

asyncio.run(main())
