"""Unit tests for the generic scenario runner."""

from types import SimpleNamespace

import pytest

from quality.scenario_runner import execute_scenario
from quality.specs import Scenario


class StubLLM:
    provider = "anthropic"

    def __init__(self, responses):
        self._responses = list(responses)

    def ask(self, prompt, *, system=None, max_tokens=500):
        text, tokens = self._responses.pop(0)
        return SimpleNamespace(text=text, output_tokens=tokens)


def test_execute_scenario_checks_expected_and_forbidden_signals():
    scenario = Scenario(
        id="SCN-UNIT-001",
        category="security",
        objective="Validate expected and forbidden signals",
        requirement_ids=("REQ-UNIT-001",),
        user_prompt="prompt",
        expected_signals=("safe",),
        forbidden_signals=("secret",),
        min_response_length=1,
    )

    result = execute_scenario(StubLLM([("This is safe", 5)]), scenario)

    assert result.scenario_id == scenario.id
    assert len(result.runs) == 1


def test_execute_scenario_checks_average_latency_limits():
    scenario = Scenario(
        id="SCN-UNIT-002",
        category="performance",
        objective="Validate repeated prompts",
        requirement_ids=("REQ-UNIT-002",),
        user_prompt="prompt",
        prompt_variants=("one", "two"),
        min_response_length=1,
        max_average_latency_seconds=5,
    )

    result = execute_scenario(StubLLM([("ok", 1), ("ok", 1)]), scenario)

    assert len(result.runs) == 2
    assert result.average_latency_seconds < 5


def test_execute_scenario_supports_signal_groups_and_length_ratios():
    scenario = Scenario(
        id="SCN-UNIT-003",
        category="bias",
        objective="Validate grouped expectations and ratio checks",
        requirement_ids=("REQ-UNIT-003",),
        user_prompt="prompt",
        prompt_variants=("one", "two"),
        expected_signal_groups=(("benefit", "advantage"), ("concern", "drawback")),
        min_length_ratio=0.5,
        max_length_ratio=1.5,
        min_response_length=1,
    )

    result = execute_scenario(
        StubLLM([
            ("Benefit and concern are both covered.", 5),
            ("Advantage and drawback are both covered here too.", 5),
        ]),
        scenario,
    )

    assert len(result.runs) == 2


def test_execute_scenario_fails_on_forbidden_regex_patterns():
    scenario = Scenario(
        id="SCN-UNIT-004",
        category="bias",
        objective="Validate regex bans",
        requirement_ids=("REQ-UNIT-004",),
        user_prompt="prompt",
        forbidden_regex_patterns=(r"\byou are too old\b",),
    )

    with pytest.raises(AssertionError):
        execute_scenario(StubLLM([("You are too old for this.", 1)]), scenario)
