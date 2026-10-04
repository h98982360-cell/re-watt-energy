import pytest

URL = "/ai/material-insight"

BODY = {"material": "Maize cobs", "quantity": 500, "unit": "kg", "condition": "dry"}

# A complete valid reply, which each failure case below breaks in a different way.
GOOD = {
    "potential_uses": ["Biomass fuel"],
    "potential_buyer_types": ["Briquette producers"],
    "important_characteristics": ["Moisture level, to be confirmed"],
    "summary": "Dry maize cobs may suit biomass processing.",
    "confidence": "medium",
}
NO_SUMMARY = {key: value for key, value in GOOD.items() if key != "summary"}


@pytest.mark.parametrize(
    "reply, error",
    [
        (None, TimeoutError("timed out")),
        (None, RuntimeError("Groq is down")),
        ("{not valid json", None),
        (NO_SUMMARY, None),
        ({**GOOD, "potential_uses": "Biomass fuel"}, None),  # A string, not a list.
        (None, None),  # No content at all.
        ("", None),  # Empty text.
    ],
    ids=[
        "timeout",
        "api_failure",
        "malformed_json",
        "missing_field",
        "wrong_type",
        "no_content",
        "empty_text",
    ],
)
def test_llm_failures_return_unavailable(client, llm_reply, reply, error):
    llm_reply(reply, error)
    response = client.post(URL, json=BODY)
    # The backend gets a normal 200 with available=false, never a crash.
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["message"]


def test_wrong_api_key(bare_client):
    response = bare_client.post(URL, json=BODY, headers={"x-api-key": "wrong"})
    assert response.status_code == 401


def test_missing_api_key(bare_client):
    # FastAPI rejects a request with the header missing before our check runs.
    assert bare_client.post(URL, json=BODY).status_code == 422
