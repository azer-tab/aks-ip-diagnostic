# AKS IP Diagnostic

A read-only Python CLI that inspects Azure Kubernetes Service (AKS) networking capacity and produces operator-friendly or machine-readable reports.

Use it before cluster upgrades, node-pool scaling, migrations, or incident investigation to identify:

- subnet or pod-CIDR pressure
- node-pool provisioning failures
- risky `maxPods` settings
- insufficient IP headroom for scaling and upgrades

> **Project status:** pre-production. The base Azure scan, report generation, redaction, conversion, and validation paths are implemented. Pod-level and detailed cost-analysis flags are currently placeholders and are reported as `SKIPPED`.

## Quick start

### 1. Install

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .
```

For development:

```bash
pip install -e ".[dev]"
```

### 2. Authenticate to Azure

The CLI uses `DefaultAzureCredential`, so Azure CLI credentials, managed identity, workload identity, and service-principal environment variables are supported.

For local use:

```bash
az login
az account set --subscription "<subscription-id>"
```

Azure `Reader` access is normally sufficient for the base scan. Use the narrowest practical scope that includes the AKS cluster and its networking resources.

### 3. Run a scan

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>"
```

Text output is printed to the terminal. Non-text formats are saved under `./reports/` unless `--output` is supplied.

Save a validated JSON report:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format json-pretty \
  --validate-schema \
  --output reports/aks-ip-report.json
```

## Commands

### Scan a cluster

```bash
aks-ip-diagnostic scan [options]
```

Required options:

| Option | Description |
|---|---|
| `--subscription-id` | Azure subscription ID |
| `--resource-group` | Resource group containing the AKS cluster |
| `--cluster-name` | AKS cluster name |

Common options:

| Option | Description |
|---|---|
| `--format`, `-f` | `text`, `json`, `json-pretty`, `json-compact`, `yaml`, `markdown`, or `html` |
| `--output`, `-o` | Explicit output path |
| `--redact` | Mask identifiers and IP addresses in the final report |
| `--validate-schema` | Validate generated report data before writing it |
| `--verbose` | Enable debug logging |

Accepted but not fully implemented in the current orchestrator:

| Option | Current behaviour |
|---|---|
| `--include-pod-analysis` | Adds a `pod_analysis` diagnostic with status `SKIPPED` |
| `--include-cost-analysis` | Adds a `cost_analysis` diagnostic with status `SKIPPED` |
| `--pod-lifecycle` | Parsed but not executed |
| `--kubeconfig` | Parsed but not used by the current scan workflow |
| `--region` | Parsed, but the built-in heuristic cost table is not region-aware |

### Validate a JSON report

```bash
aks-ip-diagnostic validate reports/aks-ip-report.json
```

### Convert a JSON report

```bash
aks-ip-diagnostic convert reports/aks-ip-report.json \
  --format markdown \
  --output reports/aks-ip-report.md
```

Redact while converting:

```bash
aks-ip-diagnostic convert reports/aks-ip-report.json \
  --format html \
  --redact \
  --output reports/redacted-report.html
```

### Show the version

```bash
aks-ip-diagnostic version
```

## What the base scan does

The implemented scan path:

1. Reads AKS cluster metadata.
2. Lists node pools.
3. Discovers referenced virtual-network subnets.
4. Falls back to the cluster pod CIDR when no custom subnet is available.
5. Runs IP-exhaustion, provisioning-state, subnet-capacity, and `maxPods` checks.
6. Builds a structured report.
7. Optionally validates and redacts the report.
8. Formats the report and returns an automation-friendly exit code.

The tool does not create, update, patch, or delete Azure or Kubernetes resources.

## Reports

The JSON report has these top-level sections:

```json
{
  "metadata": {},
  "cluster_info": {},
  "diagnostics": {},
  "node_pools": [],
  "subnets": [],
  "issues": [],
  "recommendations": [],
  "summary": {}
}
```

Use JSON for automation. Treat the current report contract as versioned but not yet stable enough for a `1.0` compatibility guarantee.

### Exit codes

| Code | Meaning |
|---:|---|
| `0` | Healthy scan or successful utility command |
| `1` | Scan completed with warnings |
| `2` | Scan completed with critical findings |
| `3` | Runtime, authentication, Azure API, or Kubernetes API failure |
| `4` | Invalid CLI usage |
| `5` | Report validation or conversion failure |

Example CI gate:

```bash
set +e
aks-ip-diagnostic scan \
  --subscription-id "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --format json-compact \
  --validate-schema \
  --output diagnostic-report.json
status=$?
set -e

case "$status" in
  0) echo "Healthy" ;;
  1) echo "Warnings found" ;;
  2) echo "Critical findings"; exit 2 ;;
  *) echo "Diagnostic failed with exit code $status"; exit "$status" ;;
esac
```

## Docker

```bash
docker build -t aks-ip-diagnostic:local .
docker run --rm aks-ip-diagnostic:local version
```

Run with service-principal environment variables:

```bash
docker run --rm \
  -e AZURE_CLIENT_ID \
  -e AZURE_TENANT_ID \
  -e AZURE_CLIENT_SECRET \
  aks-ip-diagnostic:local scan \
    --subscription-id "<subscription-id>" \
    --resource-group "<resource-group>" \
    --cluster-name "<cluster-name>"
```

## Architecture

```text
CLI
└── scan runner
    ├── scan configuration
    ├── orchestrator
    │   ├── Azure collector and SDK wrappers
    │   ├── diagnostic rules
    │   └── report builder
    ├── schema validation
    ├── redaction
    ├── formatting
    └── exit-code mapping
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for module responsibilities and extension points.

## Development

Run the local checks before opening a pull request:

```bash
python -m compileall -q src tests examples
pytest -q
ruff check .
ruff format --check .
bandit -r src -x tests
pip-audit
```

The GitHub CI workflow runs these checks across Python 3.10, 3.11, and 3.12 and also builds the Docker image.

## Production readiness

Do not publish this as a production-supported tool until the high-priority items in [`docs/PRODUCTION_REVIEW.md`](docs/PRODUCTION_REVIEW.md) are resolved. The main gaps are:

- optional pod and detailed cost analyses are not wired into the orchestrator
- no live Azure integration or recorded-contract test suite exists
- cost figures use a static heuristic table and should not be treated as billing data
- dependency resolution is not locked or reproducible
- release publishing needs stronger guards and provenance controls
- large diagnostic and formatting modules should be split before significant feature growth

## Documentation

| Document | Purpose |
|---|---|
| [`QUICKSTART.md`](QUICKSTART.md) | Minimal installation and first-scan path |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Execution flow and module ownership |
| [`docs/PRODUCTION_REVIEW.md`](docs/PRODUCTION_REVIEW.md) | Prioritised production-readiness findings |
| [`docs/PRODUCTION_READINESS.md`](docs/PRODUCTION_READINESS.md) | Release gate, permissions, and operating rules |
| [`docs/JSON_OUTPUT_GUIDE.md`](docs/JSON_OUTPUT_GUIDE.md) | Report validation, conversion, and automation |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Common runtime and report problems |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contributor setup and change rules |
| [`docs/RELEASE_GUIDE.md`](docs/RELEASE_GUIDE.md) | Versioning and release process |
| [`docs/DOCS_INDEX.md`](docs/DOCS_INDEX.md) | Documentation ownership map |

## Safety and limitations

- The tool is intended to be read-only.
- Redaction reduces exposure but does not replace a data-classification review.
- Capacity calculations depend on Azure SDK data and networking mode.
- Cost values are rough estimates, not invoices or pricing guarantees.
- Validate recommendations against the cluster’s networking design before making changes.
