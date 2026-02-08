"""
Custom Metric Dashboard Generator for AI QA Framework.

Reads pytest JSON results and generates a standalone HTML dashboard
with charts, category breakdowns, and trend tracking.

Usage:
    # 1. Run tests with JSON output
    pytest tests/ --json-report --json-report-file=results.json

    # 2. Generate dashboard
    python -m dashboard.generate results.json

    # Or use the convenience script:
    python -m dashboard.generate results.json -o dashboard.html
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


# -- Data extraction ---------------------------------------------------------


def _extract_metrics(data: dict) -> dict:
    """Extract key metrics from pytest-json-report output."""
    summary = data.get("summary", {})
    tests = data.get("tests", [])

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    xfailed = summary.get("xfailed", 0)
    duration = data.get("duration", 0)

    # Group by category
    categories = {}
    for test in tests:
        node_id = test.get("nodeid", "")
        # Extract category from file name: tests/test_security.py -> security
        parts = node_id.split("::")
        if parts:
            filename = parts[0].split("/")[-1].replace("test_", "").replace(".py", "")
            cat = filename.capitalize()
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0, "skipped": 0, "tests": []}

            outcome = test.get("outcome", "unknown")
            if outcome == "passed":
                categories[cat]["passed"] += 1
            elif outcome == "failed":
                categories[cat]["failed"] += 1
            else:
                categories[cat]["skipped"] += 1

            categories[cat]["tests"].append({
                "name": parts[-1] if len(parts) > 1 else node_id,
                "outcome": outcome,
                "duration": test.get("call", {}).get("duration", 0),
                "message": test.get("call", {}).get("longrepr", ""),
            })

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "xfailed": xfailed,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "duration": round(duration, 2),
        "categories": categories,
        "timestamp": data.get("created", datetime.now().isoformat()),
    }


# -- HTML generation ---------------------------------------------------------


def _generate_html(metrics: dict) -> str:
    """Generate a standalone HTML dashboard from metrics."""
    categories = metrics["categories"]

    # Build category chart data
    cat_labels = list(categories.keys())
    cat_passed = [categories[c]["passed"] for c in cat_labels]
    cat_failed = [categories[c]["failed"] for c in cat_labels]
    cat_skipped = [categories[c]["skipped"] for c in cat_labels]

    # Build test detail rows
    test_rows = ""
    for cat, data in categories.items():
        for test in data["tests"]:
            outcome = test["outcome"]
            badge_class = {
                "passed": "badge-pass",
                "failed": "badge-fail",
                "skipped": "badge-skip",
                "xfailed": "badge-skip",
            }.get(outcome, "badge-skip")

            duration_str = f"{test['duration']:.2f}s" if test["duration"] else "-"

            test_rows += f"""
            <tr>
                <td>{cat}</td>
                <td>{test['name']}</td>
                <td><span class="badge {badge_class}">{outcome}</span></td>
                <td>{duration_str}</td>
            </tr>"""

    # Status color
    if metrics["pass_rate"] == 100:
        status_color = "#10b981"
        status_text = "ALL PASSED"
    elif metrics["pass_rate"] >= 80:
        status_color = "#f59e0b"
        status_text = "SOME FAILURES"
    else:
        status_color = "#ef4444"
        status_text = "CRITICAL"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI QA Framework - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 2rem;
        }}
        .header {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        .header h1 {{
            font-size: 1.8rem;
            color: #f8fafc;
            margin-bottom: 0.5rem;
        }}
        .header .subtitle {{
            color: #94a3b8;
            font-size: 0.9rem;
        }}
        .status-banner {{
            background: {status_color}20;
            border: 1px solid {status_color};
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            margin-bottom: 2rem;
            font-size: 1.2rem;
            font-weight: 700;
            color: {status_color};
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .metric-card {{
            background: #1e293b;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
        }}
        .metric-card .value {{
            font-size: 2rem;
            font-weight: 700;
            color: #f8fafc;
        }}
        .metric-card .label {{
            color: #94a3b8;
            font-size: 0.85rem;
            margin-top: 0.3rem;
        }}
        .metric-card .value.pass {{ color: #10b981; }}
        .metric-card .value.fail {{ color: #ef4444; }}
        .metric-card .value.skip {{ color: #f59e0b; }}
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .chart-card {{
            background: #1e293b;
            border-radius: 8px;
            padding: 1.5rem;
        }}
        .chart-card h3 {{
            color: #f8fafc;
            margin-bottom: 1rem;
            font-size: 1rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid #334155;
        }}
        th {{
            background: #334155;
            color: #f8fafc;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }}
        td {{ font-size: 0.9rem; }}
        .badge {{
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-pass {{ background: #10b98120; color: #10b981; }}
        .badge-fail {{ background: #ef444420; color: #ef4444; }}
        .badge-skip {{ background: #f59e0b20; color: #f59e0b; }}
        .section-title {{
            font-size: 1.1rem;
            color: #f8fafc;
            margin-bottom: 1rem;
        }}
        .footer {{
            text-align: center;
            color: #64748b;
            font-size: 0.8rem;
            margin-top: 2rem;
        }}
        @media (max-width: 768px) {{
            .charts-grid {{ grid-template-columns: 1fr; }}
            body {{ padding: 1rem; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI QA Framework Dashboard</h1>
        <div class="subtitle">Generated: {metrics['timestamp']}</div>
    </div>

    <div class="status-banner">{status_text} &mdash; {metrics['pass_rate']}% Pass Rate</div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="value">{metrics['total']}</div>
            <div class="label">Total Tests</div>
        </div>
        <div class="metric-card">
            <div class="value pass">{metrics['passed']}</div>
            <div class="label">Passed</div>
        </div>
        <div class="metric-card">
            <div class="value fail">{metrics['failed']}</div>
            <div class="label">Failed</div>
        </div>
        <div class="metric-card">
            <div class="value skip">{metrics['skipped']}</div>
            <div class="label">Skipped</div>
        </div>
        <div class="metric-card">
            <div class="value">{metrics['duration']}s</div>
            <div class="label">Total Duration</div>
        </div>
        <div class="metric-card">
            <div class="value">{metrics['pass_rate']}%</div>
            <div class="label">Pass Rate</div>
        </div>
    </div>

    <div class="charts-grid">
        <div class="chart-card">
            <h3>Results by Category</h3>
            <canvas id="categoryChart"></canvas>
        </div>
        <div class="chart-card">
            <h3>Overall Distribution</h3>
            <canvas id="donutChart"></canvas>
        </div>
    </div>

    <h3 class="section-title">Test Details</h3>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th>Test</th>
                <th>Result</th>
                <th>Duration</th>
            </tr>
        </thead>
        <tbody>
            {test_rows}
        </tbody>
    </table>

    <div class="footer">
        AI QA Framework &bull; Generated by dashboard.generate
    </div>

    <script>
        // Category stacked bar chart
        new Chart(document.getElementById('categoryChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(cat_labels)},
                datasets: [
                    {{
                        label: 'Passed',
                        data: {json.dumps(cat_passed)},
                        backgroundColor: '#10b981',
                    }},
                    {{
                        label: 'Failed',
                        data: {json.dumps(cat_failed)},
                        backgroundColor: '#ef4444',
                    }},
                    {{
                        label: 'Skipped',
                        data: {json.dumps(cat_skipped)},
                        backgroundColor: '#f59e0b',
                    }},
                ],
            }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{
                        stacked: true,
                        ticks: {{ color: '#94a3b8' }},
                        grid: {{ display: false }},
                    }},
                    y: {{
                        stacked: true,
                        ticks: {{ color: '#94a3b8', stepSize: 1 }},
                        grid: {{ color: '#334155' }},
                    }},
                }},
                plugins: {{
                    legend: {{ labels: {{ color: '#e2e8f0' }} }},
                }},
            }},
        }});

        // Donut chart
        new Chart(document.getElementById('donutChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Passed', 'Failed', 'Skipped'],
                datasets: [{{
                    data: [{metrics['passed']}, {metrics['failed']}, {metrics['skipped']}],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
                    borderWidth: 0,
                }}],
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ labels: {{ color: '#e2e8f0' }} }},
                }},
            }},
        }});
    </script>
</body>
</html>"""


# -- CLI entry point ---------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI QA Framework HTML dashboard from test results"
    )
    parser.add_argument(
        "results_file",
        help="Path to pytest JSON report file (pytest --json-report)",
    )
    parser.add_argument(
        "-o", "--output",
        default="dashboard.html",
        help="Output HTML file (default: dashboard.html)",
    )
    args = parser.parse_args()

    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"Error: Results file not found: {results_path}")
        sys.exit(1)

    with open(results_path) as f:
        data = json.load(f)

    metrics = _extract_metrics(data)
    html = _generate_html(metrics)

    output_path = Path(args.output)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {output_path.resolve()}")
    print(f"  Tests: {metrics['total']} | Passed: {metrics['passed']} | "
          f"Failed: {metrics['failed']} | Pass Rate: {metrics['pass_rate']}%")


if __name__ == "__main__":
    main()
