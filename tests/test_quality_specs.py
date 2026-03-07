"""Unit tests for quality specification loading and validation."""

from quality.specs import load_quality_gates, load_quality_specs, load_requirements, load_scenarios


def test_load_requirements_returns_expected_fields():
    requirements = load_requirements()

    assert requirements, "Expected at least one requirement"
    assert all(requirement.id.startswith("REQ-") for requirement in requirements)
    assert all(requirement.acceptance_criteria for requirement in requirements)


def test_load_scenarios_returns_expected_fields():
    scenarios = load_scenarios()

    assert scenarios, "Expected at least one scenario"
    assert all(scenario.id.startswith("SCN-") for scenario in scenarios)
    assert all(scenario.requirement_ids for scenario in scenarios)


def test_load_quality_specs_validates_cross_links():
    requirements, scenarios, gates = load_quality_specs()

    assert requirements and scenarios
    assert gates.overall_pass_rate >= 0


def test_load_quality_gates_reads_thresholds():
    gates = load_quality_gates()

    assert gates.critical_requirements_pass_rate == 100
    assert gates.high_risk_coverage == 95
