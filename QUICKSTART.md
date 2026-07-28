# Quick start

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .
```

For contributors:

```bash
pip install -e ".[dev]"
```

## Authenticate

```bash
az login
az account set --subscription "<subscription-id>"
```

The identity needs read access to the AKS cluster, its node pools, and referenced networking resources.

## Run the first scan

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>"
```

## Save and validate JSON

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format json-pretty \
  --validate-schema \
  --output reports/aks-ip-report.json
```

Validate an existing report:

```bash
aks-ip-diagnostic validate reports/aks-ip-report.json
```

Convert it to Markdown:

```bash
aks-ip-diagnostic convert reports/aks-ip-report.json \
  --format markdown \
  --output reports/aks-ip-report.md
```

## Share a redacted report

```bash
aks-ip-diagnostic convert reports/aks-ip-report.json \
  --format markdown \
  --redact \
  --output reports/redacted-report.md
```

Review the result manually before sharing it outside the platform team.

## Interpret the result

| Value | Meaning |
|---|---|
| `HEALTHY` | No warning or critical issues were detected |
| `WARNING` | Capacity or configuration risk needs planned action |
| `CRITICAL` | A finding may block scaling, upgrades, or provisioning |

Exit codes are `0`, `1`, and `2` for those states. Codes `3` to `5` indicate execution, usage, or report-processing failures.

## Current feature boundary

The base Azure scan is implemented. `--include-pod-analysis` and `--include-cost-analysis` currently add `SKIPPED` diagnostics rather than running those analyses. See the README and `docs/PRODUCTION_REVIEW.md` before deploying the optional Helm chart or publishing a release.

## Run the containerized CLI

Build a local image. Pass a version because the Docker build context does not include the Git metadata used by `setuptools-scm`:

```bash
VERSION="0.1.0"
docker build \
  --build-arg APP_VERSION="$VERSION" \
  -t aks-ip-diagnostic:local \
  .
```

Verify it:

```bash
docker run --rm aks-ip-diagnostic:local version
```

Run a scan and save the report on the host:

```bash
mkdir -p reports

docker run --rm \
  --env-file .env.azure \
  --mount type=bind,src="$(pwd)/reports",dst=/app/reports \
  aks-ip-diagnostic:local scan \
    --subscription-id "<subscription-id>" \
    --resource-group "<resource-group>" \
    --cluster-name "<cluster-name>" \
    --format json-pretty \
    --output /app/reports/aks-ip-report.json
```

The `.env.azure` file should contain `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_CLIENT_SECRET`. Keep it out of source control and restrict its permissions with `chmod 600 .env.azure`.

## Helm workflow purpose

The release workflow's Helm job lints and packages the Kubernetes chart into a `.tgz` artifact. It does not deploy the application. Retain the job when Kubernetes installation is supported; remove it when the project is distributed only through Python packages and container images.
