from reports.formatters import DiagnosticReportBuilder, create_issue
from reports.json_validator import ReportValidator


def test_summary_counts_canonical_issues_once():
    builder = DiagnosticReportBuilder("aks", "rg", "sub")
    issue = create_issue(
        severity="WARNING",
        code="TEST_WARNING",
        message="Example warning",
        affected_resource="system",
    )
    builder.add_issue(issue)
    builder.add_diagnostic_result("provisioning_state", "PASS", "LOW", [], {})
    builder.add_diagnostic_result("ip_exhaustion", "FAIL", "HIGH", [issue], {})
    builder.add_diagnostic_result("subnet_capacity", "PASS", "LOW", [], {})
    builder.add_diagnostic_result("max_pods_configuration", "PASS", "LOW", [], {})
    builder.set_summary("WARNING", "MEDIUM")

    report = builder.build()

    assert report["summary"]["total_issues"] == 1
    assert report["summary"]["warnings"] == 1
    assert report["summary"]["critical_issues"] == 0
    assert report["summary"]["healthy_checks"] == 3
    assert ReportValidator.validate_diagnostic_report(report) == (True, [])


def test_report_timestamps_use_utc_iso8601_format():
    builder = DiagnosticReportBuilder("aks", "rg", "sub")
    builder.add_diagnostic_result("provisioning_state", "PASS", "LOW", [], {})
    builder.set_summary("HEALTHY", "LOW")

    report = builder.build()

    assert report["metadata"]["timestamp"].endswith("Z")
    assert report["diagnostics"]["provisioning_state"]["checked_at"].endswith("Z")
