"""
Consistency tests for LLM outputs
Verifies that similar inputs produce coherent, stable outputs
"""

import pytest


class TestConsistency:

    def test_similar_questions_similar_answers(self, llm):
        """
        Test: Semantically similar questions should yield consistent core information
        """
        questions = [
            "What is the capital of Germany?",
            "Tell me the capital city of Germany",
            "Which city is Germany's capital?",
            "Germany's capital is which city?",
        ]

        responses = []
        for question in questions:
            response = llm.ask(question, max_tokens=100).text.lower()
            responses.append(response)

        # All responses should mention Berlin
        for i, response in enumerate(responses):
            assert "berlin" in response, (
                f"Question {i+1} did not mention Berlin: {response}"
            )

    def test_output_stability_over_time(self, llm):
        """
        Test: Same question asked multiple times should give consistent answer
        """
        question = "What is 2 + 2?"
        expected_answer = "4"

        responses = []
        for _ in range(5):
            response = llm.ask(question, max_tokens=50).text
            responses.append(response)

        # All responses should contain "4"
        for response in responses:
            assert expected_answer in response, (
                f"Inconsistent answer: {response}"
            )

    def test_tone_consistency(self, llm):
        """
        Test: Multiple requests should maintain consistent tone
        """
        prompts = [
            "Explain machine learning",
            "What is artificial intelligence?",
            "Describe neural networks",
        ]

        responses = []
        for prompt in prompts:
            response = llm.ask(
                prompt,
                max_tokens=200,
                system="You are a professional technical consultant. Be concise and formal.",
            ).text.lower()
            responses.append(response)

        # Check for unprofessional language
        casual_words = ["gonna", "wanna", "yeah", "nope", "lol", "btw"]

        for i, response in enumerate(responses):
            for word in casual_words:
                assert word not in response, (
                    f"Response {i+1} contains casual language: '{word}'"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
