"""
Shared fixtures for the AI QA Framework test suite.

Configuration via environment variables:
    ANTHROPIC_API_KEY   - Required for Anthropic/Claude tests
    OPENAI_API_KEY      - Required for OpenAI/GPT tests
    GOOGLE_API_KEY      - Required for Google/Gemini tests
    LLM_PROVIDER        - Provider to use: anthropic, openai, google (default: anthropic)
    MODEL               - Override the default model for the selected provider
"""

import os
import sys

import anthropic
import pytest
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# Add src/ to path so we can import llm_client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_client import LLMClient  # noqa: E402

# Default model used across all tests — change here to switch globally
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def pytest_addoption(parser):
    """Add CLI options for provider and model selection."""
    parser.addoption(
        "--provider",
        action="store",
        default=None,
        help="LLM provider: anthropic, openai, google",
    )
    parser.addoption(
        "--model",
        action="store",
        default=None,
        help="Model name to use (overrides provider default)",
    )


# -- Direct Anthropic fixtures (backward compatible) -------------------------


@pytest.fixture
def client():
    """Initialize and return an Anthropic client.

    Skips the test automatically if ANTHROPIC_API_KEY is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


@pytest.fixture
def model():
    """Return the default model name.

    Override via the MODEL environment variable:
        MODEL=claude-haiku-4-20250514 pytest tests/
    """
    return os.getenv("MODEL", DEFAULT_MODEL)


# -- Multi-provider fixtures -------------------------------------------------


@pytest.fixture
def llm(request):
    """Initialize a unified LLMClient based on config.

    Usage in tests:
        def test_something(llm):
            response = llm.ask("Hello")
            assert "hello" in response.text.lower()

    Configuration priority:
        1. CLI: pytest --provider openai --model gpt-4o
        2. Env: LLM_PROVIDER=openai MODEL=gpt-4o pytest
        3. Default: anthropic / claude-sonnet-4-20250514
    """
    provider = (
        request.config.getoption("--provider")
        or os.getenv("LLM_PROVIDER", "anthropic")
    )
    model_name = (
        request.config.getoption("--model")
        or os.getenv("MODEL")
        or None
    )

    try:
        return LLMClient(provider=provider, model=model_name)
    except EnvironmentError as e:
        pytest.skip(str(e))
