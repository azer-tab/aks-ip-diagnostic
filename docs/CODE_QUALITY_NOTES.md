# Code quality notes

This project should pass the same checks locally and in CI before a release is tagged or an image is published.

## Required checks

```bash
python -m compileall -q src tests examples
pytest -q
ruff check .
ruff format --check .
bandit -r src -x tests
pip-audit
```

CI also builds the Docker image.

## Current test strategy

The tests are intentionally split across:

- Azure/Kubernetes client wrapper behavior
- diagnostic rule behavior
- production CLI behavior
- pod-level analysis behavior
- orchestrator/report-format behavior

The orchestrator tests are important because they prove the scan workflow can run against fake collectors without live Azure credentials. Do not remove them to make CI pass. If a formatter label, report shape, or diagnostic contract changes, update the implementation and tests together.

## Recent CI blocker

The failing orchestrator-related test was caused by stale text-output expectations. The test expected operator-facing section labels such as `Subnet / CIDR capacity` and `Node pools`, while the formatter still emitted older headings. The formatter now emits labels aligned with the README and refactoring notes, and the full local pytest suite passes.

## How to handle future failing tests

Use this order of preference:

1. Fix implementation regressions.
2. Update stale fixtures or assertions when behavior changed intentionally.
3. Split overly broad tests into smaller tests.
4. Mark a test with a reason only when the feature is genuinely not implemented yet.
5. Delete a test only when the behavior is removed from the product and the docs are updated accordingly.

Removing tests simply to unblock CI hides product risk and makes later refactors harder.

## Pod analysis refactor notes

The pod-level analyzer should keep collection and calculation separate:

- `get_all_pods()` performs read-only Kubernetes pod collection.
- `get_all_nodes()` performs read-only Kubernetes node collection.
- `analyze_pod_distribution(pods, nodes)` calculates distribution from supplied fixtures or collected data.
- `analyze_by_node(pods, nodes)` derives per-node capacity from Kubernetes `status.allocatable.pods`.
- `calculate_pod_density(pods, nodes)` counts running pods for active density metrics.

This design keeps the module testable with plain Python dictionaries and avoids requiring a live AKS cluster for unit tests.
