# Code quality notes

## Local checks

```bash
python -m compileall -q src tests examples
pytest -q
ruff check .
ruff format --check .
bandit -r src -x tests
pip-audit
```

The CI workflow runs tests, linting, formatting, compilation, dependency auditing, a static security scan, and a Docker build.

## Test strategy

Keep coverage across these boundaries:

- Azure and Kubernetes client wrappers with injected clients
- diagnostic rule calculations
- CLI commands and exit codes
- report schema, redaction, and conversion
- orchestrator assembly with fake collectors
- text, JSON, Markdown, and HTML rendering contracts

Tests should import package names such as `aks_ip_diagnostic` and `diagnostics`, not `src.*`. This better reflects an installed package.

## Current gaps

- no live or recorded Azure SDK contract tests
- no golden report compatibility suite
- limited negative-path and timeout coverage
- no coverage threshold
- optional pod and detailed cost analysis are not exercised by the active orchestrator

Do not comment out failing tests to unblock CI. Fix implementation regressions or update assertions when a behaviour change is intentional and documented.
