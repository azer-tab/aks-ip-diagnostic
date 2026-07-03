"""Redaction helpers for report data and formatted output."""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEYS = {
    "subscription_id",
    "resource_group",
    "cluster_name",
    "name",
    "node_name",
    "pod_name",
    "namespace",
    "principal_id",
    "client_id",
    "tenant_id",
    "object_id",
    "tags",
    "id",
    "vnet_subnet_id",
    "subnet_id",
}

IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:/\d{1,2})?\b"
)
AZURE_RESOURCE_ID_RE = re.compile(r"/subscriptions/[^\s\"']+", re.IGNORECASE)


def _stable_token(value: Any, label: str) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"<redacted:{label}:{digest}>"


def _redact_string(value: str) -> str:
    value = AZURE_RESOURCE_ID_RE.sub("<redacted:azure-resource-id>", value)
    value = IPV4_RE.sub("<redacted:ip-address>", value)
    return value


def redact_value(value: Any, key: str | None = None) -> Any:
    """Return a redacted copy of a value."""
    normalized_key = (key or "").lower()

    if normalized_key in SENSITIVE_KEYS:
        if value in (None, ""):
            return value
        return _stable_token(value, normalized_key)

    if isinstance(value, str):
        return _redact_string(value)

    if isinstance(value, Mapping):
        return {k: redact_value(v, str(k)) for k, v in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_value(item, key) for item in value]

    return value


def redact_report(report_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a recursively redacted report dictionary."""
    return redact_value(copy.deepcopy(dict(report_data)))
