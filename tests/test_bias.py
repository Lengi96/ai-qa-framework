"""Bias tests executed from reusable scenario specifications."""

import pytest

from scenario_helpers import run_scenario_test, scenario_ids, scenarios_for


@pytest.mark.bias
@pytest.mark.parametrize("scenario", scenarios_for("bias"), ids=scenario_ids)
def test_bias_scenarios(llm, scenario, record_property):
    run_scenario_test(llm, scenario, record_property)
