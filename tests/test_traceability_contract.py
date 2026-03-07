"""Contract tests for requirement and scenario traceability."""

from quality.specs import load_requirements, load_scenarios


def test_every_scenario_requirement_exists():
    requirements = {requirement.id for requirement in load_requirements()}

    for scenario in load_scenarios():
        assert set(scenario.requirement_ids).issubset(requirements), scenario.id


def test_every_critical_requirement_has_scenarios():
    for requirement in load_requirements():
        if requirement.release_gate == "critical":
            assert requirement.linked_scenarios, requirement.id


def test_requirement_and_scenario_links_are_bidirectional():
    scenarios = {scenario.id: scenario for scenario in load_scenarios()}

    for requirement in load_requirements():
        for scenario_id in requirement.linked_scenarios:
            assert requirement.id in scenarios[scenario_id].requirement_ids
