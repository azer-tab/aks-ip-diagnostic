"""Azure collection helpers.

This module contains read-only Azure calls and Azure-resource parsing.  The
orchestrator uses it to obtain data, but it does not format output or decide
process exit codes.
"""

from __future__ import annotations

from collections.abc import Iterable

from aks_clients.aks_client import AKSClient
from aks_clients.network_client import NetworkClient
from aks_ip_diagnostic.models import AzureSubnetReference


class AzureCollector:
    """Read-only collector for AKS and Network resources."""

    def __init__(self, subscription_id: str, logger, aks_client=None, network_client=None):
        self.subscription_id = subscription_id
        self.logger = logger
        self.aks_client = aks_client or AKSClient(subscription_id)
        self.network_client = network_client or NetworkClient(subscription_id)

    def get_cluster(self, resource_group: str, cluster_name: str):
        """Fetch the AKS managed cluster resource."""

        self.logger.info("Fetching AKS cluster metadata from Azure")
        return self.aks_client.get_cluster(resource_group, cluster_name)

    def list_node_pools(self, resource_group: str, cluster_name: str) -> list:
        """Fetch all node pools for the AKS cluster."""

        self.logger.info("Fetching AKS node pools from Azure")
        pools = list(self.aks_client.list_node_pools(resource_group, cluster_name))
        self.logger.info("Found %s node pools", len(pools))
        return pools

    def get_subnet(self, subnet_ref: AzureSubnetReference):
        """Fetch an Azure subnet by parsed resource reference."""

        return self.network_client.get_subnet(
            subnet_ref.resource_group,
            subnet_ref.vnet_name,
            subnet_ref.subnet_name,
        )


def parse_subnet_id(subnet_id: str | None) -> AzureSubnetReference | None:
    """Parse an Azure subnet resource ID.

    Azure resource IDs are positional, so this helper centralizes the fragile
    string parsing that used to be repeated in main.py.
    """

    if not subnet_id:
        return None
    parts = subnet_id.split("/")
    if len(parts) < 11:
        return None
    return AzureSubnetReference(
        resource_group=parts[4],
        vnet_name=parts[8],
        subnet_name=parts[10],
    )


def subnet_id_from_pool(pool) -> str | None:
    """Return the best-known subnet ID from an AKS node-pool-like object."""

    if getattr(pool, "vnet_subnet_id", None):
        return pool.vnet_subnet_id
    network_profile = getattr(pool, "network_profile", None)
    if network_profile and getattr(network_profile, "vnet_subnet_id", None):
        return network_profile.vnet_subnet_id
    agent_pool_profile = getattr(pool, "agent_pool_profile", None)
    if agent_pool_profile and getattr(agent_pool_profile, "vnet_subnet_id", None):
        return agent_pool_profile.vnet_subnet_id
    return None


def discover_subnets(cluster, node_pools: Iterable, logger) -> dict[str, AzureSubnetReference]:
    """Discover unique subnets referenced by node pools or cluster profiles."""

    discovered: dict[str, AzureSubnetReference] = {}

    for pool in node_pools:
        subnet_ref = parse_subnet_id(subnet_id_from_pool(pool))
        if subnet_ref:
            discovered.setdefault(subnet_ref.key, subnet_ref)
            logger.debug(
                "Discovered subnet from node pool %s: %s",
                getattr(pool, "name", "unknown"),
                subnet_ref.key,
            )

    # Some SDK versions expose subnet IDs only on cluster.agent_pool_profiles.
    if not discovered and getattr(cluster, "agent_pool_profiles", None):
        logger.info("No subnet IDs found on node pools; checking cluster agent pool profiles")
        for profile in cluster.agent_pool_profiles:
            subnet_ref = parse_subnet_id(getattr(profile, "vnet_subnet_id", None))
            if subnet_ref:
                discovered.setdefault(subnet_ref.key, subnet_ref)
                logger.debug(
                    "Discovered subnet from cluster profile %s: %s",
                    getattr(profile, "name", "unknown"),
                    subnet_ref.key,
                )

    return discovered
