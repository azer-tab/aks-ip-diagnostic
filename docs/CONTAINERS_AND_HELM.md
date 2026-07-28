# Containers and Helm

## Container versioning

The Python distribution uses `setuptools-scm`, which derives versions from Git tags. Docker builds normally exclude `.git`, so the Dockerfile accepts `APP_VERSION` and exposes it through:

```text
SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AKS_IP_DIAGNOSTIC
```

Release builds should pass the tag without its leading `v`:

```bash
docker build --build-arg APP_VERSION="${GITHUB_REF_NAME#v}" .
```

Without this argument, local builds use the Dockerfile fallback `0.0.0`.

## Authentication

For local container execution, service-principal environment variables are the most predictable authentication mechanism:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_CLIENT_SECRET
```

In Kubernetes, prefer workload identity or another secretless identity mechanism where available. Do not bake credentials into the image or chart values committed to source control.

## Persisting reports

The image runs as an unprivileged user. Mount a writable volume or bind mount and write reports into that mount. For Kubernetes executions, use an appropriate persistent volume, object-storage upload step, or log/report collection mechanism so that reports are not lost when the pod exits.

## What the Helm release job provides

The release job validates the chart and creates a versioned chart archive. This provides:

- repeatable Kubernetes installation manifests
- chart syntax and template validation during releases
- a chart artifact tied to the application release
- a basis for later OCI registry publication

It does not deploy to a cluster. Deployment requires a separate environment-specific workflow with cluster authentication, approval controls, namespace selection, values management, and rollback procedures.

## When to remove the Helm job

Remove the job when there is no supported Kubernetes deployment model or the chart is experimental and should not be emitted as a release artifact. Keeping an unused chart in a release pipeline creates maintenance overhead and can imply support that the project does not actually provide.
