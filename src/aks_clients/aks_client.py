from azure.identity import DefaultAzureCredential
from azure.mgmt.containerservice import ContainerServiceClient

class AKSClient:
    def __init__(self, subscription_id):
        self.subscription_id = subscription_id
        self.credential = DefaultAzureCredential()
        self.client = ContainerServiceClient(self.credential, self.subscription_id)

    def get_cluster(self, resource_group_name, cluster_name):
        """Get raw cluster object from Azure SDK."""
        try:
            return self.client.managed_clusters.get(resource_group_name, cluster_name)
        except Exception as e:
            print(f"Error retrieving cluster: {e}")
            return None
    
    def get_cluster_info(self, resource_group_name, cluster_name):
        try:
            cluster = self.client.managed_clusters.get(resource_group_name, cluster_name)
            return {
                "name": cluster.name,
                "location": cluster.location,
                "node_resource_group": cluster.node_resource_group,
                "dns_prefix": cluster.dns_prefix,
                "agent_pool_profiles": cluster.agent_pool_profiles
            }
        except Exception as e:
            print(f"Error retrieving cluster info: {e}")
            return None

    def list_node_pools(self, resource_group_name, cluster_name):
        """Get raw node pools iterator from Azure SDK."""
        try:
            return self.client.agent_pools.list(resource_group_name, cluster_name)
        except Exception as e:
            print(f"Error listing node pools: {e}")
            return None
    
    def get_node_pool_info(self, resource_group_name, cluster_name):
        try:
            node_pools = self.client.agent_pools.list(resource_group_name, cluster_name)
            return [pool.as_dict() for pool in node_pools]
        except Exception as e:
            print(f"Error retrieving node pool info: {e}")
            return None

    def get_provisioning_state(self, resource_group_name, cluster_name):
        try:
            cluster = self.client.managed_clusters.get(resource_group_name, cluster_name)
            return cluster.provisioning_state
        except Exception as e:
            print(f"Error retrieving provisioning state: {e}")
            return None

    def get_max_pods(self, resource_group_name, cluster_name):
        try:
            node_pools = self.get_node_pool_info(resource_group_name, cluster_name)
            return {pool.name: pool.max_pods for pool in node_pools}
        except Exception as e:
            print(f"Error retrieving max pods configuration: {e}")
            return None