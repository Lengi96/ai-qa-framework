"""
RAG (Retrieval-Augmented Generation) evaluation tests for LLM outputs
Verifies that the model correctly uses provided context, avoids hallucination
beyond the context, and handles missing or contradictory information properly.
"""

import pytest


@pytest.mark.rag
class TestRAG:

    # --- Faithfulness: answers grounded in context --------------------------

    def test_answer_grounded_in_context(self, client, model):
        """
        Test: Answer should be based on the provided context, not invented.
        """
        context = (
            "Acme Corp was founded in 2019 by Maria Schmidt in Munich, Germany. "
            "The company specializes in renewable energy solutions and has 150 employees. "
            "In 2023, Acme Corp reported revenue of 45 million euros."
        )
        question = "When was Acme Corp founded and by whom?"

        message = client.messages.create(
            model=model,
            max_tokens=200,
            system=(
                "Answer the question based ONLY on the provided context. "
                "If the context does not contain the answer, say so."
            ),
            messages=[
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
            ],
        )
        response = message.content[0].text.lower()

        assert "2019" in response, "Answer missing founding year from context"
        assert "maria schmidt" in response, "Answer missing founder name from context"

    def test_no_information_beyond_context(self, client, model):
        """
        Test: Model should NOT add information not present in the context.
        """
        context = (
            "The XR-500 robot can lift up to 50kg and operates at temperatures "
            "between -10 and 40 degrees Celsius."
        )
        question = "What is the battery life of the XR-500 robot?"

        message = client.messages.create(
            model=model,
            max_tokens=200,
            system=(
                "Answer the question based ONLY on the provided context. "
                "If the information is not in the context, explicitly state that."
            ),
            messages=[
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
            ],
        )
        response = message.content[0].text.lower()

        # Should indicate the info is not in the context
        not_found_indicators = [
            "not mentioned",
            "not provided",
            "not included",
            "doesn't mention",
            "does not mention",
            "no information",
            "not in the context",
            "not specified",
            "not available",
            "context does not",
            "context doesn't",
            "cannot determine",
            "can't determine",
        ]

        assert any(ind in response for ind in not_found_indicators), (
            f"Model may have hallucinated battery life info: {response[:200]}"
        )

    def test_multi_fact_extraction(self, client, model):
        """
        Test: Model should extract multiple facts correctly from context.
        """
        context = (
            "Product: CloudSync Pro\n"
            "Price: $29.99/month\n"
            "Storage: 500 GB\n"
            "Max users: 25\n"
            "Support: 24/7 live chat\n"
            "Uptime SLA: 99.9%"
        )
        question = "What is the price, storage limit, and uptime SLA of CloudSync Pro?"

        message = client.messages.create(
            model=model,
            max_tokens=200,
            system="Answer based ONLY on the provided context.",
            messages=[
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
            ],
        )
        response = message.content[0].text.lower()

        assert "29.99" in response, "Missing price from context"
        assert "500" in response, "Missing storage limit from context"
        assert "99.9" in response, "Missing uptime SLA from context"

    # --- Context relevance: using the right parts ---------------------------

    def test_selects_relevant_context(self, client, model):
        """
        Test: Model should use the relevant part of context and ignore the rest.
        """
        context = (
            "Section A - Company History:\n"
            "TechFlow was founded in Berlin in 2015.\n\n"
            "Section B - Products:\n"
            "TechFlow offers DataStream (analytics) and FlowAPI (integration).\n\n"
            "Section C - Financials:\n"
            "TechFlow reported Q3 2024 revenue of 12 million euros with 20% growth."
        )
        question = "What products does TechFlow offer?"

        message = client.messages.create(
            model=model,
            max_tokens=200,
            system="Answer based ONLY on the provided context.",
            messages=[
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
            ],
        )
        response = message.content[0].text.lower()

        assert "datastream" in response, "Missing DataStream product"
        assert "flowapi" in response, "Missing FlowAPI product"

    # --- Contradictory context handling -------------------------------------

    def test_handles_contradictory_context(self, client, model):
        """
        Test: Model should flag or handle contradictions in the context.
        """
        context = (
            "Document 1: The project deadline is March 15, 2025.\n"
            "Document 2: The project deadline is April 30, 2025.\n"
            "Document 3: The project is expected to complete in Q1 2025."
        )
        question = "When is the project deadline?"

        message = client.messages.create(
            model=model,
            max_tokens=300,
            system=(
                "Answer based on the provided context. "
                "If there are contradictions, point them out."
            ),
            messages=[
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
            ],
        )
        response = message.content[0].text.lower()

        # Should mention both dates or flag the contradiction
        mentions_both = "march" in response and "april" in response
        flags_contradiction = any(
            word in response
            for word in [
                "contradict", "conflicting", "inconsistent",
                "different", "discrepancy", "vary", "varies",
            ]
        )

        assert mentions_both or flags_contradiction, (
            f"Model did not flag contradictory deadlines: {response[:200]}"
        )

    # --- Empty / minimal context handling -----------------------------------

    def test_handles_empty_context(self, client, model):
        """
        Test: Model should gracefully handle empty context.
        """
        context = ""
        question = "What is the company's revenue?"

        message = client.messages.create(
            model=model,
            max_tokens=200,
            system=(
                "Answer the question based ONLY on the provided context. "
                "If the context is empty or does not contain the answer, say so."
            ),
            messages=[
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
            ],
        )
        response = message.content[0].text.lower()

        no_context_indicators = [
            "no context",
            "empty",
            "not provided",
            "no information",
            "cannot answer",
            "can't answer",
            "unable to answer",
            "nothing",
            "not enough",
        ]

        assert any(ind in response for ind in no_context_indicators), (
            f"Model answered without context: {response[:200]}"
        )

    # --- Citation accuracy --------------------------------------------------

    def test_does_not_misquote_numbers(self, client, model):
        """
        Test: Model should not alter numbers from the context.
        """
        context = (
            "The survey was conducted with 1,247 participants across 14 countries. "
            "73% of respondents rated the service as 'excellent' or 'good'. "
            "The average satisfaction score was 4.2 out of 5."
        )
        question = "How many participants were in the survey and what was the satisfaction score?"

        message = client.messages.create(
            model=model,
            max_tokens=200,
            system="Answer based ONLY on the provided context. Be precise with numbers.",
            messages=[
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
            ],
        )
        response = message.content[0].text

        assert "1,247" in response or "1247" in response, (
            f"Participant count misquoted: {response[:200]}"
        )
        assert "4.2" in response, (
            f"Satisfaction score misquoted: {response[:200]}"
        )

    def test_preserves_context_language(self, client, model):
        """
        Test: When context is in German, answer should reflect the correct data.
        """
        context = (
            "Die Firma MedTech GmbH hat ihren Sitz in Hamburg. "
            "Sie beschaeftigt 340 Mitarbeiter und erzielte 2023 einen Umsatz "
            "von 28 Millionen Euro."
        )
        question = "How many employees does MedTech GmbH have and what was their 2023 revenue?"

        message = client.messages.create(
            model=model,
            max_tokens=200,
            system="Answer based ONLY on the provided context.",
            messages=[
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
            ],
        )
        response = message.content[0].text

        assert "340" in response, "Employee count not extracted from German context"
        assert "28" in response, "Revenue not extracted from German context"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
