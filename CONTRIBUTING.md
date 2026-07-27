# Contributing

## Set up the project

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Run the quality gate

```bash
python -m compileall -q src tests examples
pytest -q
ruff check .
ruff format --check .
bandit -r src -x tests
pip-audit
```

## Change rules

- Keep Azure and Kubernetes access read-only.
- Keep CLI parsing in `aks_ip_diagnostic/cli.py`.
- Keep API calls in collectors or client wrappers.
- Keep diagnostic calculations independent of output formatting.
- Update the JSON schema whenever report fields change.
- Add or update tests for every behaviour change.
- Do not comment out failing tests to make CI pass.
- Document planned behaviour separately from implemented behaviour.

## Adding a diagnostic

1. Put the calculation in `src/diagnostics/`.
2. Return serialisable issue data with stable codes.
3. Integrate it through the orchestrator.
4. Add the diagnostic result to the report schema.
5. Add unit tests and an orchestrator contract test.
6. Update the README and relevant guide.

## Pull requests

Describe:

- the user or operator problem
- the behaviour change
- test evidence
- report-schema impact
- security or permission impact
- backward-compatibility impact
