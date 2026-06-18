def check_provisioning_state(aks_client, resource_group, cluster_name):
    """
    Check the provisioning state of node pools in the specified AKS cluster.
    
    Parameters:
    aks_client: An instance of the AKS client to interact with Azure.
    resource_group (str): The resource group containing the AKS cluster.
    cluster_name (str): The name of the AKS cluster.

    Returns:
    dict: A dictionary containing the provisioning state of each node pool.
    """
    node_pools = aks_client.get_node_pools(resource_group, cluster_name)
    provisioning_states = {}

    for pool in node_pools:
        provisioning_states[pool.name] = pool.provisioning_state

    return provisioning_states


def flag_provisioning_failures(provisioning_states):
    """
    Flag any node pools that are in a failed provisioning state.
    
    Parameters:
    provisioning_states (dict): A dictionary of node pool names and their provisioning states.

    Returns:
    list: A list of node pool names that have failed provisioning.
    """
    failed_pools = [name for name, state in provisioning_states.items() if state != 'Succeeded']
    return failed_pools


def diagnose_provisioning_state(aks_client, resource_group, cluster_name):
    """
    Diagnose the provisioning state of node pools and identify any failures.
    
    Parameters:
    aks_client: An instance of the AKS client to interact with Azure.
    resource_group (str): The resource group containing the AKS cluster.
    cluster_name (str): The name of the AKS cluster.

    Returns:
    dict: A report containing the provisioning states and any flagged failures.
    """
    provisioning_states = check_provisioning_state(aks_client, resource_group, cluster_name)
    failed_pools = flag_provisioning_failures(provisioning_states)

    return {
        'provisioning_states': provisioning_states,
        'failed_pools': failed_pools
    }