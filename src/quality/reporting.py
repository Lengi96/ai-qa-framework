"""Build traceability and release-readiness artifacts from pytest JSON output."""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from .specs import GateConfig, Requirement, Scenario


SCENARIO_ID_PATTERN = re.compile(r"\[(?P<scenario_id>[A-Z0-9-]+)\]$")


def _scenario_result_map(results_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for test in results_data.get("tests", []):
        nodeid = test.get("nodeid", "")
        match = SCENARIO_ID_PATTERN.search(nodeid)
        if not match:
            continue
        scenario_id = match.group("scenario_id")
        mapped[scenario_id] = {
            "nodeid": nodeid,
            "outcome": test.get("outcome", "unknown"),
            "duration": round(test.get("call", {}).get("duration", 0.0), 3),
            "message": test.get("call", {}).get("longrepr", ""),
        }
    return mapped


def _iso_timestamp(value: Any) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).isoformat()
    if isinstance(value, str) and value.strip():
        return value
    return datetime.now().isoformat()


def _coverage_percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 1)


def build_traceability_report(
    results_data: dict[str, Any],
    requirements: tuple[Requirement, ...],
    scenarios: tuple[Scenario, ...],
    gate_config: GateConfig,
    *,
    provider: str | None = None,
    model: str | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scenario_results = _scenario_result_map(results_data)
    scenario_index = {scenario.id: scenario for scenario in scenarios}
    summary = results_data.get("summary", {})
    total_requirements = len(requirements)

    requirement_rows: list[dict[str, Any]] = []
    uncovered_criteria: list[dict[str, Any]] = []
    requirements_without_tests: list[str] = []
    critical_requirements = 0
    critical_passed = 0
    failed_critical_requirements: list[str] = []

    risk_buckets: dict[str, dict[str, int]] = {}

    for requirement in requirements:
        linked_results = []
        executed_count = 0
        passed_count = 0

        for scenario_id in requirement.linked_scenarios:
            scenario = scenario_index.get(scenario_id)
            result = scenario_results.get(scenario_id)
            row = {
                "scenario_id": scenario_id,
                "category": scenario.category if scenario else "unknown",
                "severity": scenario.severity if scenario else "unknown",
                "outcome": result["outcome"] if result else "not_run",
                "duration": result["duration"] if result else 0,
                "nodeid": result["nodeid"] if result else "",
                "message": result["message"] if result else "",
            }
            linked_results.append(row)
            if result:
                executed_count += 1
                if result["outcome"] == "passed":
                    passed_count += 1

        covered = executed_count > 0
        passed = passed_count == len(requirement.linked_scenarios) and covered
        partial = covered and not passed

        if not covered:
            requirements_without_tests.append(requirement.id)
            uncovered_criteria.append(
                {
                    "requirement_id": requirement.id,
                    "criteria": list(requirement.acceptance_criteria),
                }
            )

        if requirement.release_gate == "critical":
            critical_requirements += 1
            if passed:
                critical_passed += 1
            else:
                failed_critical_requirements.append(requirement.id)

        risk_bucket = risk_buckets.setdefault(requirement.risk, {"total": 0, "covered": 0, "passed": 0})
        risk_bucket["total"] += 1
        risk_bucket["covered"] += int(covered)
        risk_bucket["passed"] += int(passed)

        requirement_rows.append(
            {
                "id": requirement.id,
                "title": requirement.title,
                "feature": requirement.feature,
                "priority": requirement.priority,
                "risk": requirement.risk,
                "release_gate": requirement.release_gate,
                "covered": covered,
                "passed": passed,
                "partial": partial,
                "linked_scenarios": linked_results,
                "acceptance_criteria": list(requirement.acceptance_criteria),
            }
        )

    covered_requirements = sum(1 for row in requirement_rows if row["covered"])
    passed_requirements = sum(1 for row in requirement_rows if row["passed"])

    high_risk_total = sum(
        1 for requirement in requirements if requirement.risk in {"high", "critical"}
    )
    high_risk_covered = sum(
        1
        for row in requirement_rows
        if row["risk"] in {"high", "critical"} and row["covered"]
    )

    report = {
        "metadata": {
            "timestamp": _iso_timestamp(results_data.get("created")),
            "provider": provider or "unknown",
            "model": model or "unknown",
        },
        "test_summary": {
            "total": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "overall_pass_rate": _coverage_percent(summary.get("passed", 0), summary.get("total", 0)),
        },
        "requirement_summary": {
            "total": total_requirements,
            "covered": covered_requirements,
            "passed": passed_requirements,
            "coverage_rate": _coverage_percent(covered_requirements, total_requirements),
            "pass_rate": _coverage_percent(passed_requirements, total_requirements),
            "critical_total": critical_requirements,
            "critical_passed": critical_passed,
            "critical_pass_rate": _coverage_percent(critical_passed, critical_requirements),
        },
        "risk_summary": {
            risk: {
                **values,
                "coverage_rate": _coverage_percent(values["covered"], values["total"]),
                "pass_rate": _coverage_percent(values["passed"], values["total"]),
            }
            for risk, values in sorted(risk_buckets.items())
        },
        "gaps": {
            "requirements_without_tests": requirements_without_tests,
            "failed_critical_requirements": failed_critical_requirements,
            "untested_acceptance_criteria": uncovered_criteria,
        },
        "requirements": requirement_rows,
        "history": history or [],
    }

    release_summary = build_release_summary(report, gate_config, high_risk_total, high_risk_covered)
    report["release_summary"] = release_summary
    return report


def build_release_summary(
    report: dict[str, Any],
    gate_config: GateConfig,
    high_risk_total: int | None = None,
    high_risk_covered: int | None = None,
) -> dict[str, Any]:
    overall_pass_rate = report["test_summary"]["overall_pass_rate"]
    critical_pass_rate = report["requirement_summary"]["critical_pass_rate"]
    if high_risk_total is None:
        high_risk_total = sum(
            1
            for requirement in report["requirements"]
            if requirement["risk"] in {"high", "critical"}
        )
    if high_risk_covered is None:
        high_risk_covered = sum(
            1
            for requirement in report["requirements"]
            if requirement["risk"] in {"high", "critical"} and requirement["covered"]
        )
    high_risk_coverage = _coverage_percent(high_risk_covered, high_risk_total)
    reasons: list[str] = []

    if overall_pass_rate < gate_config.overall_pass_rate:
        reasons.append(
            f"Overall pass rate {overall_pass_rate}% is below the gate of {gate_config.overall_pass_rate}%."
        )
    if critical_pass_rate < gate_config.critical_requirements_pass_rate:
        reasons.append(
            "Critical requirement pass rate is below the configured threshold."
        )
    if high_risk_coverage < gate_config.high_risk_coverage:
        reasons.append(
            f"High-risk requirement coverage {high_risk_coverage}% is below the gate of {gate_config.high_risk_coverage}%."
        )
    if gate_config.zero_failed_critical_requirements and report["gaps"]["failed_critical_requirements"]:
        reasons.append("At least one critical requirement has not passed.")

    minor_risks = []
    if report["gaps"]["requirements_without_tests"]:
        minor_risks.append("Some requirements have no executed scenario coverage.")
    if report["gaps"]["untested_acceptance_criteria"]:
        minor_risks.append("Some acceptance criteria remain untested.")

    if reasons:
        decision = "NO-GO"
    elif minor_risks:
        decision = "GO WITH RISKS"
        reasons.extend(minor_risks)
    else:
        decision = "GO"

    return {
        "decision": decision,
        "reasons": reasons,
        "thresholds": {
            "overall_pass_rate": gate_config.overall_pass_rate,
            "critical_requirements_pass_rate": gate_config.critical_requirements_pass_rate,
            "high_risk_coverage": gate_config.high_risk_coverage,
            "zero_failed_critical_requirements": gate_config.zero_failed_critical_requirements,
        },
        "actuals": {
            "overall_pass_rate": overall_pass_rate,
            "critical_requirements_pass_rate": critical_pass_rate,
            "high_risk_coverage": high_risk_coverage,
        },
    }


def generate_traceability_html(report: dict[str, Any]) -> str:
    release_summary = report["release_summary"]
    decision = release_summary["decision"]
    reasons = release_summary["reasons"] or ["No blocking gaps detected."]

    requirement_rows = []
    for requirement in report["requirements"]:
        scenario_rows = "".join(
            (
                "<li>"
                f"{escape(item['scenario_id'])} "
                f"<strong>{escape(item['outcome'])}</strong>"
                "</li>"
            )
            for item in requirement["linked_scenarios"]
        )
        status = "Passed" if requirement["passed"] else "Covered" if requirement["covered"] else "Gap"
        requirement_rows.append(
            f"""
            <tr>
              <td>{escape(requirement['id'])}</td>
              <td>{escape(requirement['title'])}</td>
              <td>{escape(requirement['risk'])}</td>
              <td>{escape(status)}</td>
              <td><ul>{scenario_rows}</ul></td>
            </tr>
            """
        )

    gap_items = []
    for requirement_id in report["gaps"]["requirements_without_tests"]:
        gap_items.append(f"<li>{escape(requirement_id)} has no executed scenario.</li>")
    for criterion_gap in report["gaps"]["untested_acceptance_criteria"]:
        criteria = "".join(f"<li>{escape(item)}</li>" for item in criterion_gap["criteria"])
        gap_items.append(
            "<li>"
            f"{escape(criterion_gap['requirement_id'])} has untested acceptance criteria:<ul>{criteria}</ul>"
            "</li>"
        )
    if not gap_items:
        gap_items.append("<li>No traceability gaps detected.</li>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI QA Framework Traceability Report</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 2rem; color: #0f172a; background: #f8fafc; }}
    h1, h2 {{ color: #0f172a; }}
    .decision {{ padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; background: #e2e8f0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; background: white; }}
    th, td {{ padding: 0.8rem; border: 1px solid #cbd5e1; vertical-align: top; }}
    th {{ background: #e2e8f0; text-align: left; }}
    ul {{ margin: 0; padding-left: 1.2rem; }}
  </style>
</head>
<body>
  <h1>Traceability Report</h1>
  <div class="decision">
    <strong>Release decision:</strong> {escape(decision)}
    <ul>{''.join(f'<li>{escape(reason)}</li>' for reason in reasons)}</ul>
  </div>

  <h2>Traceability Matrix</h2>
  <table>
    <thead>
      <tr>
        <th>Requirement</th>
        <th>Title</th>
        <th>Risk</th>
        <th>Status</th>
        <th>Linked Scenarios</th>
      </tr>
    </thead>
    <tbody>
      {''.join(requirement_rows)}
    </tbody>
  </table>

  <h2>Open Gaps</h2>
  <ul>{''.join(gap_items)}</ul>
</body>
</html>"""


def load_history(history_dir: str | Path | None) -> list[dict[str, Any]]:
    if not history_dir:
        return []

    directory = Path(history_dir)
    if not directory.exists():
        return []

    history: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if "summary" not in data:
            continue
        history.append(
            {
                "timestamp": _iso_timestamp(data.get("created")),
                "overall_pass_rate": _coverage_percent(
                    data.get("summary", {}).get("passed", 0),
                    data.get("summary", {}).get("total", 0),
                ),
            }
        )
    return history


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    destination = Path(path)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
