import pytest

URL = "/ai/material-insight"

BODY = {
    "material": "Maize cobs",
    "quantity": 500,
    "unit": "kg",
    "condition": "dry",
    "location": "Kiambu",
}

# A valid model reply with no numbers in it, so any quantity passes the number check.
REPLY = {
    "potential_uses": ["Biomass fuel"],
    "potential_buyer_types": ["Briquette producers"],
    "important_characteristics": ["Moisture level, to be confirmed"],
    "summary": "Dry maize cobs may suit biomass processing.",
    "confidence": "medium",
}


def test_valid_maize_cobs(client, llm_reply):
    llm_reply(REPLY)
    result = client.post(URL, json=BODY).json()
    # The material and disclaimer are added by our code, not the model.
    assert result["available"] is True
    assert result["data"]["material"] == "Maize cobs"
    assert result["data"]["disclaimer"]


@pytest.mark.parametrize("quantity", [1, 500, 25000.5])
def test_different_quantities(client, llm_reply, quantity):
    llm_reply(REPLY)
    response = client.post(URL, json={**BODY, "quantity": quantity})
    assert response.json()["available"] is True


@pytest.mark.parametrize(
    "condition", ["dry", "moist", "wet", "working", "degraded", "faulty", "unknown"]
)
def test_different_conditions(client, llm_reply, condition):
    llm_reply(REPLY)
    response = client.post(URL, json={**BODY, "condition": condition})
    assert response.json()["available"] is True


def test_unknown_material(client, llm_reply):
    # A material we have never heard of is still accepted.
    llm_reply(REPLY)
    response = client.post(URL, json={**BODY, "material": "Zorblax fibre"})
    assert response.json()["available"] is True


def test_missing_material(client):
    body = {key: value for key, value in BODY.items() if key != "material"}
    assert client.post(URL, json=body).status_code == 422


def test_missing_quantity(client):
    body = {key: value for key, value in BODY.items() if key != "quantity"}
    assert client.post(URL, json=body).status_code == 422


@pytest.mark.parametrize("quantity", [-5, 0])
def test_quantity_must_be_positive(client, quantity):
    response = client.post(URL, json={**BODY, "quantity": quantity})
    assert response.status_code == 422


def test_description_length_limit(client, llm_reply):
    llm_reply(REPLY)
    # 1000 characters is allowed, 1001 is rejected.
    ok = client.post(URL, json={**BODY, "description": "x" * 1000})
    too_long = client.post(URL, json={**BODY, "description": "x" * 1001})
    assert ok.status_code == 200
    assert too_long.status_code == 422


def test_invented_number_is_rejected(client, llm_reply):
    # The model mentions 12, which is not in the listing.
    llm_reply({**REPLY, "summary": "Moisture is around 12 percent."})
    assert client.post(URL, json=BODY).json()["available"] is False


def test_invalid_llm_response(client, llm_reply):
    llm_reply("this is not json")
    assert client.post(URL, json=BODY).json()["available"] is False
