# Cost Analysis Guide

## Overview

The cost analysis feature translates technical IP waste metrics into financial impact, helping you justify optimization work and prioritize technical debt remediation. It calculates:

- **IP Waste Costs**: Monthly/annual cost of unused IP addresses
- **Optimization Savings**: Potential savings from reducing maxPods
- **ROI Analysis**: Payback period and return on investment
- **Cost Projections**: 1-3 year cost trend forecasts

## How It Works

### Azure IP Pricing Model

Azure charges for VNet IP addresses beyond the first 50 free IPs:

- **First 50 IPs**: Free
- **Additional IPs**: $0.005 per IP per month ($0.06 per year)
- **Regional Variations**: Some regions have different pricing

**Example**:
- Cluster with 800 reserved IPs
- Charged for: 800 - 50 = 750 IPs
- Monthly cost: 750 × $0.005 = $3.75
- Annual cost: 750 × $0.06 = $45.00

### Waste Calculation

IP waste occurs when nodes reserve more IPs than they actually use:

```
Reserved IPs per Node = maxPods + System Reserve
System Reserve = 1 (for node itself) + CNI overhead

Example:
- Node with maxPods=110
- Reserved IPs = 110 + 1 = 111 IPs
- Actual pods running = 45
- Wasted IPs = 111 - 45 = 66 IPs
- Waste percentage = (66 / 111) × 100 = 59.5%
```

### Cost Calculation

**Current Costs**:
```
Total IPs Reserved = Σ (maxPods + 1) for all nodes
Billable IPs = Total IPs - 50 (free tier)
Monthly IP Cost = Billable IPs × $0.005
Annual IP Cost = Monthly Cost × 12
```

**Waste Costs**:
```
Wasted IPs = Σ (Reserved IPs - Used IPs) for all nodes
Monthly Waste Cost = max(0, Wasted IPs - 50) × $0.005
Annual Waste Cost = Monthly Waste × 12
```

**VM Costs** (optional):
- Estimated based on node VM sizes
- Used for total cluster cost context
- Not included in waste calculations (VMs still needed for pods)

## Usage

### Basic Cost Analysis

```bash
python src/main.py \
  --subscription-id "your-sub-id" \
  --resource-group "your-rg" \
  --cluster-name "your-cluster" \
  --include-pod-analysis \
  --include-cost-analysis \
  --format text
```

**Note**: `--include-pod-analysis` is required for cost analysis because we need actual pod counts to calculate waste.

### Specify Region

Different Azure regions may have different pricing:

```bash
python src/main.py \
  --cluster-name "prod-cluster" \
  --include-pod-analysis \
  --include-cost-analysis \
  --region westus2 \
  --format json-pretty
```

Supported regions:
- `eastus` (default)
- `westus`, `westus2`, `westus3`
- `centralus`, `northcentralus`, `southcentralus`
- `eastus2`, `westeurope`, `northeurope`
- And all other Azure regions

### Export for Reporting

Generate different formats for different audiences:

```bash
# Technical report (JSON)
python src/main.py ... --include-cost-analysis --format json-pretty --output cost-technical.json

# Executive summary (Markdown)
python src/main.py ... --include-cost-analysis --format markdown --output cost-executive.md

# Text report for terminal
python src/main.py ... --include-cost-analysis --format text
```

## Output Interpretation

### Text Format Example

```
COST ANALYSIS:
  Status: PASS (Financial Impact: HIGH)

  Current Monthly Costs:
    IP Addresses: $12.50
    VM Compute:   $450.00
    Total:        $462.50
    Annual Total: $5,550.00

  💰 IP Waste Costs:
    Unused IPs:   557 (69.6% waste)
    Monthly Cost: $8.71
    Annual Cost:  $104.52
    ⚠️  High waste detected - over 20% of IP costs are wasted!

  💡 Total Potential Savings:
    Monthly:  $8.71
    Annual:   $104.52
    3-Year:   $313.56

  📊 ROI Analysis:
    Payback Period: 2.3 months
    3-Year ROI:     1567%
    Implementation: MEDIUM

  Summary: HIGH financial impact - Immediate action recommended
```

### Field Explanations

**Current Monthly Costs**:
- `IP Addresses`: Cost of all reserved IPs (excluding 50 free)
- `VM Compute`: Estimated VM costs (for context only)
- `Total`: Combined IP + VM costs
- `Annual Total`: Total × 12

**IP Waste Costs**:
- `Unused IPs`: Number and percentage of wasted IPs
- `Monthly Cost`: Monthly cost of wasted IPs
- `Annual Cost`: Annual cost of wasted IPs
- Warning if waste > 20%

**Total Potential Savings**:
- `Monthly`: Potential monthly savings from all optimizations
- `Annual`: Potential annual savings
- `3-Year`: Projected 3-year savings

**ROI Analysis**:
- `Payback Period`: Months to recover implementation cost
- `3-Year ROI`: Total return as % of implementation cost
- `Implementation`: Effort level (LOW/MEDIUM/HIGH)

**Summary**:
- Overall financial impact assessment
- Action recommendation based on waste level

### Risk Levels

Cost analysis uses risk levels to indicate financial impact:

| Waste % | Risk Level | Action |
|---------|-----------|--------|
| 0-10%   | LOW       | Monitor - minimal waste |
| 10-20%  | MEDIUM    | Consider optimization |
| 20-30%  | HIGH      | Optimization recommended |
| 30%+    | CRITICAL  | Immediate action needed |

## JSON Output Structure

```json
{
  "diagnostics": {
    "cost_analysis": {
      "status": "PASS",
      "risk_level": "HIGH",
      "details": {
        "region": "eastus",
        "pricing": {
          "ip_per_month": 0.005,
          "free_ips": 50
        },
        "current_costs": {
          "total_ips": 800,
          "billable_ips": 750,
          "ip_monthly": 3.75,
          "ip_annual": 45.00,
          "vm_monthly": 450.00,
          "total_monthly": 453.75,
          "total_annual": 5445.00
        },
        "waste_costs": {
          "unused_ip_count": 557,
          "waste_percentage": 69.6,
          "monthly_cost": 8.71,
          "annual_cost": 104.52
        },
        "optimization_savings": {
          "maxpods_reduction": {
            "from": 110,
            "to": 60,
            "monthly_savings": 6.25,
            "annual_savings": 75.00
          },
          "node_consolidation": {
            "removable_nodes": 2,
            "monthly_savings": 112.50,
            "annual_savings": 1350.00
          }
        },
        "total_potential_savings": {
          "monthly": 118.75,
          "annual": 1425.00,
          "three_year": 4275.00
        },
        "roi_analysis": {
          "implementation_cost": 800.00,
          "payback_period_months": 6.7,
          "three_year_roi_percentage": 534,
          "implementation_effort": "MEDIUM"
        },
        "cost_projections": {
          "year_1": {
            "current_trajectory": 5445.00,
            "optimized": 3870.00,
            "savings": 1575.00
          },
          "year_2": {...},
          "year_3": {...}
        },
        "summary": {
          "status": "HIGH",
          "message": "HIGH financial impact - Optimization recommended"
        }
      }
    }
  }
}
```

## Understanding ROI

### Payback Period

Time to recover implementation cost through savings:

```
Payback Period (months) = Implementation Cost / Monthly Savings

Example:
- Implementation Cost: $800 (2 days @ $400/day)
- Monthly Savings: $118.75
- Payback Period: 800 / 118.75 = 6.7 months
```

**Interpretation**:
- < 6 months: Excellent ROI
- 6-12 months: Good ROI
- 12-24 months: Fair ROI
- > 24 months: Consider other priorities

### 3-Year ROI Percentage

Total return as percentage of implementation cost:

```
3-Year ROI % = (3-Year Savings / Implementation Cost) × 100

Example:
- 3-Year Savings: $4,275
- Implementation Cost: $800
- ROI: (4275 / 800) × 100 = 534%
```

**Interpretation**:
- > 300%: Excellent return
- 200-300%: Good return
- 100-200%: Fair return
- < 100%: Marginal return

### Implementation Effort

Estimated effort level for implementing optimizations:

| Level | Description | Typical Time | Cost Estimate |
|-------|-------------|--------------|---------------|
| LOW | Simple config changes | 2-4 hours | $200-400 |
| MEDIUM | Create new node pools, migrate pods | 1-2 days | $800-1600 |
| HIGH | Complex migration, subnet changes | 3-5 days | $2400-4000 |

**Factors**:
- Number of node pools affected
- Whether subnet changes are needed
- Pod migration complexity
- Testing and validation requirements

## Business Use Cases

### 1. Executive Reporting

**Question**: "How much are we wasting on unused IP addresses?"

**Answer from Cost Analysis**:
```
Current Annual Spend: $5,550
Annual IP Waste: $104.52 (1.9% of total)
Potential 3-Year Savings: $313.56
ROI: 1567% (6.7 month payback)
```

**Action**: Present markdown or HTML report to management showing clear ROI.

### 2. Budget Planning

**Question**: "Should we invest in cluster optimization this quarter?"

**Cost Analysis Provides**:
- Current wastage rate and trend
- Projected savings over budget period
- Implementation cost vs. savings
- Payback timeline

**Decision Framework**:
- Waste > 20% + Payback < 12 months → Approve
- Waste 10-20% + Payback < 24 months → Consider
- Waste < 10% → Monitor, optimize other areas first

### 3. Technical Debt Prioritization

**Question**: "Which optimization projects should we tackle first?"

**Use Cost Analysis To**:
- Compare ROI across clusters
- Identify high-waste, low-effort optimizations
- Justify engineering time allocation

**Example Priority Matrix**:

| Cluster | Waste % | Monthly Savings | Effort | Priority |
|---------|---------|----------------|--------|----------|
| Prod-1  | 69%     | $118          | MEDIUM | HIGH |
| Dev-3   | 45%     | $22           | LOW    | MEDIUM |
| Test-2  | 15%     | $8            | HIGH   | LOW |

### 4. FinOps Integration

Track cost optimization over time:

```bash
# Run monthly and compare trends
python src/main.py ... --include-cost-analysis --output month-$(date +%Y-%m).json

# Compare month-over-month
jq '.diagnostics.cost_analysis.details.waste_costs' month-*.json
```

**Key Metrics to Track**:
- Waste percentage trend
- Actual vs. projected savings
- New waste introduced by deployments
- ROI achievement rate

## Optimization Strategies

Based on cost analysis results:

### Quick Wins (< 1 day)

**Target**: Low implementation effort, fast payback

1. **Reduce maxPods on Underutilized Node Pools**
   - Identify pools with < 50% pod utilization
   - Calculate optimal maxPods based on actual usage
   - Update node pool configuration
   - Estimated savings: 10-30% of IP costs

2. **Remove Idle Nodes**
   - Find nodes with < 10 pods
   - Drain and delete
   - Let autoscaler recreate if needed
   - Estimated savings: Full VM + IP costs per node

### Medium Wins (1-2 weeks)

**Target**: Moderate effort, good ROI

1. **Create Right-Sized Node Pools**
   - Design new pools with optimal maxPods (30-50)
   - Gradually migrate workloads
   - Delete old oversized pools
   - Estimated savings: 30-50% of IP costs

2. **Implement Pod Bin Packing**
   - Use node affinity / anti-affinity
   - Consolidate pods on fewer nodes
   - Scale down node count
   - Estimated savings: 20-40% of total costs

### Strategic Wins (1-3 months)

**Target**: High effort, transformational change

1. **Subnet Rightsizing**
   - Plan new subnet with appropriate CIDR
   - Create new node pools in new subnet
   - Complete workload migration
   - Delete old infrastructure
   - Estimated savings: 50-70% of IP costs

2. **Multi-Cluster Strategy**
   - Separate dev/test from production
   - Use smaller maxPods for non-prod
   - Optimize each cluster independently
   - Estimated savings: 40-60% overall

## API Reference

### CostAnalyzer Class

```python
from analytics.cost_analyzer import CostAnalyzer, AzurePricing

# Initialize
analyzer = CostAnalyzer(region='eastus')

# Check pricing
pricing = analyzer.pricing
print(f"IP cost: ${pricing.ip_per_month}/month")
print(f"Free tier: {pricing.free_ips} IPs")

# Calculate IP waste cost
waste_cost = analyzer.calculate_ip_waste_cost(
    total_ips_reserved=800,
    total_ips_used=243
)
print(f"Monthly waste: ${waste_cost['monthly_cost']:.2f}")
print(f"Waste percentage: {waste_cost['waste_percentage']:.1f}%")

# Calculate optimization savings
savings = analyzer.calculate_optimization_savings(
    current_maxpods=110,
    recommended_maxpods=60,
    node_count=8
)
print(f"Monthly savings: ${savings['monthly']:.2f}")

# Full cluster analysis
cost_report = analyzer.analyze_cluster_costs({
    'cluster_name': 'prod-cluster',
    'subnet_capacity': {...},
    'node_analysis': [...],
    'pod_ip_analysis': {...},
    'recommendations': [...]
})
```

### Helper Functions

```python
from analytics.cost_analyzer import format_currency

# Format monetary values
print(format_currency(1234.56))  # "$1,234.56"
print(format_currency(0.05))      # "$0.05"
print(format_currency(1000000))   # "$1,000,000.00"
```

## Limitations

### Current Limitations

1. **VM Pricing Estimates**:
   - Uses approximate VM costs
   - Actual costs may vary with reservations/spot instances
   - IP costs are accurate, VM costs are informational

2. **Regional Pricing**:
   - Currently uses single IP price for all regions
   - Some regions may have different pricing
   - Future: Load region-specific pricing from Azure API

3. **Additional Costs Not Included**:
   - Storage costs
   - Network egress
   - Load balancer costs
   - These don't relate to IP waste

4. **Implementation Cost Estimates**:
   - Based on typical scenarios
   - Your actual effort may vary
   - Consider as rough guidance, not exact

### Future Enhancements

- [ ] Real-time Azure pricing API integration
- [ ] Support for reserved instances in VM cost
- [ ] Spot instance pricing considerations
- [ ] Historical cost trend analysis
- [ ] Cost anomaly detection
- [ ] Budget threshold alerts
- [ ] Multi-cluster cost aggregation
- [ ] Cost allocation by namespace/label
- [ ] Integration with Azure Cost Management

## Troubleshooting

### Cost Analysis Skipped

**Error**: "Cost analysis failed: 'node_analysis' key not found"

**Solution**: Cost analysis requires pod-level analysis. Add `--include-pod-analysis`:

```bash
python src/main.py ... --include-pod-analysis --include-cost-analysis
```

### Zero or Negative Costs

**Issue**: Cost report shows $0.00 for everything

**Causes**:
1. Cluster has < 50 IPs (within free tier)
2. No pod-level data available
3. Error reading subnet capacity

**Debug**:
```bash
# Check if pod analysis is working
python src/main.py ... --include-pod-analysis --format text | grep "Pod IP Analysis"

# Check subnet capacity
python src/main.py ... --format json-pretty | jq '.diagnostics.subnet_capacity'
```

### Incorrect Savings Estimates

**Issue**: Savings seem too high or too low

**Causes**:
1. VM cost estimates may not match your pricing
2. Implementation effort may vary
3. ROI calculation uses assumptions

**Recommendation**:
- Focus on IP waste costs (most accurate)
- Verify VM costs against Azure portal
- Adjust implementation cost estimates for your team

## Best Practices

### 1. Run Regularly

```bash
# Monthly cost tracking
crontab -e
0 0 1 * * cd /path/to/aks-ip-diagnostic && \
  python src/main.py ... --include-cost-analysis \
  --output reports/cost-$(date +\%Y-\%m).json
```

### 2. Set Thresholds

```bash
# Alert on high waste
WASTE=$(jq '.diagnostics.cost_analysis.details.waste_costs.waste_percentage' report.json)
if (( $(echo "$WASTE > 30" | bc -l) )); then
  send_alert "High IP waste: ${WASTE}%"
fi
```

### 3. Track Progress

```bash
# Compare before/after optimization
python src/main.py ... --include-cost-analysis --output before.json
# [implement optimizations]
python src/main.py ... --include-cost-analysis --output after.json

# Calculate actual savings
jq -s '.[0].diagnostics.cost_analysis.details.waste_costs.monthly_cost - 
       .[1].diagnostics.cost_analysis.details.waste_costs.monthly_cost' \
  before.json after.json
```

### 4. Document Decisions

Keep cost reports with infrastructure documentation:

```
infrastructure/
├── docs/
│   ├── cost-analysis-2024-01.json
│   ├── optimization-plan.md
│   └── savings-report-q1.md
├── terraform/
└── helm/
```

## Further Reading

- [Pod-Level Analysis](POD_LEVEL_ANALYSIS.md) - Understanding IP waste metrics
- [Safety Guarantees](SAFETY_GUARANTEES.md) - Confirmation of read-only operations
- [JSON Output Guide](JSON_OUTPUT_GUIDE.md) - Working with JSON reports
- [Azure IP Pricing](https://azure.microsoft.com/pricing/details/virtual-network/)
- [AKS Best Practices](https://docs.microsoft.com/azure/aks/best-practices)

## Support

For issues or questions:
- GitHub Issues: [repository-url]/issues
- Documentation: docs/
- Examples: examples/cost_analysis_demo.py
