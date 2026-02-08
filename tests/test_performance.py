"""
Performance tests for LLM outputs
Verifies response times, token efficiency, and SLA compliance
"""

import time

import pytest


class TestPerformance:

    def test_response_time_simple_query(self, client, model):
        """
        Test: Simple queries should respond within 10 seconds.
        """
        prompt = "What is the capital of France?"
        max_seconds = 10

        start = time.time()
        message = client.messages.create(
            model=model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        elapsed = time.time() - start

        assert message.content[0].text, "Empty response received"
        assert elapsed < max_seconds, (
            f"Response took {elapsed:.2f}s, SLA is {max_seconds}s"
        )

    def test_response_time_complex_query(self, client, model):
        """
        Test: Complex queries should respond within 30 seconds.
        """
        prompt = (
            "Explain the differences between microservices and monolithic "
            "architecture. Cover scalability, deployment, and maintenance."
        )
        max_seconds = 30

        start = time.time()
        message = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        elapsed = time.time() - start

        assert message.content[0].text, "Empty response received"
        assert elapsed < max_seconds, (
            f"Response took {elapsed:.2f}s, SLA is {max_seconds}s"
        )

    def test_token_efficiency_concise(self, client, model):
        """
        Test: When asked for a concise answer, response should not exceed
        a reasonable token count (avoid unnecessarily verbose output).
        """
        prompt = "In one sentence, what is Python?"

        message = client.messages.create(
            model=model,
            max_tokens=200,
            system="Be as concise as possible. Answer in one sentence only.",
            messages=[{"role": "user", "content": prompt}],
        )

        response = message.content[0].text
        output_tokens = message.usage.output_tokens

        # A one-sentence answer should not need more than 80 tokens
        max_tokens = 80
        assert output_tokens <= max_tokens, (
            f"Response used {output_tokens} tokens for a one-sentence answer "
            f"(max {max_tokens}): {response}"
        )

    def test_no_empty_responses(self, client, model):
        """
        Test: Model should never return an empty response to a valid question.
        """
        prompts = [
            "Hello, how are you?",
            "What is 1 + 1?",
            "Name a color.",
        ]

        for prompt in prompts:
            message = client.messages.create(
                model=model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )

            response = message.content[0].text.strip()
            assert len(response) > 0, (
                f"Empty response for prompt: '{prompt}'"
            )

    def test_average_latency_within_sla(self, client, model):
        """
        Test: Average response time over multiple requests should stay
        within SLA (average < 8 seconds).
        """
        prompts = [
            "What is 2 + 2?",
            "Name the largest ocean.",
            "What color is the sky?",
        ]
        max_avg_seconds = 8
        times = []

        for prompt in prompts:
            start = time.time()
            message = client.messages.create(
                model=model,
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            elapsed = time.time() - start
            times.append(elapsed)

            assert message.content[0].text, f"Empty response for: {prompt}"

        avg_time = sum(times) / len(times)
        assert avg_time < max_avg_seconds, (
            f"Average latency {avg_time:.2f}s exceeds SLA of {max_avg_seconds}s. "
            f"Individual times: {[f'{t:.2f}s' for t in times]}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
