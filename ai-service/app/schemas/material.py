from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import Condition, Unit

# What the backend sends us.
class MaterialInsightRequest(BaseModel):
    # Strips spaces around text, so whitespace cannot pass as a real value.
    model_config = ConfigDict(str_strip_whitespace=True)
    material: str = Field(min_length=2, max_length=100)
    quantity: float = Field(gt=0)
    unit: Unit
    condition: Condition
    location: str | None = Field(None, max_length=100)
    availability: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=1000)
    image_provided: bool = False

# The parts the LLM writes.
class MaterialInsightDraft(BaseModel):
    potential_uses: list[str] = Field(min_length=1)
    potential_buyer_types: list[str] = Field(min_length=1)
    important_characteristics: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)
    confidence: Literal["low", "medium", "high"]

# The final answer: the LLM draft plus two fields the code fills in.
class MaterialInsightResult(MaterialInsightDraft):
    material: str
    disclaimer: str
