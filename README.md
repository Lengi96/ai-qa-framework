# AI/LLM Quality Assurance Framework

Automated testing framework for evaluating Large Language Model (LLM) outputs in production environments.

## 🎯 Purpose
Modern applications integrate AI/LLM features (chatbots, content generation, document analysis). Traditional QA methods fail because:
- Non-deterministic outputs (same input → different responses)
- No classical "expected results"
- New risk categories: hallucinations, prompt injections, data leakage

This framework provides automated tests for AI-specific quality dimensions.

## ✨ Features
- **Security Testing**: Prompt injection detection, sensitive data leakage prevention
- **Consistency Testing**: Verify similar inputs produce coherent outputs
- **Hallucination Detection**: Catch fabricated information
- **Performance Testing**: Response time SLAs, token efficiency
- **Brand Compliance**: Tone, language style validation

## 🚀 Use Cases
- Customer service chatbot validation
- AI-generated content quality assurance
- Continuous monitoring of LLM behavior
- Regression testing for prompt engineering changes

## 📦 Installation
```bash
# Clone repository
git clone https://github.com/christoph-lengowski/ai-qa-framework.git
cd ai-qa-framework

# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-api-key-here"
```

## 🧪 Running Tests
```bash
# Run all tests
pytest tests/

# Generate HTML report
pytest tests/ --html=report.html
```

## 📊 Test Categories
- `test_security.py`: Prompt injection, data leakage
- `test_consistency.py`: Output stability across similar inputs
- `test_hallucination.py`: Factual accuracy verification
- `test_performance.py`: Latency & token efficiency

## 🛠️ Tech Stack
- Python 3.11+
- Pytest
- Anthropic Claude API
- GitHub Actions (CI/CD)

## 📈 Roadmap
- [ ] Multi-model support (GPT-4, Gemini)
- [ ] UI testing integration (Playwright)
- [ ] Bias detection tests
- [ ] Custom metric dashboards

## 📝 License
MIT License - see LICENSE file

## 👤 Author
Christoph Lengowski - IT Consultant specializing in QA & AI Testing
```

4. Scroll runter, klick **"Commit changes"**
5. Im Pop-up: Klick **"Commit changes"** (nochmal bestätigen)

**3.2 requirements.txt erstellen**
1. Klick oben links auf **"ai-qa-framework"** (zurück zur Hauptseite)
2. Klick **"Add file"** → "Create new file"
3. Dateiname: `requirements.txt`
4. Inhalt:
```
anthropic==0.18.0
pytest==8.0.0
pytest-html==4.1.1
python-dotenv==1.0.0
