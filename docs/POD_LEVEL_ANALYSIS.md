# Pod-Level IP Usage Analysis

Comprehensive pod-level IP usage analysis for Azure Kubernetes Service (AKS) clusters to identify inefficiencies, waste, and optimization opportunities.

## Overview

The Pod-Level IP Analysis module provides granular insights into how IP addresses are consumed at the pod level, going beyond node-level analysis to identify:

- **IP waste** from over-provisioned node pools
- **Pod distribution** imbalances across nodes
- **Stuck pods** holding IP addresses
- **Multi-IP pods** consuming extra addresses
- **Host network** usage patterns
- **Namespace-level** IP consumption
- **Lifecycle-based** IP allocation patterns

## Features

### 1. **Pod Distribution Analysis**
Analyzes how pods are distributed across nodes:
- Min/Max/Avg pods per node
- Standard deviation and balance metrics
- Node utilization percentage
- Imbalance detection

### 2. **IP Allocation Tracking**
Tracks actual IP address allocation:
- Total IPs allocated vs available
- Unique IP count
- Pods without IPs (pending/failed)
- IP conflict detection
- IP range categorization

### 3. **Namespace Analysis**
Per-namespace metrics:
- Pod count and health status
- IP allocation rate
- Running vs pending pods
- Resource consumption patterns

### 4. **Node-Level Breakdown**
Detailed per-node analysis:
- Pod count and utilization
- IP consumption
- Remaining capacity
- Node pool identification
- System vs user nodes

### 5. **Pod Density Metrics**
Calculate and categorize pod density:
- Pods per node ratio
- Density status (LOW/OPTIMAL/HIGH/CRITICAL)
- Performance impact assessment
- Scaling recommendations

### 6. **IP Waste Detection**
Identify wasted IP addresses:
- Actual vs reserved IP comparison
- Waste percentage calculation
- Cost impact assessment
- Optimization opportunities

### 7. **Special Case Identification**
Find special pod configurations:
- **Multi-IP pods** (dual-stack, multi-CNI)
- **Host network pods** (not consuming pod IPs)
- **Stuck pods** holding IPs
- **Failed pods** with allocated IPs

### 8. **Lifecycle Analysis**
IP usage across pod lifecycle:
- IP allocation by pod phase
- Stuck pods consuming IPs
- Lifecycle-based waste identification

## Usage

### Basic Analysis

```bash
python examples/pod_analysis_demo.py \
  --cluster-name my-aks-cluster \
  --resource-group my-rg \
  --subscription-id 12345678-1234-1234-1234-123456789abc
```

### With Lifecycle Analysis

```bash
python examples/pod_analysis_demo.py \
  --cluster-name my-aks-cluster \
  --resource-group my-rg \
  --subscription-id 12345678-1234-1234-1234-123456789abc \
  --lifecycle
```

### Save to JSON

```bash
python examples/pod_analysis_demo.py \
  --cluster-name my-aks-cluster \
  --resource-group my-rg \
  --subscription-id 12345678-1234-1234-1234-123456789abc \
  --output pod-analysis.json \
  --format json-pretty
```

### Programmatic Usage

```python
from azure.kubernetes_client import KubernetesClient
from azure.network_client import NetworkClient
from diagnostics.pod_ip_analysis import PodIPAnalyzer

# Initialize clients
k8s_client = KubernetesClient(cluster_name="my-cluster")
network_client = NetworkClient(subscription_id="sub-id")

# Create analyzer
analyzer = PodIPAnalyzer(k8s_client, network_client)

# Run analysis
analysis = analyzer.analyze_cluster_pods("my-cluster", "my-rg")

# Access results
print(f"Total pods: {analysis['total_pods']}")
print(f"IP waste: {analysis['ip_waste_analysis']['waste_percentage']}%")
print(f"Pod density: {analysis['pod_density']['density_status']}")

# Check issues
for issue in analysis['issues']:
    print(f"[{issue['severity']}] {issue['title']}")

# Get recommendations
for rec in analysis['recommendations']:
    print(f"[{rec['priority']}] {rec['title']}: {rec['action']}")
```

## Output Structure

### Analysis Result

```json
{
  "timestamp": "2026-01-16T10:30:00Z",
  "cluster_name": "production-aks",
  "total_pods": 245,
  "total_nodes": 8,
  "pod_distribution": {
    "min_pods_per_node": 18,
    "max_pods_per_node": 45,
    "avg_pods_per_node": 30.62,
    "std_deviation": 8.45,
    "balanced": false,
    "imbalance_percentage": 27.6
  },
  "ip_allocation": {
    "total_ips_allocated": 243,
    "pods_without_ip": 2,
    "unique_ips": 243,
    "has_conflicts": false,
    "allocation_rate": 99.18
  },
  "namespace_analysis": {
    "total_namespaces": 12,
    "namespaces": [
      {
        "namespace": "production",
        "pod_count": 85,
        "running_pods": 82,
        "pending_pods": 3,
        "ip_count": 82,
        "ip_allocation_rate": 96.47,
        "health_percentage": 96.47
      }
    ]
  },
  "pod_density": {
    "total_running_pods": 240,
    "total_nodes": 8,
    "pods_per_node": 30.0,
    "density_status": "OPTIMAL",
    "recommendation": "Pod density is within optimal range."
  },
  "ip_waste_analysis": {
    "actual_pod_ips": 243,
    "reserved_ips": 800,
    "wasted_ips": 557,
    "waste_percentage": 69.62,
    "waste_level": "CRITICAL",
    "impact": "Severe IP waste, immediate optimization needed",
    "cost_implication": "High"
  },
  "multi_ip_pods": [
    {
      "name": "web-app-dual-stack",
      "namespace": "production",
      "ip_addresses": ["10.244.1.5", "fd00::5"],
      "ip_count": 2,
      "reason": "IPv4/IPv6 dual-stack"
    }
  ],
  "host_network_pods": [
    {
      "name": "node-exporter-abcd",
      "namespace": "monitoring",
      "node": "aks-nodepool1-12345678-vmss000001",
      "uses_host_ip": true
    }
  ],
  "issues": [
    {
      "severity": "CRITICAL",
      "category": "IP_WASTE",
      "title": "CRITICAL IP address waste detected",
      "description": "69.62% of reserved IPs are unused. Wasting 557 IP addresses.",
      "impact": "Severe IP waste, immediate optimization needed",
      "affected_resources": ["cluster-wide"]
    }
  ],
  "recommendations": [
    {
      "priority": "HIGH",
      "category": "IP_OPTIMIZATION",
      "title": "Reduce maxPods to match actual usage",
      "description": "Currently wasting 557 IPs (69.62% waste rate)",
      "action": "Analyze actual pod density and reduce maxPods configuration accordingly",
      "expected_benefit": "Free up approximately 557 IP addresses",
      "implementation_complexity": "Medium - requires node pool recreation"
    }
  ]
}
```

## Key Metrics Explained

### Pod Distribution Balance

**Balanced** when standard deviation < 20% of mean:
- ✅ Balanced: Even workload distribution
- ❌ Unbalanced: Some nodes overloaded, others idle

**Imbalance percentage** = (std_dev / avg) × 100
- < 20%: Good distribution
- 20-40%: Moderate imbalance
- > 40%: Significant imbalance

### Pod Density Status

Based on pods per node:
- **LOW** (< 10): Under-utilized, cost optimization opportunity
- **OPTIMAL** (10-30): Healthy density
- **HIGH** (30-50): Monitor performance
- **CRITICAL** (> 50): Add nodes immediately

### IP Waste Level

Based on waste percentage:
- **LOW** (< 20%): Efficient utilization
- **MEDIUM** (20-40%): Room for optimization
- **HIGH** (40-60%): Significant waste
- **CRITICAL** (> 60%): Immediate action needed

## Common Scenarios

### Scenario 1: High IP Waste

**Symptoms:**
- Waste percentage > 50%
- Large gap between reserved and actual IPs
- Low pod density

**Diagnosis:**
```json
{
  "ip_waste_analysis": {
    "waste_percentage": 72.5,
    "wasted_ips": 580,
    "waste_level": "CRITICAL"
  },
  "pod_density": {
    "pods_per_node": 12.5,
    "density_status": "LOW"
  }
}
```

**Solution:**
1. Reduce maxPods from 100 to 30-50
2. Create new node pool with optimized settings
3. Migrate workloads
4. Delete old node pool

### Scenario 2: Unbalanced Distribution

**Symptoms:**
- High standard deviation
- Some nodes at 90%+ utilization
- Others at < 30%

**Diagnosis:**
```json
{
  "pod_distribution": {
    "min_pods_per_node": 8,
    "max_pods_per_node": 58,
    "imbalance_percentage": 45.2,
    "balanced": false
  }
}
```

**Solution:**
1. Review pod affinity/anti-affinity rules
2. Check for node taints and tolerations
3. Enable pod topology spread constraints
4. Rebalance workloads

### Scenario 3: Stuck Pods Consuming IPs

**Symptoms:**
- Pods in Pending/Failed state with IPs
- Wasted IPs in lifecycle analysis

**Diagnosis:**
```json
{
  "lifecycle_analysis": {
    "stuck_pods_with_ip": [
      {
        "name": "app-pod-xyz",
        "phase": "Pending",
        "ip_address": "10.244.2.15",
        "issue": "Pending pod holding IP address"
      }
    ],
    "wasted_ips_in_stuck_pods": 23
  }
}
```

**Solution:**
1. Identify root cause (resource constraints, image pull failures)
2. Fix underlying issues
3. Delete stuck pods
4. Implement pod disruption budgets

### Scenario 4: High Pod Density

**Symptoms:**
- Pods per node > 50
- Performance degradation
- Frequent evictions

**Diagnosis:**
```json
{
  "pod_density": {
    "pods_per_node": 68.3,
    "density_status": "CRITICAL",
    "recommendation": "Add nodes immediately"
  }
}
```

**Solution:**
1. Enable cluster autoscaler
2. Manually add nodes
3. Review workload resource requests
4. Consider increasing node VM size

## Integration with Main Tool

### Add to CLI

```bash
# Run combined diagnostic
python src/main.py \
  --cluster-name my-cluster \
  --resource-group my-rg \
  --subscription-id sub-id \
  --include-pod-analysis \
  --format json-pretty \
  --output full-diagnostic.json
```

### Integrate with Reports

```python
from diagnostics.pod_ip_analysis import PodIPAnalyzer

# In main diagnostic flow
analyzer = PodIPAnalyzer(k8s_client, network_client)
pod_analysis = analyzer.analyze_cluster_pods(cluster_name, resource_group)

# Add to report
builder.add_diagnostic_result(
    "pod_ip_analysis",
    status="FAIL" if pod_analysis['issues'] else "PASS",
    risk_level=pod_analysis['ip_waste_analysis']['waste_level'],
    issues=pod_analysis['issues']
)
```

## Best Practices

### 1. Regular Monitoring
Run pod-level analysis:
- **Daily**: In production clusters
- **Weekly**: In dev/test environments
- **After deployments**: Validate impact

### 2. Set Thresholds
Define acceptable levels:
- Pod density: 20-40 pods/node
- IP waste: < 30%
- Distribution imbalance: < 25%

### 3. Automate Alerts
Trigger alerts when:
- IP waste > 50%
- Pod density > 60 pods/node
- Distribution imbalance > 40%
- Stuck pods > 10

### 4. Correlate with Performance
Compare pod analysis with:
- Node CPU/memory utilization
- Application latency metrics
- Network throughput
- Error rates

## Troubleshooting

### Issue: "Unable to connect to Kubernetes API"

**Solution:**
```bash
# Verify kubeconfig
kubectl cluster-info

# Or get AKS credentials
az aks get-credentials \
  --resource-group my-rg \
  --name my-cluster \
  --admin
```

### Issue: "Metrics server not found"

**Solution:**
```bash
# Install metrics server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Issue: "Permission denied"

**Solution:**
```bash
# Ensure you have proper RBAC permissions
kubectl auth can-i list pods --all-namespaces
kubectl auth can-i list nodes
```

## Performance Considerations

- **Small clusters** (< 100 pods): < 5 seconds
- **Medium clusters** (100-500 pods): 5-15 seconds
- **Large clusters** (> 500 pods): 15-60 seconds

Optimize performance:
- Use field selectors to filter pods
- Limit namespace scope if needed
- Cache node information
- Run analysis during low-traffic periods

## API Reference

See [pod_ip_analysis.py](../src/diagnostics/pod_ip_analysis.py) for complete API documentation.

### Main Classes

- `PodIPAnalyzer`: Main analysis class
- `KubernetesClient`: Kubernetes API wrapper

### Key Methods

- `analyze_cluster_pods()`: Full pod analysis
- `analyze_pod_distribution()`: Distribution metrics
- `analyze_ip_allocation()`: IP tracking
- `analyze_by_namespace()`: Namespace breakdown
- `analyze_by_node()`: Node-level analysis
- `calculate_pod_density()`: Density metrics
- `analyze_ip_waste()`: Waste detection
- `detect_issues()`: Issue identification
- `generate_recommendations()`: Actionable advice

## Future Enhancements

Planned features:
- Historical trending
- Predictive analysis
- Cost estimation per pod
- Network policy impact
- Service mesh integration
- Multi-cluster comparison
