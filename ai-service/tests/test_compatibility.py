import pytest

URL = "/ai/compatibility-insight"


def make_body(**match):
    # The test body, with any match_result fields replaced by the test.
    return {
        "buyer_requirement": {
            "material": "Maize cobs",
            "required_quantity": 2000,
            "unit": "kg",
            "condition": "dry",
            "purpose": "biomass processing",
        },
        "match_result": {
            "supplier_count": 5,
            "matched_quantity": 2150,
            "required_quantity": 2000,
            "quantity_sufficient": True,
            "material_compatible": True,
            "condition_compatible": True,
            **match,
        },
    }


# A valid model reply with no numbers in it.
REPLY = {
    "reasons": ["The material is compatible."],
    "considerations": ["Actual quantity and quality are confirmed at handover."],
    "summary": "The match meets the buyer requirement.",
}


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"matched_quantity": 2000}, "high"),  # Requirement exactly met.
        ({}, "high"),  # Supply exceeds the requirement.
        (
            {"supplier_count": 4, "matched_quantity": 1500, "quantity_sufficient": False},
            "partial",
        ),
        ({"material_compatible": False}, "low"),
        ({"condition_compatible": False}, "low"),
    ],
    ids=["exactly_met", "exceeds", "below", "material_mismatch", "condition_mismatch"],
)
def test_rating_comes_from_the_flags(client, llm_reply, overrides, expected):
    llm_reply(REPLY)
    result = client.post(URL, json=make_body(**overrides)).json()
    assert result["available"] is True
    assert result["data"]["compatibility"] == expected


def test_model_cannot_change_the_rating(client, llm_reply):
    # The model tries to say "high" for a partial match, and our code ignores it.
    llm_reply({**REPLY, "compatibility": "high"})
    body = make_body(matched_quantity=1500, quantity_sufficient=False)
    result = client.post(URL, json=body).json()
    assert result["data"]["compatibility"] == "partial"


def test_missing_match_result(client):
    body = make_body()
    del body["match_result"]
    assert client.post(URL, json=body).status_code == 422


def test_invented_number_is_rejected(client, llm_reply):
    # The model writes a shortfall of 500, which the backend never sent.
    llm_reply({**REPLY, "summary": "The supply is short by 500 kg."})
    body = make_body(matched_quantity=1500, quantity_sufficient=False)
    assert client.post(URL, json=body).json()["available"] is False


def test_invalid_llm_response(client, llm_reply):
    llm_reply("this is not json")
    assert client.post(URL, json=make_body()).json()["available"] is False
