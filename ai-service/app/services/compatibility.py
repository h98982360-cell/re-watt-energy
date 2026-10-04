import json
import logging
from app.prompts.compatibility import SYSTEM_PROMPT
from app.schemas.compatibility import (
    CompatibilityDraft,
    CompatibilityRequest,
    CompatibilityResult,
    MatchResult,
)
from app.services.llm import AIUnavailableError, generate_structured
from app.utils.validation import has_invented_numbers, numbers_in

logger = logging.getLogger(__name__)

# Function to get rating 
def get_rating(match: MatchResult) -> str:
    # high when all three backend checks passed
    if match.quantity_sufficient and match.material_compatible and match.condition_compatible:
        return "high"

    # partial when only the quantity falls short
    if match.material_compatible and match.condition_compatible:
        return "partial"

    # low when the material or the condition does not match
    return "low"

# Function to get compatibility insights 
def get_compatibility_insight(request: CompatibilityRequest) -> CompatibilityResult:
    # the rating comes from our code, not from the model
    rating = get_rating(request.match_result)

    # the model gets the backend's facts plus the rating to explain
    facts = json.dumps({**request.model_dump(), "compatibility_rating": rating})
    draft = generate_structured(SYSTEM_PROMPT, facts, CompatibilityDraft)

    # joins everything the model wrote into one text so we can scan it
    written = " ".join([draft.summary, *draft.reasons, *draft.considerations])

    # rejects the answer if the model used a number that is not in the facts
    if has_invented_numbers(written, facts):
        # logs the numbers that were not in the input, so you can see why it was rejected
        logger.warning("rejected, invented numbers: %s", numbers_in(written) - numbers_in(facts))
        raise AIUnavailableError("response contained numbers not in the input")

    # adds the rating our code chose to the model's draft
    return CompatibilityResult(**draft.model_dump(), compatibility=rating)


    