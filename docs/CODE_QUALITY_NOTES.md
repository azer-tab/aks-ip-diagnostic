# Code Quality Notes

This project is expected to pass the same checks locally and in CI before a release is tagged.

## Required local checks

```bash
ruff check .
ruff format --check .
python -m compileall -q src tests examples
pytest -q
```

## Pod analysis refactor notes

The pod-level analyzer previously had several unresolved static-analysis errors caused by a partially merged method:

- pod/node collection logic was mixed with pod-distribution calculations
- `pods`, `nodes`, `allocatable`, and `total_pods` were referenced outside their scope
- Ruff could not safely auto-fix those problems because they were correctness issues, not formatting issues

The corrected structure keeps collection and calculation separate:

- `get_all_pods()` performs the read-only Kubernetes pod collection
- `get_all_nodes()` performs the read-only Kubernetes node collection
- `analyze_pod_distribution(pods, nodes)` calculates distribution from supplied fixtures or collected data
- `analyze_by_node(pods, nodes)` derives per-node capacity from Kubernetes `status.allocatable.pods`
- `calculate_pod_density(pods, nodes)` counts only Running pods for active density metrics

This design makes the module easier to test because every calculation method can be called with plain Python dictionaries and does not need a live AKS cluster.
