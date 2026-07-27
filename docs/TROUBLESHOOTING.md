# Troubleshooting

## Authentication failed

Confirm the active Azure identity and subscription:

```bash
az account show
az account set --subscription "<subscription-id>"
```

For service-principal or workload-identity use, verify that the expected `AZURE_*` environment variables or federated identity configuration are available to the process.

Run with `--verbose` to include debug logging. Do not publish verbose logs without reviewing them for infrastructure identifiers.

## Cluster or subnet cannot be read

The identity needs read access to the AKS cluster, node pools, and referenced networking resources. Cross-resource-group virtual networks may require an additional role assignment at the network resource group or subnet scope.

## A non-text report was not printed

Non-text formats are saved to `./reports/` by default. Supply an explicit path when automation needs a predictable filename:

```bash
aks-ip-diagnostic scan ... --format json-compact --output report.json
```

## Validation failed

Validate the report directly:

```bash
aks-ip-diagnostic validate report.json
```

A validation failure returns exit code `5`. Check whether the report was created by an older version or modified after generation. Preserve `metadata.tool_version` when diagnosing compatibility issues.

## The command returned exit code 1 or 2

Those codes mean the scan completed successfully but found risk:

- `1`: warning findings
- `2`: critical findings

Inspect `summary`, `issues`, and `recommendations` in the JSON report before deciding whether to fail a deployment or upgrade gate.

## Pod or cost analysis says SKIPPED

This is expected in version `0.3.3`. The current orchestrator accepts the flags but does not execute those optional modules. Use only the base Azure scan results until the integration is completed.

## Docker cannot access Azure credentials

Pass the identity method into the container. For a service principal:

```bash
docker run --rm \
  -e AZURE_CLIENT_ID \
  -e AZURE_TENANT_ID \
  -e AZURE_CLIENT_SECRET \
  aks-ip-diagnostic:local scan ...
```

For managed or workload identity, use the identity integration supported by the runtime platform rather than copying local credential files into the image.

## `ImportError: cannot import name 'UTC' from 'datetime'`

This error affected version `0.3.2` when it was installed with Python 3.10. The code imported `datetime.UTC`, which is available only in Python 3.11 and newer even though the package supports Python 3.10+.

Upgrade to version `0.3.3` or newer and reinstall the package inside the active virtual environment:

```bash
python -m pip install --upgrade --force-reinstall .
```

For an editable development installation, use:

```bash
python -m pip install --upgrade -e '.[dev]'
```

Confirm the interpreter and installed package version:

```bash
python --version
python -c "import aks_ip_diagnostic; print(aks_ip_diagnostic.__version__)"
```
