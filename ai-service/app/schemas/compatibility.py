from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import Condition, Unit

# The only values we accept, shared by both capabilities.
class BuyerRequirement(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    material: str = Field(min_length=2, max_length=100)
    required_quantity: float = Field(gt=0)
    unit: Unit
    condition: Condition
    purpose: str | None = Field(None, max_length=200)

# What the backend sends us.
class MatchResult(BaseModel):
    supplier_count: int = Field(ge=0)
    matched_quantity: float = Field(ge=0)
    required_quantity: float = Field(gt=0)
    quantity_sufficient: bool
    material_compatible: bool
    condition_compatible: bool

# The request we send to the LLM, which includes the buyer's requirement and the match result.
class CompatibilityRequest(BaseModel):
    buyer_requirement: BuyerRequirement
    match_result: MatchResult

# The request we send to the LLM
class CompatibilityDraft(BaseModel):
    reasons: list[str] = Field(min_length=1)
    considerations: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)

# The final answer: the rating is set by our code, not the LLM.
class CompatibilityResult(CompatibilityDraft):
    compatibility: Literal["high", "partial", "low"]
