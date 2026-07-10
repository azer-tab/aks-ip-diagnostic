# AKS IP Diagnostic

AKS IP Diagnostic is a read-only Python CLI for checking Azure Kubernetes Service (AKS) IP capacity, subnet pressure, pod IP usage, and node-pool configuration risk.

It is intended for platform engineers, SREs, and cloud/network teams who need a repeatable diagnostic report before scaling, upgrading, rebuilding, or investigating AKS networking incidents.

## Current project state

The project has been refactored from a prototype-style script into an installable CLI package.

Current state:

- package version: `0.3.2`
- preferred command: `aks-ip-diagnostic`
- legacy compatibility: `python src/main.py` and no-subcommand CLI invocation still work
- CI target: compile check, unit tests, Ruff, Bandit, pip-audit, and Docker build
- release options: Docker image, optional Python package, optional Helm CronJob chart

The codebase is close to release-ready, but the release gate should pass before publishing images or packages. Do not remove failing tests to unblock CI. Fix stale assertions, test fixtures, or implementation regressions instead.

## What the tool answers

- Is the cluster close to IP exhaustion?
- Are node pools configured with risky or wasteful `maxPods` values?
- Are subnets or pod CIDRs under pressure?
- Are node pools in failed or non-succeeded provisioning states?
- Does optional pod-level data show workload distribution or lifecycle issues?
- Can a report be saved, validated, converted, and redacted for sharing?

## Main features

- AKS cluster metadata collection
- node-pool provisioning-state checks
- node-count and `maxPods` analysis
- subnet or pod CIDR capacity reporting, depending on networking mode and permissions
- optional Kubernetes pod-level analysis
- optional estimated cost/capacity-waste analysis
- output formats: `text`, `json`, `json-pretty`, `json-compact`, `yaml`, `markdown`, `html`
- JSON report validation and conversion
- sensitive-value redaction
- deterministic exit codes for CI and automation
- Dockerfile and optional Helm chart

## Project layout

```text
.
├── src/
│   ├── aks_ip_diagnostic/
│   │   ├── cli.py                  # CLI commands and argument parsing
│   │   ├── scan_runner.py          # scan execution, validation, redaction, output
│   │   ├── orchestrator.py         # diagnostic workflow coordination
│   │   ├── models.py               # runtime config/result models
│   │   ├── status.py               # status and risk helpers
│   │   ├── redaction.py            # report redaction
│   │   └── collectors/azure.py     # read-only Azure collection layer
│   ├── aks_clients/                # Azure and Kubernetes SDK wrappers
│   ├── diagnostics/                # diagnostic checks
│   ├── reports/                    # formatters and JSON validation
│   ├── analytics/                  # optional cost analysis support
│   ├── utils/                      # shared helpers
│   └── main.py                     # legacy compatibility shim
├── tests/                          # unit and CLI tests
├── docs/                           # operational and release documentation
├── examples/                       # demo scripts
├── charts/aks-ip-diagnostic/       # optional Helm CronJob chart
├── QUICKSTART.md
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Installation

For development, install the package and dev tooling from `pyproject.toml`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

For runtime-only use:

```bash
python -m pip install --upgrade pip
pip install .
```

You can also install from the dependency files:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Authentication and permissions

Authenticate to Azure with any Azure Identity-supported method, such as Azure CLI login, managed identity, workload identity, or service principal credentials.

```bash
az login
az account set --subscription "<subscription-id>"
az account show
```

For optional pod-level analysis, configure Kubernetes access:

```bash
az aks get-credentials \
  --resource-group "<resource-group>" \
  --name "<cluster-name>"

kubectl cluster-info
kubectl auth can-i list nodes
kubectl auth can-i list pods --all-namespaces
```

Azure `Reader` at the resource group or subscription scope is usually sufficient for the Azure checks. Pod-level analysis requires Kubernetes read access to pods, nodes, and namespaces. See `docs/PRODUCTION_READINESS.md` for stricter least-privilege guidance.

## Quick start

Run a basic read-only scan:

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

Run with Kubernetes pod-level analysis:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --format text
```

Run with pod-level and estimated cost analysis:

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

Generate a redacted report for sharing:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --redact \
  --format markdown \
  --output reports/redacted-report.md
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
--output, -o          output file path
--include-pod-analysis
--include-cost-analysis
--region              Azure region used for cost estimates; default: eastus
--pod-lifecycle       include pod lifecycle analysis
--kubeconfig          path to kubeconfig file
--redact              redact sensitive identifiers and IP addresses
--validate-schema     validate generated report data before formatting/saving
--verbose             enable debug logging
```

### `validate`

Validates an existing JSON report:

```bash
aks-ip-diagnostic validate reports/aks-ip-report.json
```

### `convert`

Converts an existing JSON report to another format:

```bash
aks-ip-diagnostic convert reports/aks-ip-report.json \
  --format markdown \
  --output reports/aks-ip-report.md
```

Redact during conversion:

```bash
aks-ip-diagnostic convert reports/aks-ip-report.json \
  --format html \
  --redact \
  --output reports/redacted-report.html
```

### `version`

Prints the installed version:

```bash
aks-ip-diagnostic version
```

## Backward compatibility

The historical no-subcommand form is still treated as `scan`:

```bash
aks-ip-diagnostic \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>"
```

The legacy script path also remains available:

```bash
python src/main.py \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>"
```

New automation should use the installed `aks-ip-diagnostic` command.

## Output and reports

Text output is intended for operators at a terminal. JSON is the preferred automation surface. Use `json-pretty` for human-readable saved reports and `json-compact` for pipelines.

Typical text sections include:

```text
Executive summary
Diagnostic results
Subnet / CIDR capacity
Node pools
Recommendations
```

A JSON report is organized around these top-level sections:

```json
{
  "metadata": {},
  "cluster_info": {},
  "diagnostics": {},
  "node_pools": [],
  "subnets": [],
  "recommendations": [],
  "summary": {}
}
```

See `docs/JSON_OUTPUT_GUIDE.md` for report validation, conversion, and automation examples.

## Exit codes

```text
0  Healthy scan or successful utility command
1  Scan completed with warnings
2  Scan completed with critical findings
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
  --format json-pretty \
  --output diagnostic-report.json

case "$?" in
  0) echo "AKS IP diagnostic passed" ;;
  1) echo "AKS IP diagnostic found warnings" ;;
  2) echo "AKS IP diagnostic found critical issues"; exit 2 ;;
  *) echo "AKS IP diagnostic failed to run"; exit 3 ;;
esac
```

## Development and CI

Run the same core checks locally before pushing:

```bash
python -m compileall -q src tests examples
pytest -q
ruff check .
ruff format --check .
bandit -r src -x tests
pip-audit
```

The current orchestrator-related failure was a stale formatter expectation: the test expected operator-friendly section labels that the formatter did not emit consistently. The right fix is to align the formatter and tests, not delete the test file. Orchestrator tests are valuable because they prove the scan workflow can be exercised with fake collectors and no live Azure dependency.

## Docker

Build and smoke-test the image:

```bash
docker build -t aks-ip-diagnostic:local .
docker run --rm aks-ip-diagnostic:local version
docker run --rm aks-ip-diagnostic:local --help
```

Run a scan with service principal environment variables:

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

For pod-level analysis with a local kubeconfig:

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

## Documentation map

| Document | Purpose |
|---|---|
| `QUICKSTART.md` | Short setup and first-run guide. |
| `docs/DOCS_INDEX.md` | Documentation ownership and update checklist. |
| `docs/PRODUCTION_READINESS.md` | Release gates, safety model, permissions, and operational checks. |
| `docs/REFACTORING_NOTES.md` | Architecture notes for the CLI/orchestrator refactor. |
| `docs/JSON_OUTPUT_GUIDE.md` | JSON output, validation, conversion, and automation usage. |
| `docs/POD_LEVEL_ANALYSIS.md` | Optional Kubernetes pod-level analysis behavior and RBAC. |
| `docs/COST_ANALYSIS_GUIDE.md` | Cost-estimation logic, caveats, and safe interpretation. |
| `docs/RELEASE_GUIDE.md` | Docker Hub, Python package, GitHub release, and versioning process. |
| `docs/HELM_CHART_GUIDE.md` | Optional Helm/CronJob deployment guide. |
| `docs/CODE_QUALITY_NOTES.md` | Local quality gates and notes from recent test/refactor cleanup. |

## Safety model

This tool is intended to be read-only.

Expected behavior:

- no Azure create/update/delete operations
- no Kubernetes create/update/patch/delete operations
- no pod execution
- no node mutation
- no workload mutation

Recommendations may describe remediation steps, but the tool should not perform remediation.

## Known limitations

- Cost analysis is estimated and should be verified against Azure billing data and current pricing before financial decisions.
- Pod-level analysis requires Kubernetes API access and can fail independently from the base Azure scan.
- Some subnet details depend on AKS networking mode and Azure permissions.
- Redaction reduces exposure but does not replace a formal data-classification review.
- The JSON schema should be protected with golden-file tests before declaring a stable `1.0.0` report contract.
