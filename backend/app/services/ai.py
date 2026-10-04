from __future__ import annotations

from typing import Any

import httpx

from ..config import settings


class AIServiceError(Exception):
    pass


def request_insight(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.ai_service_api_key:
        return {
            "available": False,
            "message": "AI service is not configured.",
        }

    url = f"{settings.ai_service_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = httpx.post(
            url,
            headers={"x-api-key": settings.ai_service_api_key},
            json=payload,
            timeout=settings.ai_service_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise AIServiceError("AI service request failed") from error

    if not isinstance(body, dict) or "available" not in body:
        raise AIServiceError("AI service returned an invalid response")
    return body
