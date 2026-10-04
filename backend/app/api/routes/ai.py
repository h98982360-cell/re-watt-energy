from __future__ import annotations

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ...database import get_db
from ...models import BuyerRequirement, Listing, Match, User
from ...security import require_roles
from ...services.ai import AIServiceError, request_insight
from ...services.units import base_unit_for, from_base

router = APIRouter(prefix="/ai", tags=["AI"])

AIUnit = Literal["kg", "pieces"]
AICondition = Literal["dry", "moist", "wet", "working", "degraded", "faulty", "unknown"]


class ListingInsightIn(BaseModel):
    listing_id: int = Field(gt=0)


class RequirementInsightIn(BaseModel):
    requirement_id: int = Field(gt=0)
    match_id: int | None = Field(default=None, gt=0)


def _ai_unit(unit: str) -> AIUnit:
    base_unit = base_unit_for(unit)
    if base_unit == "kg":
        return "kg"
    if base_unit == "piece":
        return "pieces"
    raise HTTPException(
        status_code=422,
        detail="AI insights support only kilogram and piece quantities.",
    )


def _ai_condition(condition: str) -> AICondition:
    if condition in {"dry", "moist", "wet", "working", "degraded", "faulty"}:
        return condition  # type: ignore[return-value]
    return "unknown"


def _ai_error_response(error: AIServiceError) -> dict[str, object]:
    return {"available": False, "message": str(error)}


def _call_ai(path: str, payload: dict) -> dict[str, object]:
    try:
        return request_insight(path, payload)
    except AIServiceError as error:
        return _ai_error_response(error)


@router.post("/insights/listing")
def listing_insight(
    payload: ListingInsightIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("supplier", "admin")),
):
    listing = db.scalar(
        select(Listing)
        .where(Listing.id == payload.listing_id)
        .options(joinedload(Listing.material), joinedload(Listing.evidence))
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found.")
    if user.role != "admin" and listing.supplier_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this listing.")

    ai_payload = {
        "material": listing.material.name,
        "quantity": float(
            from_base(Decimal(listing.quantity_base), base_unit_for(listing.unit))
        ),
        "unit": _ai_unit(listing.unit),
        "condition": _ai_condition(listing.condition),
        "location": ", ".join(value for value in (listing.city, listing.county) if value) or None,
        "availability": listing.status,
        "description": listing.description or listing.material.description,
        "image_provided": bool(listing.evidence),
    }
    result = _call_ai("/ai/material-insight", ai_payload)
    listing.ai_insight_json = result
    db.commit()
    return result


@router.post("/insights/requirement")
def requirement_insight(
    payload: RequirementInsightIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("buyer", "admin")),
):
    requirement = db.scalar(
        select(BuyerRequirement)
        .where(BuyerRequirement.id == payload.requirement_id)
        .options(joinedload(BuyerRequirement.material))
    )
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found.")
    if user.role != "admin" and requirement.buyer_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this requirement.")

    match_query = select(Match).where(Match.requirement_id == requirement.id)
    if payload.match_id is not None:
        match_query = match_query.where(Match.id == payload.match_id)
    match = db.scalar(match_query.order_by(Match.created_at.desc()))
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found for this requirement.")

    unit = _ai_unit(requirement.unit)
    acceptable_conditions = [
        _ai_condition(condition) for condition in requirement.acceptable_conditions
    ]
    condition = acceptable_conditions[0] if len(set(acceptable_conditions)) == 1 else "unknown"
    ai_base_unit = base_unit_for(requirement.unit)
    required_quantity = from_base(Decimal(requirement.quantity_base), ai_base_unit)
    matched_quantity = from_base(Decimal(match.matched_quantity_base), ai_base_unit)
    condition_compatible = all(
        not acceptable_conditions or _ai_condition(item.get("condition", "unknown")) in acceptable_conditions
        for item in match.aggregation_snapshot
    )

    ai_payload = {
        "buyer_requirement": {
            "material": requirement.material.name,
            "required_quantity": float(required_quantity),
            "unit": unit,
            "condition": condition,
            "purpose": requirement.intended_use,
        },
        "match_result": {
            "supplier_count": match.supplier_count,
            "matched_quantity": float(matched_quantity),
            "required_quantity": float(required_quantity),
            "quantity_sufficient": matched_quantity >= required_quantity,
            "material_compatible": True,
            "condition_compatible": condition_compatible,
        },
    }
    return _call_ai("/ai/compatibility-insight", ai_payload)
