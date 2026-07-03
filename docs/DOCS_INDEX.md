# Documentation index

The `docs/` folder is useful and should stay in the repository. The README is the quick entry point; these files cover operational details that would make the README too long.

## Recommended docs to keep

| File | Purpose | Keep? |
|---|---|---|
| `PRODUCTION_READINESS.md` | Release gates, security posture, permissions, and operational checks. | Yes |
| `REFACTORING_NOTES.md` | Explains the new architecture after the main-file refactor. | Yes |
| `JSON_OUTPUT_GUIDE.md` | Documents stable report formats, validation, conversion, and automation usage. | Yes |
| `POD_LEVEL_ANALYSIS.md` | Explains the optional Kubernetes API based pod analysis. | Yes |
| `COST_ANALYSIS_GUIDE.md` | Explains cost and waste estimates with caveats. | Yes |
| `RELEASE_GUIDE.md` | Docker Hub, Python package, GitHub release, and versioning process. | Yes |
| `HELM_CHART_GUIDE.md` | Optional Helm/CronJob deployment guidance. | Yes, if you want scheduled in-cluster scans |

## When to add new docs

Add a new document only when the content is too detailed for `README.md` or when it is a reusable operational runbook. Otherwise, prefer updating the README.

## Documentation update checklist

Before a release, check that:

```bash
python -m compileall -q src tests
pytest -q
aks-ip-diagnostic --help
aks-ip-diagnostic version
```

Then review:

- command examples still match the CLI
- version numbers match `pyproject.toml`, `src/aks_ip_diagnostic/__init__.py`, and the Helm chart if changed
- Docker image names in examples use your real Docker Hub namespace
- security and permission examples are still least-privilege
- generated reports are not committed unless they are sanitized examples

- `CODE_QUALITY_NOTES.md` - local quality gates and notes from the pod-analysis refactor.
