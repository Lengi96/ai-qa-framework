"""Dashboard and release artifact generator for the AI QA Framework."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from html import escape
from pathlib import Path

from ..quality.reporting import (
    build_traceability_report,
    generate_traceability_html,
    load_history,
    write_json,
)
from ..quality.specs import load_quality_specs


def _extract_metrics(data: dict) -> dict:
    summary = data.get("summary", {})
    tests = data.get("tests", [])
    categories: dict[str, dict[str, int]] = {}

    for test in tests:
        nodeid = test.get("nodeid", "")
        filename = nodeid.split("::")[0].split("/")[-1].split("\\")[-1]
        category = filename.replace("test_", "").replace(".py", "").replace("_scenarios", "")
        category = category.capitalize() if category else "Unknown"
        bucket = categories.setdefault(category, {"passed": 0, "failed": 0, "skipped": 0})
        outcome = test.get("outcome", "unknown")
        if outcome == "passed":
            bucket["passed"] += 1
        elif outcome == "failed":
            bucket["failed"] += 1
        else:
            bucket["skipped"] += 1

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration": round(float(data.get("duration", 0.0)), 2),
        "pass_rate": round((passed / total) * 100, 1) if total else 0.0,
        "timestamp": data.get("created", datetime.now().isoformat()),
        "categories": categories,
    }


def _format_timestamp(timestamp: object) -> str:
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str) and timestamp.strip():
        raw = timestamp.strip()
        try:
            dt = datetime.fromtimestamp(float(raw))
        except ValueError:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    else:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _release_color(decision: str) -> str:
    return {
        "GO": "#16a34a",
        "GO WITH RISKS": "#d97706",
        "NO-GO": "#dc2626",
    }.get(decision, "#475569")


def _build_requirement_rows(traceability: dict) -> str:
    rows = []
    for requirement in traceability["requirements"]:
        scenario_text = ", ".join(
            f"{item['scenario_id']} ({item['outcome']})" for item in requirement["linked_scenarios"]
        )
        status = "Passed" if requirement["passed"] else "Covered" if requirement["covered"] else "Gap"
        rows.append(
            f"<tr><td>{escape(requirement['id'])}</td>"
            f"<td>{escape(requirement['title'])}</td>"
            f"<td>{escape(requirement['risk'])}</td>"
            f"<td>{escape(status)}</td>"
            f"<td>{escape(scenario_text)}</td></tr>"
        )
    return "".join(rows)


def _build_risk_rows(traceability: dict) -> str:
    rows = []
    for risk, values in traceability["risk_summary"].items():
        rows.append(
            f"<tr><td>{escape(risk)}</td>"
            f"<td>{values['covered']} / {values['total']}</td>"
            f"<td>{values['coverage_rate']}%</td>"
            f"<td>{values['pass_rate']}%</td></tr>"
        )
    return "".join(rows)


def _build_gap_items(traceability: dict) -> str:
    items = []
    for requirement_id in traceability["gaps"]["requirements_without_tests"]:
        items.append(f"<li>{escape(requirement_id)} has no executed scenario coverage.</li>")
    for requirement_id in traceability["gaps"]["failed_critical_requirements"]:
        items.append(f"<li>{escape(requirement_id)} is critical and not fully passed.</li>")
    for criterion_gap in traceability["gaps"]["untested_acceptance_criteria"]:
        criteria = "; ".join(criterion_gap["criteria"])
        items.append(
            f"<li>{escape(criterion_gap['requirement_id'])} has untested acceptance criteria: {escape(criteria)}</li>"
        )
    return "".join(items) or "<li>No open gaps detected.</li>"


def _build_history_rows(traceability: dict) -> str:
    history = traceability.get("history", [])
    if not history:
        current = traceability["metadata"]
        decision = traceability["release_summary"]["decision"]
        return (
            f"<tr><td>{escape(_format_timestamp(current['timestamp']))}</td>"
            f"<td>{escape(current['provider'])}</td>"
            f"<td>{escape(current['model'])}</td>"
            f"<td>{traceability['test_summary']['overall_pass_rate']}%</td>"
            f"<td>{escape(decision)}</td></tr>"
        )

    rows = []
    for item in history:
        rows.append(
            f"<tr><td>{escape(_format_timestamp(item['timestamp']))}</td>"
            f"<td>{escape(str(item.get('provider', 'n/a')))}</td>"
            f"<td>{escape(str(item.get('model', 'n/a')))}</td>"
            f"<td>{escape(str(item['overall_pass_rate']))}%</td>"
            f"<td>{escape(str(item.get('decision', 'n/a')))}</td></tr>"
        )
    return "".join(rows)


def _generate_html(metrics: dict, traceability: dict) -> str:
    release = traceability["release_summary"]
    release_color = _release_color(release["decision"])
    chart_labels = list(metrics["categories"].keys())
    chart_passed = [metrics["categories"][name]["passed"] for name in chart_labels]
    chart_failed = [metrics["categories"][name]["failed"] for name in chart_labels]
    chart_skipped = [metrics["categories"][name]["skipped"] for name in chart_labels]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI QA Framework Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 2rem; background: #0f172a; color: #e2e8f0; }}
    h1, h2, h3 {{ color: #f8fafc; }}
    .grid {{ display: grid; gap: 1rem; }}
    .metrics {{ grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin-bottom: 1.5rem; }}
    .two {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); margin-bottom: 1.5rem; }}
    .card {{ background: #1e293b; border-radius: 12px; padding: 1.25rem; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25); }}
    .value {{ font-size: 2rem; font-weight: 700; color: #f8fafc; }}
    .label {{ color: #94a3b8; font-size: 0.85rem; margin-top: 0.25rem; }}
    .decision {{ border-left: 6px solid {release_color}; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 0.75rem; }}
    th, td {{ padding: 0.75rem; border-bottom: 1px solid #334155; text-align: left; vertical-align: top; }}
    th {{ color: #cbd5e1; font-size: 0.82rem; text-transform: uppercase; }}
    .banner {{ margin-bottom: 1.5rem; background: {release_color}22; border: 1px solid {release_color}; border-radius: 12px; padding: 1rem 1.25rem; }}
    .banner strong {{ color: {release_color}; }}
    ul {{ padding-left: 1.2rem; }}
    a {{ color: #93c5fd; }}
  </style>
</head>
<body>
  <div class="banner">
    <strong>{escape(release['decision'])}</strong>
    <div>Generated {_format_timestamp(metrics['timestamp'])} for provider {escape(traceability['metadata']['provider'])} / model {escape(traceability['metadata']['model'])}</div>
  </div>

  <div class="grid metrics">
    <div class="card"><div class="value">{metrics['total']}</div><div class="label">Total Tests</div></div>
    <div class="card"><div class="value">{metrics['passed']}</div><div class="label">Passed</div></div>
    <div class="card"><div class="value">{metrics['failed']}</div><div class="label">Failed</div></div>
    <div class="card"><div class="value">{metrics['pass_rate']}%</div><div class="label">Overall Pass Rate</div></div>
    <div class="card"><div class="value">{traceability['requirement_summary']['coverage_rate']}%</div><div class="label">Requirement Coverage</div></div>
    <div class="card"><div class="value">{traceability['release_summary']['actuals']['high_risk_coverage']}%</div><div class="label">High-Risk Coverage</div></div>
  </div>

  <div class="grid two">
    <div class="card decision">
      <h2>Release Decision</h2>
      <p><strong>{escape(release['decision'])}</strong></p>
      <ul>{''.join(f'<li>{escape(reason)}</li>' for reason in release['reasons']) or '<li>No blocking reasons recorded.</li>'}</ul>
      <p><a href="traceability.html">Open traceability report</a></p>
    </div>
    <div class="card">
      <h2>Requirement Summary</h2>
      <table>
        <tr><th>Total</th><td>{traceability['requirement_summary']['total']}</td></tr>
        <tr><th>Covered</th><td>{traceability['requirement_summary']['covered']}</td></tr>
        <tr><th>Passed</th><td>{traceability['requirement_summary']['passed']}</td></tr>
        <tr><th>Critical Pass Rate</th><td>{traceability['requirement_summary']['critical_pass_rate']}%</td></tr>
      </table>
    </div>
  </div>

  <div class="grid two">
    <div class="card">
      <h2>Category Results</h2>
      <canvas id="categoryChart"></canvas>
    </div>
    <div class="card">
      <h2>Open Gaps</h2>
      <ul>{_build_gap_items(traceability)}</ul>
    </div>
  </div>

  <div class="grid two">
    <div class="card">
      <h2>Coverage by Risk</h2>
      <table>
        <thead><tr><th>Risk</th><th>Covered</th><th>Coverage</th><th>Pass</th></tr></thead>
        <tbody>{_build_risk_rows(traceability)}</tbody>
      </table>
    </div>
    <div class="card">
      <h2>Provider / Model History</h2>
      <table>
        <thead><tr><th>Timestamp</th><th>Provider</th><th>Model</th><th>Pass Rate</th><th>Decision</th></tr></thead>
        <tbody>{_build_history_rows(traceability)}</tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <h2>Requirement Traceability</h2>
    <table>
      <thead><tr><th>Requirement</th><th>Title</th><th>Risk</th><th>Status</th><th>Linked Scenarios</th></tr></thead>
      <tbody>{_build_requirement_rows(traceability)}</tbody>
    </table>
  </div>

  <script>
    new Chart(document.getElementById('categoryChart'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(chart_labels)},
        datasets: [
          {{ label: 'Passed', data: {json.dumps(chart_passed)}, backgroundColor: '#10b981' }},
          {{ label: 'Failed', data: {json.dumps(chart_failed)}, backgroundColor: '#ef4444' }},
          {{ label: 'Skipped', data: {json.dumps(chart_skipped)}, backgroundColor: '#f59e0b' }},
        ],
      }},
      options: {{
        responsive: true,
        scales: {{
          x: {{ stacked: true, ticks: {{ color: '#cbd5e1' }}, grid: {{ display: false }} }},
          y: {{ stacked: true, ticks: {{ color: '#cbd5e1', stepSize: 1 }}, grid: {{ color: '#334155' }} }},
        }},
        plugins: {{ legend: {{ labels: {{ color: '#e2e8f0' }} }} }},
      }},
    }});
  </script>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate dashboard and release-readiness artifacts")
    parser.add_argument("results_file", help="Path to pytest JSON report file")
    parser.add_argument("-o", "--output", default="dashboard.html", help="Output dashboard HTML")
    parser.add_argument("--provider", default=None, help="Provider label for the current run")
    parser.add_argument("--model", default=None, help="Model label for the current run")
    parser.add_argument("--history-dir", default=None, help="Optional directory with prior pytest JSON reports")
    parser.add_argument("--traceability-out", default="traceability.json", help="Traceability JSON output path")
    parser.add_argument("--traceability-html", default="traceability.html", help="Traceability HTML output path")
    parser.add_argument("--release-summary-out", default="release_summary.json", help="Release summary JSON output path")
    parser.add_argument("--fail-on-no-go", action="store_true", help="Exit with code 1 when the decision is NO-GO")
    args = parser.parse_args()

    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"Error: Results file not found: {results_path}")
        return 1

    with results_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    metrics = _extract_metrics(data)
    requirements, scenarios, gates = load_quality_specs()
    history = load_history(args.history_dir)
    traceability = build_traceability_report(
        data,
        requirements,
        scenarios,
        gates,
        provider=args.provider,
        model=args.model,
        history=history,
    )

    dashboard_html = _generate_html(metrics, traceability)
    Path(args.output).write_text(dashboard_html, encoding="utf-8")
    Path(args.traceability_html).write_text(generate_traceability_html(traceability), encoding="utf-8")
    write_json(args.traceability_out, traceability)
    write_json(args.release_summary_out, traceability["release_summary"])

    print(f"Dashboard generated: {Path(args.output).resolve()}")
    print(f"Traceability JSON: {Path(args.traceability_out).resolve()}")
    print(f"Release summary: {Path(args.release_summary_out).resolve()}")
    print(f"Decision: {traceability['release_summary']['decision']}")

    if args.fail_on_no_go and traceability["release_summary"]["decision"] == "NO-GO":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

