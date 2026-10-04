import json
import logging
from pydantic import BaseModel
from groq import Groq
from app.config import settings

logger = logging.getLogger(__name__)

# one Groq client for the whole app, using the key and timeout from .env
client = Groq(api_key=settings.groq_api_key, timeout=settings.llm_timeout_seconds)


# the only error the rest of the app has to handle
class AIUnavailableError(Exception):
    pass

# Function to generate structured data
def generate_structured(
    system_prompt: str, user_prompt: str, output_model: type[BaseModel]
) -> BaseModel:
    # adds the expected JSON shape to the rules so the model knows which keys to return
    schema = json.dumps(output_model.model_json_schema())
    system = f"{system_prompt}\n\nReply with JSON only, matching this schema:\n{schema}"

    try:
        # sends both prompts to Groq and asks for a JSON object back
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,  # no randomness, so the same input gives a steady answer
        )
        text = response.choices[0].message.content

        # an empty reply counts as a failure
        if not text:
            raise ValueError("empty response")

        # checks the JSON against our model, rejecting missing or wrong-type fields
        return output_model.model_validate_json(text)

    except Exception as error:
        # any failure (timeout, Groq error, bad JSON) becomes one error type,
        # and the real cause is logged for you to read
        logger.error("LLM call failed: %s", error)
        raise AIUnavailableError("LLM call failed") from error