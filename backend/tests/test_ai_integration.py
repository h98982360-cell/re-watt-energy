from fastapi.testclient import TestClient


def register(
    client: TestClient,
    *,
    email: str,
    role: str,
    business_name: str,
    supplier_type: str | None = None,
) -> tuple[str, dict]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "safe-demo-password-123",
            "full_name": business_name,
            "role": role,
            "business_name": business_name,
            "supplier_type": supplier_type,
            "county": "Kiambu",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["access_token"], body["user"]


def _verify_supplier(client, admin_token, supplier_id):
    response = client.patch(
        f"/api/admin/verifications/{supplier_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"decision": "verified"},
    )
    assert response.status_code == 200, response.text


def _catalog_material_id(client):
    catalog = client.get("/api/catalog").json()
    return next(
        material["id"]
        for category in catalog
        for material in category["materials"]
        if material["slug"] == "maize-cobs"
    )


def test_listing_insight_sends_listing_facts(client, monkeypatch):
    supplier_token, supplier = register(
        client,
        email="ai-supplier@example.com",
        role="supplier",
        business_name="AI Supplier",
        supplier_type="farmer",
    )
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "safe-admin-password-123"},
    )
    admin_token = admin_login.json()["access_token"]
    _verify_supplier(client, admin_token, supplier["id"])

    listing = client.post(
        "/api/listings",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "material_id": _catalog_material_id(client),
            "title": "Dry maize cobs",
            "condition": "dry",
            "quantity": 500,
            "unit": "kg",
            "county": "Kiambu",
            "description": "Clean cobs",
        },
    )
    assert listing.status_code == 201, listing.text

    calls = []

    def fake_request(path, payload):
        calls.append((path, payload))
        return {"available": True, "data": {"summary": "AI insight"}}

    monkeypatch.setattr("app.api.routes.ai.request_insight", fake_request)
    response = client.post(
        "/api/ai/insights/listing",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={"listing_id": listing.json()["id"]},
    )

    assert response.status_code == 200
    assert calls == [
        (
            "/ai/material-insight",
            {
                "material": "Maize cobs",
                "quantity": 500.0,
                "unit": "kg",
                "condition": "dry",
                "location": "Kiambu",
                "availability": "active",
                "description": "Clean cobs",
                "image_provided": False,
            },
        )
    ]


def test_requirement_insight_sends_backend_match_facts(client, monkeypatch):
    buyer_token, _ = register(
        client,
        email="ai-buyer@example.com",
        role="buyer",
        business_name="AI Buyer",
    )
    supplier_token, supplier = register(
        client,
        email="ai-match-supplier@example.com",
        role="supplier",
        business_name="AI Match Supplier",
        supplier_type="farmer",
    )
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "safe-admin-password-123"},
    )
    admin_token = admin_login.json()["access_token"]
    _verify_supplier(client, admin_token, supplier["id"])
    material_id = _catalog_material_id(client)

    listing = client.post(
        "/api/listings",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "material_id": material_id,
            "title": "Dry maize cobs",
            "condition": "dry",
            "quantity": 500,
            "unit": "kg",
            "county": "Kiambu",
        },
    )
    assert listing.status_code == 201, listing.text

    requirement = client.post(
        "/api/requirements",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "material_id": material_id,
            "title": "Cobs for fuel",
            "quantity": 400,
            "unit": "kg",
            "acceptable_conditions": ["dry"],
            "intended_use": "Biomass fuel",
        },
    )
    assert requirement.status_code == 201, requirement.text
    match = client.post(
        f"/api/requirements/{requirement.json()['id']}/matches",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert match.status_code == 201, match.text

    calls = []

    def fake_request(path, payload):
        calls.append((path, payload))
        return {"available": True, "data": {"summary": "Compatibility insight"}}

    monkeypatch.setattr("app.api.routes.ai.request_insight", fake_request)
    response = client.post(
        "/api/ai/insights/requirement",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"requirement_id": requirement.json()["id"], "match_id": match.json()["id"]},
    )

    assert response.status_code == 200
    assert calls == [
        (
            "/ai/compatibility-insight",
            {
                "buyer_requirement": {
                    "material": "Maize cobs",
                    "required_quantity": 400.0,
                    "unit": "kg",
                    "condition": "dry",
                    "purpose": "Biomass fuel",
                },
                "match_result": {
                    "supplier_count": 1,
                    "matched_quantity": 500.0,
                    "required_quantity": 400.0,
                    "quantity_sufficient": True,
                    "material_compatible": True,
                    "condition_compatible": True,
                },
            },
        )
    ]
