# Documentation index

The README is the user-facing entry point. Detailed operational and engineering guidance lives under `docs/`.

| File | Audience | Purpose |
|---|---|---|
| `ARCHITECTURE.md` | Maintainers | Execution flow, module ownership, and extension rules |
| `PRODUCTION_REVIEW.md` | Maintainers and release owners | Prioritised production-readiness findings and recommended sequence |
| `PRODUCTION_READINESS.md` | Operators and release owners | Release gate, permissions, safety rules, and runtime checks |
| `JSON_OUTPUT_GUIDE.md` | Automation users | JSON validation, conversion, redaction, and pipeline usage |
| `POD_LEVEL_ANALYSIS.md` | Maintainers | Intended pod-analysis behaviour and RBAC; not yet wired into the active scan |
| `COST_ANALYSIS_GUIDE.md` | Maintainers and users | Cost-model assumptions and caveats; detailed analysis is not yet wired into the active scan |
| `TROUBLESHOOTING.md` | Operators | Common authentication, permissions, output, and validation problems |
| `RELEASE_GUIDE.md` | Release owners | Versioning and publication process |
| `HELM_CHART_GUIDE.md` | Platform teams | Optional CronJob deployment guidance |
| `CODE_QUALITY_NOTES.md` | Contributors | Local quality checks and test strategy |
| `REFACTORING_NOTES.md` | Maintainers | Historical refactor context |

## Documentation rules

- Document implemented behaviour separately from planned behaviour.
- Keep command examples consistent with the live CLI help.
- Update the JSON schema and examples whenever report fields change.
- Keep versions aligned in `pyproject.toml`, package metadata, and Helm files.
- Do not describe a release as production-ready until the release gate and Priority 0 review items pass.
- Review redaction and data-handling guidance whenever new report fields are added.
