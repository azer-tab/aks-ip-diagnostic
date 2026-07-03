# AKS IP Diagnostic

Read-only production CLI for diagnosing Azure Kubernetes Service (AKS) IP capacity, pod IP usage, subnet pressure, and node-pool configuration risk.

The tool is designed for platform engineers, SREs, and cloud/network teams who need a repeatable way to answer:

- Is this AKS cluster close to IP exhaustion?
- Are node pools configured with unsafe or wasteful `maxPods` values?
- Is pod distribution creating avoidable IP or capacity pressure?
- Which findings are warnings versus critical issues?
- Can the report be safely shared with sensitive values redacted?

## Current status

This repository has been refactored from a prototype-style script into a production-oriented Python CLI.

The current architecture separates:

- command-line parsing
- scan configuration
- Azure collection
- diagnostic orchestration
- report formatting
- report validation
- redaction
- exit-code mapping

The legacy entry point still works, but new usage should prefer the `aks-ip-diagnostic` command.

## Features

### Core diagnostics

- AKS cluster metadata collection
- node-pool provisioning-state checks
- node-count and `maxPods` analysis
- pod CIDR and service CIDR reporting
- subnet / CIDR capacity summary where data is available
- warning and critical finding classification
- operator-friendly recommended actions

### Optional pod-level analysis

When Kubernetes API access is available, the tool can include pod-level information such as:

- pod distribution across nodes
- pod density signals
- stuck, pending, or failed pod detection
- namespace-level usage breakdown
- host-network pod handling
- lifecycle-oriented pod analysis

### Optional cost analysis

Cost analysis estimates the operational impact of wasteful IP allocation and over-provisioning.

Cost output should be treated as an estimate. Pricing assumptions can change, and final financial decisions should be verified against Azure pricing and billing data.

### Production CLI features

- subcommands: `scan`, `validate`, `convert`, and `version`
- backward-compatible legacy invocation
- clean text output for terminals
- JSON/YAML/Markdown/HTML output for automation and reporting
- schema validation for generated or saved JSON reports
- redaction mode for sensitive infrastructure metadata
- deterministic process exit codes
- Docker support
- GitHub Actions CI with tests, dependency audit, static security scan, and Docker build

## Project structure

```text
aks-ip-diagnostic-main/
├── src/
│   ├── aks_ip_diagnostic/
│   │   ├── cli.py                  # Production CLI and subcommands
│   │   ├── scan_runner.py          # CLI-to-orchestrator execution layer
│   │   ├── orchestrator.py         # Coordinates collection and diagnostics
│   │   ├── models.py               # Typed runtime configuration/result models
│   │   ├── status.py               # Status and risk classification helpers
│   │   ├── paths.py                # Report output path handling
│   │   ├── redaction.py            # Sensitive data redaction
│   │   └── collectors/
│   │       └── azure.py            # Read-only Azure collection layer
│   ├── aks_clients/                # Azure and Kubernetes SDK wrappers
│   ├── diagnostics/                # Diagnostic checks
│   ├── reports/                    # Formatters and JSON validation
│   ├── utils/                      # Logging and shared helpers
│   └── main.py                     # Backward-compatible legacy shim
├── tests/                          # Unit and CLI tests
├── docs/                           # Detailed guides and architecture notes
├── examples/                       # Demo scripts
├── .github/workflows/ci.yml        # CI pipeline
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

The important design change is that `src/main.py` is no longer the application brain. It is now a compatibility shim. New code should enter through `aks_ip_diagnostic.cli`, then flow into `scan_runner` and `AKSDiagnosticOrchestrator`.

## Requirements

- Python 3.10 or newer
- Azure credentials with read access to the target AKS cluster
- Kubernetes access only if pod-level analysis is enabled
- Optional: Docker, if you want to run the packaged container image

## Installation

### Local development install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### Runtime-only install

```bash
python -m pip install --upgrade pip
pip install .
```

### Dependency files

You can also install directly from requirements files:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

For normal development, `pip install -e ".[dev]"` is preferred because it installs the CLI and developer tooling from `pyproject.toml`.

## Authentication and permissions

### Azure authentication

Use one of the Azure Identity-supported methods, such as Azure CLI login, managed identity, workload identity, or service principal credentials.

For local use:

```bash
az login
az account set --subscription "<subscription-id>"
az account show
```

### Kubernetes authentication

Pod-level analysis requires kubeconfig access to the target cluster:

```bash
az aks get-credentials \
  --resource-group "<resource-group>" \
  --name "<cluster-name>"

kubectl cluster-info
kubectl get nodes
kubectl get pods --all-namespaces
```

### Minimum permission model

For Azure, the built-in `Reader` role at the resource group or subscription scope is usually enough for the current read-only checks.

For Kubernetes pod-level analysis, the user or service account should be able to:

```bash
kubectl auth can-i list nodes
kubectl auth can-i list pods --all-namespaces
kubectl auth can-i list namespaces
```

For stricter least-privilege guidance, see `docs/PRODUCTION_READINESS.md`.

## Quick start

Run a basic scan and print clean text output:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format text
```

Save a JSON report:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format json-pretty \
  --output reports/aks-ip-report.json
```

Run with pod-level analysis:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --format text
```

Run with cost analysis:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --include-cost-analysis \
  --region eastus \
  --format json-pretty \
  --output reports/aks-ip-cost-report.json
```

Validate generated report data during the scan:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format json-pretty \
  --output reports/aks-ip-report.json \
  --validate-schema
```

Generate a redacted report for sharing:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --format json-pretty \
  --output reports/redacted-report.json \
  --redact
```

## Commands

### `scan`

Runs an AKS diagnostic scan.

```bash
aks-ip-diagnostic scan [options]
```

Required options:

```text
--subscription-id     Azure subscription ID
--resource-group      Azure resource group containing the AKS cluster
--cluster-name        AKS cluster name
```

Common options:

```text
--format, -f          text, json, json-pretty, json-compact, yaml, markdown, html
--output, -o          write report to a specific file path
--include-pod-analysis
--include-cost-analysis
--region              Azure region used for cost estimates; default: eastus
--pod-lifecycle       include pod lifecycle analysis
--kubeconfig          path to kubeconfig file
--redact              redact sensitive identifiers and IP addresses
--validate-schema     validate generated report before formatting/saving
--verbose             enable debug logging
```

### `validate`

Validates an existing JSON report:

```bash
aks-ip-diagnostic validate reports/aks-ip-report.json
```

Successful validation returns exit code `0`. Validation failure returns exit code `5`.

### `convert`

Converts an existing JSON report to another output format:

```bash
aks-ip-diagnostic convert reports/aks-ip-report.json \
  --format markdown \
  --output reports/aks-ip-report.md
```

Convert and redact at the same time:

```bash
aks-ip-diagnostic convert reports/aks-ip-report.json \
  --format html \
  --output reports/redacted-report.html \
  --redact
```

### `version`

Prints the installed tool version:

```bash
aks-ip-diagnostic version
```

## Backward compatibility

The old no-subcommand form still works:

```bash
aks-ip-diagnostic \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>"
```

Internally, this is treated as:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>"
```

The legacy script path also remains available for existing automation:

```bash
python src/main.py \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>"
```

New automation should use the installed `aks-ip-diagnostic` command.

## Output formats

Supported formats:

```text
text
json
json-pretty
json-compact
yaml
markdown
html
```

Recommended usage:

- use `text` for terminal review
- use `json-pretty` for saved reports humans may inspect
- use `json-compact` for pipelines and storage
- use `markdown` for runbooks, tickets, and pull requests
- use `html` for shareable report pages

## Cleaner text output

The refactored text output is organized for operators. It is intentionally shorter and easier to scan than the earlier report.

Typical sections:

```text
Executive summary
Top findings
Diagnostic checks
Subnet / CIDR capacity
Node pools
Recommended next actions
```

Example shape:

```text
AKS IP Diagnostic Report
========================

Executive summary
-----------------
Cluster:      my-aks
Resource grp: my-rg
Status:       WARNING
Risk:         MEDIUM
Issues:       3

Top findings
------------
[WARNING] maxPods is higher than recommended for nodepool1
[WARNING] Pod CIDR utilization is increasing

Diagnostic checks
-----------------
IP exhaustion:        PASS
Provisioning state:   PASS
Max pods:             WARNING

Recommended next actions
------------------------
1. Review maxPods on node pools with low utilization.
2. Confirm subnet growth capacity before the next scale event.
3. Re-run with --include-pod-analysis for workload-level detail.
```

Exact output depends on the available Azure/Kubernetes data and selected flags.

## Exit codes

The CLI returns deterministic exit codes for automation:

```text
0  Healthy scan or successful utility command
1  Warnings found
2  Critical issues found
3  Runtime, authentication, Azure API, or Kubernetes API failure
4  Invalid CLI usage
5  Report validation or conversion failure
```

Example CI gate:

```bash
aks-ip-diagnostic scan \
  --subscription-id "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --include-pod-analysis \
  --format json-pretty \
  --output diagnostic-report.json

case "$?" in
  0) echo "AKS IP diagnostic passed" ;;
  1) echo "AKS IP diagnostic found warnings" ;;
  2) echo "AKS IP diagnostic found critical issues"; exit 2 ;;
  *) echo "AKS IP diagnostic failed to run"; exit 3 ;;
esac
```

## Redaction

Use `--redact` when generating or converting reports that may be shared outside the immediate platform team.

Redaction targets include:

- subscription IDs
- resource groups
- cluster names
- Azure resource IDs
- private IPv4 addresses and CIDRs
- node names
- pod names
- namespace-style fields
- principal, tenant, client, and object IDs
- tags

Example:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --redact \
  --format markdown \
  --output reports/sanitized-report.md
```

Redaction is a safety feature, not a formal data-loss-prevention product. Review reports before sharing them broadly.

## Docker

Build the image:

```bash
docker build -t aks-ip-diagnostic:local .
```

Run the image:

```bash
docker run --rm \
  -e AZURE_CLIENT_ID \
  -e AZURE_TENANT_ID \
  -e AZURE_CLIENT_SECRET \
  aks-ip-diagnostic:local scan \
    --subscription-id "<subscription-id>" \
    --resource-group "<resource-group>" \
    --cluster-name "<cluster-name>" \
    --format text
```

To use a local kubeconfig for pod-level analysis:

```bash
docker run --rm \
  -v "$HOME/.kube:/home/appuser/.kube:ro" \
  aks-ip-diagnostic:local scan \
    --subscription-id "<subscription-id>" \
    --resource-group "<resource-group>" \
    --cluster-name "<cluster-name>" \
    --include-pod-analysis \
    --kubeconfig /home/appuser/.kube/config
```

## CI/CD

The included GitHub Actions workflow runs:

```text
python -m compileall src tests
pytest
pip-audit
bandit -r src -x tests
docker build
```

Run the same checks locally:

```bash
python -m compileall src tests
pytest
pip-audit
bandit -r src -x tests
```

## Configuration

A small `config.yaml` is included for threshold-style configuration:

```yaml
ip_exhaustion_threshold: 10
provisioning_state_timeout: 300
subnet_capacity_threshold: 5
max_pods_limit: 110
```

The current production CLI primarily uses explicit command-line options. Treat `config.yaml` as a threshold/configuration reference rather than the main runtime interface.

## Development workflow

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Compile-check the codebase:

```bash
python -m compileall src tests
```

Run the CLI from source without installing:

```bash
PYTHONPATH=src python -m aks_ip_diagnostic --help
PYTHONPATH=src python -m aks_ip_diagnostic version
```

Run a scan from source:

```bash
PYTHONPATH=src python -m aks_ip_diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format text
```

## Architecture notes

The refactor introduced a clearer flow:

```text
CLI
  -> ScanConfig
  -> scan_runner
  -> AKSDiagnosticOrchestrator
  -> collectors
  -> diagnostics
  -> report data
  -> validation/redaction
  -> formatter
  -> stdout or file
  -> exit code
```

Why this matters:

- the CLI is now thin and testable
- diagnostics are easier to test without live Azure
- output behavior is centralized
- redaction is applied consistently
- validation can be enabled during generation or run later
- process exit codes are controlled in one place

For more detail, read `docs/REFACTORING_NOTES.md`.

## Troubleshooting

### Azure authentication fails

Check that the active identity can read the subscription/resource group:

```bash
az account show
az account set --subscription "<subscription-id>"
az aks show --resource-group "<resource-group>" --name "<cluster-name>"
```

### Kubernetes pod-level analysis fails

Verify kubeconfig and RBAC:

```bash
kubectl cluster-info
kubectl get nodes
kubectl get pods --all-namespaces
kubectl auth can-i list nodes
kubectl auth can-i list pods --all-namespaces
```

You can still run the base Azure scan without `--include-pod-analysis`.

### JSON validation fails

Validate the saved report directly:

```bash
aks-ip-diagnostic validate reports/aks-ip-report.json
```

Then inspect the reported schema errors. Validation failures usually mean the report shape changed and the schema/tests need to be updated together.

### Cost analysis looks different from billing data

Cost analysis is an estimate. Confirm final numbers against your Azure billing data, region, reservation/commitment discounts, and internal chargeback model.

## Documentation

Additional documentation:

- `QUICKSTART.md` - shorter setup and first-run guide
- `docs/REFACTORING_NOTES.md` - explanation of the production refactor
- `docs/PRODUCTION_READINESS.md` - production safety, release gates, and permissions
- `docs/JSON_OUTPUT_GUIDE.md` - JSON output details
- `docs/POD_LEVEL_ANALYSIS.md` - pod-level analysis details
- `docs/COST_ANALYSIS_GUIDE.md` - cost analysis details
- `examples/` - demo scripts

## Safety model

This tool is intended to be read-only. It should collect data and generate reports; it should not mutate Azure or Kubernetes resources.

Expected behavior:

- no Azure create/update/delete operations
- no Kubernetes create/update/delete operations
- no pod execution
- no node mutation
- no workload mutation

Review `docs/PRODUCTION_READINESS.md` before using the tool in regulated or highly sensitive environments.

## Known limitations

- Cost analysis is estimated and should be verified externally.
- Some diagnostics depend on Azure/Kubernetes API permissions and may be incomplete if access is restricted.
- Redaction reduces exposure but does not replace a formal data-classification review.
- The codebase is now refactored, but additional hardening can still improve typed report models, integration-test coverage, and schema versioning.

## Contributing

Recommended contribution workflow:

1. Install with `pip install -e ".[dev]"`.
2. Add or update tests for the behavior you change.
3. Run `python -m compileall src tests`.
4. Run `pytest`.
5. Run `pip-audit` and `bandit -r src -x tests` where available.
6. Keep CLI behavior backward compatible unless the change is intentionally breaking.

Good areas for future improvement:

- stronger typed report models
- more mocked Azure/Kubernetes integration tests
- additional output formats
- richer JSON schema versioning
- more precise least-privilege role examples
- better configuration-file support


## Additional documentation

The `docs/` folder is intentionally kept. It contains operational guides that are too detailed for the README:

| Guide | Purpose |
|---|---|
| `docs/DOCS_INDEX.md` | Explains which docs are necessary and when to update them. |
| `docs/PRODUCTION_READINESS.md` | Release gates, read-only safety model, permissions, and operational checks. |
| `docs/REFACTORING_NOTES.md` | Explains the `main.py` refactor and new module responsibilities. |
| `docs/JSON_OUTPUT_GUIDE.md` | JSON formats, validation, conversion, and automation usage. |
| `docs/POD_LEVEL_ANALYSIS.md` | Optional Kubernetes pod-level analysis behavior and RBAC. |
| `docs/COST_ANALYSIS_GUIDE.md` | Cost-estimation logic, caveats, and safe interpretation. |
| `docs/RELEASE_GUIDE.md` | Docker Hub, Python package, GitHub release, and versioning process. |
| `docs/HELM_CHART_GUIDE.md` | Optional Helm/CronJob deployment guide. |

## Release options

### Docker Hub

The project can be published to Docker Hub after CI passes:

```bash
docker build -t <dockerhub-user>/aks-ip-diagnostic:0.3.2 .
docker run --rm <dockerhub-user>/aks-ip-diagnostic:0.3.2 version
docker push <dockerhub-user>/aks-ip-diagnostic:0.3.2
```

See `docs/RELEASE_GUIDE.md` for the full release process and GitHub Actions setup.

### Python package

A Python package release is optional but useful for users who want direct CLI installation:

```bash
python -m build
python -m twine check dist/*
```

Publish to TestPyPI before publishing publicly.

### Helm chart

A Helm chart is optional. It is useful when you want scheduled in-cluster scans as a Kubernetes CronJob. The chart lives in:

```text
charts/aks-ip-diagnostic/
```

See `docs/HELM_CHART_GUIDE.md` for install, package, and authentication guidance.
