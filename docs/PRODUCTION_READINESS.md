# Production readiness guide

This project is a read-only diagnostic utility for AKS IP capacity, pod IP usage, subnet pressure, and node-pool configuration risk.

## Production readiness status

The project is close to a releasable CLI/container image after the refactor, but treat it as production-ready only when the release gate below passes in CI and in a clean local environment.

## Release gate

Run these commands before publishing a Docker image, Python package, or Helm chart:

```bash
python -m compileall -q src tests
pytest -q
ruff check src tests
bandit -r src -x tests
pip-audit
python -m build
python -m twine check dist/*
docker build -t aks-ip-diagnostic:local .
docker run --rm aks-ip-diagnostic:local version
```

Optional Helm checks if you use the chart:

```bash
helm lint charts/aks-ip-diagnostic
helm template aks-ip-diagnostic charts/aks-ip-diagnostic \
  --set azure.subscriptionId="00000000-0000-0000-0000-000000000000" \
  --set azure.resourceGroup="example-rg" \
  --set azure.clusterName="example-aks"
```

## Read-only safety model

The tool should only perform read operations.

Allowed Azure operation types:

- get AKS cluster metadata
- list node pools
- get/list virtual networks and subnets
- get/list network interfaces when needed for IP analysis

Allowed Kubernetes operation types:

- get/list pods
- get/list nodes
- get/list namespaces

Do not add these operation types to this project:

- Azure create/update/delete operations
- Kubernetes create/update/patch/delete operations
- `kubectl exec`
- cordon, drain, scale, restart, or remediation actions
- secret extraction

The tool may recommend remediation, but it should not perform remediation.

## Minimum Azure permissions

For most use cases, Azure built-in `Reader` at the resource group scope is sufficient. For stricter environments, create a custom role with read actions similar to:

```json
{
  "Actions": [
    "Microsoft.ContainerService/managedClusters/read",
    "Microsoft.ContainerService/managedClusters/agentPools/read",
    "Microsoft.Network/virtualNetworks/read",
    "Microsoft.Network/virtualNetworks/subnets/read",
    "Microsoft.Network/networkInterfaces/read"
  ],
  "NotActions": [],
  "DataActions": [],
  "NotDataActions": []
}
```

Assign at the narrowest practical scope, usually the resource group containing the AKS cluster and networking resources.

## Minimum Kubernetes RBAC

Pod-level analysis requires read access to pods, nodes, and namespaces.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: aks-ip-diagnostic-readonly
rules:
  - apiGroups: [""]
    resources: ["pods", "nodes", "namespaces"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: aks-ip-diagnostic-readonly
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: aks-ip-diagnostic-readonly
subjects:
  - kind: ServiceAccount
    name: aks-ip-diagnostic
    namespace: aks-ip-diagnostic
```

## Runtime expectations

Prefer these entry points:

```bash
aks-ip-diagnostic scan --subscription-id ... --resource-group ... --cluster-name ...
aks-ip-diagnostic validate report.json
aks-ip-diagnostic convert report.json --format markdown --output report.md
aks-ip-diagnostic version
```

The historical no-subcommand form is still supported and is treated as `scan`.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Healthy scan or successful utility command |
| 1 | Scan completed with warnings |
| 2 | Scan completed with critical findings |
| 3 | Runtime/auth/API/config failure |
| 4 | Invalid CLI usage |
| 5 | Report validation or conversion failure |

Automation should evaluate both the exit code and the JSON report contents.

## Sensitive data handling

Reports can contain infrastructure metadata. Use redaction when sharing outside the immediate platform team:

```bash
aks-ip-diagnostic scan ... --format json --redact --output redacted-report.json
aks-ip-diagnostic convert report.json --format markdown --redact --output redacted-report.md
```

Redaction is intended for safe sharing, not for forensic-grade anonymization. Review reports manually before publishing externally.

## Docker readiness

The Dockerfile is suitable for publishing after the release gate passes. Before pushing:

```bash
docker build -t aks-ip-diagnostic:local .
docker run --rm aks-ip-diagnostic:local version
docker run --rm aks-ip-diagnostic:local --help
```

Then tag the image with your Docker Hub namespace and version. See `docs/RELEASE_GUIDE.md`.

## Python package readiness

The project uses `pyproject.toml` and an installable console script. A package release is optional, but recommended if users need direct pip installation.

Before publishing:

```bash
python -m build
python -m twine check dist/*
```

Publish to TestPyPI before public PyPI.

## Helm readiness

Helm is optional. Use it only when you want scheduled in-cluster scans as a Kubernetes CronJob. See `docs/HELM_CHART_GUIDE.md`.

## Known limitations

- Cost analysis is estimated and should not be treated as billing truth.
- Kubernetes pod-level analysis requires Kubernetes API access and may fail independently of Azure collection.
- The tool does not remediate findings.
- Schema compatibility should be protected with tests before declaring a stable `1.0.0` release.
