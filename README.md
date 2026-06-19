# Azure Kubernetes Service IP Diagnostic Tool

Comprehensive AKS IP exhaustion analyzer with pod-level insights, cost analysis, and lifecycle tracking. Features advanced diagnostics (IP waste detection, pod distribution, stuck pods, maxPods optimization) with multiple output formats (JSON, YAML, Markdown, HTML, text). Includes ROI calculations and regional pricing for infrastructure optimization.


## Features

### Core Diagnostics
- **IP Exhaustion Detection**: Identifies potential IP exhaustion issues within the AKS cluster
- **Provisioning State Evaluation**: Checks the provisioning state of node pools and flags any failures
- **Subnet Capacity Assessment**: Evaluates the capacity of subnets to ensure they meet the requirements for deployed node pools
- **MaxPods Configuration Check**: Analyzes the maxPods settings to ensure they do not exceed safe limits

### Pod-Level Analysis
- **Pod Distribution Analysis**: Analyzes workload balance across nodes with imbalance detection
- **IP Waste Detection**: Identifies unused IPs from over-provisioned node pools (waste percentage calculation)
- **Pod Density Metrics**: Calculates pods per node and categorizes as LOW/OPTIMAL/HIGH/CRITICAL
- **Namespace Breakdown**: Per-namespace pod counts, IP usage, and health metrics
- **Node Utilization**: Detailed per-node analysis with capacity and IP consumption
- **Stuck Pod Detection**: Finds pending/failed pods holding IP addresses
- **Multi-IP Pods**: Identifies dual-stack and multi-CNI configurations
- **Host Network Pods**: Tracks pods not consuming pod IPs
- **Lifecycle Analysis**: Analyzes IP usage patterns across pod lifecycle phases

### Cost Analysis
- **IP Waste Costs**: Calculate monthly/annual costs of unused IP addresses
- **Optimization Savings**: Estimate savings from reducing maxPods configuration
- **Node Scaling Savings**: Calculate potential savings from removing underutilized nodes
- **ROI Analysis**: Payback period and 3-year ROI projections for optimizations
- **Regional Pricing**: Support for different Azure regions with accurate pricing
- **Executive Summaries**: Business-friendly cost impact statements
- **Cost Projections**: 1-year, 2-year, and 3-year cost trend forecasts

### Output Formats
- **JSON** (pretty, compact, sorted)
- **YAML**
- **Text** (terminal-friendly)
- **Markdown** (documentation-ready)
- **HTML** (web-ready reports)

## Project Structure

```
aks-ip-diagnostic
├── src
│   ├── diagnostics
│   ├── azure
│   ├── reports
│   └── utils
├── tests
├── requirements.txt
├── setup.py
├── config.yaml
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd aks-ip-diagnostic
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Diagnostic

Run standard node-level diagnostics:

```bash
python src/main.py \
  --subscription-id "your-subscription-id" \
  --resource-group "your-resource-group" \
  --cluster-name "your-cluster-name" \
  --format json-pretty \
  --output diagnostic-report.json
```

### With Pod-Level Analysis

Include comprehensive pod-level IP usage analysis:

```bash
python src/main.py \
  --subscription-id "your-subscription-id" \
  --resource-group "your-resource-group" \
  --cluster-name "your-cluster-name" \
  --include-pod-analysis \
  --format json-pretty \
  --output full-diagnostic.json
```

### With Cost Analysis

Calculate IP waste costs and potential savings:

```bash
python src/main.py \
  --subscription-id "your-subscription-id" \
  --resource-group "your-resource-group" \
  --cluster-name "your-cluster-name" \
  --include-pod-analysis \
  --include-cost-analysis \
  --region eastus \
  --format json-pretty \
  --output cost-report.json
```

This will show:
- Monthly/annual IP waste costs
- Potential savings from optimization
- ROI analysis with payback period
- 3-year cost projections

**Note**: Cost analysis requires pod-level analysis to calculate accurate waste metrics.

### With Lifecycle Analysis

Add pod lifecycle IP usage patterns:

```bash
python src/main.py \
  --subscription-id "your-subscription-id" \
  --resource-group "your-resource-group" \
  --cluster-name "your-cluster-name" \
  --include-pod-analysis \
  --pod-lifecycle \
  --format json-pretty \
  --output detailed-report.json
```

### Quick Text Output

```bash
python src/main.py \
  --subscription-id "your-sub-id" \
  --resource-group "my-rg" \
  --cluster-name "my-aks" \
  --include-pod-analysis \
  --format text
```

### Additional Options

```bash
# Validate an existing report
python src/main.py --validate report.json

# Convert report format
python src/main.py --input report.json --format markdown --output report.md

# Use custom kubeconfig
python src/main.py \
  --cluster-name my-cluster \
  --include-pod-analysis \
  --kubeconfig ~/.kube/custom-config

# Verbose logging
python src/main.py \
  --cluster-name my-cluster \
  --include-pod-analysis \
  --verbose
```

### All Available Options

```
Options:
  --subscription-id         Azure subscription ID
  --resource-group          Azure resource group name
  --cluster-name            AKS cluster name
  --format, -f              Output format (text, json, json-pretty, json-compact, yaml, markdown, html)
  --output, -o              Output file path (default: stdout)
  --include-pod-analysis    Include pod-level IP usage analysis
  --include-cost-analysis   Include cost analysis (requires --include-pod-analysis)
  --region                  Azure region for pricing (default: eastus)
  --pod-lifecycle           Include pod lifecycle analysis
  --kubeconfig              Path to kubeconfig file
  --config                  Path to configuration file
  --verbose                 Enable verbose logging
  --validate, -v            Validate a JSON report file
  --input, -i               Input JSON report file to load and convert
  --no-validation           Skip validation when saving JSON reports
  --no-enrichment           Skip data enrichment when saving JSON reports
```

## Prerequisites

### Azure Authentication

EnsExample Output

### Text Format

```
================================================================================
AKS IP EXHAUSTION DIAGNOSTIC REPORT
================================================================================

Cluster: production-aks
Resource Group: prod-rg
Subscription: 12345678-1234-1234-1234-123456789abc

Scan Timestamp: 2026-01-22T10:30:00Z
Scan Duration: 12.45s

--------------------------------------------------------------------------------
SUMMARY
--------------------------------------------------------------------------------
Overall Status: WARNING
Risk Level: HIGH
Total Issues: 8
  Critical: 2
  Warnings: 6
  Healthy Checks: 3

--------------------------------------------------------------------------------
POD IP ANALYSIS
--------------------------------------------------------------------------------
  Total Pods: 245
  Total Nodes: 8
  Pod Density: 30.62 pods/node (OPTIMAL)
  IP Waste: 557 IPs (69.62%) - CRITICAL
  
  Issues:
    [CRITICAL] CRITICAL IP address waste detected
      Resource: cluster-wide
      Description: 69.62% of reserved IPs are unused. Wasting 557 IP addresses.
    
    [WARNING] Unbalanced pod distribution across nodes
      Imbalance: 27.6% - Some nodes overloaded, others idle
```

### JSON Output

```json
{
  "metadata": {
    "version": "1.0",
    "timestamp": "2026-01-22T10:30:00Z",
    "scan_duration_seconds": 12.45
  },
  "diagnostics": {
    "pod_ip_analysis": {
   Troubleshooting

### "Unable to connect to Kubernetes API"

Ensure you have valid kubeconfig:

```bash
az aks get-credentials --resource-group my-rg --name my-cluster
kubectl cluster-info
```

### "Authentication failed"

Check Azure authentication:

```bash
az login
az account show
```

### "Metrics server not found"

Pod metrics require metrics-server:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### "Permission denied"

Verify RBAC permissions:

```bash
kubectl auth can-i list pods --all-namespaces
kubectl auth can-i list nodes
```

## Use Cases

### 1. Pre-Production Validation
Run diagnostics before deploying to production to ensure adequate IP capacity.

### 2. Troubleshooting Failed Upgrades
Identify IP exhaustion as the root cause of upgrade failures.

### 3. Cost Optimization
Find over-provisioned node pools and optimize maxPods settings.

### 4. Capacity Planning
Determine remaining IP capacity and plan for cluster growth.

### 5. Regular Health Checks
Schedule periodic scans to catch issues early.

## CI/CD Integration

### Azure DevOps

```yaml
- task: Bash@3
  displayName: 'AKS IP Diagnostic'
  inputs:
    targetType: 'inline'
    script: |
      python src/main.py \
        --subscription-id $(AZURE_SUBSCRIPTION_ID) \
        --resource-group $(RESOURCE_GROUP) \
        --cluster-name $(CLUSTER_NAME) \
        --include-pod-analysis \
        --format json \
        --output diagnostic.json
      
      RISK_LEVEL=$(jq -r '.summary.risk_level' diagnostic.json)
      if [ "$RISK_LEVEL" == "CRITICAL" ]; then
        echo "##vso[task.logissue type=error]Critical IP issues detected"
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
      --include-pod-analysis \
      --format json-pretty \
      --output diagnostic-report.json
```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

Areas for contribution:
- Additional diagnostic checks
- New output formats
- Integration with monitoring tools
- Performance optimizations
- Documentation improvements
      "details": {
        "total_pods": 245,
        "pod_density": {
          "pods_per_node": 30.62,
          "density_status": "OPTIMAL"
        },
        "ip_waste": {
          "waste_percentage": 69.62,
          "wasted_ips": 557,
          "waste_level": "CRITICAL"
        }
      }
    }
  }
}
```

## Key Insights

The tool provides actionable insights:

1. **IP Waste Detection** - Identifies over-provisioned node pools wasting IP addresses
2. **Pod Distribution** - Finds workload imbalances causing resource hotspots
3. **Stuck Pods** - Detects pending/failed pods holding IPs unnecessarily
4. **Capacity Planning** - Calculates remaining capacity for different maxPods values
5. **Cost Optimization** - Recommends maxPods reduction to free up IPs and reduce subnet size

## Documentation

- [JSON Output Guide](docs/JSON_OUTPUT_GUIDE.md) - Comprehensive JSON schema and usage
- [Pod-Level Analysis](docs/POD_LEVEL_ANALYSIS.md) - Detailed pod analysis documentation
- [Examples](examples/) - Code examples and demos

## Testing

Unit tests are provided to ensure the functionality of the diagnostic tool. To run the tests, use:

```bashaccount set --subscription "your-subscription-id"
```

### Kubernetes Access

For pod-level analysis, ensure you have access to the Kubernetes API:

```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group your-rg \
  --name your-cluster-name

# Verify access
kubectl cluster-info
kubectl get nodes
kubectl get pods --all-namespaces
```

### Required Permissions

- **Azure**: Reader role on the subscription or resource group
- **Kubernetes**: List permissions for pods and nodes across all namespaces

## Configuration

Configuration settings can be adjusted in the `config.yaml` file. This includes thresholds for flagging issues related to IP exhaustion, subnet capacity, and maxPods configurations.

Example `config.yaml`:

```yaml
subscription_id: "12345678-1234-1234-1234-123456789abc"
resource_group: "my-resource-group"
cluster_name: "my-aks-cluster"

thresholds:
  ip_waste_percentage: 30  # Alert if IP waste > 30%
  pod_density_critical: 60  # Alert if > 60 pods/node
  subnet_usage_warning: 80  # Alert if subnet > 80% full
  max_pods_safe_limit: 50   # Recommend reducing if > 50
```

## Testing

Unit tests are provided to ensure the functionality of the diagnostic tool. To run the tests, use:

```
pytest tests/
```

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
