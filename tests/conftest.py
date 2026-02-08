"""
Shared fixtures for the AI QA Framework test suite.

Configuration via environment variables:
    ANTHROPIC_API_KEY   - Required for Anthropic/Claude tests
    OPENAI_API_KEY      - Required for OpenAI/GPT tests
    GOOGLE_API_KEY      - Required for Google/Gemini tests
    LLM_PROVIDER        - Provider to use: anthropic, openai, google (default: anthropic)
    MODEL               - Override the default model for the selected provider
    CHATBOT_BASE_URL    - Base URL for Playwright UI tests
    UI_SELECTOR_*       - Override default CSS selectors for UI tests
"""

import os
import sys

import anthropic
import pytest
from dotenv import load_dotenv

# Load .env file from project root
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"), override=True)

# Add src/ and tests/ to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from llm_client import LLMClient  # noqa: E402
from ui_selectors import UISelectors  # noqa: E402

# Default model used across all tests — change here to switch globally
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def pytest_addoption(parser):
    """Add CLI options for provider, model, and UI testing."""
    # LLM options
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
    # UI / Playwright options
    parser.addoption(
        "--base-url",
        action="store",
        default=None,
        help="Base URL for chatbot UI tests",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run Playwright in headed mode (visible browser)",
    )
    parser.addoption(
        "--selector-input",
        action="store",
        default=None,
        help="CSS selector for chat input field",
    )
    parser.addoption(
        "--selector-send",
        action="store",
        default=None,
        help="CSS selector for send button",
    )
    parser.addoption(
        "--selector-messages",
        action="store",
        default=None,
        help="CSS selector for messages container",
    )
    parser.addoption(
        "--selector-response",
        action="store",
        default=None,
        help="CSS selector for bot response messages",
    )
    parser.addoption(
        "--selector-loading",
        action="store",
        default=None,
        help="CSS selector for loading indicator",
    )
    parser.addoption(
        "--selector-error",
        action="store",
        default=None,
        help="CSS selector for error display",
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


# -- Playwright / UI fixtures -----------------------------------------------


@pytest.fixture(scope="session")
def browser(request):
    """Launch a Playwright browser for UI tests.

    Skips all UI tests if Playwright is not installed.
    Use --headed to run with a visible browser window.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright is not installed (pip install playwright)")

    headed = request.config.getoption("--headed")
    pw = sync_playwright().start()
    bro = pw.chromium.launch(headless=not headed)
    yield bro
    bro.close()
    pw.stop()


@pytest.fixture
def page(request, browser):
    """Create a new browser page for each test.

    Navigates to --base-url or CHATBOT_BASE_URL.
    Skips if no base URL is configured.
    """
    base_url = (
        request.config.getoption("--base-url")
        or os.getenv("CHATBOT_BASE_URL")
    )
    if not base_url:
        pytest.skip("No --base-url or CHATBOT_BASE_URL configured")

    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.goto(base_url, wait_until="networkidle")
    yield pg
    pg.close()
    ctx.close()


@pytest.fixture
def ui_selectors(request):
    """Build UISelectors from CLI options, env vars, or defaults.

    Priority: CLI option > environment variable > default.
    """
    defaults = UISelectors()
    return UISelectors(
        input=(
            request.config.getoption("--selector-input")
            or os.getenv("UI_SELECTOR_INPUT")
            or defaults.input
        ),
        send=(
            request.config.getoption("--selector-send")
            or os.getenv("UI_SELECTOR_SEND")
            or defaults.send
        ),
        messages=(
            request.config.getoption("--selector-messages")
            or os.getenv("UI_SELECTOR_MESSAGES")
            or defaults.messages
        ),
        response=(
            request.config.getoption("--selector-response")
            or os.getenv("UI_SELECTOR_RESPONSE")
            or defaults.response
        ),
        loading=(
            request.config.getoption("--selector-loading")
            or os.getenv("UI_SELECTOR_LOADING")
            or defaults.loading
        ),
        error=(
            request.config.getoption("--selector-error")
            or os.getenv("UI_SELECTOR_ERROR")
            or defaults.error
        ),
    )
