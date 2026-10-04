from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Category, Material

DEFAULT_CATALOG = (
    {
        "slug": "agricultural-residues",
        "name": "Agricultural residues",
        "description": "Useful agricultural by-products and biomass feedstock.",
        "materials": (
            {
                "slug": "maize-cobs",
                "name": "Maize cobs",
                "description": "Maize cobs for biomass processing and other productive uses.",
                "typical_conditions": ["dry", "mixed", "wet"],
                "typical_units": ["kg", "tonne", "bag"],
                "primary_uses": ["Briquettes", "Pellets", "Biomass fuel"],
                "buyer_types": ["Biomass processors", "Briquette producers", "Pellet processors"],
                "quality_notes": "Dry, clean material is generally preferred. Condition should be confirmed at handover.",
            },

        ),
    },
    {
        "slug": "energy-storage",
        "name": "Energy storage",
        "description": "Used and recoverable batteries and energy storage components.",
        "materials": (
            {
                "slug": "battery",
                "name": "Battery",
                "description": "Used or end-of-life batteries for recycling, refurbishment, or repurposing.",
                "typical_conditions": ["working", "degraded", "unknown"],
                "typical_units": ["pieces", "kg"],
                "primary_uses": ["Recycling", "Refurbishment", "Energy storage repurposing"],
                "buyer_types": ["Recyclers", "Refurbishers", "E-waste processors"],
                "quality_notes": "State of charge and cycle count should be disclosed where known.",
            },
        ),
    },
    {
        "slug": "solar-equipment",
        "name": "Solar equipment",
        "description": "Used and recoverable solar panels and photovoltaic components.",
        "materials": (
            {
                "slug": "solar-panel",
                "name": "Solar panel",
                "description": "Used or decommissioned solar panels for resale, refurbishment, or recycling.",
                "typical_conditions": ["working", "degraded", "unknown"],
                "typical_units": ["pieces", "kg"],
                "primary_uses": ["Resale", "Refurbishment", "Recycling"],
                "buyer_types": ["Solar installers", "Recyclers", "Refurbishers"],
                "quality_notes": "Wattage rating and visible damage should be disclosed at listing.",
            },
        ),
    },
)


def seed_catalog(db: Session) -> None:
    for category_data in DEFAULT_CATALOG:
        category = db.scalar(select(Category).where(Category.slug == category_data["slug"]))
        if category is None:
            category = Category(
                slug=category_data["slug"],
                name=category_data["name"],
                description=category_data["description"],
                sort_order=0,
                is_active=True,
            )
            db.add(category)
            db.flush()
        for material_data in category_data["materials"]:
            material = db.scalar(
                select(Material).where(
                    Material.category_id == category.id,
                    Material.slug == material_data["slug"],
                )
            )
            if material is None:
                db.add(Material(category_id=category.id, **material_data))
    db.commit()
