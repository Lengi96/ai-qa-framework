"""
Shared fixtures for the AI QA Framework test suite.
"""

import os

import anthropic
import pytest
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# Default model used across all tests — change here to switch globally
DEFAULT_MODEL = "claude-sonnet-4-20250514"


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
