from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ...database import get_db
from ...models import BuyerProfile, SupplierProfile, User, VerificationRecord
from ...security import require_roles

router = APIRouter(prefix="/admin", tags=["Administration"])


class VerificationDecisionIn(BaseModel):
    decision: Literal["verified", "rejected"]
    note: str | None = Field(default=None, max_length=2000)


@router.get("/verifications/pending")
def pending_verifications(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    users = db.scalars(
        select(User)
        .where(User.role.in_(["supplier", "buyer"]), User.status == "pending")
        .options(joinedload(User.supplier_profile), joinedload(User.buyer_profile))
        .order_by(User.created_at.asc())
    ).unique().all()
    return [
        {
            "user_id": user.id,
            "email": user.email,
            "name": user.full_name,
            "role": user.role,
            "business_name": (
                user.supplier_profile.business_name
                if user.supplier_profile
                else user.buyer_profile.business_name if user.buyer_profile else None
            ),
            "county": (
                user.supplier_profile.county
                if user.supplier_profile
                else user.buyer_profile.county if user.buyer_profile else None
            ),
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


@router.patch("/verifications/{user_id}")
def decide_verification(
    user_id: int,
    payload: VerificationDecisionIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    user = db.scalar(
        select(User)
        .where(User.id == user_id, User.role.in_(["supplier", "buyer"]))
        .options(joinedload(User.supplier_profile), joinedload(User.buyer_profile))
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    if user.status != "pending":
        raise HTTPException(status_code=409, detail="This account has already been reviewed.")
    now = datetime.now(timezone.utc)
    profile = user.supplier_profile or user.buyer_profile
    if profile is None:
        raise HTTPException(status_code=409, detail="Account profile is incomplete.")
    profile.verification_status = payload.decision
    profile.verified_at = now if payload.decision == "verified" else None
    profile.verified_by_id = admin.id
    user.status = "active" if payload.decision == "verified" else "rejected"
    db.add(
        VerificationRecord(
            user_id=user.id,
            type="business",
            status=payload.decision,
            reviewed_by_id=admin.id,
            reviewed_at=now,
            review_notes=payload.note,
        )
    )
    db.commit()
    return {"user_id": user.id, "status": user.status, "verification_status": profile.verification_status}
