"""CLI-facing scan runner.

This layer converts command-line options into ScanConfig, calls the diagnostic
orchestrator, validates/redacts/formats the report, writes output, and returns
one of the documented process exit codes.
"""

from __future__ import annotations

import sys
from typing import Any

from aks_ip_diagnostic.exit_codes import RUNTIME_ERROR, code_for_status
from aks_ip_diagnostic.models import ScanConfig, ScanResult
from aks_ip_diagnostic.orchestrator import AKSDiagnosticOrchestrator
from aks_ip_diagnostic.paths import get_report_path
from aks_ip_diagnostic.redaction import redact_report
from reports.formatters import OutputFormat, format_report
from reports.json_validator import ReportValidator
from utils.logger import setup_logger


def run_scan(config: ScanConfig) -> ScanResult:
    """Run the diagnostic engine and return structured data.

    Tests can call this function directly with fake collectors injected into the
    orchestrator in future expansions.  The function intentionally performs no
    printing so that output behavior stays isolated in run_diagnostic().
    """

    logger = setup_logger(__name__, verbose=config.verbose)
    report = AKSDiagnosticOrchestrator(config=config, logger=logger).run()
    return ScanResult(report=report)


def _validate_generated_report(report: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate report data and normalize the validator return shape."""

    return ReportValidator.validate_diagnostic_report(report)


def _write_or_print_report(config: ScanConfig, formatted_output: str) -> None:
    """Write report output to a file or stdout using the production output rules."""

    if config.output or config.output_format != "text":
        output_path = get_report_path(config.cluster_name, config.output_format, config.output)
        output_path.write_text(formatted_output, encoding="utf-8")
        print(f"Report saved to: {output_path}")
        return

    try:
        print(formatted_output)
    except UnicodeEncodeError:  # pragma: no cover - terminal dependent fallback
        print(formatted_output.encode("ascii", errors="replace").decode("ascii"))


def run_diagnostic(args) -> int:
    """Backward-compatible entry point used by the CLI and legacy imports."""

    config = ScanConfig.from_args(args)
    logger = setup_logger(__name__, verbose=config.verbose)

    try:
        result = run_scan(config)
        report = result.report

        if config.validate_schema:
            is_valid, validation_errors = _validate_generated_report(report)
            if not is_valid:
                logger.error("Generated report failed schema validation: %s", validation_errors)
                print("Generated report failed schema validation", file=sys.stderr)
                for error in validation_errors:
                    print(f"- {error}", file=sys.stderr)
                return RUNTIME_ERROR

        if config.redact:
            report = redact_report(report)

        formatted_output = format_report(report, OutputFormat(config.output_format))
        _write_or_print_report(config, formatted_output)
        logger.info("Diagnostic completed successfully")
        return code_for_status(report.get("summary", {}).get("overall_status"))

    except Exception as exc:
        logger.error("Diagnostic failed: %s", exc, exc_info=True)
        print(f"Error: {exc}", file=sys.stderr)
        return RUNTIME_ERROR
