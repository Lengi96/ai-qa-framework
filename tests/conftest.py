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
import re
import sys

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
DEFAULT_MODEL = "claude-haiku-4-5"

_REPORT_ENHANCEMENT_MARKER = "ai-qa-report-enhancements"
_REPORT_EXTRA_STYLE = """
/* ai-qa-report-enhancements */
html, body {
  background: #f8fafc;
  color: #0f172a;
}
body {
  min-width: 0;
  max-width: 1280px;
  margin: 0 auto;
  padding: 1rem;
  font-size: 14px;
  line-height: 1.45;
}
a {
  color: #1d4ed8;
}
#results-table {
  color: #0f172a;
  display: block;
  overflow-x: auto;
  white-space: nowrap;
}
#results-table-head th {
  position: sticky;
  top: 0;
  z-index: 4;
  background: #e2e8f0;
}
#results-table th,
#results-table td,
#environment td {
  border-color: #cbd5e1;
}
.filters button,
.collapse button {
  color: #1e293b;
}
.filters button:hover,
.collapse button:hover {
  color: #0f172a;
}
button:focus-visible,
input:focus-visible,
.collapsible td[tabindex="0"]:focus-visible,
.logexpander:focus-visible {
  outline: 3px solid #2563eb;
  outline-offset: 2px;
}
@media (max-width: 900px) {
  body {
    padding: 0.75rem;
  }
  .summary__data,
  .summary__spacer {
    flex: 1 1 auto;
  }
.controls {
  margin-top: 0.5rem;
  padding: 0.5rem 0.65rem;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 8px;
  gap: 0.75rem;
}
.filters {
  gap: 0.35rem 0.7rem;
}
.filters .filter {
  margin-right: 0.2rem;
}
.filters span {
  display: inline-flex;
  align-items: center;
  padding: 0.12rem 0.4rem;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}
.filters .passed {
  color: #166534;
  background: #dcfce7;
}
.filters .failed {
  color: #991b1b;
  background: #fee2e2;
}
.filters .skipped,
.filters .xfailed,
.filters .xpassed,
.filters .error,
.filters .rerun,
.filters .retried {
  color: #92400e;
  background: #fef3c7;
}
#results-table .col-result {
  font-weight: 700;
}
#results-table .passed .col-result {
  color: #166534;
  background: #f0fdf4;
}
#results-table .failed .col-result {
  color: #991b1b;
  background: #fef2f2;
}
#results-table .skipped .col-result,
#results-table .xfailed .col-result,
#results-table .xpassed .col-result,
#results-table .error .col-result,
#results-table .rerun .col-result {
  color: #92400e;
  background: #fffbeb;
}
#results-table tbody tr:hover td {
  background: #f8fafc;
}
.summary .run-count {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}
.summary .filter {
  color: #334155;
}
button {
  border-radius: 6px;
  padding: 0.2rem 0.5rem;
}
button:hover {
  background: #e2e8f0;
}
@media (max-width: 900px) {
  .controls {
    width: 100%;
  }
  .filters span {
    font-size: 11px;
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    scroll-behavior: auto !important;
  }
}
@media (prefers-contrast: more) {
  #results-table .passed .col-result,
  #results-table .failed .col-result,
  #results-table .skipped .col-result,
  #results-table .xfailed .col-result,
  #results-table .xpassed .col-result,
  #results-table .error .col-result,
  #results-table .rerun .col-result {
    outline: 2px solid currentColor;
    outline-offset: -2px;
  }
}
@media (forced-colors: active) {
  #results-table .col-result,
  .filters span {
    border: 1px solid ButtonText;
  }
}

#environment-header h2 {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
#environment-header h2::before {
  content: "▾";
  font-size: 0.85em;
  color: #475569;
}
#environment-header.collapsed h2::before {
  content: "▸";
}

#results-table-head th {
  box-shadow: inset 0 -1px 0 #94a3b8;
}
#results-table-head th.sortable {
  user-select: none;
}
#results-table-head th.sortable:hover {
  background: #dbeafe;
}
#results-table-head th.sortable:focus-visible {
  outline: 3px solid #2563eb;
  outline-offset: -3px;
}

.summary__reload__button {
  border: 1px solid #16a34a;
}
.summary__reload__button:hover {
  background-color: #15803d;
}

#environment td:first-child {
  font-weight: 600;
  color: #0f172a;
}

#results-table td.col-testId {
  max-width: 52ch;
  overflow: hidden;
  text-overflow: ellipsis;
}

#results-table td.col-duration,
#results-table th[data-column-type="duration"] {
  text-align: right;
}

#results-table td.col-links {
  min-width: 70px;
}

#results-table .extras-row td {
  background: #f8fafc;
}

.logwrapper {
  border-radius: 6px;
}

.logwrapper .log {
  border-color: #cbd5e1;
}

.media {
  border-radius: 6px;
}

.media-container__nav--left,
.media-container__nav--right {
  font-weight: 700;
}

.col-result.collapsed:hover::after,
.col-result:hover::after {
  color: #64748b;
}

.sortable.asc:after,
.sortable.desc:after {
  border-left-width: 7px;
  border-right-width: 7px;
  border-top-width: 7px;
  border-bottom-width: 7px;
}

.summary {
  margin-bottom: 0.75rem;
}

.summary h2 {
  margin-bottom: 0.35rem;
}

.additional-summary.prefix,
.additional-summary.summary,
.additional-summary.postfix {
  color: #475569;
}

.summary__data a {
  font-weight: 600;
}

#not-found-message td {
  color: #334155;
  font-style: italic;
}

.filter__label {
  font-weight: 700;
  color: #1e293b;
}

#environment-header {
  cursor: pointer;
}

#environment-header h2 {
  color: #0f172a;
}

#results-table,
#environment {
  border-radius: 8px;
  overflow: hidden;
}

#results-table th,
#results-table td {
  vertical-align: top;
}

#results-table td.col-duration {
  white-space: nowrap;
}

#results-table td.col-links {
  white-space: nowrap;
}

#results-table .collapsible td:not(.col-links) {
  transition: background-color 120ms ease;
}

#results-table .collapsible td:not(.col-links):hover {
  background: #eff6ff;
}

#results-table .extras-row .extra {
  border-top: none;
}

#results-table-head th:last-child {
  text-align: center;
}

#results-table td.col-links {
  text-align: center;
}

.summary .controls .collapse {
  margin-left: auto;
}

@media (max-width: 900px) {
  .summary .controls .collapse {
    margin-left: 0;
  }
}

.summary .controls .collapse button {
  text-decoration: none;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
}

.summary .controls .collapse button:hover {
  background: #e2e8f0;
}

.summary .controls .collapse button:active {
  background: #cbd5e1;
}

.summary .controls .collapse button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.summary .controls .filters input[type="checkbox"] {
  accent-color: #2563eb;
}

.summary .controls .filters input[type="checkbox"]:disabled + span {
  opacity: 0.65;
}

.summary__reload {
  margin-top: 0.35rem;
}

.run-count {
  margin-bottom: 0.3rem;
}

.summary .filter {
  margin-bottom: 0.45rem;
}

.summary__reload__button {
  min-height: 40px;
}

.summary__reload__button div {
  line-height: 1.2;
}

.summary .controls .filters {
  align-items: center;
}

.summary .controls .collapse {
  align-items: center;
}

.summary .controls {
  align-items: center;
}

.summary__data {
  min-width: 0;
}

.summary__spacer {
  display: none;
}
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  .filters {
    flex-wrap: wrap;
    gap: 0.25rem 0.6rem;
  }
}
"""

_REPORT_EXTRA_SCRIPT = """
(() => {
  const reportTitle = 'AI QA Test Report';
  document.title = reportTitle;
  const headTitle = document.getElementById('head-title');
  const title = document.getElementById('title');
  if (headTitle) headTitle.textContent = reportTitle;
  if (title) title.textContent = reportTitle;

  const generatedLine = document.querySelector('body > p');
  if (generatedLine && !document.getElementById('dashboard-link')) {
    const sep = document.createTextNode(' | ');
    const link = document.createElement('a');
    link.id = 'dashboard-link';
    link.href = 'dashboard.html';
    link.textContent = 'Open dashboard';
    generatedLine.appendChild(sep);
    generatedLine.appendChild(link);
  }

  const envHeader = document.getElementById('environment-header');
  const envTable = document.getElementById('environment');
  if (envHeader && envTable) {
    envTable.classList.add('hidden');
    envHeader.classList.add('collapsed');
  }

  const filtersRoot = document.querySelector('.filters');
  if (filtersRoot) {
    const filterInputs = filtersRoot.querySelectorAll('input.filter');
    filterInputs.forEach((input) => {
      const countLabel = input.nextElementSibling;
      if (!countLabel) return;
      const text = countLabel.textContent || '';
      if (/^\\s*0\\b/.test(text)) {
        input.classList.add('hidden');
        countLabel.classList.add('hidden');
      }
    });
  }

  // Make expand/collapse cells keyboard-accessible.
  const cells = document.querySelectorAll('.collapsible td:not(.col-links)');
  cells.forEach((cell) => {
    cell.setAttribute('role', 'button');
    cell.setAttribute('tabindex', '0');
    cell.setAttribute('aria-label', 'Toggle test details');
    cell.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        cell.click();
      }
    });
  });

  const expanders = document.querySelectorAll('.logexpander');
  expanders.forEach((expander) => {
    expander.setAttribute('role', 'button');
    expander.setAttribute('tabindex', '0');
    expander.setAttribute('aria-label', 'Expand or collapse log output');
    expander.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        expander.click();
      }
    });
  });
})();
"""


def _enhance_pytest_html_report(report_path: str) -> None:
    """Apply accessibility and responsive UX enhancements to pytest-html output."""
    if not report_path or not os.path.exists(report_path):
        return

    with open(report_path, encoding="utf-8") as f:
        html = f.read()

    if _REPORT_ENHANCEMENT_MARKER in html:
        return

    if "<html>" in html:
        html = html.replace("<html>", '<html lang="en">', 1)

    if "name=\"viewport\"" not in html and "</head>" in html:
        html = html.replace(
            "</head>",
            '    <meta name="viewport" content="width=device-width, initial-scale=1"/>\n  </head>',
            1,
        )

    if "</style>" in html:
        html = html.replace(
            "</style>",
            f"\n{_REPORT_EXTRA_STYLE}\n</style>",
            1,
        )

    if "</body>" in html:
        html = html.replace(
            "</body>",
            (
                f"<script id=\"{_REPORT_ENHANCEMENT_MARKER}\">{_REPORT_EXTRA_SCRIPT}</script>\n"
                "</body>"
            ),
            1,
        )

    # Remove stale gray defaults in case the upstream report format changes.
    html = re.sub(r"color:\s*#999;", "color: #334155;", html)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)


def _looks_like_auth_error(exc: Exception) -> bool:
    message = str(exc).lower()
    indicators = (
        "authentication",
        "unauthorized",
        "invalid x-api-key",
        "invalid api key",
        "api key",
        "401",
    )
    return any(indicator in message for indicator in indicators)


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
    try:
        import anthropic
    except ImportError:
        pytest.skip("anthropic package is not installed")
    return anthropic.Anthropic(api_key=api_key)


@pytest.fixture
def model():
    """Return the default model name.

    Override via the MODEL environment variable:
        MODEL=claude-haiku-4-5 pytest tests/
    """
    return os.getenv("MODEL", DEFAULT_MODEL)


# -- Multi-provider fixtures -------------------------------------------------


@pytest.fixture(scope="session")
def llm(pytestconfig):
    """Initialize a unified LLMClient based on config.

    Usage in tests:
        def test_something(llm):
            response = llm.ask("Hello")
            assert "hello" in response.text.lower()

    Configuration priority:
        1. CLI: pytest --provider openai --model gpt-4o
        2. Env: LLM_PROVIDER=openai MODEL=gpt-4o pytest
        3. Default: anthropic / claude-haiku-4-5
    """
    provider = pytestconfig.getoption("--provider") or os.getenv("LLM_PROVIDER", "anthropic")
    model_name = (
        pytestconfig.getoption("--model")
        or os.getenv("MODEL")
        or None
    )

    try:
        client = LLMClient(provider=provider, model=model_name)
    except EnvironmentError as e:
        pytest.skip(str(e))
    try:
        client.ask("Ping", max_tokens=5)
    except Exception as e:
        if _looks_like_auth_error(e):
            pytest.skip(f"{provider} credentials invalid or unauthorized: {e}")
        raise

    return client


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


@pytest.hookimpl(trylast=True, hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):
    """Patch pytest-html report for better mobile UX and accessibility."""
    yield
    html_path = getattr(session.config.option, "htmlpath", None)
    if not html_path:
        return
    try:
        _enhance_pytest_html_report(os.path.abspath(str(html_path)))
    except OSError:
        # Never fail a test run because report post-processing failed.
        pass
