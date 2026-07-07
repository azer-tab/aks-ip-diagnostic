from types import SimpleNamespace

from src.aks_ip_diagnostic.models import ScanConfig
from src.aks_ip_diagnostic.orchestrator import AKSDiagnosticOrchestrator
from src.reports.formatters import OutputFormat, format_report
from src.utils.logger import setup_logger


class FakeAzureCollector:
    """Small fake collector proving the orchestrator is testable without Azure."""

    def __init__(self, cluster, pools):
        self.cluster = cluster
        self.pools = pools
        self.aks_client = SimpleNamespace()
        self.network_client = SimpleNamespace()

    def get_cluster(self, resource_group, cluster_name):
        return self.cluster

    def list_node_pools(self, resource_group, cluster_name):
        return self.pools


def test_orchestrator_builds_report_without_cli_or_live_azure():
    cluster = SimpleNamespace(
        location="eastus",
        kubernetes_version="1.29.0",
        network_profile=SimpleNamespace(pod_cidr="10.244.0.0/16", service_cidr="10.0.0.0/16"),
        tags={"env": "test"},
    )
    pools = [
        SimpleNamespace(
            name="system",
            provisioning_state="Succeeded",
            count=3,
            vm_size="Standard_D2s_v3",
            max_pods=30,
            enable_auto_scaling=False,
        )
    ]
    config = ScanConfig(subscription_id="sub", resource_group="rg", cluster_name="aks")
    logger = setup_logger("test-orchestrator", verbose=False)

    report = AKSDiagnosticOrchestrator(config, logger, FakeAzureCollector(cluster, pools)).run()  # type: ignore

    assert report["cluster_info"]["name"] == "aks"
    assert report["cluster_info"]["location"] == "eastus"
    assert report["node_pools"][0]["name"] == "system"
    assert report["summary"]["overall_status"] == "HEALTHY"


def test_clean_text_output_contains_operator_tables():
    report = {
        "metadata": {"timestamp": "2026-01-01T00:00:00Z", "scan_duration_seconds": 1},
        "cluster_info": {
            "name": "aks",
            "resource_group": "rg",
            "subscription_id": "sub",
        },
        "summary": {
            "overall_status": "HEALTHY",
            "risk_level": "LOW",
            "total_issues": 0,
        },
        "diagnostics": {"ip_exhaustion": {"status": "PASS", "risk_level": "LOW", "issues": []}},
        "subnets": [
            {
                "name": "pod-cidr",
                "cidr": "10.244.0.0/16",
                "used_ips": 90,
                "available_ips": 65446,
                "utilization_percent": 0.14,
                "status": "HEALTHY",
            }
        ],
        "node_pools": [
            {
                "name": "system",
                "provisioning_state": "Succeeded",
                "count": 3,
                "max_pods": 30,
            }
        ],
        "issues": [],
        "recommendations": [],
    }

    output = format_report(report, OutputFormat.TEXT)

    assert "Executive summary" in output
    assert "Subnet / CIDR capacity" in output
    assert "Node pools" in output
    assert "No issues detected" in output
