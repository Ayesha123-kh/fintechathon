import pytest

from app.services import merchant_screen as ms


@pytest.fixture
def model(monkeypatch):
    """Stand in for the self-hosted LLM: returns whatever the test sets."""
    answer: dict = {"value": None}

    async def fake(system, user, max_tokens=800):
        return answer["value"]

    monkeypatch.setattr(ms, "complete_json", fake)
    return answer


async def test_business_goes_on_to_pending(model):
    model["value"] = {"kind": "business", "confidence": 0.95}
    verdict = await ms.classify_payee("Kababjees", "Debited at Kababjees")
    assert verdict is True and ms.status_for(verdict) == "pending"


async def test_person_is_kept_from_the_deal_bots(model):
    model["value"] = {"kind": "person", "confidence": 0.9}
    verdict = await ms.classify_payee("Ali Khan", "Transfer to Ali Khan")
    assert verdict is False and ms.status_for(verdict) == "personal"


async def test_unsure_business_counts_as_personal(model):
    model["value"] = {"kind": "business", "confidence": 0.3}
    assert await ms.classify_payee("A. Raza") is False


async def test_garbled_answer_counts_as_personal(model):
    model["value"] = {"kind": "business", "confidence": "high"}
    assert await ms.classify_payee("X") is False


async def test_model_offline_holds_the_merchant(model):
    model["value"] = None
    verdict = await ms.classify_payee("Kababjees")
    assert verdict is None and ms.status_for(verdict) == "screening"
