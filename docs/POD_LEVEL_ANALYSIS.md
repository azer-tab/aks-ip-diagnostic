# Pod-level IP usage analysis

Pod-level analysis is optional. It requires Kubernetes API access and gives a more accurate view of how IP capacity is actually being consumed inside the cluster.

## What it adds

When enabled, the tool can inspect:

- pods across all namespaces
- node placement
- pod phases such as Running, Pending, Failed, or Succeeded
- host-network pods
- pods without assigned IPs
- namespace-level distribution
- node-level pod density
- possible stuck or failed pods holding capacity

## Enable pod analysis

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --format text
```

Use a specific kubeconfig if needed:

```bash
aks-ip-diagnostic scan \
  --subscription-id "<subscription-id>" \
  --resource-group "<resource-group>" \
  --cluster-name "<cluster-name>" \
  --include-pod-analysis \
  --kubeconfig ~/.kube/config \
  --format json \
  --output reports/pod-analysis.json
```

## Required Kubernetes permissions

The caller needs read-only access:

```bash
kubectl auth can-i list nodes
kubectl auth can-i list namespaces
kubectl auth can-i list pods --all-namespaces
```

Least-privilege ClusterRole example:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: aks-ip-diagnostic-readonly
rules:
  - apiGroups: [""]
    resources: ["pods", "nodes", "namespaces"]
    verbs: ["get", "list"]
```

## How to interpret results

| Finding | Meaning | Recommended investigation |
|---|---|---|
| High pod density | Nodes are close to configured pod capacity | Review node-pool scale-out limits and workload placement |
| Low pod density with high `maxPods` | Possible IP over-reservation | Review whether `maxPods` is too high for this node pool |
| Many pending pods | Scheduling, capacity, quota, or IP pressure may exist | Check events, autoscaler, quotas, and node conditions |
| Failed/stuck pods | Workload lifecycle may be wasting capacity | Review controllers, cleanup policies, and failed jobs |
| Host-network pods | These may not consume normal pod IPs | Separate them from pod IP pressure calculations |

## Limitations

- Pod-level analysis depends on Kubernetes API availability and RBAC.
- The scan is a point-in-time snapshot.
- Short-lived pods may appear or disappear during collection.
- Some networking modes can change how pod IPs are allocated and reported.
- The tool is diagnostic only; it does not delete pods or change scheduling.

## Recommended production use

For periodic reporting, run pod-level analysis from an environment with stable Kubernetes credentials. If you run it inside AKS, use the optional Helm chart and a read-only service account.
