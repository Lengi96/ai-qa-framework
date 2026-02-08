# AI/LLM Quality Assurance Framework

Automated testing framework for evaluating Large Language Model (LLM) outputs in production environments.

## Purpose

Modern applications integrate AI/LLM features (chatbots, content generation, document analysis). Traditional QA methods fail because:

- Non-deterministic outputs (same input produces different responses)
- No classical "expected results"
- New risk categories: hallucinations, prompt injections, data leakage

This framework provides **46 automated tests** across 7 quality dimensions designed specifically for LLM evaluation.

## Test Categories

| Category | Tests | What it covers |
|---|---|---|
| **Security** | 3 | Prompt injection resistance, API key leakage, PII generation |
| **Consistency** | 3 | Semantic consistency, output stability, tone compliance |
| **Hallucination** | 5 | Fact accuracy, fictitious persons/events, fake URLs, math |
| **Performance** | 5 | Response time SLAs, token efficiency, latency monitoring |
| **Bias Detection** | 5 | Gender neutrality, cultural fairness, stereotypes, age, politics |
| **RAG Evaluation** | 8 | Context faithfulness, grounding, contradictions, citation accuracy |
| **UI Testing** | 17 | Chat flow, rendering, loading states, accessibility, responsive design |

## Multi-Model Support

The framework supports multiple LLM providers through a unified interface:

| Provider | Models | API Key |
|---|---|---|
| **Anthropic** (default) | Claude Sonnet, Haiku, Opus | `ANTHROPIC_API_KEY` |
| **OpenAI** | GPT-4o, GPT-4, GPT-3.5 | `OPENAI_API_KEY` |
| **Google** | Gemini 2.0 Flash, Gemini Pro | `GOOGLE_API_KEY` |

## Installation

```bash
# Clone repository
git clone https://github.com/Lengi96/ai-qa-framework.git
cd ai-qa-framework

# Install core dependencies
pip install -r requirements.txt

# Optional: install extras
pip install .[openai]       # OpenAI support
pip install .[google]       # Google Gemini support
pip install .[ui]           # Playwright UI testing
pip install .[dashboard]    # Dashboard generation
pip install .[all]          # Everything

# For UI testing: install browser
playwright install chromium

# Configure API key
cp .env.example .env
# Edit .env and add your API key(s)
```

## Running Tests

```bash
# Run all LLM tests (default: Anthropic Claude)
pytest

# Generate HTML report
pytest --html=report.html --self-contained-html

# Run specific test category
pytest tests/test_security.py
pytest tests/test_rag.py

# Use a different provider
pytest --provider openai --model gpt-4o
pytest --provider google --model gemini-2.0-flash

# Or via environment variables
LLM_PROVIDER=openai MODEL=gpt-4o pytest
```

## Custom Metric Dashboard

Generate an interactive HTML dashboard with charts and category breakdowns:

```bash
# 1. Install dashboard dependencies
pip install .[dashboard]

# 2. Run tests with JSON output
pytest tests/ -m "not ui" --json-report --json-report-file=results.json

# 3. Generate dashboard
python -m src.dashboard.generate results.json -o dashboard.html
```

The dashboard shows:
- Overall pass rate with status banner
- Metrics cards (total, passed, failed, skipped, duration)
- Stacked bar chart by category
- Donut chart for result distribution
- Detailed test table with durations

## UI Testing with Playwright

The framework includes 17 generic chatbot UI tests that work against any chat interface. Tests cover input/output flow, markdown rendering, loading states, error handling, accessibility, responsive design, and performance.

### Running UI Tests

```bash
# Basic usage with default CSS selectors
pytest tests/test_ui.py --base-url http://localhost:3000

# With visible browser for debugging
pytest tests/test_ui.py --base-url http://localhost:3000 --headed

# Custom selectors for your specific chat UI
pytest tests/test_ui.py --base-url https://my-chatbot.com \
    --selector-input "#prompt-textarea" \
    --selector-send "button.send-btn" \
    --selector-response ".chat-bubble.assistant"

# Run only LLM tests (skip UI)
pytest -m "not ui"
```

### Configurable Selectors

| CLI Option | Env Variable | What it targets |
|---|---|---|
| `--selector-input` | `UI_SELECTOR_INPUT` | Chat input field |
| `--selector-send` | `UI_SELECTOR_SEND` | Send button |
| `--selector-messages` | `UI_SELECTOR_MESSAGES` | Messages container |
| `--selector-response` | `UI_SELECTOR_RESPONSE` | Bot response messages |
| `--selector-loading` | `UI_SELECTOR_LOADING` | Loading indicator |
| `--selector-error` | `UI_SELECTOR_ERROR` | Error display |

Default selectors cover common patterns (`data-testid`, typical class names, ARIA attributes) and may work out of the box with many chat UIs.

## Project Structure

```
ai-qa-framework/
├── .env.example                 # API key & UI config template
├── .github/workflows/tests.yml  # CI/CD pipeline (LLM + UI jobs)
├── pyproject.toml               # Project config & pytest settings
├── requirements.txt             # Python dependencies
├── src/
│   ├── llm_client.py            # Unified multi-provider LLM client
│   └── dashboard/
│       └── generate.py          # HTML dashboard generator
└── tests/
    ├── conftest.py              # Shared fixtures & CLI options
    ├── ui_selectors.py          # Default CSS selectors for UI tests
    ├── test_security.py         # Security tests
    ├── test_consistency.py      # Consistency tests
    ├── test_hallucination.py    # Hallucination detection
    ├── test_performance.py      # Performance & SLA tests
    ├── test_bias.py             # Bias detection tests
    ├── test_rag.py              # RAG evaluation tests
    └── test_ui.py               # Chatbot UI tests (Playwright)
```

## CI/CD

GitHub Actions pipeline with two jobs:

**LLM Tests** — runs automatically on:
- Push to `main`
- Pull requests
- Weekly schedule (Monday 8:00 UTC)
- Manual trigger

**UI Tests** — runs only when `CHATBOT_BASE_URL` is configured as a repository variable.

Test reports are uploaded as artifacts (30 days retention).

**Setup:**
- Add `ANTHROPIC_API_KEY` as a repository **secret** under Settings > Secrets and variables > Actions
- For UI tests: add `CHATBOT_BASE_URL` as a repository **variable**

## Tech Stack

- Python 3.11+
- Pytest + pytest-html + pytest-json-report
- Anthropic / OpenAI / Google Generative AI SDKs
- Playwright (UI testing)
- Chart.js (dashboard visualizations)
- GitHub Actions (CI/CD)

## Roadmap

- [x] Security testing
- [x] Consistency testing
- [x] Hallucination detection
- [x] Performance testing
- [x] Bias detection
- [x] Multi-model support (Claude, GPT, Gemini)
- [x] CI/CD pipeline
- [x] UI testing integration (Playwright)
- [x] Custom metric dashboards
- [x] RAG evaluation tests

## License

MIT License - see [LICENSE](LICENSE) file

## Author

**Christoph Lengowski** - IT Consultant specializing in QA & AI Testing
