from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import BuyerProfile, SupplierProfile, User
from ...security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=255)
    role: Literal["supplier", "buyer"]
    phone: str | None = Field(default=None, max_length=32)
    supplier_type: str | None = Field(default=None, max_length=64)
    business_name: str = Field(min_length=2, max_length=255)
    business_type: str | None = Field(default=None, max_length=64)
    county: str | None = Field(default=None, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def require_supplier_type(self):
        if self.role == "supplier" and not self.supplier_type:
            raise ValueError("Supplier accounts require a supplier type.")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


def serialize_user(user: User) -> dict:
    profile = user.supplier_profile if user.role == "supplier" else user.buyer_profile
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "status": user.status,
        "is_verified": bool(profile and profile.verification_status == "verified"),
        "business_name": getattr(profile, "business_name", None),
        "county": getattr(profile, "county", None),
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=422, detail="Password must be no more than 72 UTF-8 bytes.")
    user = User(
        email=payload.email,
        phone=payload.phone or None,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        status="pending",
        is_active=True,
    )
    if payload.role == "supplier":
        user.supplier_profile = SupplierProfile(
            supplier_type=payload.supplier_type.strip(),
            business_name=payload.business_name.strip(),
            county=payload.county,
        )
    else:
        user.buyer_profile = BuyerProfile(
            business_name=payload.business_name.strip(),
            business_type=payload.business_type,
            county=payload.county,
        )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or phone already exists.",
        ) from None
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": serialize_user(user)}


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": serialize_user(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return serialize_user(user)
