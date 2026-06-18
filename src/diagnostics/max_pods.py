def evaluate_max_pods(node_pools, max_pods_limit):
    """
    Evaluates the maxPods configuration for each node pool and flags any configurations
    that exceed the specified safe limits.

    Parameters:
    - node_pools: List of dictionaries containing node pool configurations.
    - max_pods_limit: The maximum safe limit for maxPods configuration.

    Returns:
    - List of issues found, if any.
    """
    issues = []

    for pool in node_pools:
        pool_name = pool.get('name')
        max_pods = pool.get('maxPods')

        if max_pods > max_pods_limit:
            issues.append(f"Node pool '{pool_name}' exceeds maxPods limit: {max_pods} > {max_pods_limit}")

    return issues


def check_max_pods_configuration(aks_client, max_pods_limit):
    """
    Checks the maxPods configuration for all node pools in the AKS cluster.

    Parameters:
    - aks_client: An instance of the AKS client to retrieve node pool information.
    - max_pods_limit: The maximum safe limit for maxPods configuration.

    Returns:
    - List of issues found, if any.
    """
    node_pools = aks_client.get_node_pools()
    return evaluate_max_pods(node_pools, max_pods_limit)