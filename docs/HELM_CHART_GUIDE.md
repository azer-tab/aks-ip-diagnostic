# Helm chart guide

A Helm chart is optional for this project.

You do not need Helm if users will run the tool from a laptop, a CI job, or a one-off Docker command. Helm becomes useful when you want to run the diagnostic tool inside Kubernetes as a repeatable CronJob with a service account, RBAC, and standardized values.

## When Helm is worth it

Use the chart when you want:

- scheduled scans, for example every night
- reports written to container logs for collection by your log platform
- a consistent in-cluster deployment model
- Kubernetes RBAC managed as code
- Azure Workload Identity or managed identity based authentication

Avoid Helm when:

- the tool is used manually by a small team
- each scan targets a different external cluster
- Azure authentication is not available inside the cluster
- you only need local CLI output

## Chart location

The optional chart is included at:

```text
charts/aks-ip-diagnostic/
```

It deploys a Kubernetes `CronJob` by default. The job runs:

```bash
aks-ip-diagnostic scan ...
```

## Required values

At minimum, set:

```yaml
azure:
  subscriptionId: "<subscription-id>"
  resourceGroup: "<resource-group>"
  clusterName: "<aks-cluster-name>"
```

Set the image repository to your Docker Hub repository:

```yaml
image:
  repository: "<dockerhub-user>/aks-ip-diagnostic"
  tag: "0.3.2"
```

## Install from local chart

```bash
helm lint charts/aks-ip-diagnostic
helm template aks-ip-diagnostic charts/aks-ip-diagnostic \
  --set azure.subscriptionId="<subscription-id>" \
  --set azure.resourceGroup="<resource-group>" \
  --set azure.clusterName="<cluster-name>" \
  --set image.repository="<dockerhub-user>/aks-ip-diagnostic" \
  --set image.tag="0.3.2"

helm install aks-ip-diagnostic charts/aks-ip-diagnostic \
  --namespace aks-ip-diagnostic \
  --create-namespace \
  --set azure.subscriptionId="<subscription-id>" \
  --set azure.resourceGroup="<resource-group>" \
  --set azure.clusterName="<cluster-name>" \
  --set image.repository="<dockerhub-user>/aks-ip-diagnostic" \
  --set image.tag="0.3.2"
```

## Package the chart

```bash
helm package charts/aks-ip-diagnostic --destination dist
```

This creates a file similar to:

```text
dist/aks-ip-diagnostic-0.1.0.tgz
```

## Authentication notes

The chart does not create Azure credentials for you. Use one of these approaches:

1. Azure Workload Identity, recommended for AKS-hosted scheduled scans.
2. Managed identity, when available in your execution environment.
3. Existing Kubernetes secret containing service principal environment variables.

For service principal style authentication, create a secret outside Helm:

```bash
kubectl create secret generic aks-ip-diagnostic-azure \
  --namespace aks-ip-diagnostic \
  --from-literal=AZURE_CLIENT_ID="<client-id>" \
  --from-literal=AZURE_TENANT_ID="<tenant-id>" \
  --from-literal=AZURE_CLIENT_SECRET="<client-secret>"
```

Then set:

```yaml
envFromSecret: aks-ip-diagnostic-azure
```

Do not commit secrets into `values.yaml`.

## Run once instead of waiting for the schedule

```bash
kubectl create job --from=cronjob/aks-ip-diagnostic aks-ip-diagnostic-manual \
  --namespace aks-ip-diagnostic

kubectl logs job/aks-ip-diagnostic-manual --namespace aks-ip-diagnostic
```

## Uninstall

```bash
helm uninstall aks-ip-diagnostic --namespace aks-ip-diagnostic
```

## Helm release answer

A Helm package is not mandatory for this project. It is recommended only if your preferred operating model is scheduled scans inside Kubernetes. For laptop, CI, or Docker-only usage, Docker Hub plus a Python package release is enough.
