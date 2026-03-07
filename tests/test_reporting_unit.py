"""Unit tests for traceability and release summary generation."""

from quality.reporting import build_traceability_report, generate_traceability_html
from quality.specs import load_quality_specs


def _sample_results():
    return {
        "created": 1771777801.613059,
        "summary": {"passed": 3, "failed": 1, "skipped": 0, "total": 4},
        "tests": [
            {
                "nodeid": "tests/test_security.py::test_security_scenarios[SCN-SEC-PROMPT-INJECTION]",
                "outcome": "passed",
                "call": {"duration": 1.2, "longrepr": ""},
            },
            {
                "nodeid": "tests/test_security.py::test_security_scenarios[SCN-SEC-API-KEY-LEAKAGE]",
                "outcome": "passed",
                "call": {"duration": 1.1, "longrepr": ""},
            },
            {
                "nodeid": "tests/test_security.py::test_security_scenarios[SCN-SEC-PII-GENERATION]",
                "outcome": "failed",
                "call": {"duration": 1.4, "longrepr": "assertion"},
            },
            {
                "nodeid": "tests/test_performance.py::test_performance_scenarios[SCN-PERF-SIMPLE-LATENCY]",
                "outcome": "passed",
                "call": {"duration": 0.9, "longrepr": ""},
            },
        ],
    }


def test_build_traceability_report_calculates_release_summary():
    requirements, scenarios, gates = load_quality_specs()
    report = build_traceability_report(
        _sample_results(),
        requirements,
        scenarios,
        gates,
        provider="anthropic",
        model="claude-haiku-4-5",
    )

    assert report["metadata"]["provider"] == "anthropic"
    assert report["release_summary"]["decision"] == "NO-GO"
    assert report["gaps"]["requirements_without_tests"]


def test_generate_traceability_html_includes_decision_and_matrix():
    requirements, scenarios, gates = load_quality_specs()
    report = build_traceability_report(_sample_results(), requirements, scenarios, gates)

    html = generate_traceability_html(report)

    assert "Traceability Report" in html
    assert report["release_summary"]["decision"] in html
    assert "Traceability Matrix" in html
