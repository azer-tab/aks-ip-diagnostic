# Quick Start Guide

Get started with the AKS IP Diagnostic Tool in 5 minutes!

## 1. Installation (2 minutes)

```bash
# Clone the repository
git clone <repository-url>
cd aks-ip-diagnostic

# Install dependencies
pip install -r requirements.txt
```

## 2. Azure Authentication (1 minute)

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "your-subscription-id"

# Get AKS credentials (for pod analysis)
az aks get-credentials --resource-group your-rg --name your-cluster
```

## 3. Run Your First Diagnostic (30 seconds)

### Basic Node-Level Analysis

```bash
aks-ip-diagnostic scan \
  --subscription-id "your-sub-id" \
  --resource-group "your-rg" \
  --cluster-name "your-cluster" \
  --format text
```

### Complete Analysis (Node + Pod Level)

```bash
aks-ip-diagnostic scan \
  --subscription-id "your-sub-id" \
  --resource-group "your-rg" \
  --cluster-name "your-cluster" \
  --include-pod-analysis \
  --format json-pretty \
  --output report.json
```

## 4. Understanding Results (1 minute)

### Key Metrics to Check

✅ **Overall Status**: HEALTHY, WARNING, or CRITICAL
- HEALTHY: No issues detected
- WARNING: Non-critical issues found
- CRITICAL: Immediate action required

✅ **Risk Level**: LOW, MEDIUM, HIGH, or CRITICAL
- Indicates severity of detected issues

✅ **IP Waste Percentage**
- < 20%: Efficient ✅
- 20-40%: Room for optimization 🟡
- 40-60%: Significant waste 🟠
- > 60%: Critical waste 🔴

✅ **Pod Density**
- < 10 pods/node: Under-utilized
- 10-30 pods/node: Optimal ✅
- 30-50 pods/node: High 🟡
- > 50 pods/node: Critical 🔴

## 5. Common Scenarios

### Scenario 1: Troubleshooting Failed Upgrades

```bash
# Run diagnostic to check for IP exhaustion
aks-ip-diagnostic scan \
  --cluster-name failed-cluster \
  --resource-group prod-rg \
  --subscription-id your-sub-id \
  --include-pod-analysis \
  --format text

# Look for:
# - SubnetIsFull errors
# - High IP waste
# - maxPods > 50
```

**Expected Output:**
```
⚠️  ISSUES DETECTED (3):
  🔴 [CRITICAL] Node pool in Failed state
     Subnet systempool-sn is full - cannot provision nodes
     
  🔴 [CRITICAL] 70% IP waste detected
     557 IPs reserved but only 243 used
```

**Solution:**
1. Create new subnet with /22 CIDR
2. Create new node pool in new subnet
3. Migrate workloads
4. Delete old node pool

### Scenario 2: Cost Optimization

```bash
# Check for IP waste and over-provisioning
aks-ip-diagnostic scan \
  --cluster-name my-cluster \
  --include-pod-analysis \
  --format json-pretty \
  --output optimization-report.json

# Parse results
jq '.diagnostics.pod_ip_analysis.details.ip_waste' optimization-report.json
```

**If waste_percentage > 50%:**

Reduce maxPods from 100 to 30-50:
```bash
# Create new node pool with optimized settings
az aks nodepool add \
  --resource-group my-rg \
  --cluster-name my-cluster \
  --name optimized \
  --node-count 3 \
  --max-pods 30
```

### Scenario 3: Capacity Planning

```bash
# Get detailed capacity metrics
aks-ip-diagnostic scan \
  --cluster-name my-cluster \
  --include-pod-analysis \
  --pod-lifecycle \
  --format json-pretty \
  --output capacity-report.json

# Check remaining capacity
jq '.diagnostics.pod_ip_analysis.details' capacity-report.json
```

**Look for:**
- Available IPs per subnet
- Current vs maximum pod capacity
- Projected growth capacity

## Quick Reference

### Most Common Commands

```bash
# Standard diagnostic
aks-ip-diagnostic scan --cluster-name <name> --format text

# Full analysis with JSON output
aks-ip-diagnostic scan \
  --cluster-name <name> \
  --include-pod-analysis \
  --format json-pretty \
  --output report.json

# Validate existing report
aks-ip-diagnostic validate report.json

# Convert JSON to Markdown
aks-ip-diagnostic convert report.json \
  --format markdown \
  --output report.md
```

### Output Formats

- `text` - Human-readable terminal output
- `json-pretty` - Formatted JSON (default for files)
- `json-compact` - Single-line JSON
- `yaml` - YAML format
- `markdown` - Documentation-ready
- `html` - Web-ready report

### Required Permissions

**Azure:**
- Reader role on subscription or resource group

**Kubernetes (for pod analysis):**
```bash
# Verify you have permissions
kubectl auth can-i list pods --all-namespaces
kubectl auth can-i list nodes
```

## What's Next?

### Learn More
- [Full Documentation](README.md)
- [Pod-Level Analysis Guide](docs/POD_LEVEL_ANALYSIS.md)
- [JSON Output Reference](docs/JSON_OUTPUT_GUIDE.md)

### Run Examples
```bash
# Run demo scripts
python examples/json_output_demo.py
python examples/pod_analysis_demo.py --help
```

### Automate
Set up scheduled diagnostics:

```bash
# Add to crontab for daily checks
0 9 * * * cd /path/to/aks-ip-diagnostic && aks-ip-diagnostic scan \
  --cluster-name prod-cluster \
  --include-pod-analysis \
  --format json \
  --output /reports/daily-$(date +\%Y\%m\%d).json
```

## Need Help?

### Error Messages

**"Unable to connect to Kubernetes API"**
```bash
az aks get-credentials --resource-group my-rg --name my-cluster
```

**"Authentication failed"**
```bash
az login
az account show
```

**"Module not found"**
```bash
pip install -r requirements.txt
```

### Get Support
- Check [Troubleshooting](README.md#troubleshooting) section
- Review [Documentation](docs/)
- Open an issue on GitHub

## Success Checklist

After running your first diagnostic:

- [ ] Tool executed successfully
- [ ] Report generated
- [ ] Overall status understood
- [ ] Key metrics reviewed
- [ ] Issues (if any) documented
- [ ] Next steps identified

**You're ready to optimize your AKS cluster! 🚀**
