# Cost analysis guide

Cost analysis is optional and should be treated as an estimate. It is designed to help platform teams prioritize IP capacity and node-pool configuration work; it is not a replacement for Azure billing data.

## Important billing caveat

Do not assume that every private AKS pod IP has a direct per-IP Azure charge. The useful cost signal in this tool is mainly operational waste and capacity pressure:

- oversized `maxPods` values reserve more IP capacity than workloads actually need
- exhausted subnets force disruptive network changes or cluster/node-pool redesign
- low pod density may indicate avoidable node or subnet expansion
- waste can create indirect cost by accelerating subnet growth, cluster rebuilds, or node-pool fragmentation

Financial output should be labelled as estimated and validated against current Azure pricing, your billing exports, and your internal cost model before making business decisions.

## What the analysis tries to estimate

The cost model can help answer:

- how many IPs appear reserved versus actively used
- how much capacity may be wasted by current node-pool settings
- whether reducing `maxPods` could delay subnet exhaustion
- which node pools deserve optimization first
- how much operational risk exists if growth continues

## Required inputs

For meaningful cost analysis, enable pod-level analysis so the tool can compare real pod usage to configured capacity:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --include-cost-analysis \
  --format text
```

## Core formulas

The simplified IP capacity model is:

```text
Reserved IP capacity per node ~= maxPods + node/system overhead
Estimated wasted IP capacity = reserved IP capacity - observed pod IP usage
Waste percentage = estimated wasted IP capacity / reserved IP capacity
```

The exact behavior can vary by AKS networking mode, CNI configuration, subnet layout, and Kubernetes scheduling patterns. Use the result as a decision-support signal, not as an exact billing statement.

## Recommended interpretation

| Signal | Meaning | Action |
|---|---|---|
| High waste, low pod density | Node pools may be over-provisioned for IP capacity | Review `maxPods`, autoscaling, and workload placement |
| High utilization, low free subnet capacity | Subnet exhaustion risk | Plan subnet expansion or node-pool/network redesign |
| High pending/stuck pods | IPs may be held by unhealthy workload states | Investigate workload lifecycle and scheduling failures |
| Imbalanced pod placement | Some nodes consume more capacity than others | Review taints, affinities, topology spread, and autoscaler behavior |

## Safer reporting language

Use these phrases in reports and presentations:

- estimated capacity waste
- estimated optimization opportunity
- potential avoided subnet pressure
- operational risk reduction

Avoid claiming exact cost savings unless you have validated the numbers against billing exports or current pricing data.

## Example workflow

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --include-cost-analysis \
  --format json \
  --output reports/cost-report.json

aks-ip-diagnostic convert reports/cost-report.json \
  --format markdown \
  --redact \
  --output reports/cost-report-redacted.md
```

## Production recommendation

For production use, make the cost model configurable before using it for financial commitments. A future enhancement should support:

- external pricing configuration
- organization-specific chargeback rates
- region-specific assumptions
- billing export correlation
- explicit pricing-source metadata in the report
