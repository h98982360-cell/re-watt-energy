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
