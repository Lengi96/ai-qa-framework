"""Generic scenario execution for prompt-driven LLM QA tests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from time import perf_counter

from .specs import Scenario


@dataclass(frozen=True)
class ScenarioRun:
    prompt: str
    response_text: str
    latency_seconds: float
    output_tokens: int


@dataclass(frozen=True)
class ScenarioExecutionResult:
    scenario_id: str
    runs: tuple[ScenarioRun, ...]

    @property
    def average_latency_seconds(self) -> float:
        if not self.runs:
            return 0.0
        return sum(run.latency_seconds for run in self.runs) / len(self.runs)


def is_scenario_applicable(scenario: Scenario, provider: str) -> bool:
    return not scenario.provider_scope or provider.lower() in scenario.provider_scope


def _compose_prompt(scenario: Scenario, prompt: str) -> str:
    if scenario.context:
        return f"Context: {scenario.context}\n\nQuestion: {prompt}"
    return prompt


def _normalize(text: str) -> str:
    return text.lower().strip()


def _assert_expected_signals(response: str, scenario: Scenario) -> None:
    if not scenario.expected_signals:
        return

    haystack = _normalize(response)
    signals = tuple(_normalize(signal) for signal in scenario.expected_signals)
    if scenario.expected_match == "any":
        if any(signal in haystack for signal in signals):
            return
        raise AssertionError(
            f"{scenario.id}: response did not contain any expected signal. "
            f"Expected one of {list(scenario.expected_signals)!r}, got {response[:240]!r}"
        )

    missing = [signal for signal in signals if signal not in haystack]
    if missing:
        raise AssertionError(
            f"{scenario.id}: response missing expected signals {missing!r}. "
            f"Got {response[:240]!r}"
        )


def _assert_expected_signal_groups(response: str, scenario: Scenario) -> None:
    if not scenario.expected_signal_groups:
        return

    haystack = _normalize(response)
    missing_groups = []
    for group in scenario.expected_signal_groups:
        normalized_group = tuple(_normalize(signal) for signal in group)
        if not any(signal in haystack for signal in normalized_group):
            missing_groups.append(list(group))

    if missing_groups:
        raise AssertionError(
            f"{scenario.id}: response missed one or more expected signal groups {missing_groups!r}. "
            f"Got {response[:240]!r}"
        )


def _assert_forbidden_signals(response: str, scenario: Scenario) -> None:
    if not scenario.forbidden_signals:
        return

    haystack = _normalize(response)
    matched = [signal for signal in scenario.forbidden_signals if _normalize(signal) in haystack]
    if matched:
        raise AssertionError(
            f"{scenario.id}: response contained forbidden signals {matched!r}. "
            f"Got {response[:240]!r}"
        )


def _assert_forbidden_regex_patterns(response: str, scenario: Scenario) -> None:
    if not scenario.forbidden_regex_patterns:
        return

    matches = [pattern for pattern in scenario.forbidden_regex_patterns if re.search(pattern, response, re.IGNORECASE)]
    if matches:
        raise AssertionError(
            f"{scenario.id}: response matched forbidden regex patterns {matches!r}. "
            f"Got {response[:240]!r}"
        )


def _assert_length_ratios(runs: list[ScenarioRun], scenario: Scenario) -> None:
    if not runs:
        return
    if scenario.min_length_ratio is None and scenario.max_length_ratio is None:
        return

    lengths = [len(run.response_text) for run in runs]
    average_length = sum(lengths) / len(lengths)
    for length in lengths:
        ratio = 0.0 if average_length == 0 else length / average_length
        if scenario.min_length_ratio is not None and ratio <= scenario.min_length_ratio:
            raise AssertionError(
                f"{scenario.id}: response length ratio {ratio:.2f} was below {scenario.min_length_ratio:.2f}."
            )
        if scenario.max_length_ratio is not None and ratio >= scenario.max_length_ratio:
            raise AssertionError(
                f"{scenario.id}: response length ratio {ratio:.2f} exceeded {scenario.max_length_ratio:.2f}."
            )


def execute_scenario(llm, scenario: Scenario) -> ScenarioExecutionResult:
    """Execute a scenario against the unified llm fixture and assert its checks."""
    runs: list[ScenarioRun] = []
    prompts = list(scenario.prompts) * max(1, scenario.repeat_count)

    for prompt in prompts:
        rendered_prompt = _compose_prompt(scenario, prompt)
        started_at = perf_counter()
        response = llm.ask(
            rendered_prompt,
            system=scenario.system_prompt,
            max_tokens=scenario.max_tokens,
        )
        latency = perf_counter() - started_at
        text = response.text.strip()

        if len(text) < scenario.min_response_length:
            raise AssertionError(
                f"{scenario.id}: response shorter than {scenario.min_response_length} characters. "
                f"Got {text!r}"
            )

        _assert_expected_signals(text, scenario)
        _assert_expected_signal_groups(text, scenario)
        _assert_forbidden_signals(text, scenario)
        _assert_forbidden_regex_patterns(text, scenario)

        if scenario.max_latency_seconds is not None and latency >= scenario.max_latency_seconds:
            raise AssertionError(
                f"{scenario.id}: latency {latency:.2f}s exceeded "
                f"{scenario.max_latency_seconds:.2f}s"
            )

        if scenario.max_output_tokens is not None and response.output_tokens > scenario.max_output_tokens:
            raise AssertionError(
                f"{scenario.id}: output tokens {response.output_tokens} exceeded "
                f"{scenario.max_output_tokens}"
            )

        runs.append(
            ScenarioRun(
                prompt=prompt,
                response_text=text,
                latency_seconds=latency,
                output_tokens=response.output_tokens,
            )
        )

    _assert_length_ratios(runs, scenario)
    result = ScenarioExecutionResult(scenario_id=scenario.id, runs=tuple(runs))

    if (
        scenario.max_average_latency_seconds is not None
        and result.average_latency_seconds >= scenario.max_average_latency_seconds
    ):
        raise AssertionError(
            f"{scenario.id}: average latency {result.average_latency_seconds:.2f}s exceeded "
            f"{scenario.max_average_latency_seconds:.2f}s"
        )

    return result
