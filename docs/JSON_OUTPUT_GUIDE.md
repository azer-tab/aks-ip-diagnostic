# Enhanced JSON Output Formats

The AKS IP Diagnostic Tool now supports comprehensive JSON output formats with schema validation, multiple formatting styles, and easy format conversion.

## Features

### 1. **Multiple Output Formats**
- **JSON Pretty** - Human-readable with indentation
- **JSON Compact** - Single-line for parsing
- **JSON** - Sorted keys with indentation
- **YAML** - Alternative structured format
- **Text** - Terminal-friendly output
- **Markdown** - Documentation-ready format
- **HTML** - Web-ready reports

### 2. **JSON Schema Validation**
All JSON outputs conform to a strict schema ensuring:
- Consistent structure across reports
- Type safety and validation
- Interoperability with other tools
- API contract stability

### 3. **Data Enrichment**
Automatic calculation of:
- IP allocation requirements per node
- Subnet capacity metrics
- Usage percentages
- Remaining capacity projections

## Usage Examples

### Basic Diagnostic with JSON Output

```bash
# Pretty JSON to stdout
python src/main.py --format json-pretty

# Save to file
python src/main.py --format json-pretty --output report.json

# Compact JSON (single line)
python src/main.py --format json-compact --output report.json

# With specific cluster
python src/main.py \
  --subscription-id "12345678-1234-1234-1234-123456789abc" \
  --resource-group "my-rg" \
  --cluster-name "my-aks-cluster" \
  --format json-pretty \
  --output diagnostic-report.json
```

### Format Conversion

```bash
# Convert JSON report to Markdown
python src/main.py --input report.json --format markdown --output report.md

# Convert to YAML
python src/main.py --input report.json --format yaml --output report.yaml

# Convert to text
python src/main.py --input report.json --format text
```

### Report Validation

```bash
# Validate a JSON report file
python src/main.py --validate report.json

# Skip validation when saving (faster)
python src/main.py --format json --output report.json --no-validation

# Skip enrichment (use raw data)
python src/main.py --format json --output report.json --no-enrichment
```

## JSON Structure

### Complete Report Schema

```json
{
  "metadata": {
    "version": "1.0",
    "timestamp": "2026-01-16T10:30:00Z",
    "tool_version": "1.0.0",
    "scan_duration_seconds": 12.45
  },
  "cluster_info": {
    "name": "production-aks",
    "resource_group": "prod-rg",
    "subscription_id": "12345678-1234-1234-1234-123456789abc",
    "location": "eastus",
    "kubernetes_version": "1.28.3",
    "network_plugin": "azure",
    "dns_service_ip": "10.0.0.10",
    "service_cidr": "10.0.0.0/16",
    "pod_cidr": null
  },
  "diagnostics": {
    "provisioning_state": {
      "status": "FAIL",
      "risk_level": "CRITICAL",
      "issues": [
        {
          "severity": "CRITICAL",
          "code": "SubnetIsFull",
          "message": "Subnet is full",
          "affected_resource": "sysnodepool",
          "details": {},
          "remediation": "Migrate to larger subnet"
        }
      ],
      "details": {},
      "checked_at": "2026-01-16T10:30:00Z"
    },
    "ip_exhaustion": { ... },
    "subnet_capacity": { ... },
    "max_pods": { ... }
  },
  "node_pools": [
    {
      "name": "sysnodepool",
      "mode": "System",
      "provisioning_state": "Failed",
      "count": 2,
      "vm_size": "Standard_D2s_v3",
      "max_pods": 100,
      "enable_auto_scaling": true,
      "min_count": 1,
      "max_count": 3,
      "subnet_id": "/subscriptions/.../subnets/system-sn",
      "subnet_name": "system-sn",
      "upgrade_settings": {
        "max_surge": "10%",
        "max_unavailable": 0
      },
      "ip_allocation": {
        "required_ips_per_node": 101,
        "total_required_ips": 202,
        "surge_ip_requirement": 20,
        "potential_max_ips": 303
      },
      "error_details": {
        "code": "SubnetIsFull",
        "message": "Subnet does not have enough capacity"
      }
    }
  ],
  "subnets": [
    {
      "name": "system-sn",
      "address_prefix": "10.53.0.0/24",
      "address_space_size": 256,
      "available_ips": 11,
      "used_ips": 240,
      "reserved_ips": 5,
      "usage_percentage": 95.6,
      "attached_node_pools": ["sysnodepool"],
      "is_full": true,
      "remaining_capacity": {
        "additional_nodes_max_pods_30": 0,
        "additional_nodes_max_pods_50": 0,
        "additional_nodes_max_pods_100": 0
      }
    }
  ],
  "recommendations": [
    {
      "priority": "CRITICAL",
      "category": "IP_EXHAUSTION",
      "title": "Migrate to larger subnet",
      "description": "System pool failed due to IP exhaustion",
      "affected_resources": ["sysnodepool"],
      "impact": "Cluster operations blocked",
      "recommendation": "Create /22 subnet and migrate",
      "implementation_steps": [
        "Create new subnet",
        "Create new node pool",
        "Migrate workloads",
        "Delete old pool"
      ],
      "estimated_downtime": "Zero with proper migration",
      "automation_available": true,
      "documentation_links": [
        "https://docs.microsoft.com/azure/aks/..."
      ]
    }
  ],
  "summary": {
    "overall_status": "CRITICAL",
    "risk_level": "CRITICAL",
    "total_issues": 8,
    "critical_issues": 3,
    "warnings": 5,
    "healthy_checks": 0
  }
}
```

## Programmatic Usage

### Python API

```python
from reports.formatters import (
    DiagnosticReportBuilder,
    OutputFormat,
    format_report,
    create_issue,
    create_recommendation
)
from reports.json_validator import save_json_report, ReportValidator

# Build report
builder = DiagnosticReportBuilder(
    cluster_name="my-cluster",
    resource_group="my-rg",
    subscription_id="sub-id"
)

# Add diagnostic results
builder.add_diagnostic_result(
    "ip_exhaustion",
    status="FAIL",
    risk_level="CRITICAL",
    issues=[
        create_issue(
            severity="CRITICAL",
            code="SubnetIsFull",
            message="Subnet is exhausted"
        )
    ]
)

# Build and format
report_data = builder.build()
json_output = format_report(report_data, OutputFormat.JSON_PRETTY)

# Save with validation
success, message = save_json_report(
    report_data,
    "output.json",
    validate=True,
    enrich=True,
    pretty=True
)

# Validate existing report
is_valid, errors = ReportValidator.validate_diagnostic_report(report_data)
```

## Schema Details

### Issue Object
```json
{
  "severity": "CRITICAL|ERROR|WARNING|INFO",
  "code": "error_code",
  "message": "Human readable message",
  "affected_resource": "resource-name",
  "details": {},
  "remediation": "How to fix"
}
```

### Recommendation Object
```json
{
  "priority": "CRITICAL|HIGH|MEDIUM|LOW",
  "category": "IP_EXHAUSTION|SUBNET_CAPACITY|MAX_PODS|PROVISIONING|CONFIGURATION",
  "title": "Short title",
  "description": "Detailed description",
  "affected_resources": ["resource1", "resource2"],
  "impact": "Impact description",
  "recommendation": "What to do",
  "implementation_steps": ["step1", "step2"],
  "estimated_downtime": "downtime estimate",
  "automation_available": true|false,
  "documentation_links": ["url1", "url2"]
}
```

## Integration Examples

### CI/CD Pipeline

```yaml
# Azure DevOps Pipeline
- task: Bash@3
  displayName: 'Run AKS Diagnostic'
  inputs:
    targetType: 'inline'
    script: |
      python src/main.py \
        --subscription-id $(SUBSCRIPTION_ID) \
        --resource-group $(RESOURCE_GROUP) \
        --cluster-name $(CLUSTER_NAME) \
        --format json \
        --output diagnostic-report.json
      
      # Parse results
      RISK_LEVEL=$(jq -r '.summary.risk_level' diagnostic-report.json)
      
      if [ "$RISK_LEVEL" == "CRITICAL" ]; then
        echo "##vso[task.logissue type=error]Critical IP exhaustion detected"
        exit 1
      fi
```

### GitHub Actions

```yaml
- name: AKS IP Diagnostic
  run: |
    python src/main.py \
      --subscription-id ${{ secrets.AZURE_SUBSCRIPTION_ID }} \
      --resource-group ${{ vars.RESOURCE_GROUP }} \
      --cluster-name ${{ vars.CLUSTER_NAME }} \
      --format json-pretty \
      --output $GITHUB_WORKSPACE/diagnostic-report.json
    
    # Upload artifact
    echo "RISK_LEVEL=$(jq -r '.summary.risk_level' diagnostic-report.json)" >> $GITHUB_OUTPUT

- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: diagnostic-report
    path: diagnostic-report.json
```

### REST API Integration

```python
import requests
import json

# Run diagnostic and get JSON
with open('diagnostic-report.json') as f:
    report = json.load(f)

# Send to monitoring system
response = requests.post(
    'https://monitoring.example.com/api/aks-reports',
    json=report,
    headers={'Authorization': f'Bearer {token}'}
)

# Process critical issues
if report['summary']['risk_level'] == 'CRITICAL':
    # Send alert
    critical_issues = [
        issue for diagnostic in report['diagnostics'].values()
        for issue in diagnostic.get('issues', [])
        if issue['severity'] == 'CRITICAL'
    ]
    
    send_alert(critical_issues)
```

## Best Practices

### 1. **Always Validate Reports**
```bash
# Validate before sharing
python src/main.py --validate report.json
```

### 2. **Use Enrichment for Analysis**
Enriched reports include calculated fields like IP requirements and capacity metrics.

### 3. **Store Reports for Trending**
```bash
# Include timestamp in filename
python src/main.py \
  --format json \
  --output "reports/aks-diagnostic-$(date +%Y%m%d-%H%M%S).json"
```

### 4. **Parse Programmatically**
```bash
# Extract specific data with jq
jq '.summary.risk_level' report.json
jq '.diagnostics.ip_exhaustion.issues[] | select(.severity=="CRITICAL")' report.json
jq '.recommendations[] | select(.priority=="CRITICAL") | .title' report.json
```

## Error Handling

### Validation Errors
```bash
$ python src/main.py --validate invalid-report.json
✗ Invalid report file:
  - 'cluster_info' is a required property
  - Additional properties are not allowed ('extra_field')
```

### Conversion Errors
```bash
$ python src/main.py --input corrupted.json --format markdown
✗ Failed to load report: Invalid JSON: Expecting property name enclosed in double quotes
```

## Performance

- **JSON Pretty**: ~50ms for typical report
- **JSON Compact**: ~30ms for typical report
- **Validation**: ~10ms additional overhead
- **Enrichment**: ~20ms additional overhead

For best performance in CI/CD, use `--no-validation --no-enrichment` if schema compliance is not critical.

## Troubleshooting

### Common Issues

**Issue**: Validation fails on custom fields
```bash
# Skip validation for custom reports
python src/main.py --format json --output report.json --no-validation
```

**Issue**: Large reports cause memory issues
```bash
# Use compact format to reduce size
python src/main.py --format json-compact --output report.json
```

**Issue**: Cannot convert old reports
```bash
# Old reports may not have required fields
# Solution: Re-run diagnostic or add missing fields manually
```

## Additional Resources

- [JSON Schema Documentation](./json_schema.py)
- [Formatter API Reference](./formatters.py)
- [Validation Guide](./json_validator.py)
- [Example Scripts](../examples/json_output_demo.py)
