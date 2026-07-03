"""Process exit codes for automation-friendly CLI behavior."""

HEALTHY = 0
WARNINGS_FOUND = 1
CRITICAL_ISSUES_FOUND = 2
RUNTIME_ERROR = 3
INVALID_USAGE = 4
VALIDATION_FAILED = 5


def code_for_status(overall_status: str | None) -> int:
    """Map report overall status to a process exit code."""
    status = (overall_status or "").upper()
    if status == "CRITICAL":
        return CRITICAL_ISSUES_FOUND
    if status == "WARNING":
        return WARNINGS_FOUND
    if status == "HEALTHY":
        return HEALTHY
    return RUNTIME_ERROR
