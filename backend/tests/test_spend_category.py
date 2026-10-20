from app.mcp import user_server
from app.seed.data import CATEGORIES
from app.services.categorize import rule_category


def test_petrol_and_friends_are_fuel():
    for words in ("petrol", "10k petrol", "diesel for the car", "CNG filling station", "petrol pump", "PSO"):
        assert rule_category(words) == "fuel", words


def test_the_tool_description_lists_every_real_category():
    doc = user_server.record_transaction.__doc__ or ""
    for slug, *_ in CATEGORIES:
        assert slug in doc, slug
