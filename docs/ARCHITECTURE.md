# Architecture

## Execution flow

```text
aks-ip-diagnostic
  -> aks_ip_diagnostic.cli
    -> aks_ip_diagnostic.scan_runner
      -> ScanConfig
      -> AKSDiagnosticOrchestrator
        -> AzureCollector
          -> AKSClient
          -> NetworkClient
        -> diagnostic rules
        -> DiagnosticReportBuilder
      -> schema validation
      -> redaction
      -> output formatter
      -> file/stdout handling
      -> exit code
```

## Module responsibilities

| Module | Responsibility |
|---|---|
| `aks_ip_diagnostic/cli.py` | Argument parsing and command dispatch |
| `aks_ip_diagnostic/scan_runner.py` | CLI-to-engine boundary, validation, redaction, output, exit codes |
| `aks_ip_diagnostic/models.py` | Typed scan configuration and result objects |
| `aks_ip_diagnostic/orchestrator.py` | High-level scan workflow and report assembly |
| `aks_ip_diagnostic/collectors/azure.py` | Read-only Azure collection and subnet discovery |
| `aks_clients/` | Thin Azure and Kubernetes SDK wrappers |
| `diagnostics/` | Diagnostic calculations and issue generation |
| `reports/formatters.py` | Report builder and output renderers |
| `reports/json_schema.py` | JSON report contracts |
| `reports/json_validator.py` | Validation, loading, saving, and enrichment helpers |
| `utils/` | Logging and cost/health calculation helpers |

## Current boundaries

The base workflow uses Azure cluster, node-pool, and subnet data. The repository also contains pod-analysis and detailed cost-analysis modules, but the orchestrator does not currently execute them. The command-line flags are retained for compatibility and produce `SKIPPED` diagnostics.

## Extension rules

- Keep SDK calls in collectors or client wrappers.
- Keep diagnostic calculations independent of CLI arguments and file output.
- Return plain serialisable dictionaries from diagnostics.
- Add report fields to the JSON schema in the same change.
- Add unit tests for each diagnostic rule and an orchestrator contract test.
- Do not add remediation or mutation operations to this repository.

## Recommended next refactor

`orchestrator.py`, `diagnostics/pod_ip_analysis.py`, and `reports/formatters.py` are large and mix multiple subdomains. Split them by capability before adding more checks:

```text
orchestration/
  cluster_scan.py
  optional_analysis.py

reports/
  builder.py
  text.py
  markdown.py
  html.py
  json.py

diagnostics/pods/
  collection.py
  distribution.py
  lifecycle.py
  recommendations.py
```

This reduces regression risk, makes ownership clearer, and allows capability-specific tests.
