"""Data-driven RAG tests executed from reusable scenario specifications."""

import pytest

from scenario_helpers import run_scenario_test, scenario_ids, scenarios_for


@pytest.mark.rag
@pytest.mark.parametrize("scenario", scenarios_for("rag"), ids=scenario_ids)
def test_rag_scenarios_from_specs(llm, scenario, record_property):
    run_scenario_test(llm, scenario, record_property)
