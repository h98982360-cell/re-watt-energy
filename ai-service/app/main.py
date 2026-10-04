from fastapi import Depends, FastAPI, Header, HTTPException
from app.config import settings
from app.schemas.common import AIResponse
from app.schemas.compatibility import CompatibilityRequest
from app.schemas.material import MaterialInsightRequest
from app.services.compatibility import get_compatibility_insight
from app.services.llm import AIUnavailableError
from app.services.material_insight import get_material_insight

app = FastAPI(title="AI Service")
# The backend calls the two endpoints below. They return a 200 with available=false instead of an error response if the LLM fails, so the backend can continue to work without crashing.
UNAVAILABLE = "AI insight is temporarily unavailable."

# Rejects any request whose x-api-key header does not match our secret
def check_api_key(x_api_key: str = Header()):
    # rejects any request whose x-api-key header does not match our secret
    if x_api_key != settings.ai_service_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

# lets the backend check the service is running
@app.get("/health")
def health():
    return {"status": "ok"}

# The two endpoints below are the only ones the backend calls. They return a 200 with available=false instead of an error response if the LLM fails, so the backend can continue to work without crashing.
@app.post(
    "/ai/material-insight",
    response_model=AIResponse,
    dependencies=[Depends(check_api_key)],
)
def material_insight(request: MaterialInsightRequest):
    # any AI failure becomes available=false instead of an error response
    try:
        result = get_material_insight(request)
    except AIUnavailableError:
        return AIResponse(available=False, message=UNAVAILABLE)
    return AIResponse(available=True, data=result.model_dump())

# The backend calls this endpoint to get a compatibility insight from the LLM. It returns a 200 with available=false instead of an error response if the LLM fails, so the backend can continue to work without crashing.
@app.post(
    "/ai/compatibility-insight",
    response_model=AIResponse,
    dependencies=[Depends(check_api_key)],
)
def compatibility_insight(request: CompatibilityRequest):
    # success returns data, failure returns the fallback
    try:
        result = get_compatibility_insight(request)
    except AIUnavailableError:
        return AIResponse(available=False, message=UNAVAILABLE)
    return AIResponse(available=True, data=result.model_dump())