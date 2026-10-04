from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric as SqlDecimal,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TimestampMixin, utcnow


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    materials: Mapped[list["Material"]] = relationship(
        "Material", back_populates="category",
        order_by="Material.sort_order",
        cascade="all, delete-orphan",
    )


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    typical_conditions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    typical_units: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    primary_uses: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    buyer_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    quality_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["Category"] = relationship("Category", back_populates="materials")

    __table_args__ = (
        UniqueConstraint("category_id", "slug", name="uq_materials_category_slug"),
        Index("ix_materials_category", "category_id"),
    )


class Listing(Base, TimestampMixin):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    condition: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity_declared: Mapped[Decimal] = mapped_column(SqlDecimal(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_base: Mapped[Decimal] = mapped_column(SqlDecimal(18, 4), nullable=False)
    price_per_unit: Mapped[Decimal | None] = mapped_column(SqlDecimal(14, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    county: Mapped[str | None] = mapped_column(String(128), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(SqlDecimal(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(SqlDecimal(9, 6), nullable=True)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    quantity_available_base: Mapped[Decimal] = mapped_column(SqlDecimal(18, 4), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ai_insight_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    supplier: Mapped["User"] = relationship("User", back_populates="listings")
    material: Mapped["Material"] = relationship("Material")
    evidence: Mapped[list["ListingEvidence"]] = relationship(
        "ListingEvidence", back_populates="listing", cascade="all, delete-orphan"
    )
    match_items: Mapped[list["MatchItem"]] = relationship(
        "MatchItem", back_populates="listing", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="listing", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_listings_material_status", "material_id", "status"),
        Index("ix_listings_supplier_status", "supplier_id", "status"),
        Index("ix_listings_location", "county"),
    )


class ListingEvidence(Base):
    __tablename__ = "listing_evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    listing: Mapped["Listing"] = relationship("Listing", back_populates="evidence")


class BuyerRequirement(Base, TimestampMixin):
    __tablename__ = "buyer_requirements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity_declared: Mapped[Decimal] = mapped_column(SqlDecimal(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_base: Mapped[Decimal] = mapped_column(SqlDecimal(18, 4), nullable=False)
    target_price_per_unit: Mapped[Decimal | None] = mapped_column(SqlDecimal(14, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    acceptable_conditions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    delivery_counties: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    max_radius_km: Mapped[Decimal | None] = mapped_column(SqlDecimal(10, 2), nullable=True)
    required_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    intended_use: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    buyer: Mapped["User"] = relationship("User", back_populates="requirements")
    material: Mapped["Material"] = relationship("Material")
    matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="requirement", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_requirements_material_status", "material_id", "status"),
        Index("ix_requirements_buyer", "buyer_id"),
    )


class Match(Base, TimestampMixin):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("buyer_requirements.id", ondelete="CASCADE"), nullable=False
    )
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="proposed", nullable=False)
    requested_quantity_base: Mapped[Decimal] = mapped_column(SqlDecimal(18, 4), nullable=False)
    matched_quantity_base: Mapped[Decimal] = mapped_column(
        SqlDecimal(18, 4), default=Decimal("0"), nullable=False
    )
    supplier_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coverage_percent: Mapped[Decimal] = mapped_column(
        SqlDecimal(7, 4), default=Decimal("0"), nullable=False
    )
    aggregation_snapshot: Mapped[list[dict]] = mapped_column(
        JSON, default=list, nullable=False
    )
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="buyer_search", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    requirement: Mapped["BuyerRequirement"] = relationship(
        "BuyerRequirement", back_populates="matches"
    )
    buyer: Mapped["User"] = relationship("User", back_populates="received_matches")
    items: Mapped[list["MatchItem"]] = relationship(
        "MatchItem", back_populates="match", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="match", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_matches_requirement", "requirement_id"),
        Index("ix_matches_status", "status"),
    )


class MatchItem(Base):
    __tablename__ = "match_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    quantity_offered_base: Mapped[Decimal] = mapped_column(SqlDecimal(18, 4), nullable=False)
    quantity_allocated_base: Mapped[Decimal] = mapped_column(
        SqlDecimal(18, 4), default=Decimal("0"), nullable=False
    )
    distance_km: Mapped[Decimal | None] = mapped_column(SqlDecimal(10, 3), nullable=True)
    fitness_score: Mapped[Decimal | None] = mapped_column(SqlDecimal(7, 4), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(SqlDecimal(14, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="invited", nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    match: Mapped["Match"] = relationship("Match", back_populates="items")
    listing: Mapped["Listing"] = relationship("Listing", back_populates="match_items")
    supplier_user: Mapped["User"] = relationship("User", back_populates="match_items")
    transaction: Mapped["Transaction | None"] = relationship(
        "Transaction",
        back_populates="match_item",
        foreign_keys="Transaction.match_item_id",
        uselist=False,
    )

    __table_args__ = (
        Index("ix_match_items_match", "match_id"),
        Index("ix_match_items_supplier", "supplier_id"),
        UniqueConstraint("match_id", "listing_id", name="uq_match_items_match_listing"),
    )


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int | None] = mapped_column(
        ForeignKey("matches.id", ondelete="SET NULL"), nullable=True
    )
    match_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("match_items.id", ondelete="SET NULL"), nullable=True
    )
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("buyer_requirements.id", ondelete="CASCADE"), nullable=False
    )
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)
    quantity_declared_base: Mapped[Decimal] = mapped_column(SqlDecimal(18, 4), nullable=False)
    quantity_received_base: Mapped[Decimal | None] = mapped_column(SqlDecimal(18, 4), nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(SqlDecimal(14, 4), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(SqlDecimal(16, 2), nullable=False)
    platform_fee: Mapped[Decimal] = mapped_column(
        SqlDecimal(16, 2), default=Decimal("0"), nullable=False
    )
    total: Mapped[Decimal] = mapped_column(SqlDecimal(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending_handover", nullable=False
    )
    payment_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    handover_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quantity_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    match: Mapped["Match | None"] = relationship("Match", back_populates="transactions")
    match_item: Mapped["MatchItem | None"] = relationship(
        "MatchItem",
        back_populates="transaction",
        foreign_keys=[match_item_id],
        uselist=False,
    )
    listing: Mapped["Listing"] = relationship("Listing", back_populates="transactions")
    supplier: Mapped["User"] = relationship(
        "User",
        foreign_keys="Transaction.supplier_id",
        back_populates="transactions_as_supplier",
    )
    buyer: Mapped["User"] = relationship(
        "User",
        foreign_keys="Transaction.buyer_id",
        back_populates="transactions_as_buyer",
    )
    material: Mapped["Material"] = relationship("Material")
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="transaction", cascade="all, delete-orphan"
    )
    dispute: Mapped["Dispute | None"] = relationship(
        "Dispute", back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_transactions_match", "match_id"),
        Index("ix_transactions_supplier", "supplier_id"),
        Index("ix_transactions_buyer", "buyer_id"),
        Index("ix_transactions_status", "status"),
    )


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    payer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    payee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(SqlDecimal(16, 2), nullable=False)
    platform_fee_amount: Mapped[Decimal] = mapped_column(
        SqlDecimal(16, 2), default=Decimal("0"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="payments")
    payer: Mapped["User"] = relationship(
        "User", foreign_keys="Payment.payer_id",
        back_populates="payments_made",
    )
    payee: Mapped["User"] = relationship(
        "User", foreign_keys="Payment.payee_id",
        back_populates="payments_received",
    )


class Dispute(Base, TimestampMixin):
    __tablename__ = "disputes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    opened_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    supplier_claim_qty_base: Mapped[Decimal | None] = mapped_column(SqlDecimal(18, 4), nullable=True)
    buyer_claim_qty_base: Mapped[Decimal | None] = mapped_column(SqlDecimal(18, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    resolution: Mapped[str] = mapped_column(String(64), default="none", nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="dispute")
    messages: Mapped[list["DisputeMessage"]] = relationship(
        "DisputeMessage", back_populates="dispute", cascade="all, delete-orphan"
    )


class DisputeMessage(Base):
    __tablename__ = "dispute_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dispute_id: Mapped[int] = mapped_column(
        ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    dispute: Mapped["Dispute"] = relationship("Dispute", back_populates="messages")


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    author: Mapped["User"] = relationship(
        "User", foreign_keys="Feedback.author_id", back_populates="feedback_given"
    )
    subject: Mapped["User"] = relationship(
        "User", foreign_keys="Feedback.subject_id", back_populates="feedback_received"
    )

    __table_args__ = (
        UniqueConstraint("transaction_id", "author_id", name="uq_feedback_transaction_author"),
    )


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at"),
        Index("ix_notifications_created", "created_at"),
    )
