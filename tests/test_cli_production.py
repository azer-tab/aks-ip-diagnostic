import json
from pathlib import Path

from aks_ip_diagnostic.cli import main
from aks_ip_diagnostic.exit_codes import (
    CRITICAL_ISSUES_FOUND,
    HEALTHY,
    WARNINGS_FOUND,
    code_for_status,
)
from aks_ip_diagnostic.redaction import redact_report


def sample_report():
    return {
        "metadata": {
            "version": "1.0",
            "timestamp": "2026-01-01T00:00:00Z",
            "tool_version": "0.2.0",
        },
        "cluster_info": {
            "name": "prod-aks",
            "resource_group": "rg-prod",
            "subscription_id": "00000000-0000-0000-0000-000000000000",
        },
        "diagnostics": {},
        "node_pools": [],
        "subnets": [],
        "recommendations": [],
        "summary": {"overall_status": "HEALTHY", "risk_level": "LOW", "total_issues": 0},
    }


def test_exit_code_mapping():
    assert code_for_status("HEALTHY") == HEALTHY
    assert code_for_status("WARNING") == WARNINGS_FOUND
    assert code_for_status("CRITICAL") == CRITICAL_ISSUES_FOUND


def test_redaction_masks_sensitive_fields_and_ips():
    report = sample_report()
    report["cluster_info"]["private_ip"] = "10.0.1.4"
    redacted = redact_report(report)
    assert redacted["cluster_info"]["name"].startswith("<redacted:name:")
    assert redacted["cluster_info"]["resource_group"].startswith("<redacted:resource_group:")
    assert redacted["cluster_info"]["private_ip"] == "<redacted:ip-address>"


def test_validate_command_accepts_valid_report(tmp_path: Path):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(sample_report()), encoding="utf-8")
    assert main(["validate", str(report_path)]) == HEALTHY


def test_convert_command_writes_markdown(tmp_path: Path):
    report_path = tmp_path / "report.json"
    output_path = tmp_path / "report.md"
    report_path.write_text(json.dumps(sample_report()), encoding="utf-8")
    assert (
        main(["convert", str(report_path), "--format", "markdown", "--output", str(output_path)])
        == HEALTHY
    )
    assert output_path.exists()
    assert "AKS IP Exhaustion Diagnostic Report" in output_path.read_text(encoding="utf-8")
