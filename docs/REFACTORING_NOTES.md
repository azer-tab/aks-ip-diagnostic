# Refactoring notes

This document explains the proper `main.py` refactor that changed the project from a monolithic script into a more maintainable CLI application.

## Why the refactor was needed

The original `src/main.py` mixed several responsibilities:

- command-line parsing
- Azure SDK access
- Kubernetes SDK access
- diagnostic business logic
- report generation
- file output
- exception handling
- exit-code behavior

That made the tool difficult to test, extend, and operate safely. The refactor separates those concerns.

## New execution flow

```text
aks-ip-diagnostic CLI
  -> aks_ip_diagnostic.cli
    -> aks_ip_diagnostic.scan_runner
      -> ScanConfig
      -> AKSDiagnosticOrchestrator
        -> AzureCollector
        -> diagnostics modules
        -> report builder
      -> schema validation / redaction / formatting
      -> file or stdout output
      -> documented exit code
```

## Important modules

### `src/main.py`

Now a backward-compatible shim. It delegates to the package CLI so old commands still work:

```bash
python src/main.py --subscription-id ... --resource-group ... --cluster-name ...
```

New code should not add application logic to this file.

### `src/aks_ip_diagnostic/cli.py`

Owns argument parsing and subcommands:

- `scan`
- `validate`
- `convert`
- `version`

This file should stay focused on CLI behavior only.

### `src/aks_ip_diagnostic/models.py`

Defines typed runtime objects such as `ScanConfig` and `ScanResult`. This avoids passing raw `argparse.Namespace` objects deep into the application.

### `src/aks_ip_diagnostic/scan_runner.py`

Bridges the CLI and the diagnostic engine. It handles:

- converting CLI args into `ScanConfig`
- calling the orchestrator
- optional schema validation
- optional redaction
- output formatting
- file/stdout behavior
- exit-code mapping

### `src/aks_ip_diagnostic/orchestrator.py`

Coordinates the diagnostic workflow. It should remain the high-level business process and should not contain CLI parsing or Docker/package concerns.

### `src/aks_ip_diagnostic/collectors/azure.py`

Contains read-only Azure collection and subnet parsing. Azure SDK calls should stay here or in the existing lower-level `aks_clients` wrappers.

### `src/reports/formatters.py`

Owns output formatting. The cleaner text output is organized for operators:

- executive summary
- executive summary
- diagnostic results
- subnet / CIDR capacity
- node pools
- recommendations

## Rules for future changes

- Do not put new business logic into `src/main.py`.
- Keep CLI-only code in `cli.py`.
- Keep orchestration in `orchestrator.py`.
- Keep Azure/Kubernetes API access in collectors or clients.
- Keep formatting in `reports/`.
- Add unit tests for each new diagnostic rule.
- Preserve backward-compatible CLI behavior unless making a major release.

## Validation commands

```bash
python -m compileall -q src tests
pytest -q
PYTHONPATH=src python -m aks_ip_diagnostic --help
PYTHONPATH=src python -m aks_ip_diagnostic version
```
