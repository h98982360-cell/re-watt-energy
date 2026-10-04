from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database, main
from app.models import Base, User
from app.security import hash_password


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_sessions = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(database, "SessionLocal", testing_sessions)
    monkeypatch.setattr(main, "SessionLocal", testing_sessions)
    monkeypatch.setattr(main, "init_db", lambda: Base.metadata.create_all(bind=engine))
    with TestClient(main.app) as test_client:
        with testing_sessions() as db:
            db.add(
                User(
                    email="admin@example.com",
                    password_hash=hash_password("safe-admin-password-123"),
                    full_name="Test Admin",
                    role="admin",
                    status="active",
                    is_active=True,
                )
            )
            db.commit()
        yield test_client
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def register(
    client: TestClient,
    *,
    email: str,
    role: str,
    business_name: str,
    supplier_type: str | None = None,
) -> tuple[str, dict]:
    payload = {
        "email": email,
        "password": "safe-demo-password-123",
        "full_name": business_name,
        "role": role,
        "business_name": business_name,
        "supplier_type": supplier_type,
        "county": "Kiambu",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    return body["access_token"], body["user"]


def test_health_catalog_and_registration(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
    catalog = client.get("/api/catalog")
    assert catalog.status_code == 200
    materials = catalog.json()[0]["materials"]
    assert any(material["slug"] == "maize-cobs" for material in materials)

    token, user = register(
        client,
        email="supplier@example.com",
        role="supplier",
        business_name="Green Farm",
        supplier_type="farmer",
    )
    assert user["role"] == "supplier"
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    duplicate = client.post(
        "/api/auth/register",
        json={
            "email": "supplier@example.com",
            "password": "safe-demo-password-123",
            "full_name": "Another Supplier",
            "role": "supplier",
            "business_name": "Second Farm",
            "supplier_type": "farmer",
        },
    )
    assert duplicate.status_code == 409


def test_unverified_supplier_cannot_publish(client: TestClient) -> None:
    token, _ = register(
        client,
        email="pending@example.com",
        role="supplier",
        business_name="Pending Farm",
        supplier_type="farmer",
    )
    material_id = client.get("/api/catalog").json()[0]["materials"][0]["id"]
    response = client.post(
        "/api/listings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "material_id": material_id,
            "title": "Dry maize cobs",
            "condition": "dry",
            "quantity": 500,
            "unit": "kg",
        },
    )
    assert response.status_code == 403


def test_aggregated_match_supplier_acceptance_and_transaction(client: TestClient) -> None:
    buyer_token, _ = register(
        client,
        email="buyer@example.com",
        role="buyer",
        business_name="Briquette Works",
    )
    first_token, first = register(
        client,
        email="first@example.com",
        role="supplier",
        business_name="First Farm",
        supplier_type="farmer",
    )
    second_token, second = register(
        client,
        email="second@example.com",
        role="supplier",
        business_name="Second Farm",
        supplier_type="farmer",
    )

    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "safe-admin-password-123"},
    )
    admin_token = admin_login.json()["access_token"]
    pending = client.get(
        "/api/admin/verifications/pending",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Both suppliers are pending; the buyer was also created and is pending
    pending_suppliers = {
        entry["user_id"]
        for entry in pending.json()
        if entry.get("role") == "supplier"
    }
    assert pending_suppliers == {first["id"], second["id"]}
    for supplier_id in (first["id"], second["id"]):
        verified = client.patch(
            f"/api/admin/verifications/{supplier_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"decision": "verified"},
        )
        assert verified.status_code == 200, verified.text

    catalog = client.get("/api/catalog").json()
    maize = next(material for item in catalog for material in item["materials"] if material["slug"] == "maize-cobs")
    for token, amount in ((first_token, 500), (second_token, 800)):
        response = client.post(
            "/api/listings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "material_id": maize["id"],
                "title": "Dry maize cobs",
                "condition": "dry",
                "quantity": amount,
                "unit": "kg",
                "price_per_unit": 10,
                "county": "Kiambu",
            },
        )
        assert response.status_code == 201, response.text

    requirement_response = client.post(
        "/api/requirements",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "material_id": maize["id"],
            "title": "Maize cobs for briquettes",
            "quantity": 1100,
            "unit": "kg",
            "acceptable_conditions": ["dry"],
            "delivery_counties": ["Kiambu"],
            "currency": "KES",
        },
    )
    assert requirement_response.status_code == 201, requirement_response.text
    requirement_id = requirement_response.json()["id"]
    match_response = client.post(
        f"/api/requirements/{requirement_id}/matches",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert match_response.status_code == 201, match_response.text
    match = match_response.json()
    assert match["supplier_count"] == 2
    assert match["coverage_percent"] > 100
    assert match["matched_quantity"] == 1300
    assert match["surplus"] == 200
    assert sum(float(item["quantity"]) for item in match["items"]) == 1100

    assert client.post(
        f"/api/matches/{match['id']}/respond",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"accept": True},
    ).json()["status"] == "partially_accepted"
    accepted = client.post(
        f"/api/matches/{match['id']}/respond",
        headers={"Authorization": f"Bearer {second_token}"},
        json={"accept": True},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "confirmed"
    transaction_list = client.get(
        "/api/transactions",
        headers={"Authorization": f"Bearer {buyer_token}"},
    ).json()
    assert len(transaction_list) == 2
    first_transaction = transaction_list[0]
    receipt = client.post(
        f"/api/transactions/{first_transaction['id']}/confirm-receipt",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"quantity_received": first_transaction["quantity_declared"]},
    )
    assert receipt.status_code == 200
    payment = client.post(
        f"/api/transactions/{first_transaction['id']}/payments",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"method": "mobile_money", "reference": "DEMO-123"},
    )
    assert payment.status_code == 201
    payee_token = first_token if first_transaction["supplier_id"] == first["id"] else second_token
    confirmed = client.post(
        f"/api/payments/{payment.json()['id']}/confirm-received",
        headers={"Authorization": f"Bearer {payee_token}"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["transaction_status"] == "completed"


def test_buyer_requirement_detail_exact_maize_cobs_aggregation(client: TestClient) -> None:
    buyer_token, _ = register(
        client,
        email="maize-buyer@example.com",
        role="buyer",
        business_name="Biomass Processor",
    )
    supplier_accounts = [
        register(
            client,
            email=f"maize-supplier-{index}@example.com",
            role="supplier",
            business_name=f"Maize Supplier {index}",
            supplier_type="farmer",
        )
        for index in range(1, 6)
    ]

    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "safe-admin-password-123"},
    )
    admin_token = admin_login.json()["access_token"]
    for _, supplier in supplier_accounts:
        verified = client.patch(
            f"/api/admin/verifications/{supplier['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"decision": "verified"},
        )
        assert verified.status_code == 200, verified.text

    catalog = client.get("/api/catalog").json()
    maize = next(material for item in catalog for material in item["materials"] if material["slug"] == "maize-cobs")
    for (supplier_token, _), amount in zip(supplier_accounts, (400, 500, 450, 350, 450)):
        response = client.post(
            "/api/listings",
            headers={"Authorization": f"Bearer {supplier_token}"},
            json={
                "material_id": maize["id"],
                "title": "Dry maize cobs",
                "condition": "dry",
                "quantity": amount,
                "unit": "kg",
                "price_per_unit": 50,
                "county": "Kiambu",
            },
        )
        assert response.status_code == 201, response.text

    requirement_response = client.post(
        "/api/requirements",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "material_id": maize["id"],
            "title": "Maize cobs for biomass processing",
            "quantity": 2000,
            "unit": "kg",
            "acceptable_conditions": ["dry"],
            "delivery_counties": ["Kiambu"],
            "target_price_per_unit": 50,
            "required_by": "2026-10-10",
            "intended_use": "Biomass Processing",
            "currency": "KES",
        },
    )
    assert requirement_response.status_code == 201, requirement_response.text

    match_response = client.post(
        f"/api/requirements/{requirement_response.json()['id']}/matches",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert match_response.status_code == 201, match_response.text
    match = match_response.json()
    assert match["quantity_sufficient"] is True
    assert match["matched_quantity"] == 2150
    assert match["requested_quantity"] == 2000
    assert match["supplier_count"] == 5
    assert match["surplus"] == 150
    assert match["shortfall"] == 0
    assert sum(float(item["quantity"]) for item in match["items"]) == 2000
