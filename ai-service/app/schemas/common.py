from typing import Literal
from pydantic import BaseModel

# Values accepted, shared by both categories
Unit = Literal["kg", "pieces"]
Condition = Literal["dry", "moist", "wet", "working", "degraded", "faulty", "unknown"]
# Every endpoint returns this shape, so the backend only handles one format.
class AIResponse(BaseModel):
    available: bool
    data: dict | None = None
    message: str | None = None
