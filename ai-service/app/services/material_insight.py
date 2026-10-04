import logging

from app.prompts.material_insight import SYSTEM_PROMPT
from app.schemas.material import (
    MaterialInsightDraft,
    MaterialInsightRequest,
    MaterialInsightResult,
)
from app.services.llm import AIUnavailableError, generate_structured
from app.utils.validation import has_invented_numbers, numbers_in

logger = logging.getLogger(__name__)

# The model cannot change it
DISCLAIMER = "Actual suitability depends on buyer specifications and material quality."

# Function to get material insight
def get_material_insight(request: MaterialInsightRequest) -> MaterialInsightResult:
    # the listing as JSON is the only information the model gets
    facts = request.model_dump_json()
    draft = generate_structured(SYSTEM_PROMPT, facts, MaterialInsightDraft)

    # joins everything the model wrote into one text so we can scan it
    written = " ".join(
        [
            draft.summary,
            *draft.potential_uses,
            *draft.potential_buyer_types,
            *draft.important_characteristics,
        ]
    )

    # rejects the answer if the model used a number that is not in the listing
    if has_invented_numbers(written, facts):
        # logs the numbers that were not in the input, so you can see why it was rejected
        logger.warning("rejected, invented numbers: %s", numbers_in(written) - numbers_in(facts))
        raise AIUnavailableError("response contained numbers not in the input")

    # adds the two fields our code controls to the model's draft
    return MaterialInsightResult(
        **draft.model_dump(), material=request.material, disclaimer=DISCLAIMER
    )