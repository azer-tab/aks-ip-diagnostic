# Production-readiness review

Review date: 2026-07-27  
Reviewed version: `0.3.3`

## Overall assessment

The project is a useful pre-production diagnostic CLI with a sensible read-only intent and a clearer package structure than a single-script prototype. It is not yet ready for a production support commitment.

The most important risk is the difference between advertised capabilities and the active orchestration path. The next release should narrow its claims or finish wiring those capabilities before broader adoption.

## Changes made during this review

- Rewrote the README and quick-start guide around the behaviour that exists today.
- Added an architecture guide and this prioritised review.
- Restored active orchestrator and text-format tests.
- Enabled `pytest` and `pip-audit` in CI and release workflows.
- Added read-only workflow permissions, tag/version verification, and an explicit Docker Hub publish guard.
- Aligned the generated report schema with the current report shape while retaining the older `max_pods` diagnostic alias.
- Corrected generated `metadata.tool_version` to use the package version.
- Corrected generated-schema failures to return exit code `5`.
- Normalised canonical issue counting and aligned provisioning/maxPods diagnostic severities with their issue thresholds.
- Removed duplicate and unclear headings from text output.
- Changed tests to import installed package names rather than `src.*` aliases.

## Priority 0: release blockers

### 1. Optional feature flags do not execute their named features

`--include-pod-analysis` and `--include-cost-analysis` add diagnostics with status `SKIPPED`. `--pod-lifecycle`, `--kubeconfig`, and the selected `--region` are not used by the active scan workflow.

**Action:** either wire the existing modules into the orchestrator with tests and failure isolation, or remove/hide the flags until implementation is complete.

### 2. No integration-level Azure contract test

Unit tests use simple fakes. They do not verify the current Azure SDK object shapes, authentication behaviour, networking-mode variants, throttling, or partial-permission scenarios.

**Action:** add recorded SDK fixtures or a dedicated non-production Azure test environment. Cover at least Azure CNI, overlay/managed pod CIDR, autoscaling, multiple subnets, missing permissions, and failed provisioning.

### 3. Cost output is not suitable for operational or financial decisions

The active summary always includes heuristic cost values from a static table. The table is labelled for France Central, unknown VM sizes silently default to a fixed amount, private-IP “cost” is modelled as an estimated overhead, and the CLI region is not passed into the calculation.

**Action:** clearly mark all cost fields as heuristic, disable them by default in the base summary, or replace the table with a versioned pricing provider and explicit “unknown” results. Never substitute arbitrary defaults for unknown SKUs.

### 4. Release publishing lacks sufficient safeguards

The workflow now has an explicit Docker Hub publish guard and verifies the tag against `pyproject.toml`. It still lacks image signing, SBOM generation, explicit provenance verification, immutable deployment references, and protected-environment approval.

**Action:** use protected release environments, publish and record immutable digests, and add signing, SBOM, and provenance controls.

## Priority 1: required before wider internal use

### 5. Dependency resolution is not reproducible

Dependencies use broad ranges and there is no lock or constraints file. CI can resolve different transitive versions on different days.

**Action:** adopt a generated constraints/lock workflow, use dependency update automation, and audit the locked environment.

### 6. Report contract needs compatibility tests

The schema and implementation had drifted. The schema is now aligned, but there are no golden reports or explicit compatibility rules.

**Action:** add representative golden JSON files and tests for validation, conversion, redaction, and backward compatibility. Define whether report schema version `1.0` is stable or experimental.

### 7. Error handling is too broad

Several execution boundaries catch `Exception`, which can hide programming defects and flatten distinct Azure, Kubernetes, validation, and filesystem failures into exit code `3`.

**Action:** catch typed client exceptions, add actionable error messages, preserve causes in debug logs, and test exit-code mapping.

### 8. Capacity calculations need networking-mode-specific contracts

The code uses a mixture of Azure subnet `ip_configurations`, node counts, `maxPods`, and pod-CIDR estimates. These values do not represent the same allocation model in every AKS networking mode.

**Action:** create explicit strategy classes per supported networking mode and document the source, formula, confidence, and limitations of each metric.

### 9. Large modules increase regression risk

`pod_ip_analysis.py`, `formatters.py`, and `orchestrator.py` are large and contain multiple responsibilities.

**Action:** split by capability and add focused tests before wiring optional features.

### 10. Helm output is ephemeral

The CronJob prints text but does not define durable report storage or a forwarding mechanism. A successful job may leave no usable historical artefact after log retention expires.

**Action:** add an explicit output sink design: object storage, persistent volume, log pipeline, or webhook. Avoid embedding secrets in values.

## Priority 2: operational hardening

- Add structured logs with scan IDs and stable event names.
- Add timeouts and retry/backoff policies for Azure and Kubernetes calls.
- Add telemetry that is disabled by default and contains no infrastructure identifiers.
- Add a support matrix for Python, Azure SDK, Kubernetes, AKS versions, and networking modes.
- Add `CONTRIBUTING.md`, a security policy, ownership/CODEOWNERS, and issue templates.
- Add Docker image health/smoke tests and scan the built image.
- Pin GitHub Actions to commit SHAs for higher supply-chain assurance.
- Add licence and source-distribution checks to release CI.

## Recommended release sequence

1. Publish `0.3.x` only as an experimental/internal release.
2. Resolve all Priority 0 items.
3. Add golden report and Azure contract tests.
4. Lock dependencies and harden release publishing.
5. Run a limited pilot against representative clusters.
6. Document supported networking modes and known accuracy limits.
7. Declare a stable report contract before `1.0.0`.
