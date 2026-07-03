"""Helpers for translating raw diagnostic data into status/risk values."""

from __future__ import annotations


def capacity_status(utilization_percent: float) -> str:
    """Classify subnet or CIDR utilization using the tool's standard thresholds."""

    if utilization_percent < 70:
        return "HEALTHY"
    if utilization_percent < 85:
        return "WARNING"
    return "CRITICAL"


def status_from_issues(issues: list[dict]) -> tuple[str, str]:
    """Return overall status and risk level for a list of normalized issues."""

    critical = [issue for issue in issues if issue.get("severity") == "CRITICAL"]
    warnings = [issue for issue in issues if issue.get("severity") == "WARNING"]
    if critical:
        return "CRITICAL", "CRITICAL"
    if warnings:
        return "WARNING", "HIGH"
    return "HEALTHY", "LOW"
