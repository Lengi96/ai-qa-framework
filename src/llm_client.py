"""
Unified LLM client that supports multiple providers.

Supported providers:
    - anthropic  (Claude models)
    - openai     (GPT models)
    - google     (Gemini models)

Usage:
    client = LLMClient(provider="anthropic", model="claude-sonnet-4-20250514")
    response = client.ask("What is the capital of France?")
    response = client.ask("Be formal.", system="You are a consultant.")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """Standardized response object across all providers."""

    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: object = field(default=None, repr=False)


class LLMClient:
    """Unified interface to query different LLM providers."""

    SUPPORTED_PROVIDERS = ("anthropic", "openai", "google")

    def __init__(
        self,
        provider: str = "anthropic",
        model: str | None = None,
        api_key: str | None = None,
    ):
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Supported: {', '.join(self.SUPPORTED_PROVIDERS)}"
            )

        self.provider = provider
        self.model = model or self._default_model()
        self._api_key = api_key
        self._client = self._init_client()

    # -- public API ----------------------------------------------------------

    def ask(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """Send a prompt and return a standardized LLMResponse."""
        if not prompt or not prompt.strip():
            raise ValueError("prompt must not be empty")

        handler = {
            "anthropic": self._ask_anthropic,
            "openai": self._ask_openai,
            "google": self._ask_google,
        }
        return handler[self.provider](prompt, system=system, max_tokens=max_tokens)

    # -- provider initialisation ---------------------------------------------

    def _default_model(self) -> str:
        defaults = {
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "google": "gemini-2.0-flash",
        }
        return defaults[self.provider]

    def _init_client(self):
        if self.provider == "anthropic":
            import anthropic

            key = self._api_key or os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise EnvironmentError("ANTHROPIC_API_KEY is not set")
            return anthropic.Anthropic(api_key=key)

        if self.provider == "openai":
            import openai

            key = self._api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                raise EnvironmentError("OPENAI_API_KEY is not set")
            return openai.OpenAI(api_key=key)

        if self.provider == "google":
            import google.generativeai as genai

            key = self._api_key or os.getenv("GOOGLE_API_KEY")
            if not key:
                raise EnvironmentError("GOOGLE_API_KEY is not set")
            genai.configure(api_key=key)
            return genai.GenerativeModel(self.model)

    # -- provider-specific request methods -----------------------------------

    def _ask_anthropic(self, prompt, *, system=None, max_tokens=500):
        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system

        message = self._client.messages.create(**kwargs)
        return LLMResponse(
            text=message.content[0].text,
            model=self.model,
            provider=self.provider,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            raw=message,
        )

    def _ask_openai(self, prompt, *, system=None, max_tokens=500):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
        )
        choice = response.choices[0]
        return LLMResponse(
            text=self._extract_openai_text(choice.message.content),
            model=self.model,
            provider=self.provider,
            input_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
            raw=response,
        )

    def _ask_google(self, prompt, *, system=None, max_tokens=500):
        config = {"max_output_tokens": max_tokens}

        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        response = self._client.generate_content(
            full_prompt,
            generation_config=config,
        )
        usage = getattr(response, "usage_metadata", None)
        return LLMResponse(
            text=getattr(response, "text", "") or "",
            model=self.model,
            provider=self.provider,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            raw=response,
        )

    @staticmethod
    def _extract_openai_text(content) -> str:
        """Normalize OpenAI content field across SDK response formats."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif hasattr(item, "type") and getattr(item, "type") == "text":
                    parts.append(getattr(item, "text", ""))
            return "".join(parts).strip()
        return ""
