#!/usr/bin/env python3
"""Nightly task graph audit script.

Reads index.json and checks for governance issues:
- Orphan tasks (no parent, not a goal/learn/project)
- Sibling explosion (>10 children warning, >20 critical)
- Priority distribution (P1 > 25% = warning)
- Stale in_progress tasks
- Reachability from goals (BFS from goal nodes, report unreachable %)

Output: markdown report + JSON, exit code based on severity.
Reports saved to ~/brain/audits/ when run via cron.

Usage:
    python scripts/audit_task_graph.py                    # stdout
    python scripts/audit_task_graph.py --output ~/brain/audits/  # save to dir
    python scripts/audit_task_graph.py --json              # JSON only
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Types allowed at root level without parent
ROOT_ALLOWED_TYPES = {"goal", "learn", "project"}

# Severity thresholds
SIBLING_WARN = 10
SIBLING_CRITICAL = 20
P1_PERCENT_WARN = 25
STALE_HOURS = 24  # in_progress tasks older than this


def load_index(index_path: Path) -> dict:
    """Load and validate index.json."""
    if not index_path.exists():
        print(f"Error: index.json not found at {index_path}", file=sys.stderr)
        sys.exit(2)

    with open(index_path, encoding="utf-8") as f:
        data = json.load(f)

    if data.get("version") != 2:
        print(f"Error: Unsupported index version: {data.get('version')}", file=sys.stderr)
        sys.exit(2)

    return data


def check_orphans(tasks: dict) -> list[dict]:
    """Find tasks without parent that aren't root-allowed types."""
    findings = []
    task_ids = set(tasks.keys())

    for tid, t in tasks.items():
        parent = t.get("parent")
        task_type = t.get("type", "task")

        # Skip completed/cancelled
        if t.get("status") in ("done", "cancelled"):
            continue

        # Orphan: no parent, or parent doesn't exist in index
        is_orphan = parent is None or parent not in task_ids

        if is_orphan and task_type not in ROOT_ALLOWED_TYPES:
            findings.append({
                "id": tid,
                "title": t.get("title", ""),
                "type": task_type,
                "project": t.get("project"),
                "severity": "warning",
                "check": "orphan",
                "detail": f"No parent (type: {task_type})",
            })

    return findings


def check_sibling_explosion(tasks: dict) -> list[dict]:
    """Find nodes with too many children."""
    findings = []

    for tid, t in tasks.items():
        children = t.get("children", [])
        count = len(children)

        if count > SIBLING_CRITICAL:
            findings.append({
                "id": tid,
                "title": t.get("title", ""),
                "type": t.get("type"),
                "child_count": count,
                "severity": "critical",
                "check": "sibling_explosion",
                "detail": f"{count} children (critical threshold: {SIBLING_CRITICAL})",
            })
        elif count > SIBLING_WARN:
            findings.append({
                "id": tid,
                "title": t.get("title", ""),
                "type": t.get("type"),
                "child_count": count,
                "severity": "warning",
                "check": "sibling_explosion",
                "detail": f"{count} children (warning threshold: {SIBLING_WARN})",
            })

    return findings


def check_priority_distribution(tasks: dict) -> list[dict]:
    """Check if priority distribution is skewed."""
    findings = []

    # Only check active (non-done, non-cancelled) tasks
    active_tasks = {
        tid: t for tid, t in tasks.items()
        if t.get("status") not in ("done", "cancelled")
    }

    if not active_tasks:
        return findings

    priority_counts = Counter(t.get("priority", 2) for t in active_tasks.values())
    total = len(active_tasks)
    p1_count = priority_counts.get(1, 0)
    p1_pct = (p1_count / total * 100) if total > 0 else 0

    if p1_pct > P1_PERCENT_WARN:
        findings.append({
            "check": "priority_inflation",
            "severity": "warning",
            "detail": f"P1 tasks: {p1_count}/{total} ({p1_pct:.1f}%) exceeds {P1_PERCENT_WARN}% threshold",
            "distribution": {f"P{k}": v for k, v in sorted(priority_counts.items())},
        })

    return findings


def check_stale_in_progress(tasks: dict) -> list[dict]:
    """Find in_progress tasks that haven't been modified recently."""
    findings = []
    now = datetime.now(timezone.utc)

    for tid, t in tasks.items():
        if t.get("status") != "in_progress":
            continue

        # Index doesn't always have timestamps; flag all in_progress for audit
        findings.append({
            "id": tid,
            "title": t.get("title", ""),
            "type": t.get("type"),
            "project": t.get("project"),
            "assignee": t.get("assignee"),
            "severity": "info",
            "check": "stale_in_progress",
            "detail": f"Task in_progress (assignee: {t.get('assignee', 'unassigned')})",
        })

    return findings


def check_reachability(tasks: dict) -> list[dict]:
    """Check what percentage of tasks are reachable from goal nodes."""
    findings = []

    # Find all goal nodes
    goal_ids = {tid for tid, t in tasks.items() if t.get("type") == "goal"}

    if not goal_ids:
        findings.append({
            "check": "reachability",
            "severity": "info",
            "detail": "No goal nodes found - cannot assess reachability",
        })
        return findings

    # BFS from goals through children links
    reachable = set()
    queue = list(goal_ids)

    while queue:
        current = queue.pop(0)
        if current in reachable:
            continue
        reachable.add(current)

        t = tasks.get(current, {})
        for child_id in t.get("children", []):
            if child_id not in reachable and child_id in tasks:
                queue.append(child_id)

    # Count unreachable active tasks
    active_tasks = {
        tid for tid, t in tasks.items()
        if t.get("status") not in ("done", "cancelled")
    }

    unreachable = active_tasks - reachable
    total_active = len(active_tasks)
    unreachable_count = len(unreachable)
    unreachable_pct = (unreachable_count / total_active * 100) if total_active > 0 else 0

    severity = "info"
    if unreachable_pct > 50:
        severity = "critical"
    elif unreachable_pct > 25:
        severity = "warning"

    findings.append({
        "check": "reachability",
        "severity": severity,
        "detail": (
            f"{unreachable_count}/{total_active} active tasks "
            f"({unreachable_pct:.1f}%) unreachable from goals"
        ),
        "reachable_count": total_active - unreachable_count,
        "unreachable_count": unreachable_count,
        "total_active": total_active,
        "unreachable_pct": round(unreachable_pct, 1),
    })

    return findings


def generate_markdown_report(
    findings: list[dict],
    stats: dict,
    generated: str,
) -> str:
    """Generate a markdown audit report."""
    lines = [
        "# Task Graph Audit Report",
        "",
        f"**Generated**: {generated}",
        f"**Index timestamp**: {stats.get('index_generated', 'unknown')}",
        f"**Total tasks**: {stats['total_tasks']}",
        f"**Active tasks**: {stats['active_tasks']}",
        "",
    ]

    # Summary
    severity_counts = Counter(f.get("severity") for f in findings)
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Critical: {severity_counts.get('critical', 0)}")
    lines.append(f"- Warning: {severity_counts.get('warning', 0)}")
    lines.append(f"- Info: {severity_counts.get('info', 0)}")
    lines.append("")

    # Group by check type
    checks = {}
    for f in findings:
        check = f.get("check", "unknown")
        checks.setdefault(check, []).append(f)

    check_titles = {
        "orphan": "Orphan Tasks (no parent, non-root type)",
        "sibling_explosion": "Sibling Explosion (excessive children)",
        "priority_inflation": "Priority Distribution",
        "stale_in_progress": "In-Progress Tasks",
        "reachability": "Goal Reachability",
    }

    for check_name, check_findings in checks.items():
        title = check_titles.get(check_name, check_name)
        lines.append(f"## {title}")
        lines.append("")

        for f in check_findings:
            severity = f.get("severity", "info").upper()
            detail = f.get("detail", "")
            task_id = f.get("id")

            if task_id:
                lines.append(f"- [{severity}] `{task_id}`: {detail}")
            else:
                lines.append(f"- [{severity}] {detail}")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit task graph for governance issues")
    parser.add_argument(
        "--index",
        type=Path,
        default=Path.home() / "brain" / "tasks" / "index.json",
        help="Path to index.json (default: ~/brain/tasks/index.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for reports (default: stdout only)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of markdown",
    )
    args = parser.parse_args()

    # Load index
    data = load_index(args.index)
    tasks = data.get("tasks", {})
    now = datetime.now(timezone.utc).isoformat()

    # Stats
    active_tasks = {
        tid for tid, t in tasks.items()
        if t.get("status") not in ("done", "cancelled")
    }
    stats = {
        "total_tasks": len(tasks),
        "active_tasks": len(active_tasks),
        "index_generated": data.get("generated", "unknown"),
    }

    # Run all checks
    findings = []
    findings.extend(check_orphans(tasks))
    findings.extend(check_sibling_explosion(tasks))
    findings.extend(check_priority_distribution(tasks))
    findings.extend(check_stale_in_progress(tasks))
    findings.extend(check_reachability(tasks))

    # Determine exit code
    severity_counts = Counter(f.get("severity") for f in findings)
    if severity_counts.get("critical", 0) > 0:
        exit_code = 2
    elif severity_counts.get("warning", 0) > 0:
        exit_code = 1
    else:
        exit_code = 0

    # Generate output
    report_json = {
        "generated": now,
        "stats": stats,
        "findings": findings,
        "severity_counts": dict(severity_counts),
        "exit_code": exit_code,
    }

    if args.json:
        output_text = json.dumps(report_json, indent=2)
    else:
        output_text = generate_markdown_report(findings, stats, now)

    # Write output
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        md_path = args.output / f"audit-{timestamp}.md"
        json_path = args.output / f"audit-{timestamp}.json"

        md_path.write_text(
            generate_markdown_report(findings, stats, now),
            encoding="utf-8",
        )
        json_path.write_text(
            json.dumps(report_json, indent=2),
            encoding="utf-8",
        )
        print(f"Reports written to:\n  {md_path}\n  {json_path}")
    else:
        print(output_text)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
