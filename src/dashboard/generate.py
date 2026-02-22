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
from html import escape
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


def _format_timestamp(timestamp: object) -> str:
    """Render the report timestamp as a human-readable local datetime."""
    dt: datetime | None = None

    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        raw = timestamp.strip()
        if raw:
            # Handle numeric timestamps represented as strings.
            try:
                dt = datetime.fromtimestamp(float(raw))
            except ValueError:
                # Handle ISO-like timestamps from pytest-json-report.
                try:
                    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    dt = None

    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _stringify_message(message: object) -> str:
    """Normalize pytest longrepr payloads into readable text."""
    if message is None:
        return ""
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        return "\n".join(str(item) for item in message)
    if isinstance(message, dict):
        try:
            return json.dumps(message, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return str(message)
    return str(message)


# -- HTML generation ---------------------------------------------------------


def _generate_html(metrics: dict) -> str:
    """Generate a standalone HTML dashboard from metrics."""
    categories = metrics["categories"]

    # Build category chart data
    cat_labels = list(categories.keys())
    cat_passed = [categories[c]["passed"] for c in cat_labels]
    cat_failed = [categories[c]["failed"] for c in cat_labels]
    cat_skipped = [categories[c]["skipped"] for c in cat_labels]

    # Build test detail rows (failed first, then by category and name).
    test_items: list[dict] = []
    for cat, data in categories.items():
        for test in data["tests"]:
            test_items.append({
                "category": cat,
                **test,
            })

    outcome_order = {"failed": 0, "skipped": 1, "xfailed": 1, "passed": 2}
    test_items.sort(
        key=lambda item: (
            outcome_order.get(item.get("outcome", ""), 9),
            item.get("category", ""),
            item.get("name", ""),
        )
    )

    test_rows = ""
    failure_links = ""
    failure_count = 0
    for test in test_items:
        cat = test["category"]
        name = test["name"]
        outcome = test["outcome"]
        test_id = f"{cat.lower()}-{name.lower()}".replace("_", "-")
        badge_class = {
            "passed": "badge-pass",
            "failed": "badge-fail",
            "skipped": "badge-skip",
            "xfailed": "badge-skip",
        }.get(outcome, "badge-skip")

        duration_str = f"{test['duration']:.2f}s" if test["duration"] else "-"
        message_text = _stringify_message(test.get("message"))
        detail_html = ""
        if outcome == "failed":
            failure_count += 1
            first_line = message_text.strip().splitlines()[0] if message_text.strip() else "No failure message."
            failure_links += (
                f'<li><a href="#{escape(test_id)}">{escape(cat)} / {escape(name)}</a>'
                f' <span class="failure-snippet">{escape(first_line[:180])}</span></li>'
            )
            if message_text.strip():
                detail_html = (
                    "<details class=\"failure-details\">"
                    "<summary>Failure details</summary>"
                    f"<pre>{escape(message_text)}</pre>"
                    "</details>"
                )
            else:
                detail_html = "<p class=\"failure-empty\">No failure details captured.</p>"

        test_rows += f"""
            <tr id="{escape(test_id)}" data-category="{escape(cat.lower())}" data-outcome="{escape(outcome.lower())}" data-test="{escape(name.lower())}">
                <td>{escape(cat)}</td>
                <td>
                    {escape(name)}
                    {detail_html}
                </td>
                <td><span class="badge {badge_class}">{escape(outcome)}</span></td>
                <td>{duration_str}</td>
            </tr>"""

    formatted_timestamp = _format_timestamp(metrics["timestamp"])
    chart_summary = (
        f"Categories: {', '.join(cat_labels)}. "
        f"Passed {metrics['passed']}, failed {metrics['failed']}, skipped {metrics['skipped']}."
    )
    failed_hint = (
        f" | {metrics['failed']} failing test(s) - "
        "<a href=\"#test-details\" id=\"showFailedLink\">show failed only</a>"
        if metrics["failed"] > 0
        else ""
    )
    failure_section = (
        f"""
    <section class="failure-section" aria-label="Failing tests overview">
        <h3>Failing Tests ({failure_count})</h3>
        <ul class="failure-list">
            {failure_links}
        </ul>
    </section>
"""
        if failure_count > 0
        else ""
    )

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
        .status-banner a {{
            color: #f8fafc;
            text-decoration: underline;
            margin-left: 0.4rem;
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
        .failure-section {{
            background: #7f1d1d40;
            border: 1px solid #ef4444;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .failure-section h3 {{
            color: #fecaca;
            margin-bottom: 0.6rem;
            font-size: 1rem;
        }}
        .failure-list {{
            margin: 0;
            padding-left: 1.25rem;
        }}
        .failure-list li {{
            margin: 0.3rem 0;
            color: #fee2e2;
            line-height: 1.35;
        }}
        .failure-list a {{
            color: #fca5a5;
        }}
        .failure-snippet {{
            color: #cbd5e1;
            margin-left: 0.3rem;
            font-size: 0.85rem;
        }}
        .chart-summary {{
            color: #94a3b8;
            font-size: 0.85rem;
            margin-top: 0.75rem;
        }}
        .table-controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
            align-items: center;
        }}
        .table-controls label,
        .table-controls .visible-count {{
            color: #cbd5e1;
            font-size: 0.85rem;
        }}
        .table-controls input[type="search"],
        .table-controls select {{
            background: #0f172a;
            color: #e2e8f0;
            border: 1px solid #475569;
            border-radius: 6px;
            padding: 0.4rem 0.55rem;
        }}
        .table-wrap {{
            overflow-x: auto;
        }}
        #testTable {{
            min-width: 640px;
        }}
        .failure-details {{
            margin-top: 0.45rem;
        }}
        .failure-details summary {{
            cursor: pointer;
            color: #fca5a5;
            font-size: 0.82rem;
        }}
        .failure-details pre {{
            white-space: pre-wrap;
            background: #0f172a;
            border: 1px solid #475569;
            border-radius: 6px;
            padding: 0.6rem;
            margin-top: 0.4rem;
            color: #e2e8f0;
            font-size: 0.78rem;
            max-height: 280px;
            overflow: auto;
        }}
        .failure-empty {{
            margin-top: 0.45rem;
            color: #cbd5e1;
            font-size: 0.8rem;
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
            .table-controls {{
                flex-direction: column;
                align-items: flex-start;
            }}
            th, td {{
                padding: 0.6rem 0.75rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI QA Framework Dashboard</h1>
        <div class="subtitle">Generated: {formatted_timestamp}</div>
    </div>

    <div class="status-banner">{status_text} &mdash; {metrics['pass_rate']}% Pass Rate{failed_hint}</div>
    {failure_section}

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
            <canvas id="categoryChart" role="img" aria-label="Stacked bar chart of test outcomes by category"></canvas>
        </div>
        <div class="chart-card">
            <h3>Overall Distribution</h3>
            <canvas id="donutChart" role="img" aria-label="Donut chart of overall pass, fail, and skip distribution"></canvas>
        </div>
    </div>
    <p class="chart-summary">{escape(chart_summary)}</p>

    <h3 class="section-title" id="test-details">Test Details</h3>
    <div class="table-controls">
        <label><input type="checkbox" id="failedOnly"> Show failed only</label>
        <label>Category
            <select id="categoryFilter">
                <option value="">All</option>
            </select>
        </label>
        <label>Search test
            <input type="search" id="testSearch" placeholder="e.g. age_neutral" />
        </label>
        <span class="visible-count" id="visibleCount"></span>
    </div>
    <div class="table-wrap">
        <table id="testTable">
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
    </div>

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

        const rows = Array.from(document.querySelectorAll('#testTable tbody tr'));
        const failedOnly = document.getElementById('failedOnly');
        const categoryFilter = document.getElementById('categoryFilter');
        const testSearch = document.getElementById('testSearch');
        const visibleCount = document.getElementById('visibleCount');
        const showFailedLink = document.getElementById('showFailedLink');

        const categories = Array.from(new Set(rows.map((row) => row.dataset.category))).sort();
        categories.forEach((category) => {{
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category.charAt(0).toUpperCase() + category.slice(1);
            categoryFilter.appendChild(option);
        }});

        function applyTableFilters() {{
            const searchText = testSearch.value.trim().toLowerCase();
            const selectedCategory = categoryFilter.value;
            let visible = 0;

            rows.forEach((row) => {{
                const matchesFailed = !failedOnly.checked || row.dataset.outcome === 'failed';
                const matchesCategory = !selectedCategory || row.dataset.category === selectedCategory;
                const matchesSearch = !searchText || row.dataset.test.includes(searchText);
                const show = matchesFailed && matchesCategory && matchesSearch;
                row.style.display = show ? '' : 'none';
                if (show) visible += 1;
            }});

            visibleCount.textContent = `${{visible}} / ${{rows.length}} tests shown`;
        }}

        failedOnly.addEventListener('change', applyTableFilters);
        categoryFilter.addEventListener('change', applyTableFilters);
        testSearch.addEventListener('input', applyTableFilters);
        showFailedLink?.addEventListener('click', (event) => {{
            event.preventDefault();
            failedOnly.checked = true;
            applyTableFilters();
            document.getElementById('test-details').scrollIntoView({{ behavior: 'smooth' }});
        }});

        applyTableFilters();
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
