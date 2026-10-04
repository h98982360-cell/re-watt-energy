from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, condecimal
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from ...config import settings
from ...database import get_db
from ...enums import ListingStatus, MatchStatus, TransactionStatus
from ...models import (
    BuyerRequirement,
    Category,
    Listing,
    Match,
    MatchItem,
    Material,
    Payment,
    Transaction,
    User,
)
from ...security import get_current_user, require_roles
from ...services.matching import allocate_supply, compatible_listings
from ...services.units import (
    are_compatible,
    base_unit_for,
    from_base,
    normalise_unit,
    to_base,
)

router = APIRouter(tags=["Marketplace"])


class ListingIn(BaseModel):
    material_id: int
    title: str = Field(min_length=3, max_length=255)
    condition: Literal["dry", "wet", "mixed", "contaminated", "processed", "unsorted", "unknown"]
    quantity: condecimal(gt=0, max_digits=14, decimal_places=4)
    unit: str = Field(min_length=1, max_length=32)
    price_per_unit: condecimal(ge=0, max_digits=14, decimal_places=4) | None = None
    county: str | None = Field(default=None, max_length=128)
    city: str | None = Field(default=None, max_length=128)
    available_from: date | None = None
    description: str | None = Field(default=None, max_length=4000)
    currency: str = Field(default="KES", min_length=3, max_length=8)


class RequirementIn(BaseModel):
    material_id: int
    title: str = Field(min_length=3, max_length=255)
    quantity: condecimal(gt=0, max_digits=14, decimal_places=4)
    unit: str = Field(min_length=1, max_length=32)
    acceptable_conditions: list[str] = Field(default_factory=list)
    delivery_counties: list[str] = Field(default_factory=list)
    target_price_per_unit: condecimal(ge=0, max_digits=14, decimal_places=4) | None = None
    required_by: date | None = None
    intended_use: str | None = Field(default=None, max_length=4000)
    description: str | None = Field(default=None, max_length=4000)
    currency: str = Field(default="KES", min_length=3, max_length=8)


class MatchResponseIn(BaseModel):
    accept: bool
    note: str | None = Field(default=None, max_length=1000)


class ReceiptIn(BaseModel):
    quantity_received: condecimal(gt=0, max_digits=14, decimal_places=4)


class PaymentIn(BaseModel):
    method: Literal["mobile_money", "bank_transfer", "cash", "other"]
    reference: str | None = Field(default=None, max_length=255)


def _date_at_utc(value: date | None) -> datetime | None:
    return datetime.combine(value, time.min, tzinfo=timezone.utc) if value else None


def _listing_out(listing: Listing) -> dict:
    return {
        "id": listing.id,
        "supplier_id": listing.supplier_id,
        "supplier_name": listing.supplier.full_name,
        "material_id": listing.material_id,
        "material": listing.material.name,
        "title": listing.title,
        "condition": listing.condition,
        "quantity": float(listing.quantity_declared),
        "quantity_available": float(from_base(listing.quantity_available_base, listing.unit)),
        "unit": listing.unit,
        "price_per_unit": float(listing.price_per_unit) if listing.price_per_unit is not None else None,
        "currency": listing.currency,
        "county": listing.county,
        "city": listing.city,
        "available_from": listing.available_from.date().isoformat() if listing.available_from else None,
        "description": listing.description,
        "status": listing.status,
    }


def _requirement_out(requirement: BuyerRequirement) -> dict:
    return {
        "id": requirement.id,
        "buyer_id": requirement.buyer_id,
        "material_id": requirement.material_id,
        "material": requirement.material.name,
        "title": requirement.title,
        "quantity": float(requirement.quantity_declared),
        "unit": requirement.unit,
        "acceptable_conditions": requirement.acceptable_conditions,
        "delivery_counties": requirement.delivery_counties,
        "target_price_per_unit": float(requirement.target_price_per_unit) if requirement.target_price_per_unit is not None else None,
        "required_by": requirement.required_by.date().isoformat() if requirement.required_by else None,
        "intended_use": requirement.intended_use,
        "description": requirement.description,
        "status": requirement.status,
    }


def _transaction_out(transaction: Transaction) -> dict:
    declared = from_base(transaction.quantity_declared_base, transaction.unit)
    return {
        "id": transaction.id,
        "match_id": transaction.match_id,
        "listing_id": transaction.listing_id,
        "material": transaction.material.name,
        "supplier_id": transaction.supplier_id,
        "supplier_name": transaction.supplier.full_name,
        "buyer_id": transaction.buyer_id,
        "buyer_name": transaction.buyer.full_name,
        "quantity_declared": float(declared),
        "quantity_received": (
            float(from_base(transaction.quantity_received_base, transaction.unit))
            if transaction.quantity_received_base is not None
            else None
        ),
        "unit": transaction.unit,
        "subtotal": float(transaction.subtotal),
        "platform_fee": float(transaction.platform_fee),
        "total": float(transaction.total),
        "currency": transaction.currency,
        "status": transaction.status,
        "created_at": transaction.created_at.isoformat(),
        "payments": [
            {
                "id": payment.id,
                "status": payment.status,
                "method": payment.method,
                "reference": payment.reference,
            }
            for payment in transaction.payments
        ],
    }


@router.get("/catalog")
def get_catalog(db: Session = Depends(get_db)):
    categories = db.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .options(joinedload(Category.materials))
        .order_by(Category.sort_order, Category.name)
    ).unique().all()
    return [
        {
            "id": category.id,
            "slug": category.slug,
            "name": category.name,
            "description": category.description,
            "materials": [
                {
                    "id": material.id,
                    "slug": material.slug,
                    "name": material.name,
                    "description": material.description,
                    "typical_conditions": material.typical_conditions,
                    "typical_units": material.typical_units,
                    "primary_uses": material.primary_uses,
                    "buyer_types": material.buyer_types,
                }
                for material in category.materials
                if material.is_active
            ],
        }
        for category in categories
    ]


@router.get("/listings")
def get_listings(
    db: Session = Depends(get_db),
):
    query = select(Listing).options(joinedload(Listing.supplier), joinedload(Listing.material))
    query = query.where(
        Listing.status.in_(
            [ListingStatus.ACTIVE.value, ListingStatus.PARTIALLY_ALLOCATED.value]
        ),
        Listing.quantity_available_base > 0,
    )
    listings = db.scalars(query.order_by(Listing.created_at.desc())).unique().all()
    return [_listing_out(listing) for listing in listings]


@router.post("/listings", status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("supplier")),
):
    if not user.supplier_profile or user.supplier_profile.verification_status != "verified":
        raise HTTPException(status_code=403, detail="Supplier verification is required before publishing a listing.")
    material = db.get(Material, payload.material_id)
    if material is None or not material.is_active:
        raise HTTPException(status_code=404, detail="Material not found.")
    unit = normalise_unit(payload.unit)
    try:
        quantity_base = to_base(payload.quantity, unit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if quantity_base <= 0:
        raise HTTPException(status_code=422, detail="Quantity is too small for the selected unit.")
    listing = Listing(
        supplier_id=user.id,
        material_id=material.id,
        title=payload.title.strip(),
        condition=payload.condition,
        quantity_declared=payload.quantity,
        unit=unit,
        quantity_base=quantity_base,
        price_per_unit=payload.price_per_unit,
        currency=payload.currency.upper(),
        county=payload.county,
        city=payload.city,
        available_from=_date_at_utc(payload.available_from),
        description=payload.description,
        status=ListingStatus.ACTIVE.value,
        quantity_available_base=quantity_base,
    )
    db.add(listing)
    db.commit()
    listing = db.scalar(
        select(Listing).where(Listing.id == listing.id).options(
            joinedload(Listing.supplier), joinedload(Listing.material)
        )
    )
    return _listing_out(listing)


@router.get("/requirements")
def get_requirements(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(BuyerRequirement).options(joinedload(BuyerRequirement.material))
    if user.role == "buyer":
        query = query.where(BuyerRequirement.buyer_id == user.id)
    elif user.role == "supplier":
        raise HTTPException(status_code=403, detail="Only buyers and admins can view requirements.")
    requirements = db.scalars(query.order_by(BuyerRequirement.created_at.desc())).unique().all()
    return [_requirement_out(requirement) for requirement in requirements]


@router.post("/requirements", status_code=status.HTTP_201_CREATED)
def create_requirement(
    payload: RequirementIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("buyer")),
):
    material = db.get(Material, payload.material_id)
    if material is None or not material.is_active:
        raise HTTPException(status_code=404, detail="Material not found.")
    unit = normalise_unit(payload.unit)
    try:
        quantity_base = to_base(payload.quantity, unit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    conditions = {condition.lower() for condition in payload.acceptable_conditions}
    allowed = {"dry", "wet", "mixed", "contaminated", "processed", "unsorted", "unknown"}
    if not conditions.issubset(allowed):
        raise HTTPException(status_code=422, detail="One or more material conditions are invalid.")
    requirement = BuyerRequirement(
        buyer_id=user.id,
        material_id=material.id,
        title=payload.title.strip(),
        description=payload.description,
        quantity_declared=payload.quantity,
        unit=unit,
        quantity_base=quantity_base,
        target_price_per_unit=payload.target_price_per_unit,
        currency=payload.currency.upper(),
        acceptable_conditions=sorted(conditions),
        delivery_counties=[county.strip() for county in payload.delivery_counties if county.strip()],
        required_by=_date_at_utc(payload.required_by),
        intended_use=payload.intended_use,
        status="open",
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    requirement = db.scalar(
        select(BuyerRequirement).where(BuyerRequirement.id == requirement.id).options(
            joinedload(BuyerRequirement.material)
        )
    )
    return _requirement_out(requirement)


@router.post("/requirements/{requirement_id}/matches", status_code=status.HTTP_201_CREATED)
def create_match(
    requirement_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("buyer")),
):
    requirement = db.scalar(
        select(BuyerRequirement)
        .where(BuyerRequirement.id == requirement_id, BuyerRequirement.buyer_id == user.id)
        .options(joinedload(BuyerRequirement.material))
    )
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found.")
    if requirement.status != "open":
        raise HTTPException(status_code=409, detail="This requirement is not open for matching.")
    query = (
        select(Listing)
        .where(Listing.status == ListingStatus.ACTIVE.value)
        .options(joinedload(Listing.supplier), joinedload(Listing.material))
    )
    candidates = compatible_listings(requirement, db.scalars(query).unique().all())
    allocations = allocate_supply(requirement, candidates)
    if not allocations:
        raise HTTPException(status_code=404, detail="No compatible active supply was found yet.")
    matched_quantity = sum((allocation["quantity_base"] for allocation in allocations), Decimal("0"))
    coverage = (matched_quantity / Decimal(requirement.quantity_base) * 100).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    match = Match(
        requirement_id=requirement.id,
        buyer_id=user.id,
        status=MatchStatus.REQUESTED.value,
        requested_quantity_base=requirement.quantity_base,
        matched_quantity_base=matched_quantity,
        supplier_count=len(allocations),
        coverage_percent=coverage,
        requested_at=datetime.now(timezone.utc),
        source="buyer_search",
    )
    db.add(match)
    db.flush()
    snapshot = []
    for allocation in allocations:
        listing = allocation["listing"]
        quantity = allocation["quantity_base"]
        item = MatchItem(
            match_id=match.id,
            listing_id=listing.id,
            supplier_id=listing.supplier_id,
            quantity_offered_base=listing.quantity_available_base,
            quantity_allocated_base=quantity,
            unit_price=listing.price_per_unit,
            currency=listing.currency,
            status="invited",
        )
        db.add(item)
        snapshot.append(
            {
                "listing_id": listing.id,
                "supplier_id": listing.supplier_id,
                "supplier_name": listing.supplier.full_name,
                "title": listing.title,
                "quantity_base": str(quantity),
                "quantity": str(from_base(quantity, listing.unit)),
                "unit": listing.unit,
                "condition": listing.condition,
                "county": listing.county,
            }
        )
    match.aggregation_snapshot = snapshot
    if matched_quantity >= Decimal(requirement.quantity_base):
        match.ai_explanation = (
            f"{len(allocations)} supplier offer(s) collectively cover the requested "
            f"{requirement.quantity_declared:g} {requirement.unit}. "
            "Condition and location filters were applied by marketplace rules."
        )
    else:
        match.ai_explanation = (
            f"Compatible listings currently cover {coverage}% of the requested quantity. "
            "More supply may be needed; this is a rules-based availability summary."
        )
    requirement.status = "match_requested"
    db.commit()
    db.refresh(match)
    return _match_out(match)


def _match_out(match: Match) -> dict:
    return {
        "id": match.id,
        "requirement_id": match.requirement_id,
        "status": match.status,
        "requested_quantity_base": float(match.requested_quantity_base),
        "matched_quantity_base": float(match.matched_quantity_base),
        "requested_quantity": float(match.requirement.quantity_declared),
        "matched_quantity": float(from_base(match.matched_quantity_base, match.requirement.unit)),
        "unit": match.requirement.unit,
        "base_unit": base_unit_for(match.requirement.unit),
        "supplier_count": match.supplier_count,
        "coverage_percent": float(match.coverage_percent),
        "explanation": match.ai_explanation,
        "items": match.aggregation_snapshot,
    }


@router.get("/matches")
def get_matches(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Match).options(joinedload(Match.requirement))
    if user.role == "buyer":
        query = query.where(Match.buyer_id == user.id)
    elif user.role == "supplier":
        query = query.join(MatchItem).where(MatchItem.supplier_id == user.id)
    matches = db.scalars(query.order_by(Match.created_at.desc())).unique().all()
    return [_match_out(match) for match in matches]


@router.post("/matches/{match_id}/respond")
def respond_to_match(
    match_id: int,
    payload: MatchResponseIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("supplier")),
):
    item = db.scalar(
        select(MatchItem)
        .where(MatchItem.match_id == match_id, MatchItem.supplier_id == user.id)
        .options(joinedload(MatchItem.match))
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Match invitation not found.")
    if item.status != "invited":
        raise HTTPException(status_code=409, detail="This invitation has already been answered.")
    match = item.match
    if match.status != MatchStatus.REQUESTED.value:
        raise HTTPException(status_code=409, detail="This match is no longer awaiting supplier responses.")
    item.status = "accepted" if payload.accept else "declined"
    item.response_note = payload.note
    item.responded_at = datetime.now(timezone.utc)

    if not payload.accept:
        match.status = MatchStatus.DECLINED.value
        match.requirement.status = "open"
        for remaining_item in match.items:
            if remaining_item.status == "invited":
                remaining_item.status = "withdrawn"
        db.commit()
        return {"status": match.status, "transactions": []}

    if all(candidate.status == "accepted" for candidate in match.items):
        created_transactions = []
        try:
            for candidate in match.items:
                listing = db.scalar(
                    select(Listing)
                    .where(Listing.id == candidate.listing_id)
                    .with_for_update()
                )
                if listing is None or listing.quantity_available_base < candidate.quantity_allocated_base:
                    raise HTTPException(
                        status_code=409,
                        detail="One or more listings no longer have enough available stock. Please run matching again.",
                    )
                new_available = listing.quantity_available_base - candidate.quantity_allocated_base
                statement = (
                    update(Listing)
                    .where(
                        Listing.id == listing.id,
                        Listing.quantity_available_base >= candidate.quantity_allocated_base,
                    )
                    .values(
                        quantity_available_base=new_available,
                        version=Listing.version + 1,
                        status=(
                            ListingStatus.FULLY_ALLOCATED.value
                            if new_available == 0
                            else ListingStatus.PARTIALLY_ALLOCATED.value
                        ),
                    )
                )
                if db.execute(statement).rowcount != 1:
                    raise HTTPException(status_code=409, detail="Listing stock changed; please run matching again.")
                quantity_declared = Decimal(candidate.quantity_allocated_base)
                if not are_compatible(listing.unit, match.requirement.unit):
                    raise HTTPException(status_code=422, detail="Listing and requirement units are incompatible.")
                listed_unit_quantity = quantity_declared
                from ...services.units import from_base

                listed_unit_quantity = from_base(quantity_declared, listing.unit)
                unit_price = Decimal(candidate.unit_price or 0)
                subtotal = (unit_price * listed_unit_quantity).quantize(Decimal("0.01"))
                fee = (subtotal * Decimal(str(settings.platform_fee_percent)) / Decimal("100")).quantize(
                    Decimal("0.01")
                )
                transaction = Transaction(
                    match_id=match.id,
                    match_item_id=candidate.id,
                    requirement_id=match.requirement_id,
                    listing_id=listing.id,
                    supplier_id=candidate.supplier_id,
                    buyer_id=match.buyer_id,
                    material_id=listing.material_id,
                    quantity_declared_base=quantity_declared,
                    unit=listing.unit,
                    unit_price=unit_price,
                    subtotal=subtotal,
                    platform_fee=fee,
                    total=subtotal + fee,
                    currency=candidate.currency or settings.currency,
                    status=TransactionStatus.PENDING_HANDOVER.value,
                )
                db.add(transaction)
                db.flush()
                candidate.status = "fulfilled"
                created_transactions.append(transaction.id)
            match.status = MatchStatus.CONFIRMED.value
            match.confirmed_at = datetime.now(timezone.utc)
            match.requirement.status = "confirmed"
            db.commit()
        except Exception:
            db.rollback()
            raise
        return {"status": match.status, "transactions": created_transactions}
    db.commit()
    return {"status": MatchStatus.PARTIALLY_ACCEPTED.value, "transactions": []}


@router.get("/transactions")
def get_transactions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Transaction).options(
        joinedload(Transaction.material),
        joinedload(Transaction.supplier),
        joinedload(Transaction.buyer),
    )
    if user.role == "supplier":
        query = query.where(Transaction.supplier_id == user.id)
    elif user.role == "buyer":
        query = query.where(Transaction.buyer_id == user.id)
    transactions = db.scalars(query.order_by(Transaction.created_at.desc())).unique().all()
    return [_transaction_out(transaction) for transaction in transactions]


@router.post("/transactions/{transaction_id}/confirm-receipt")
def confirm_receipt(
    transaction_id: int,
    payload: ReceiptIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("buyer")),
):
    transaction = db.scalar(
        select(Transaction)
        .where(Transaction.id == transaction_id, Transaction.buyer_id == user.id)
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if transaction.status not in {
        TransactionStatus.PENDING_HANDOVER.value,
        TransactionStatus.IN_TRANSIT.value,
        TransactionStatus.DELIVERED.value,
    }:
        raise HTTPException(status_code=409, detail="Receipt cannot be confirmed in the current transaction state.")
    try:
        received_base = to_base(payload.quantity_received, transaction.unit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if received_base > transaction.quantity_declared_base:
        raise HTTPException(status_code=422, detail="Received quantity cannot exceed the listed transaction quantity.")
    transaction.quantity_received_base = received_base
    transaction.quantity_confirmed_at = datetime.now(timezone.utc)
    transaction.status = TransactionStatus.PAYMENT_PENDING.value
    db.commit()
    return {"status": transaction.status, "quantity_received": float(received_base)}


@router.post("/transactions/{transaction_id}/payments", status_code=status.HTTP_201_CREATED)
def record_payment(
    transaction_id: int,
    payload: PaymentIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("buyer")),
):
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.buyer_id == user.id,
            Transaction.status == TransactionStatus.PAYMENT_PENDING.value,
        )
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="A payable transaction was not found.")
    payment = Payment(
        transaction_id=transaction.id,
        payer_id=transaction.buyer_id,
        payee_id=transaction.supplier_id,
        amount=transaction.total,
        platform_fee_amount=transaction.platform_fee,
        currency=transaction.currency,
        method=payload.method,
        reference=payload.reference,
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {"id": payment.id, "status": payment.status, "message": "Payment recorded for manual confirmation; no funds were moved."}


@router.post("/payments/{payment_id}/confirm-received")
def confirm_payment_received(
    payment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("supplier")),
):
    payment = db.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.payee_id == user.id)
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment record not found.")
    if payment.status != "pending":
        raise HTTPException(status_code=409, detail="This payment has already been confirmed.")
    payment.status = "released"
    payment.released_at = datetime.now(timezone.utc)
    payment.transaction.status = TransactionStatus.COMPLETED.value
    payment.transaction.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": payment.status, "transaction_status": payment.transaction.status}
