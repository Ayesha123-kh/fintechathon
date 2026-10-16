"""TEMPORARY demo data: a long-time user with ~4 months of history, plus a demo admin.

Accounts created:
  demo@bachat.pk   / demo12345   (user, onboarded, opted in to investments)
  admin@bachat.pk  / admin12345  (admin)

Remove it with:  alembic downgrade 0001
Skipped automatically when ENVIRONMENT=production.

Revision ID: 0002
Revises: 0001
"""

import random
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Session

from alembic import op
from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    Bank,
    BankAccount,
    Card,
    ChatMessage,
    Deal,
    DealRedemption,
    Goal,
    MarketSignal,
    Merchant,
    Notification,
    Plan,
    ResearchNote,
    SavingsEntry,
    Subscription,
    Transaction,
    User,
    UserFact,
    UserFollow,
    UserProfile,
)
from app.services.deals import deal_fingerprint
from app.services.text import normalize_name

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_USER = "demo@bachat.pk"
DEMO_ADMIN = "admin@bachat.pk"
DEMO_TAG = "[demo]"
DEMO_BOT = "demo-seed"


def _skip() -> bool:
    return settings.environment.lower() == "production"


def _system(conn) -> None:
    # Tables use FORCE ROW LEVEL SECURITY, which also binds the owner running migrations.
    conn.execute(sa.text("SELECT set_config('app.role', 'system', true)"))


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC) - timedelta(hours=5)  # PKT -> UTC


def upgrade() -> None:
    if _skip():
        return
    conn = op.get_bind()
    _system(conn)
    s = Session(bind=conn)
    rnd = random.Random(42)
    today = date.today()
    now = datetime.now(UTC)

    # ------------------------------------------------------------------ users
    user = User(email=DEMO_USER, password_hash=hash_password("demo12345"), full_name="Osama",
                role="user", email_verified=True, onboarding_completed=True, last_login_at=now - timedelta(days=1))
    admin = User(email=DEMO_ADMIN, password_hash=hash_password("admin12345"), full_name="Bachat Admin",
                 role="admin", email_verified=True, onboarding_completed=True)
    s.add_all([user, admin])
    s.flush()
    uid = user.id
    s.add(UserProfile(user_id=admin.id))
    s.add(UserProfile(
        user_id=uid, monthly_income=150000, salary_day=1, city="Karachi", language="en",
        savings_mode="percent", savings_value=25, goal_split_mode="deadline",
        sadqah_opt_in=True, sadqah_mode="fixed", sadqah_value=2000, sadqah_frequency="friday",
        investment_opt_in=True, investment_disclaimer_accepted_at=now - timedelta(days=100),
        risk_profile="moderate", preferred_places=["KFC", "Imtiaz Super Market", "Khaadi", "Foodpanda"],
        onboarding_state={"sadqah_asked": True, "investment_asked": True},
    ))
    plus = s.scalar(sa.select(Plan).where(Plan.code == "plus"))
    if plus:
        s.add(Subscription(user_id=uid, plan_id=plus.id, status="active", current_period_end=now + timedelta(days=14)))

    banks = {b.short_name: b for b in s.scalars(sa.select(Bank))}
    meezan = BankAccount(user_id=uid, bank_id=banks["Meezan"].id, nickname="Salary account", account_type="current",
                         last4="4821", balance=0, is_primary=True)
    hbl = BankAccount(user_id=uid, bank_id=banks["HBL"].id, nickname="Savings", account_type="savings",
                      last4="0937", balance=0)
    jazz = BankAccount(user_id=uid, bank_id=banks["JazzCash"].id, nickname="JazzCash", account_type="wallet",
                       last4="5512", balance=0)
    s.add_all([meezan, hbl, jazz])
    s.flush()
    s.add_all([
        Card(user_id=uid, bank_id=banks["Meezan"].id, account_id=meezan.id, network="visa", tier="platinum",
             card_type="debit", label="Visa Platinum Debit Card of Meezan Bank", last4="4821"),
        Card(user_id=uid, bank_id=banks["HBL"].id, account_id=hbl.id, network="mastercard", tier="gold",
             card_type="credit", label="Mastercard Gold Credit Card of Habib Bank Limited", last4="7703"),
    ])

    # ------------------------------------------------------------------ goals
    car = Goal(user_id=uid, name="Car (Honda City)", target_amount=1800000, deadline=date(today.year + 1, 6, 30),
               priority=2, icon="car", notes="Down payment plus registration.")
    umrah = Goal(user_id=uid, name="Umrah with parents", target_amount=600000, deadline=date(today.year + 1, 2, 28),
                 priority=1, icon="heart")
    emergency = Goal(user_id=uid, name="Emergency fund", target_amount=450000, priority=3, icon="umbrella")
    laptop = Goal(user_id=uid, name="New laptop", target_amount=250000, priority=4, icon="laptop", status="completed")
    s.add_all([car, umrah, emergency, laptop])
    s.flush()

    # ------------------------------------------------------------------ merchants
    merchant_rows = [
        ("KFC Pakistan", "food", "fast food restaurant"), ("Foodpanda", "food", "food delivery"),
        ("Cheezious", "food", "fast food restaurant"), ("Imtiaz Super Market", "grocery", "supermarket"),
        ("Carrefour Pakistan", "grocery", "supermarket"), ("Naheed Supermarket", "grocery", "supermarket"),
        ("PSO", "fuel", "fuel station"), ("Shell Pakistan", "fuel", "fuel station"),
        ("D. Watson", "medicine", "pharmacy"), ("Careem", "transport", "ride hailing"),
        ("Khaadi", "shopping", "women's apparel"), ("Daraz", "shopping", "online marketplace"),
        ("Bata Pakistan", "shopping", "footwear"), ("Netflix", "entertainment", "streaming"),
        ("Cinepax", "entertainment", "cinema"), ("K-Electric", "utilities", "electricity bill"),
        ("SSGC", "utilities", "gas bill"), ("Jazz", "telecom", "mobile load"),
        ("StormFiber", "telecom", "internet"), ("Outfitters", "shopping", "men's and women's apparel"),
    ]
    for name, cat, sub in merchant_rows:
        conn.execute(sa.text(
            "INSERT INTO merchants (id, name, normalized_name, category_slug, subcategory, cities, sources, "
            "sources_status, seen_in_transactions) VALUES (:id, :n, :nn, :c, :sub, '[\"Karachi\"]', '{}', 'pending', 0) "
            "ON CONFLICT (normalized_name) DO NOTHING"),
            {"id": uuid.uuid4(), "n": name, "nn": normalize_name(name), "c": cat, "sub": sub})
    merchants = {m.normalized_name: m for m in s.scalars(sa.select(Merchant))}

    def merchant(name: str) -> Merchant:
        return merchants[normalize_name(name)]

    # ------------------------------------------------------------------ transactions (last ~4 months)
    balances = {meezan.id: Decimal(95000), hbl.id: Decimal(430000), jazz.id: Decimal(3500)}
    txs: list[Transaction] = []

    def tx(day: date, hour: int, amount, direction: str, account: BankAccount, name: str = "",
           category: str | None = None, channel: str = "card", income: bool = False, desc: str = "") -> Transaction:
        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
        m = merchant(name) if name and normalize_name(name) in merchants else None
        balances[account.id] += amount if direction == "credit" else -amount
        t = Transaction(user_id=uid, account_id=account.id, occurred_at=_at(day, hour, rnd.randint(0, 59)),
                        amount=amount, direction=direction, merchant_raw=name, merchant_id=m.id if m else None,
                        category_slug=category or (m.category_slug if m else "misc"), description=desc or DEMO_TAG,
                        channel=channel, source=rnd.choice(["gmail", "gmail", "gmail", "chat"]),
                        external_id=f"demo:{uuid.uuid4().hex}", balance_after=balances[account.id], is_income=income)
        if m:
            m.seen_in_transactions += 1
        txs.append(t)
        return t

    start = today - timedelta(days=118)
    salaries: list[tuple[Transaction, date]] = []
    day = start
    while day <= today:
        if day.day == 1:
            salaries.append((tx(day, 10, 150000, "credit", meezan, "Salary - Systems Ltd", "income", "transfer", True), day))
            tx(day, 12, 37500, "debit", meezan, "Transfer to HBL savings", "transfer", "transfer")
            tx(day, 12, 37500, "credit", hbl, "Transfer from Meezan", "transfer", "transfer")
        if day.day == 3:
            tx(day, 11, 35000, "debit", meezan, "House rent (Raast)", "housing", "transfer")
        if day.day == 8:
            tx(day, 19, rnd.randint(7000, 12000), "debit", meezan, "K-Electric", channel="bill")
            tx(day, 19, rnd.randint(1500, 3200), "debit", meezan, "SSGC", channel="bill")
            tx(day, 19, 4500, "debit", meezan, "StormFiber", channel="bill")
        if day.day == 15:
            tx(day, 21, 1500, "debit", meezan, "Netflix", channel="online")
            tx(day, 13, 3000, "debit", jazz, "Jazz", channel="online")
            tx(day, 13, 5000, "credit", jazz, "Top up from Meezan", "transfer", "transfer")
        weekday = day.weekday()
        if rnd.random() < 0.25:
            tx(day, 13, rnd.randint(700, 2200), "debit", meezan, rnd.choice(["KFC Pakistan", "Cheezious", "Foodpanda"]))
        if weekday in (4, 5) and rnd.random() < 0.5:
            tx(day, 20, rnd.randint(1800, 3800), "debit", meezan, rnd.choice(["KFC Pakistan", "Foodpanda", "Cheezious"]))
        if weekday == 6 and rnd.random() < 0.7:
            tx(day, 17, rnd.randint(4000, 9000), "debit", meezan,
               rnd.choice(["Imtiaz Super Market", "Carrefour Pakistan", "Naheed Supermarket"]))
        if weekday == 0:
            tx(day, 8, rnd.randint(3500, 5500), "debit", meezan, rnd.choice(["PSO", "Shell Pakistan"]))
        if rnd.random() < 0.18:
            tx(day, 9, rnd.randint(350, 1100), "debit", jazz, "Careem", channel="online")
        if rnd.random() < 0.06:
            tx(day, 18, rnd.randint(800, 4500), "debit", meezan, "D. Watson")
        if rnd.random() < 0.05:
            tx(day, 16, rnd.randint(3500, 9500), "debit", meezan, rnd.choice(["Khaadi", "Outfitters", "Bata Pakistan", "Daraz"]))
        day += timedelta(days=1)
    # The laptop goal was finished last month and bought from savings.
    laptop_day = today - timedelta(days=40)
    tx(laptop_day, 15, 249000, "debit", hbl, "Daraz", "shopping", "online", desc="Laptop purchase (goal completed)")
    tx(laptop_day - timedelta(days=1), 15, 70000, "credit", hbl, "Bonus credit", "income", "transfer", True)
    s.add_all(txs)
    meezan.balance, hbl.balance, jazz.balance = balances[meezan.id], balances[hbl.id], balances[jazz.id]
    s.flush()

    # ------------------------------------------------------------------ savings ledger
    def save(goal: Goal | None, amount, source: str, when: datetime, note: str, tx_id=None, account=hbl) -> None:
        amount = Decimal(str(amount))
        s.add(SavingsEntry(user_id=uid, goal_id=goal.id if goal else None, account_id=account.id, amount=amount,
                           source=source, note=note, transaction_id=tx_id, created_at=when))
        if goal:
            goal.saved_amount = Decimal(goal.saved_amount or 0) + amount

    before = _at(start - timedelta(days=20), 12)
    save(emergency, 110000, "manual", before, "Existing savings moved in during onboarding")
    save(car, 70000, "manual", before, "Existing savings moved in during onboarding")
    save(laptop, 180000, "manual", before, "Existing savings moved in during onboarding")
    for salary, d in salaries:
        when = _at(d, 12)
        save(umrah, 16500, "allocation", when, "Monthly savings from income", salary.id)
        save(car, 14000, "allocation", when, "Monthly savings from income", salary.id)
        save(emergency, 7000, "allocation", when, "Monthly savings from income", salary.id)
    save(laptop, 70000, "manual", _at(laptop_day - timedelta(days=1), 16), "Bonus added to laptop goal")
    save(laptop, -250000, "goal_completed", _at(laptop_day, 15), "Bought the laptop 🎉")
    laptop.saved_amount = Decimal(250000)  # keep the completed goal showing 100 %

    # ------------------------------------------------------------------ deals
    until = today + timedelta(days=45)
    deal_rows = [
        ("KFC Pakistan", "20% off with Meezan Visa Platinum", "food", "fast food restaurant", "percent", 20, 2000,
         "Meezan", "visa", "platinum", "debit", [4, 5, 6]),
        ("Khaadi", "15% off with HBL credit cards", "shopping", "women's apparel", "percent", 15, 5000,
         "HBL", "mastercard", None, "credit", []),
        ("Foodpanda", "Rs. 400 off on orders above Rs. 1,500", "food", "food delivery", "flat", 400, None,
         None, None, None, None, []),
        ("Imtiaz Super Market", "10% off groceries with Meezan debit cards", "grocery", "supermarket", "percent", 10,
         1500, "Meezan", None, None, "debit", [6]),
        ("PSO", "5% cashback on fuel with Meezan Visa", "fuel", "fuel station", "cashback", 5, 1000,
         "Meezan", "visa", None, "debit", []),
        ("D. Watson", "10% off on medicines, any card", "medicine", "pharmacy", "percent", 10, 1000,
         None, None, None, None, []),
        ("Cinepax", "50% off movie tickets on Tuesdays", "entertainment", "cinema", "percent", 50, 1200,
         "Meezan", None, None, "debit", [1]),
        ("Outfitters", "Season sale: up to 30% off", "shopping", "men's and women's apparel", "percent", 30, None,
         None, None, None, None, []),
        ("Carrefour Pakistan", "5% off with HBL credit cards", "grocery", "supermarket", "percent", 5, 1500,
         "HBL", None, None, "credit", []),
        ("Bata Pakistan", "20% off with HBL Mastercard", "shopping", "footwear", "percent", 20, 2500,
         "HBL", "mastercard", None, "credit", []),
        ("Cheezious", "Buy 1 get 1 free on Wednesdays", "food", "fast food restaurant", "bogo", None, None,
         None, None, None, None, [2]),
    ]
    deals: dict[str, Deal] = {}
    for (mname, title, cat, dtype, dkind, value, cap, bank, net, tier, ctype, days) in deal_rows:
        d = Deal(merchant_id=merchant(mname).id, merchant_name=mname, title=title,
                 description=f"{DEMO_TAG} Sample deal for the demo account.", discount_type=dkind,
                 discount_value=value, max_discount=cap, category_slug=cat, deal_type=dtype,
                 requires_card=bank is not None, bank_id=banks[bank].id if bank else None, card_network=net,
                 card_tier=tier, card_type=ctype, days_of_week=days, cities=[], valid_from=today - timedelta(days=10),
                 valid_until=until, source_url=None, source_kind="other", status="active", confidence=0.9,
                 fingerprint=deal_fingerprint(mname, title, bank, until))
        s.add(d)
        deals[mname] = d
    s.add(Deal(merchant_name="Daraz", title="11.11 sale: 40% off electronics (needs review)", category_slug="shopping",
               description=f"{DEMO_TAG} Low-confidence deal waiting for admin review.", discount_type="percent",
               discount_value=40, valid_until=until, source_kind="instagram", status="pending_review", confidence=0.4,
               fingerprint=deal_fingerprint("Daraz", "11.11 sale demo", None, until)))
    s.flush()
    for mname, spent, saved, goal, ago in [("KFC Pakistan", 3200, 640, umrah, 30), ("Khaadi", 12500, 1875, car, 21),
                                          ("Imtiaz Super Market", 11800, 1180, None, 9), ("KFC Pakistan", 2600, 520, umrah, 3)]:
        when = now - timedelta(days=ago)
        s.add(DealRedemption(user_id=uid, deal_id=deals[mname].id, amount_spent=spent, amount_saved=saved,
                             goal_id=goal.id if goal else None, created_at=when))
        save(goal or emergency, saved, "deal_saving", when, f"Saved with deal: {deals[mname].title}", account=meezan)

    # ------------------------------------------------------------------ market desk output
    for asset, sym, sig, conf, price, why in [
        ("gold_silver", "XAU", "hold", 0.7, 4158, "Gold steady near record highs; PKR stable this week."),
        ("psx", "OGDC", "buy", 0.65, 302.25, "Broke above 300 on strong volume after higher dividend payout."),
        ("psx", "MEBL", "watch", 0.6, 418.4, "Awaiting SBP policy decision; Islamic banking deposits growing."),
        ("crypto", "BTC", "alert", 0.55, 80921, "Down ~3% in 24h amid ETF outflows; high volatility."),
        ("foreign_stocks", "NVDA", "hold", 0.6, 187.2, "Consolidating after earnings; valuation stretched."),
        ("pk_real_estate", "DHA_KHI", "watch", 0.5, None, "Listings up, prices flat; new FBR valuation table pending."),
    ]:
        s.add(MarketSignal(asset_class=asset, cluster_slug=None, symbol=sym, signal=sig, confidence=conf, price=price,
                           horizon="swing", rationale=f"{DEMO_TAG} {why}", created_by=DEMO_BOT,
                           created_at=now - timedelta(hours=rnd.randint(2, 40))))
    for asset, title, summary, sentiment in [
        ("gold_silver", "Gold holds gains as USD softens", "- Spot ~USD 4,150/oz\n- Local tola ~Rs. 432,000 spot equivalent", "bullish"),
        ("psx", "KSE-100 extends rally on rate-cut hopes", "- Index up 2.1% this week\n- E&P and banks led", "bullish"),
        ("crypto", "Bitcoin volatility returns", "- BTC -3% in 24h\n- Regulatory framework in Pakistan evolving", "neutral"),
        ("foreign_stocks", "US tech earnings mixed", "- Mega-caps beat on cloud\n- Guidance cautious", "neutral"),
        ("pk_real_estate", "Karachi property market flat", "- DHA prices unchanged m/m\n- Rentals up 4%", "neutral"),
    ]:
        s.add(ResearchNote(asset_class=asset, kind="analysis", title=title, summary=f"{DEMO_TAG}\n{summary}",
                           sentiment=sentiment, symbols=[], sources=["https://example.com/demo"], created_by=DEMO_BOT,
                           created_at=now - timedelta(hours=rnd.randint(3, 30))))
    s.add_all([UserFollow(user_id=uid, asset_class="gold_silver", symbol="XAU"),
               UserFollow(user_id=uid, asset_class="psx", symbol="OGDC")])

    # ------------------------------------------------------------------ memory, notifications, chat
    for fact, cat, ago in [("Got a 15% increment in July (salary now Rs. 150,000)", "income", 95),
                           ("Wants to take their parents for Umrah before Ramadan", "goals", 110),
                           ("Prefers Roman Urdu or English, short answers", "preferences", 110),
                           ("Eats out most Friday nights, usually KFC or Cheezious", "habits", 60)]:
        s.add(UserFact(user_id=uid, fact=fact, category=cat, created_at=now - timedelta(days=ago)))

    for kind, title, body, url, ago, read in [
        ("motivation", "Great job, Osama! 🌱", "You saved Rs. 9,120 this week. Keep it up!", "/dashboard", 6, True),
        ("deal", "Friday deal at KFC", "20% off with your Meezan Visa Platinum tonight.", "/dashboard", 6, True),
        ("sadqah", "Sadqah reminder 🤲", "Your planned sadqah: Rs. 2,000.", "/dashboard?chat=1", 6, True),
        ("goal", "Goal reached! 🎉", "You've fully saved for “New laptop”. Mubarak ho!", f"/goals/{laptop.id}", 40, True),
        ("chat", "Savings Coach", "Food delivery is up 18% this month. Want a quick plan?", "/dashboard?chat=1", 1, False),
        ("motivation", "Nice save! 💚", "Rs. 520 went to your savings with the KFC deal.", "/dashboard", 3, False),
    ]:
        s.add(Notification(user_id=uid, kind=kind, title=title, body=body, url=url, pushed=True,
                           read_at=(now - timedelta(days=ago)) if read else None, created_at=now - timedelta(days=ago)))

    convo = [
        (118, "user", "you", "Assalam o alaikum! I want to start saving properly."),
        (118, "bot", "Finance Assistant", "Walaikum assalam Osama! 👋 Let's set up your plan. Which banks or wallets do you use?"),
        (118, "user", "you", "Meezan for salary, HBL for savings and JazzCash."),
        (118, "bot", "Finance Assistant", "Got it, all 3 saved. Which cards do you have?"),
        (118, "user", "you", "Meezan Visa Platinum debit and HBL Mastercard Gold credit card"),
        (118, "bot", "Finance Assistant", "Saved both. These unlock bank discounts at **KFC, Khaadi, Imtiaz** and more."),
        (118, "user", "you", "Salary 130k on the 1st. I want a car by next June and Umrah with my parents before Ramadan."),
        (118, "bot", "Finance Assistant", "Created 2 goals:\n- Car (Honda City): Rs. 1,800,000\n- Umrah with parents: Rs. 600,000\n\nSaving 25% of your salary and splitting it by deadline keeps both on track."),
        (95, "user", "you", "Good news, I got a 15% increment!"),
        (95, "bot", "Finance Assistant", "Mubarak ho! 🎉 I updated your income to Rs. 150,000. Your monthly savings grow to Rs. 37,500."),
        (3, "user", "you", "Used the KFC deal yesterday, bill was 2600"),
        (3, "bot", "Deals Advisor", "Shabash! You saved Rs. 520, now in your Umrah goal. That's Rs. 1,160 saved with KFC deals this month."),
        (1, "bot", "Savings Coach", "Quick check-in: food delivery is up 18% this month (Rs. 21,400). Cooking 2 of those dinners at home saves ~Rs. 6,000, enough to move your Car goal 2 weeks closer. Want a weekly food budget?"),
    ]
    for i, (ago, role, sender, text) in enumerate(convo):
        s.add(ChatMessage(user_id=uid, role=role, sender=sender, text=text, kind="text", final=True,
                          created_at=now - timedelta(days=ago) + timedelta(minutes=i)))
    s.flush()


def downgrade() -> None:
    conn = op.get_bind()
    _system(conn)
    # Everything owned by the demo users goes with them (ON DELETE CASCADE).
    conn.execute(sa.text("DELETE FROM users WHERE email IN (:u, :a)"), {"u": DEMO_USER, "a": DEMO_ADMIN})
    conn.execute(sa.text("DELETE FROM deals WHERE description LIKE :t"), {"t": f"{DEMO_TAG}%"})
    conn.execute(sa.text("DELETE FROM market_signals WHERE created_by = :b"), {"b": DEMO_BOT})
    conn.execute(sa.text("DELETE FROM research_notes WHERE created_by = :b"), {"b": DEMO_BOT})
