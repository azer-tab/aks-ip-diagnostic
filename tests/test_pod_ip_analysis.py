from src.diagnostics.pod_ip_analysis import PodIPAnalyzer


def _node(name: str, allocatable: int = 30, pool: str = "user") -> dict:
    return {
        "metadata": {"name": name, "labels": {"agentpool": pool}},
        "status": {
            "allocatable": {"pods": str(allocatable)},
            "capacity": {"pods": str(allocatable)},
        },
    }


def _pod(name: str, node: str | None, phase: str = "Running", ip: str | None = None) -> dict:
    pod = {
        "metadata": {"name": name, "namespace": "default"},
        "spec": {"nodeName": node} if node else {},
        "status": {"phase": phase},
    }
    if ip:
        pod["status"]["podIP"] = ip
    return pod


class FakeKubernetesClient:
    def __init__(self, pods: list[dict], nodes: list[dict]):
        self._pods = pods
        self._nodes = nodes

    def list_pods_all_namespaces(self) -> list[dict]:
        return self._pods

    def list_nodes(self) -> list[dict]:
        return self._nodes


def test_analyzer_collects_pods_and_nodes_from_client():
    pods = [_pod("web", "node-a", ip="10.244.0.10")]
    nodes = [_node("node-a")]
    analyzer = PodIPAnalyzer(FakeKubernetesClient(pods, nodes), network_client=None)

    assert analyzer.get_all_pods() == pods
    assert analyzer.get_all_nodes() == nodes


def test_pod_distribution_includes_empty_nodes():
    pods = [_pod("web", "node-a"), _pod("api", "node-a")]
    nodes = [_node("node-a"), _node("node-b")]
    analyzer = PodIPAnalyzer(k8s_client=None, network_client=None)

    result = analyzer.analyze_pod_distribution(pods, nodes)

    assert result["min_pods_per_node"] == 0
    assert result["max_pods_per_node"] == 2
    assert result["nodes_with_pods"] == 1
    assert result["total_nodes"] == 2
    assert result["balanced"] is False


def test_node_analysis_uses_allocatable_pod_capacity():
    pods = [
        _pod("web", "node-a", ip="10.244.0.10"),
        _pod("api", "node-a", ip="10.244.0.11"),
    ]
    nodes = [_node("node-a", allocatable=4)]
    analyzer = PodIPAnalyzer(k8s_client=None, network_client=None)

    result = analyzer.analyze_by_node(pods, nodes)

    assert result[0]["max_pods"] == 4
    assert result[0]["remaining_capacity"] == 2
    assert result[0]["utilization_percentage"] == 50.0


def test_pod_density_counts_only_running_pods():
    pods = [
        _pod("running", "node-a", phase="Running"),
        _pod("done", "node-a", phase="Succeeded"),
        _pod("pending", None, phase="Pending"),
    ]
    nodes = [_node("node-a"), _node("node-b")]
    analyzer = PodIPAnalyzer(k8s_client=None, network_client=None)

    result = analyzer.calculate_pod_density(pods, nodes)

    assert result["total_running_pods"] == 1
    assert result["total_nodes"] == 2
    assert result["pods_per_node"] == 0.5
    assert result["density_status"] == "LOW"
