"""Production CLI for AKS IP Diagnostic."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from reports.formatters import OutputFormat, format_report
from reports.json_validator import ReportValidator

from . import __version__
from .exit_codes import HEALTHY, INVALID_USAGE, VALIDATION_FAILED
from .redaction import redact_report


class ProductionArgumentParser(argparse.ArgumentParser):
    """Argument parser that returns the documented invalid-usage exit code."""

    def error(self, message: str) -> None:  # pragma: no cover - argparse behavior
        self.print_usage(sys.stderr)
        self.exit(INVALID_USAGE, f"{self.prog}: error: {message}\n")


def _add_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--subscription-id", required=True, help="Azure subscription ID")
    parser.add_argument(
        "--resource-group", required=True, help="Azure resource group containing the AKS cluster"
    )
    parser.add_argument("--cluster-name", required=True, help="Name of the AKS cluster to analyze")
    parser.add_argument(
        "--format",
        "-f",
        choices=[item.value for item in OutputFormat],
        default="text",
        help="Output format",
    )
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument(
        "--include-pod-analysis", action="store_true", help="Include pod-level IP usage analysis"
    )
    parser.add_argument(
        "--include-cost-analysis", action="store_true", help="Include estimated cost analysis"
    )
    parser.add_argument("--region", default="eastus", help="Azure region for cost estimates")
    parser.add_argument(
        "--pod-lifecycle", action="store_true", help="Include pod lifecycle analysis"
    )
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument(
        "--redact",
        action="store_true",
        help="Redact sensitive identifiers and IP addresses from output",
    )
    parser.add_argument(
        "--validate-schema",
        action="store_true",
        help="Validate generated report data before formatting/saving",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose/debug logging")


def build_parser() -> argparse.ArgumentParser:
    parser = ProductionArgumentParser(
        prog="aks-ip-diagnostic",
        description="Read-only AKS IP capacity and pod IP diagnostic tool",
    )
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Run a diagnostic scan")
    _add_scan_args(scan_parser)

    validate_parser = subparsers.add_parser("validate", help="Validate a JSON report")
    validate_parser.add_argument("report", help="Path to JSON report")

    convert_parser = subparsers.add_parser(
        "convert", help="Convert a JSON report to another format"
    )
    convert_parser.add_argument("report", help="Path to JSON report")
    convert_parser.add_argument(
        "--format",
        "-f",
        choices=[item.value for item in OutputFormat],
        default="markdown",
        help="Output format",
    )
    convert_parser.add_argument("--output", "-o", help="Output file path")
    convert_parser.add_argument(
        "--redact", action="store_true", help="Redact sensitive data before conversion"
    )

    subparsers.add_parser("version", help="Print version information")
    return parser


def _normalize_legacy_args(argv: Sequence[str]) -> list[str]:
    """Support the historical no-subcommand form by treating it as `scan`."""
    args = list(argv)
    if not args:
        return args
    if args[0] in {"scan", "validate", "convert", "version", "-h", "--help"}:
        return args
    return ["scan", *args]


def _validate_report_file(path: str) -> int:
    valid, errors, _ = ReportValidator.validate_json_file(path)
    if valid:
        print(f"Valid report: {path}")
        return HEALTHY
    print(f"Invalid report: {path}", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return VALIDATION_FAILED


def _convert_report(args: argparse.Namespace) -> int:
    path = Path(args.report)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Unable to read JSON report '{path}': {exc}", file=sys.stderr)
        return VALIDATION_FAILED

    if args.redact:
        data = redact_report(data)

    output = format_report(data, OutputFormat(args.format))
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Converted report saved to: {output_path}")
    else:
        print(output)
    return HEALTHY


def main(argv: Sequence[str] | None = None) -> int:
    argv = _normalize_legacy_args(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        parser.print_help()
        return INVALID_USAGE

    if args.command == "version":
        print(f"aks-ip-diagnostic {__version__}")
        return HEALTHY

    if args.command == "validate":
        return _validate_report_file(args.report)

    if args.command == "convert":
        return _convert_report(args)

    if args.command == "scan":
        from aks_ip_diagnostic.scan_runner import run_diagnostic

        return run_diagnostic(args)

    parser.print_help()
    return INVALID_USAGE
