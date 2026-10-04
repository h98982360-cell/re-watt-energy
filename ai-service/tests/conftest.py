import json
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# Fake settings set before the app loads, so tests never use the real .env or key.
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["GROQ_MODEL"] = "test-model"
os.environ["LLM_TIMEOUT_SECONDS"] = "5"
os.environ["AI_SERVICE_API_KEY"] = "test-key"

from app.main import app as api  # noqa: E402
from app.services import llm  # noqa: E402


# Stands in for the Groq client and returns whatever the test asks for.
class FakeGroq:
    def __init__(self, content, error):
        self.content = content
        self.error = error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        # Raises the error if the test set one, otherwise returns the content.
        if self.error:
            raise self.error
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def client():
    # A test client that sends the correct API key with every request.
    return TestClient(api, headers={"x-api-key": "test-key"})


@pytest.fixture
def bare_client():
    # A test client that sends no API key, used for the auth tests.
    return TestClient(api)


@pytest.fixture
def llm_reply(monkeypatch):
    def set_reply(reply=None, error=None):
        # Dicts become JSON text; anything else is sent exactly as given.
        content = json.dumps(reply) if isinstance(reply, dict) else reply
        monkeypatch.setattr(llm, "client", FakeGroq(content, error))

    return set_reply
