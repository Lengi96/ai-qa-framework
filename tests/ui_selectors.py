"""
Default CSS selectors for common chatbot UI patterns.
Override via CLI options (--selector-*) or environment variables (UI_SELECTOR_*).
"""

from dataclasses import dataclass


@dataclass
class UISelectors:
    """CSS selectors for locating chatbot UI elements.

    Each selector uses comma-separated alternatives to match
    multiple common chat UI frameworks out of the box.
    """

    input: str = (
        "textarea[placeholder*='message'], "
        "textarea[placeholder*='Message'], "
        "input[type='text'][placeholder*='message'], "
        "#chat-input, "
        "[data-testid='chat-input']"
    )
    send: str = (
        "button[type='submit'], "
        "button[aria-label*='send'], "
        "button[aria-label*='Send'], "
        "[data-testid='send-button']"
    )
    messages: str = (
        ".messages, "
        ".chat-messages, "
        "[role='log'], "
        "[data-testid='messages']"
    )
    response: str = (
        ".assistant-message, "
        ".bot-message, "
        ".message.assistant, "
        "[data-testid='bot-response']"
    )
    loading: str = (
        ".loading, "
        ".spinner, "
        "[aria-busy='true'], "
        "[data-testid='loading']"
    )
    error: str = (
        ".error, "
        ".error-message, "
        "[role='alert'], "
        "[data-testid='error']"
    )
