from app.services.text import assistant_failure_message


def test_a_refused_step_is_not_called_an_unreachable_service():
    raw = "error: One or more tool operations failed or were denied. See the tool results."
    msg = assistant_failure_message(raw)
    assert "rejected" in msg and "unreachable" not in msg


def test_a_model_that_cannot_be_reached_says_so():
    for raw in ("error: fetch failed", "error: request timed out", "ECONNREFUSED"):
        assert "unreachable" in assistant_failure_message(raw)


def test_anything_else_gets_a_neutral_message():
    msg = assistant_failure_message("error: something odd")
    assert "unreachable" not in msg and "rejected" not in msg and "try again" in msg
