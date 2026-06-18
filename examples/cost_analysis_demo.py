"""
Cost Analysis Demo

This script demonstrates how to use the cost analysis features
to calculate IP waste costs and optimization savings for your AKS cluster.

Cost analysis helps translate technical IP waste metrics into business value
by showing actual dollar amounts being wasted and potential ROI from optimizations.

Key Metrics:
- IP Waste Costs: Monthly/annual cost of unused IP addresses
- Optimization Savings: Potential savings from reducing maxPods
- ROI Analysis: Payback period and 3-year return on investment
- Cost Projections: Future cost trends based on current usage

Azure IP Pricing:
- First 50 IPs: Free
- Additional IPs: $0.005 per IP per month
- Varies by region (use --region to specify)

Usage Examples:
--------------

1. Basic cost analysis:
   python src/main.py \
     --subscription-id "your-sub-id" \
     --resource-group "your-rg" \
     --cluster-name "your-cluster" \
     --include-pod-analysis \
     --include-cost-analysis \
     --format text

2. Cost analysis with specific region pricing:
   python src/main.py \
     --cluster-name "prod-cluster" \
     --include-pod-analysis \
     --include-cost-analysis \
     --region westus2 \
     --format json-pretty \
     --output cost-report.json

3. Export cost data for executive reporting:
   python src/main.py \
     --cluster-name "prod-cluster" \
     --include-pod-analysis \
     --include-cost-analysis \
     --format markdown \
     --output cost-executive-summary.md

Output Interpretation:
---------------------

Current Monthly Costs:
  - Shows baseline spending on IPs and VM compute
  - Helps establish budget context

IP Waste Costs:
  - Money being spent on unused/wasted IP addresses
  - Key metric for justifying optimization work
  - Threshold: >20% waste is considered HIGH impact

Total Potential Savings:
  - Maximum savings possible from all optimizations
  - Includes: maxPods reduction, node consolidation, subnet rightsizing
  - Shows monthly, annual, and 3-year projections

ROI Analysis:
  - Payback Period: How long until savings offset implementation cost
  - Implementation Effort: Estimated time to implement (LOW/MEDIUM/HIGH)
  - 3-Year ROI: Total return as percentage of implementation cost
  - Helps prioritize optimization projects

Example Output:
--------------

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

Recommendations:
---------------

1. Start with Quick Wins:
   - Review nodes with <50% pod utilization
   - Consider reducing maxPods on underutilized node pools
   - Estimated effort: 2-4 hours
   - Payback: Usually 1-3 months

2. Plan Major Optimizations:
   - Subnet rightsizing requires careful planning
   - Consider creating new node pools with optimal maxPods
   - Migrate workloads gradually to minimize disruption
   - Estimated effort: 1-2 days
   - Payback: 3-6 months

3. Monitor Regularly:
   - Run cost analysis monthly to track improvements
   - Watch for new IP waste as workloads change
   - Set alerts for >20% waste threshold

4. Document Savings:
   - Keep reports for management/finance teams
   - Track actual savings vs. projections
   - Use for budget planning and optimization roadmap

Business Value:
--------------

Cost analysis transforms technical metrics into business language:
- "69% IP waste" becomes "$104.52/year wasted"
- "Reduce maxPods" becomes "$313.56 saved over 3 years"
- "Complex migration" becomes "1567% ROI"

This helps:
- Justify optimization work to management
- Prioritize technical debt remediation
- Demonstrate value of infrastructure engineering
- Support budget requests for automation tools

Safety Guarantees:
-----------------

Cost analysis is 100% read-only:
✓ Only calculates costs based on current state
✓ Never modifies cluster configuration
✓ Never changes node pools or subnets
✓ Never deploys or deletes resources
✓ Safe to run in production

See docs/SAFETY_GUARANTEES.md for complete details.

API Usage:
----------

You can also use the CostAnalyzer programmatically:

```python
from analytics.cost_analyzer import CostAnalyzer

# Initialize with region
analyzer = CostAnalyzer(region='eastus')

# Prepare diagnostic data
diagnostic_data = {
    'cluster_name': 'my-cluster',
    'resource_group': 'my-rg',
    'subnet_capacity': {...},
    'node_analysis': [...],
    'pod_ip_analysis': {...},
    'recommendations': [...]
}

# Run analysis
cost_report = analyzer.analyze_cluster_costs(diagnostic_data)

# Access specific metrics
print(f"Monthly waste: ${cost_report['waste_costs']['monthly_cost']:.2f}")
print(f"Annual savings: ${cost_report['total_potential_savings']['annual']:.2f}")
print(f"ROI: {cost_report['roi_analysis']['three_year_roi_percentage']:.0f}%")
```

Integration with CI/CD:
----------------------

You can automate cost tracking in your pipeline:

```yaml
# Azure DevOps example
- task: AzureCLI@2
  displayName: 'Run AKS Cost Analysis'
  inputs:
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      python src/main.py \
        --cluster-name $(AKS_CLUSTER) \
        --include-pod-analysis \
        --include-cost-analysis \
        --format json-pretty \
        --output $(Build.ArtifactStagingDirectory)/cost-report.json
      
      # Fail build if waste > 30%
      WASTE_PCT=$(jq '.diagnostics.cost_analysis.details.waste_costs.waste_percentage' \
        $(Build.ArtifactStagingDirectory)/cost-report.json)
      
      if (( $(echo "$WASTE_PCT > 30" | bc -l) )); then
        echo "##vso[task.logissue type=warning]High IP waste detected: ${WASTE_PCT}%"
      fi

- task: PublishBuildArtifacts@1
  displayName: 'Publish Cost Report'
  inputs:
    pathToPublish: '$(Build.ArtifactStagingDirectory)/cost-report.json'
    artifactName: 'cost-analysis'
```

Further Reading:
---------------

- Azure IP Pricing: https://azure.microsoft.com/pricing/details/virtual-network/
- AKS Networking: https://docs.microsoft.com/azure/aks/concepts-network
- Pod IP Analysis: docs/POD_LEVEL_ANALYSIS.md
- JSON Output Guide: docs/JSON_OUTPUT_GUIDE.md
- Safety Guarantees: docs/SAFETY_GUARANTEES.md

For questions or issues:
- GitHub Issues: <repository-url>/issues
- Documentation: docs/
"""

if __name__ == "__main__":
    print(__doc__)
    print("\n" + "="*80)
    print("To run cost analysis, use the main.py script with --include-cost-analysis")
    print("="*80)
