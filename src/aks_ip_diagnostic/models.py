"""Typed runtime models used by the production CLI.

The original project passed a large argparse.Namespace through most of the
program.  These dataclasses make the scan contract explicit and keep the rest
of the code independent from argparse.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScanConfig:
    """Configuration for one diagnostic scan.

    This is intentionally small and serializable.  Anything specific to the
    command-line parser should be translated into this object before the scan
    starts, so the diagnostic engine can be tested without invoking argparse.
    """

    subscription_id: str
    resource_group: str
    cluster_name: str
    output_format: str = "text"
    output: str | None = None
    include_pod_analysis: bool = False
    include_cost_analysis: bool = False
    region: str = "eastus"
    pod_lifecycle: bool = False
    kubeconfig: str | None = None
    redact: bool = False
    validate_schema: bool = False
    verbose: bool = False

    @classmethod
    def from_args(cls, args: Any) -> ScanConfig:
        """Create a scan configuration from an argparse namespace.

        Keeping this translation in one place avoids leaking argparse-specific
        defaults and attribute lookups into the orchestrator.
        """

        return cls(
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
            cluster_name=args.cluster_name,
            output_format=getattr(args, "format", "text"),
            output=getattr(args, "output", None),
            include_pod_analysis=getattr(args, "include_pod_analysis", False),
            include_cost_analysis=getattr(args, "include_cost_analysis", False),
            region=getattr(args, "region", "eastus"),
            pod_lifecycle=getattr(args, "pod_lifecycle", False),
            kubeconfig=getattr(args, "kubeconfig", None),
            redact=getattr(args, "redact", False),
            validate_schema=getattr(args, "validate_schema", False),
            verbose=getattr(args, "verbose", False),
        )


@dataclass(frozen=True)
class AzureSubnetReference:
    """Parsed reference to an Azure subnet resource."""

    resource_group: str
    vnet_name: str
    subnet_name: str

    @property
    def key(self) -> str:
        return f"{self.resource_group}/{self.vnet_name}/{self.subnet_name}"


@dataclass(frozen=True)
class ScanResult:
    """Result of a scan before it is formatted for humans or machines."""

    report: dict[str, Any]
    output_path: Path | None = None
