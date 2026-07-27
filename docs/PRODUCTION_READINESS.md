# Production readiness

The project is currently **pre-production**. Use this guide as a release gate, not as a declaration that the current version is production-supported.

## Required release gate

Run in a clean environment:

```bash
python -m compileall -q src tests examples
pytest -q
ruff check .
ruff format --check .
bandit -r src -x tests
pip-audit
python -m build
python -m twine check dist/*
docker build -t aks-ip-diagnostic:local .
docker run --rm aks-ip-diagnostic:local version
```

For the Helm chart:

```bash
helm lint charts/aks-ip-diagnostic
helm template review charts/aks-ip-diagnostic \
  --set azure.subscriptionId="00000000-0000-0000-0000-000000000000" \
  --set azure.resourceGroup="example-rg" \
  --set azure.clusterName="example-aks"
```

Resolve all Priority 0 items in `PRODUCTION_REVIEW.md` before a production support commitment.

## Read-only safety model

Allowed operations:

- read AKS cluster metadata
- list node pools
- read referenced virtual networks and subnets
- optionally get/list pods, nodes, and namespaces when pod analysis is implemented

Disallowed operations:

- Azure create, update, or delete
- Kubernetes create, update, patch, or delete
- pod execution
- cordon, drain, scale, restart, or automated remediation
- secret extraction

Recommendations may describe operator actions, but the tool must not perform them.

## Permissions

Use Azure `Reader` at the narrowest scope that contains the AKS and networking resources. A stricter custom role can use read actions for:

```text
Microsoft.ContainerService/managedClusters/read
Microsoft.ContainerService/managedClusters/agentPools/read
Microsoft.Network/virtualNetworks/read
Microsoft.Network/virtualNetworks/subnets/read
Microsoft.Network/networkInterfaces/read
```

Pod analysis is not active in the current orchestrator. When enabled, it should use Kubernetes `get` and `list` permissions only for pods, nodes, and namespaces.

## Operational rules

- Run with `--validate-schema` in automation.
- Store JSON as the canonical report format.
- Evaluate both exit code and report content.
- Use `--redact` before sharing reports outside the platform team.
- Treat cost fields as heuristic and non-authoritative.
- Keep reports in an access-controlled, retention-managed location.
- Test against representative networking modes before rollout.

## Release evidence

A release record should include:

- source commit and tag
- test and security-scan results
- dependency lock or resolved dependency manifest
- package and container digests
- SBOM and provenance when available
- Helm lint/template results when the chart is shipped
- known limitations and supported environment matrix
