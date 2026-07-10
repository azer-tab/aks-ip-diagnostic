# Quick start

This guide gets you from a clean checkout to a first AKS IP diagnostic report.

## 1. Install locally

```bash
git clone <repository-url>
cd aks-ip-diagnostic

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

For runtime-only use, `pip install .` is enough.

## 2. Authenticate

```bash
az login
az account set --subscription "<subscription-id>"
az account show
```

Pod-level analysis also requires kubeconfig access:

```bash
az aks get-credentials \
  --resource-group "<resource-group>" \
  --name "<cluster-name>"

kubectl auth can-i list nodes
kubectl auth can-i list pods --all-namespaces
```

## 3. Run a basic scan

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format text
```

## 4. Save a JSON report

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format json-pretty \
  --output reports/aks-ip-report.json
```

Validate the saved report:

```bash
aks-ip-diagnostic validate reports/aks-ip-report.json
```

Convert it to Markdown:

```bash
aks-ip-diagnostic convert reports/aks-ip-report.json \
  --format markdown \
  --output reports/aks-ip-report.md
```

## 5. Run optional pod-level analysis

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --format text
```

Pod-level analysis uses the Kubernetes API. The base Azure scan can still run without it.

## 6. Generate a shareable redacted report

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --redact \
  --format markdown \
  --output reports/redacted-aks-ip-report.md
```

Review redacted reports before sharing externally.

## Useful commands

```bash
aks-ip-diagnostic --help
aks-ip-diagnostic scan --help
aks-ip-diagnostic version
python -m compileall -q src tests examples
pytest -q
```

## Interpreting results

| Field | Meaning |
|---|---|
| `summary.overall_status` | `HEALTHY`, `WARNING`, or `CRITICAL` scan result. |
| `summary.risk_level` | Operator-facing severity level. |
| `summary.total_issues` | Number of detected findings. |
| `diagnostics` | Per-check status, risk, details, and issues. |
| `node_pools` | Normalized node-pool configuration and capacity data. |
| `subnets` | Subnet or pod CIDR capacity data where available. |
| `recommendations` | Suggested operator follow-up actions. |

Exit codes are documented in the README and `docs/PRODUCTION_READINESS.md`.

## Next documentation to read

- `README.md` for full project usage and architecture summary.
- `docs/PRODUCTION_READINESS.md` before publishing or running in production.
- `docs/JSON_OUTPUT_GUIDE.md` for report automation.
- `docs/POD_LEVEL_ANALYSIS.md` for Kubernetes RBAC and pod diagnostics.
- `docs/COST_ANALYSIS_GUIDE.md` before using estimated cost output.
