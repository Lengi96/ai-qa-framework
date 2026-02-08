"""
UI tests for chatbot web interfaces using Playwright
Verifies chat input/output flow, rendering, loading states, error handling,
accessibility, responsive design, and perceived performance.

These tests are generic and work against any chat interface.
Configure the target via --base-url and --selector-* options.
"""

import time

import pytest


def _send_message(page, selectors, text, use_enter=False):
    """Type a message and submit it.

    Returns the count of bot responses before sending.
    """
    response_count_before = len(page.query_selector_all(selectors.response))
    input_el = page.wait_for_selector(selectors.input, timeout=10000)
    input_el.fill(text)

    if use_enter:
        input_el.press("Enter")
    else:
        send_btn = page.query_selector(selectors.send)
        if send_btn and send_btn.is_visible():
            send_btn.click()
        else:
            input_el.press("Enter")

    return response_count_before


def _wait_for_response(page, selectors, previous_count, timeout=30000):
    """Wait until a new bot response appears beyond the previous count."""
    escaped = selectors.response.replace("'", "\\'")
    page.wait_for_function(
        f"document.querySelectorAll('{escaped}').length > {previous_count}",
        timeout=timeout,
    )
    responses = page.query_selector_all(selectors.response)
    return responses[-1]


@pytest.mark.ui
class TestUI:
    """Generic chatbot UI tests.

    Configure the target application via:
        --base-url           Base URL of the chatbot app
        --selector-input     CSS selector for the chat input field
        --selector-send      CSS selector for the send button
        --selector-messages  CSS selector for the message container
        --selector-response  CSS selector for bot response messages
        --selector-loading   CSS selector for loading indicator
        --selector-error     CSS selector for error display
    """

    # --- Chat Input/Output Flow ---------------------------------------------

    def test_chat_input_visible_and_focusable(self, page, ui_selectors):
        """
        Test: Chat input field should be visible and focusable.
        """
        input_el = page.wait_for_selector(ui_selectors.input, timeout=10000)

        assert input_el.is_visible(), "Chat input is not visible"

        input_el.focus()
        focused = page.evaluate(
            "document.activeElement === document.querySelector("
            f"'{ui_selectors.input}')"
        )
        assert focused, "Chat input could not be focused"

    def test_send_message_and_receive_response(self, page, ui_selectors):
        """
        Test: Sending a message should produce a bot response.
        """
        prev_count = _send_message(page, ui_selectors, "Hello")
        response_el = _wait_for_response(page, ui_selectors, prev_count)

        response_text = response_el.inner_text().strip()
        assert len(response_text) > 0, "Bot response is empty"

    def test_send_via_enter_key(self, page, ui_selectors):
        """
        Test: Pressing Enter should submit the message.
        """
        prev_count = _send_message(
            page, ui_selectors, "What is 1 + 1?", use_enter=True
        )
        response_el = _wait_for_response(page, ui_selectors, prev_count)

        response_text = response_el.inner_text().strip()
        assert len(response_text) > 0, "No response after Enter key submission"

    def test_send_button_clickable(self, page, ui_selectors):
        """
        Test: Send button should be visible and functional.
        """
        send_btn = page.query_selector(ui_selectors.send)
        if not send_btn or not send_btn.is_visible():
            pytest.skip("Send button not found — UI may use Enter-only submission")

        assert send_btn.is_enabled(), "Send button is not enabled"

        prev_count = _send_message(page, ui_selectors, "Hi there")
        response_el = _wait_for_response(page, ui_selectors, prev_count)

        assert response_el.inner_text().strip(), "No response after button click"

    def test_multiple_messages_sequential(self, page, ui_selectors):
        """
        Test: Multiple messages should be handled sequentially.
        """
        messages = ["Hello", "What is Python?", "Thanks"]

        for msg in messages:
            prev_count = _send_message(page, ui_selectors, msg)
            _wait_for_response(page, ui_selectors, prev_count)

        responses = page.query_selector_all(ui_selectors.response)
        assert len(responses) >= len(messages), (
            f"Expected at least {len(messages)} responses, got {len(responses)}"
        )

    # --- Response Rendering -------------------------------------------------

    def test_response_preserves_markdown_formatting(self, page, ui_selectors):
        """
        Test: Responses with markdown should be rendered as HTML.
        """
        prev_count = _send_message(
            page, ui_selectors,
            "List 3 benefits of automated testing in a numbered list."
        )
        response_el = _wait_for_response(page, ui_selectors, prev_count)

        html = response_el.inner_html()
        markdown_tags = ["<ol", "<ul", "<li", "<strong", "<em", "<p"]
        has_markdown = any(tag in html.lower() for tag in markdown_tags)

        if not has_markdown:
            pytest.xfail("UI does not appear to render markdown as HTML")

    def test_response_renders_code_blocks(self, page, ui_selectors):
        """
        Test: Code in responses should be rendered in code blocks.
        """
        prev_count = _send_message(
            page, ui_selectors,
            "Show a Python hello world example with code."
        )
        response_el = _wait_for_response(page, ui_selectors, prev_count)

        html = response_el.inner_html()
        has_code = "<pre" in html.lower() or "<code" in html.lower()

        if not has_code:
            pytest.xfail("UI does not appear to render code blocks")

    # --- Loading States -----------------------------------------------------

    def test_loading_indicator_visible_during_response(self, page, ui_selectors):
        """
        Test: A loading indicator should appear while waiting for a response.
        """
        _send_message(page, ui_selectors, "Explain quantum computing in detail.")

        try:
            page.wait_for_selector(
                ui_selectors.loading, state="visible", timeout=5000
            )
            loading_seen = True
        except Exception:
            loading_seen = False

        if not loading_seen:
            pytest.xfail(
                "Loading indicator not detected — "
                "response may have arrived too fast or selector doesn't match"
            )

    def test_input_disabled_during_loading(self, page, ui_selectors):
        """
        Test: Input should be disabled or read-only during response generation.
        """
        _send_message(page, ui_selectors, "Write a long essay about AI.")

        # Check immediately after submission
        input_el = page.query_selector(ui_selectors.input)
        if not input_el:
            pytest.skip("Input element not found after submission")

        is_disabled = input_el.is_disabled()
        is_readonly = input_el.get_attribute("readonly") is not None

        # Wait for response to complete before asserting
        try:
            escaped = ui_selectors.response.replace("'", "\\'")
            page.wait_for_function(
                f"document.querySelectorAll('{escaped}').length > 0",
                timeout=30000,
            )
        except Exception:
            pass

        if not is_disabled and not is_readonly:
            pytest.xfail(
                "Input was not disabled during loading — "
                "UI may allow concurrent submissions"
            )

    # --- Error Handling ------------------------------------------------------

    def test_empty_input_not_submitted(self, page, ui_selectors):
        """
        Test: Empty input should not send a message.
        """
        responses_before = len(page.query_selector_all(ui_selectors.response))

        input_el = page.wait_for_selector(ui_selectors.input, timeout=10000)
        input_el.fill("")
        input_el.press("Enter")

        # Wait briefly and check no new response appeared
        page.wait_for_timeout(2000)

        responses_after = len(page.query_selector_all(ui_selectors.response))
        assert responses_after == responses_before, (
            "A message was sent with empty input"
        )

    def test_very_long_input_handled_gracefully(self, page, ui_selectors):
        """
        Test: Very long input should not crash the application.
        """
        long_text = "a" * 10000
        input_el = page.wait_for_selector(ui_selectors.input, timeout=10000)
        input_el.fill(long_text)

        send_btn = page.query_selector(ui_selectors.send)
        if send_btn and send_btn.is_visible():
            send_btn.click()
        else:
            input_el.press("Enter")

        # Wait and verify page is still functional
        page.wait_for_timeout(3000)

        # Page should still be responsive — input should still exist
        input_still_exists = page.query_selector(ui_selectors.input)
        assert input_still_exists is not None, (
            "Page became unresponsive after very long input"
        )

    # --- Accessibility -------------------------------------------------------

    def test_input_has_aria_label_or_placeholder(self, page, ui_selectors):
        """
        Test: Chat input should have accessible labeling (WCAG compliance).
        """
        input_el = page.wait_for_selector(ui_selectors.input, timeout=10000)

        aria_label = input_el.get_attribute("aria-label")
        aria_labelledby = input_el.get_attribute("aria-labelledby")
        placeholder = input_el.get_attribute("placeholder")
        input_id = input_el.get_attribute("id")

        has_label = bool(aria_label or aria_labelledby or placeholder)
        if input_id:
            associated_label = page.query_selector(f"label[for='{input_id}']")
            has_label = has_label or associated_label is not None

        assert has_label, (
            "Chat input has no accessible label "
            "(missing aria-label, aria-labelledby, placeholder, or associated label)"
        )

    def test_keyboard_navigation_tab_order(self, page, ui_selectors):
        """
        Test: Input and send button should be reachable via Tab key.
        """
        page.keyboard.press("Tab")

        # Try up to 10 Tab presses to reach the input
        input_reached = False
        for _ in range(10):
            active = page.evaluate(
                "document.activeElement?.tagName?.toLowerCase() + "
                "'|' + (document.activeElement?.type || '')"
            )
            if active and ("textarea" in active or "text" in active):
                input_reached = True
                break
            page.keyboard.press("Tab")

        assert input_reached, (
            "Chat input was not reachable via Tab navigation within 10 presses"
        )

    def test_messages_have_appropriate_roles(self, page, ui_selectors):
        """
        Test: Message container should use appropriate ARIA roles.
        """
        # Send a message first to ensure messages are present
        prev_count = _send_message(page, ui_selectors, "Hello")
        _wait_for_response(page, ui_selectors, prev_count)

        messages_container = page.query_selector(ui_selectors.messages)
        if not messages_container:
            pytest.xfail("Messages container not found with configured selector")

        role = messages_container.get_attribute("role")
        aria_live = messages_container.get_attribute("aria-live")

        has_semantics = bool(role or aria_live)

        if not has_semantics:
            pytest.xfail(
                "Messages container has no ARIA role or aria-live attribute"
            )

    # --- Responsive Design ---------------------------------------------------

    def test_layout_mobile_viewport(self, page, ui_selectors):
        """
        Test: Chat UI should work on mobile viewport (375x667).
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.reload(wait_until="networkidle")

        input_el = page.wait_for_selector(ui_selectors.input, timeout=10000)
        assert input_el.is_visible(), "Chat input not visible on mobile viewport"

        # Verify input is not clipped (within viewport)
        box = input_el.bounding_box()
        assert box is not None, "Cannot determine input position"
        assert box["x"] >= 0 and box["x"] + box["width"] <= 375, (
            f"Input extends outside mobile viewport: x={box['x']}, "
            f"width={box['width']}"
        )

    def test_layout_desktop_viewport(self, page, ui_selectors):
        """
        Test: Chat UI should work on desktop viewport (1920x1080).
        """
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.reload(wait_until="networkidle")

        input_el = page.wait_for_selector(ui_selectors.input, timeout=10000)
        assert input_el.is_visible(), "Chat input not visible on desktop viewport"

        prev_count = _send_message(page, ui_selectors, "Hi")
        response_el = _wait_for_response(page, ui_selectors, prev_count)
        assert response_el.is_visible(), "Response not visible on desktop viewport"

    # --- Performance ---------------------------------------------------------

    def test_time_to_first_response_under_sla(self, page, ui_selectors):
        """
        Test: First visible response should appear within 30 seconds.
        """
        max_seconds = 30

        start = time.time()
        prev_count = _send_message(page, ui_selectors, "Hello")
        _wait_for_response(page, ui_selectors, prev_count, timeout=max_seconds * 1000)
        elapsed = time.time() - start

        assert elapsed < max_seconds, (
            f"Time to first response: {elapsed:.2f}s exceeds SLA of {max_seconds}s"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
