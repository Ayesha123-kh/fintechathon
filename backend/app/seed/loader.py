import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.db import system_session
from app.core.security import hash_password
from app.models import AssetClass, Bank, Category, Merchant, Plan, User, UserProfile, WatchCluster
from app.seed import data
from app.services.text import normalize_name

log = logging.getLogger(__name__)


async def load_reference_data() -> None:
    async with system_session() as s:
        for slug, name, icon, color, is_expense in data.CATEGORIES:
            await s.execute(
                insert(Category)
                .values(slug=slug, name=name, icon=icon, color=color, is_expense=is_expense)
                .on_conflict_do_update(index_elements=["slug"], set_={"name": name, "icon": icon, "color": color})
            )
        for name, short, kind, website, domains, aliases in data.BANKS:
            await s.execute(
                insert(Bank)
                .values(name=name, short_name=short, kind=kind, website=website, email_domains=domains, aliases=aliases)
                .on_conflict_do_update(
                    index_elements=["name"],
                    set_={"short_name": short, "kind": kind, "website": website, "email_domains": domains,
                          "aliases": aliases},
                )
            )
        for slug, name, desc in data.ASSET_CLASSES:
            await s.execute(
                insert(AssetClass).values(slug=slug, name=name, description=desc)
                .on_conflict_do_update(index_elements=["slug"], set_={"name": name, "description": desc})
            )
        await s.flush()
        for asset_class, slug, name, desc, symbols in data.WATCH_CLUSTERS:
            # Insert only: symbols added later (user coverage requests, admin) must survive restarts.
            await s.execute(
                insert(WatchCluster)
                .values(asset_class=asset_class, slug=slug, name=name, description=desc, symbols=symbols)
                .on_conflict_do_nothing(index_elements=["slug"])
            )
        for name, category, sub in data.SEED_MERCHANTS:
            await s.execute(
                insert(Merchant)
                .values(name=name, normalized_name=normalize_name(name), category_slug=category, subcategory=sub)
                .on_conflict_do_nothing(index_elements=["normalized_name"])
            )
        for code, name, price, features in data.PLANS:
            await s.execute(
                insert(Plan).values(code=code, name=name, price_monthly=price, features=features)
                .on_conflict_do_update(index_elements=["code"], set_={"name": name, "features": features})
            )


async def ensure_admin() -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    async with system_session() as s:
        email = settings.admin_email.lower()
        user = (await s.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user:
            if user.role != "admin":
                user.role = "admin"
            return
        user = User(email=email, password_hash=hash_password(settings.admin_password), full_name="Admin",
                    role="admin", email_verified=True, onboarding_completed=True)
        s.add(user)
        await s.flush()
        s.add(UserProfile(user_id=user.id))
        log.info("created bootstrap admin %s", email)
