"""Unit tests for internal LLM client normalization helpers."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_client import LLMClient  # noqa: E402


class _OpenAITextPart:
    """Minimal SDK-like content part for parser unit tests."""

    def __init__(self, text: str):
        self.type = "text"
        self.text = text


def test_extract_openai_text_with_plain_string():
    content = "Simple text response."

    result = LLMClient._extract_openai_text(content)

    assert result == "Simple text response."


def test_extract_openai_text_with_dict_parts():
    content = [
        {"type": "text", "text": "Hello"},
        {"type": "tool_call", "name": "ignored"},
        {"type": "text", "text": " world"},
    ]

    result = LLMClient._extract_openai_text(content)

    assert result == "Hello world"


def test_extract_openai_text_with_object_parts():
    content = [
        _OpenAITextPart("Alpha"),
        _OpenAITextPart(" Beta"),
    ]

    result = LLMClient._extract_openai_text(content)

    assert result == "Alpha Beta"


def test_extract_openai_text_with_unsupported_type_returns_empty():
    result = LLMClient._extract_openai_text({"unexpected": "shape"})

    assert result == ""
