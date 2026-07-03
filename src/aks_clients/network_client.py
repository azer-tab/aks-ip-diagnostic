"""Read-only Azure Network client wrapper for AKS diagnostics."""

from __future__ import annotations

import logging
from typing import Any

from .exceptions import AzureResourceLookupError


class NetworkClient:
    """Wrapper for read-only Azure virtual network and subnet operations."""

    def __init__(
        self, subscription_id: str, credential: Any | None = None, client: Any | None = None
    ):
        self.subscription_id = subscription_id
        self.logger = logging.getLogger(__name__)
        if client is not None:
            self.credential = credential
            self.network_client = client
            return
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.network import NetworkManagementClient
        except ImportError as exc:
            raise RuntimeError(
                "Azure SDK dependencies are not installed. Install the project with the azure extra or requirements.txt."
            ) from exc
        self.credential = credential or DefaultAzureCredential()
        self.network_client = NetworkManagementClient(self.credential, subscription_id)

    def get_subnet(
        self, resource_group_name: str, virtual_network_name: str, subnet_name: str
    ) -> Any:
        """Retrieve a subnet from Azure."""
        try:
            return self.network_client.subnets.get(
                resource_group_name, virtual_network_name, subnet_name
            )
        except Exception as exc:
            message = (
                f"Unable to read subnet '{subnet_name}' in VNet '{virtual_network_name}' "
                f"and resource group '{resource_group_name}': {exc}"
            )
            self.logger.error(message)
            raise AzureResourceLookupError(message) from exc

    def list_subnets(self, resource_group_name: str, virtual_network_name: str) -> list[Any]:
        """List all subnets in a virtual network."""
        try:
            return list(self.network_client.subnets.list(resource_group_name, virtual_network_name))
        except Exception as exc:
            message = f"Unable to list subnets in VNet '{virtual_network_name}': {exc}"
            self.logger.error(message)
            raise AzureResourceLookupError(message) from exc
