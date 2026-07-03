from types import SimpleNamespace

import pytest

from src.aks_clients.aks_client import AKSClient
from src.aks_clients.exceptions import AzureResourceLookupError
from src.aks_clients.network_client import NetworkClient


class _ManagedClusters:
    def __init__(self, cluster=None, exc=None):
        self.cluster = cluster
        self.exc = exc

    def get(self, resource_group_name, cluster_name):
        if self.exc:
            raise self.exc
        return self.cluster


class _AgentPools:
    def __init__(self, pools=None, exc=None):
        self.pools = pools or []
        self.exc = exc

    def list(self, resource_group_name, cluster_name):
        if self.exc:
            raise self.exc
        return self.pools


class _ContainerServiceClient:
    def __init__(self, cluster=None, pools=None, cluster_exc=None, pools_exc=None):
        self.managed_clusters = _ManagedClusters(cluster, cluster_exc)
        self.agent_pools = _AgentPools(pools, pools_exc)


class _Subnets:
    def __init__(self, subnet=None, subnets=None, exc=None):
        self.subnet = subnet
        self.subnets = subnets or []
        self.exc = exc

    def get(self, resource_group_name, virtual_network_name, subnet_name):
        if self.exc:
            raise self.exc
        return self.subnet

    def list(self, resource_group_name, virtual_network_name):
        if self.exc:
            raise self.exc
        return self.subnets


class _NetworkManagementClient:
    def __init__(self, subnet=None, subnets=None, exc=None):
        self.subnets = _Subnets(subnet, subnets, exc)


def test_aks_client_lists_node_pools_with_injected_client():
    pools = [SimpleNamespace(name="system", count=3), SimpleNamespace(name="user", count=5)]
    client = AKSClient("sub-id", credential=object(), client=_ContainerServiceClient(pools=pools))

    result = client.list_node_pools("rg", "cluster")

    assert [pool.name for pool in result] == ["system", "user"]


def test_aks_client_raises_typed_error_on_failure():
    client = AKSClient(
        "sub-id",
        credential=object(),
        client=_ContainerServiceClient(pools_exc=RuntimeError("boom")),
    )

    with pytest.raises(AzureResourceLookupError):
        client.list_node_pools("rg", "cluster")


def test_network_client_gets_subnet_with_injected_client():
    subnet = SimpleNamespace(name="subnet1", address_prefix="10.0.0.0/24")
    client = NetworkClient(
        "sub-id", credential=object(), client=_NetworkManagementClient(subnet=subnet)
    )

    result = client.get_subnet("rg", "vnet", "subnet1")

    assert result.name == "subnet1"
    assert result.address_prefix == "10.0.0.0/24"


def test_network_client_raises_typed_error_on_failure():
    client = NetworkClient(
        "sub-id", credential=object(), client=_NetworkManagementClient(exc=RuntimeError("boom"))
    )

    with pytest.raises(AzureResourceLookupError):
        client.get_subnet("rg", "vnet", "subnet1")
