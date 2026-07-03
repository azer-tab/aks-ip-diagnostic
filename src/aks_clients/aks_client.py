"""Read-only Azure AKS client wrapper."""

from __future__ import annotations

import logging
from typing import Any

from .exceptions import AzureResourceLookupError


class AKSClient:
    """Small read-only wrapper around Azure ContainerServiceClient."""

    def __init__(
        self, subscription_id: str, credential: Any | None = None, client: Any | None = None
    ):
        self.subscription_id = subscription_id
        self.logger = logging.getLogger(__name__)
        if client is not None:
            self.credential = credential
            self.client = client
            return
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.containerservice import ContainerServiceClient
        except ImportError as exc:
            raise RuntimeError(
                "Azure SDK dependencies are not installed. Install the project with the azure extra or requirements.txt."
            ) from exc
        self.credential = credential or DefaultAzureCredential()
        self.client = ContainerServiceClient(self.credential, self.subscription_id)

    def get_cluster(self, resource_group_name: str, cluster_name: str) -> Any:
        """Get a raw AKS managed cluster object from Azure."""
        try:
            return self.client.managed_clusters.get(resource_group_name, cluster_name)
        except Exception as exc:
            message = f"Unable to read AKS cluster '{cluster_name}' in resource group '{resource_group_name}': {exc}"
            self.logger.error(message)
            raise AzureResourceLookupError(message) from exc

    def get_cluster_info(self, resource_group_name: str, cluster_name: str) -> dict[str, Any]:
        """Get selected cluster metadata as a dictionary."""
        cluster = self.get_cluster(resource_group_name, cluster_name)
        return {
            "name": getattr(cluster, "name", None),
            "location": getattr(cluster, "location", None),
            "node_resource_group": getattr(cluster, "node_resource_group", None),
            "dns_prefix": getattr(cluster, "dns_prefix", None),
            "agent_pool_profiles": getattr(cluster, "agent_pool_profiles", None),
        }

    def list_node_pools(self, resource_group_name: str, cluster_name: str) -> list[Any]:
        """List raw AKS node pool objects."""
        try:
            return list(self.client.agent_pools.list(resource_group_name, cluster_name))
        except Exception as exc:
            message = f"Unable to list AKS node pools for '{cluster_name}': {exc}"
            self.logger.error(message)
            raise AzureResourceLookupError(message) from exc

    def get_node_pool_info(
        self, resource_group_name: str, cluster_name: str
    ) -> list[dict[str, Any]]:
        """List node pools as dictionaries."""
        node_pools = self.list_node_pools(resource_group_name, cluster_name)
        result = []
        for pool in node_pools:
            result.append(pool.as_dict() if hasattr(pool, "as_dict") else dict(pool))
        return result

    def get_node_pools(self, resource_group_name: str, cluster_name: str) -> list[Any]:
        """Compatibility alias used by diagnostic modules."""
        return self.list_node_pools(resource_group_name, cluster_name)

    def get_provisioning_state(self, resource_group_name: str, cluster_name: str) -> str | None:
        """Return the cluster provisioning state."""
        cluster = self.get_cluster(resource_group_name, cluster_name)
        return getattr(cluster, "provisioning_state", None)

    def get_max_pods(self, resource_group_name: str, cluster_name: str) -> dict[str, int | None]:
        """Return maxPods by node pool name."""
        return {
            getattr(pool, "name", "unknown"): getattr(pool, "max_pods", None)
            for pool in self.list_node_pools(resource_group_name, cluster_name)
        }
