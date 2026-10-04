from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .api.routes.admin import router as admin_router
from .api.routes.ai import router as ai_router
from .api.routes.auth import router as auth_router
from .api.routes.marketplace import router as marketplace_router
from .config import settings
from .database import SessionLocal, init_db
from .models import User
from .security import hash_password
from .services.catalog import seed_catalog


def _validate_production_settings() -> None:
    if settings.environment.lower() != "production":
        return
    if settings.secret_key == "dev-only-insecure-secret-change-me" or len(settings.secret_key) < 32:
        raise RuntimeError("Production requires a unique SECRET_KEY of at least 32 characters.")
    if settings.debug:
        raise RuntimeError("DEBUG must be false in production.")
    if settings.auto_create_schema:
        raise RuntimeError("AUTO_CREATE_SCHEMA must be false in production; apply migrations instead.")


def _bootstrap_admin() -> None:
    if not settings.admin_email and not settings.admin_password:
        return
    if not settings.admin_email or len(settings.admin_password) < 12:
        raise RuntimeError("Set both ADMIN_EMAIL and an ADMIN_PASSWORD of at least 12 characters.")
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == settings.admin_email.lower()))
        if existing:
            if existing.role != "admin":
                raise RuntimeError("ADMIN_EMAIL already belongs to a non-admin account.")
            return
        db.add(
            User(
                email=settings.admin_email.strip().lower(),
                password_hash=hash_password(settings.admin_password),
                full_name=settings.admin_name,
                role="admin",
                status="active",
                is_active=True,
            )
        )
        db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _validate_production_settings()
    if settings.auto_create_schema:
        init_db()
    with SessionLocal() as db:
        seed_catalog(db)
    _bootstrap_admin()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Verified, aggregated marketplace for recoverable materials.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(marketplace_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(ai_router, prefix=settings.api_prefix)


@app.get("/health", tags=["Operations"])
def health():
    return {"status": "ok", "service": "re-watt-energy-api"}
