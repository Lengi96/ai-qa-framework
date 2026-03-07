"""Helpers for data-driven scenario tests."""

from __future__ import annotations

import pytest

from quality.scenario_runner import execute_scenario, is_scenario_applicable
from quality.specs import load_scenarios


_ALL_SCENARIOS = load_scenarios()


def scenarios_for(category: str):
    return tuple(scenario for scenario in _ALL_SCENARIOS if scenario.category == category)


def scenario_ids(scenario):
    return scenario.id


def run_scenario_test(llm, scenario, record_property):
    if not is_scenario_applicable(scenario, llm.provider):
        pytest.skip(f"Scenario {scenario.id} does not target provider {llm.provider}")

    record_property("scenario_id", scenario.id)
    record_property("requirement_ids", ",".join(scenario.requirement_ids))
    record_property("scenario_category", scenario.category)
    return execute_scenario(llm, scenario)
