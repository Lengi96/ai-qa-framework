"""
Consistency tests for LLM outputs
Verifies that similar inputs produce coherent, stable outputs
"""

import anthropic
import pytest
import os


class TestConsistency:
    
    @pytest.fixture
    def client(self):
        """Initialize Anthropic client"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set")
        return anthropic.Anthropic(api_key=api_key)
    
    def test_similar_questions_similar_answers(self, client):
        """
        Test: Semantically similar questions should yield consistent core information
        """
        questions = [
            "What is the capital of Germany?",
            "Tell me the capital city of Germany",
            "Which city is Germany's capital?",
            "Germany's capital is which city?"
        ]
        
        responses = []
        for question in questions:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                messages=[{"role": "user", "content": question}]
            )
            responses.append(message.content[0].text.lower())
        
        # All responses should mention Berlin
        for i, response in enumerate(responses):
            assert "berlin" in response, \
                f"Question {i+1} did not mention Berlin: {response}"
    
    def test_output_stability_over_time(self, client):
        """
        Test: Same question asked multiple times should give consistent answer
        """
        question = "What is 2 + 2?"
        expected_answer = "4"
        
        responses = []
        for _ in range(5):
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=50,
                messages=[{"role": "user", "content": question}]
            )
            responses.append(message.content[0].text)
        
        # All responses should contain "4"
        for response in responses:
            assert expected_answer in response, \
                f"Inconsistent answer: {response}"
    
    def test_tone_consistency(self, client):
        """
        Test: Multiple requests should maintain consistent tone
        """
        prompts = [
            "Explain machine learning",
            "What is artificial intelligence?",
            "Describe neural networks"
        ]
        
        responses = []
        for prompt in prompts:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                system="You are a professional technical consultant. Be concise and formal.",
                messages=[{"role": "user", "content": prompt}]
            )
            responses.append(message.content[0].text.lower())
        
        # Check for unprofessional language
        casual_words = ["gonna", "wanna", "yeah", "nope", "lol", "btw"]
        
        for i, response in enumerate(responses):
            for word in casual_words:
                assert word not in response, \
                    f"Response {i+1} contains casual language: '{word}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Commit → "Add consistency tests"**

---

### 2. `.gitignore` Datei erweitern

**Klick auf `.gitignore` → Edit (Stift-Symbol) → Am Ende hinzufügen:**
```
# Test reports
report.html
assets/

# Python
__pycache__/
*.pyc
*.pyo
venv/
.env

# IDE
.vscode/
.idea/
