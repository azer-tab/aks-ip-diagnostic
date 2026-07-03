# JSON output and report conversion guide

JSON is the preferred format for automation. Text output is optimized for humans; JSON output is the stable integration surface.

## Supported formats

The CLI supports these output formats:

| Format | Use case |
|---|---|
| `text` | Human terminal output |
| `json` | Pretty JSON with sorted keys |
| `json-pretty` | Human-readable JSON preserving report order |
| `json-compact` | Compact single-line JSON for pipelines |
| `yaml` | YAML report output |
| `markdown` | Shareable written report |
| `html` | Web-viewable report |

## Generate JSON

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format json-pretty \
  --output reports/aks-report.json
```

For machine pipelines:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format json-compact \
  --output reports/aks-report.compact.json
```

## Validate a report

```bash
aks-ip-diagnostic validate reports/aks-report.json
```

During scan, you can request generated report validation:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --format json \
  --validate-schema \
  --output reports/aks-report.json
```

## Convert a saved report

```bash
aks-ip-diagnostic convert reports/aks-report.json --format markdown --output reports/aks-report.md
aks-ip-diagnostic convert reports/aks-report.json --format html --output reports/aks-report.html
aks-ip-diagnostic convert reports/aks-report.json --format text
```

To redact sensitive values during conversion:

```bash
aks-ip-diagnostic convert reports/aks-report.json \
  --format markdown \
  --redact \
  --output reports/aks-report-redacted.md
```

## High-level report structure

A report is organized around these sections:

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

Additional optional sections may appear when pod-level or cost analysis is enabled.

## Automation examples

Fail a pipeline on critical findings:

```bash
aks-ip-diagnostic scan ... --format json --output report.json
status=$?

if [ "$status" -eq 2 ]; then
  echo "Critical AKS IP diagnostic findings detected"
  exit 1
fi
```

Extract summary with `jq`:

```bash
jq '.summary' reports/aks-report.json
jq '.recommendations[]?.title' reports/aks-report.json
```

## Redaction guidance

Use redaction before sharing reports with vendors, public issue trackers, or broad internal audiences:

```bash
aks-ip-diagnostic scan ... --format json --redact --output redacted-report.json
```

Redaction masks common sensitive infrastructure fields and IP-like values. Review the output manually before external sharing.

## Schema stability

Before declaring a stable `1.0.0` release, add golden-file tests for representative report examples. This will prevent accidental breaking changes to automation consumers.
