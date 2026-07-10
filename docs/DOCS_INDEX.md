# Documentation index

The README is the main entry point. The files in `docs/` hold operational details that would make the README too long.

## Documentation map

| File | Purpose | Keep updated when |
|---|---|---|
| `PRODUCTION_READINESS.md` | Release gates, read-only safety model, permissions, and operational checks. | CI, security posture, permissions, or release process changes. |
| `REFACTORING_NOTES.md` | Explains the CLI, scan runner, orchestrator, collector, and formatter responsibilities. | Module boundaries or execution flow change. |
| `JSON_OUTPUT_GUIDE.md` | Documents report formats, validation, conversion, redaction, and automation usage. | Report shape, output formats, or schema behavior changes. |
| `POD_LEVEL_ANALYSIS.md` | Explains optional Kubernetes API based pod analysis and RBAC. | Pod analysis behavior or Kubernetes permissions change. |
| `COST_ANALYSIS_GUIDE.md` | Explains estimated cost/capacity-waste analysis and caveats. | Cost model assumptions or output fields change. |
| `RELEASE_GUIDE.md` | Docker Hub, Python package, GitHub release, and versioning process. | Versioning, publishing, or release automation changes. |
| `HELM_CHART_GUIDE.md` | Optional Helm/CronJob deployment guidance. | Chart values, image tags, auth model, or chart templates change. |
| `CODE_QUALITY_NOTES.md` | Local quality gates and notes from recent test/refactor cleanup. | CI failures, test strategy, or local quality commands change. |

## Documentation rules

- Keep quick-start commands in `README.md` and `QUICKSTART.md` consistent.
- Keep version references aligned across `pyproject.toml`, `src/aks_ip_diagnostic/__init__.py`, `charts/aks-ip-diagnostic/Chart.yaml`, and chart values.
- Do not document a release as ready until tests and CI release gates pass.
- Do not commit generated reports unless they are intentionally sanitized examples.
- Prefer updating an existing document over adding a new one unless the content is a reusable runbook.

## Pre-release documentation checklist

```bash
python -m compileall -q src tests examples
pytest -q
aks-ip-diagnostic --help
aks-ip-diagnostic scan --help
aks-ip-diagnostic version
```

Then review:

- command examples still match the CLI
- output sections and JSON fields match current formatter behavior
- CI commands match `.github/workflows/ci.yml`
- release version examples match the package and chart
- permission examples remain read-only and least-privilege
- redaction guidance is present anywhere report sharing is discussed
