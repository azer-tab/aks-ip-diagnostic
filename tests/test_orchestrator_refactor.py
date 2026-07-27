from types import SimpleNamespace

from aks_ip_diagnostic.models import ScanConfig
from aks_ip_diagnostic.orchestrator import AKSDiagnosticOrchestrator
from reports.formatters import DiagnosticReportBuilder, OutputFormat, format_report
from reports.json_validator import ReportValidator
from utils.logger import setup_logger


class FakeAzureCollector:
    """Fake collector that keeps orchestrator tests independent of Azure credentials."""

    def __init__(self, cluster, pools):
        self.cluster = cluster
        self.pools = pools
        self.aks_client = SimpleNamespace()
        self.network_client = SimpleNamespace()

    def get_cluster(self, resource_group, cluster_name):
        return self.cluster

    def list_node_pools(self, resource_group, cluster_name):
        return self.pools


class StubbedOrchestrator(AKSDiagnosticOrchestrator):
    """Exercise report assembly while isolating individual diagnostic rule tests."""

    def _add_subnet_information(self, builder, cluster, node_pools):
        self._add_managed_pod_cidr(builder, cluster, node_pools)

    def _run_diagnostics(self, builder, cluster, node_pools):
        for name in (
            "ip_exhaustion",
            "provisioning_state",
            "subnet_capacity",
            "max_pods_configuration",
        ):
            builder.add_diagnostic_result(name, "PASS", "LOW", [], {})
        return []


def test_orchestrator_builds_report_without_cli_or_live_azure():
    cluster = SimpleNamespace(
        location="eastus",
        kubernetes_version="1.29.0",
        network_profile=SimpleNamespace(
            pod_cidr="10.244.0.0/16",
            service_cidr="10.0.0.0/16",
            network_plugin="azure",
        ),
        tags={"env": "test"},
    )
    pools = [
        SimpleNamespace(
            name="system",
            mode="System",
            provisioning_state="Succeeded",
            count=3,
            vm_size="Standard_D2s_v3",
            max_pods=30,
            enable_auto_scaling=False,
        )
    ]
    config = ScanConfig(subscription_id="sub", resource_group="rg", cluster_name="aks")
    logger = setup_logger("test-orchestrator", verbose=False)

    report = StubbedOrchestrator(config, logger, FakeAzureCollector(cluster, pools)).run()

    assert report["cluster_info"]["name"] == "aks"
    assert report["cluster_info"]["location"] == "eastus"
    assert report["node_pools"][0]["name"] == "system"
    assert report["summary"]["overall_status"] == "HEALTHY"
    assert report["metadata"]["tool_version"] == "0.3.3"
    assert ReportValidator.validate_diagnostic_report(report) == (True, [])


def test_text_output_uses_operator_friendly_sections():
    report = {
        "metadata": {
            "timestamp": "2026-01-01T00:00:00Z",
            "scan_duration_seconds": 1,
            "tool_version": "0.3.3",
        },
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
        "diagnostics": {
            "ip_exhaustion": {"status": "PASS", "risk_level": "LOW", "issues": []}
        },
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

    assert "EXECUTIVE SUMMARY" in output
    assert "SUBNET / CIDR CAPACITY" in output
    assert "NODE POOLS" in output
    assert "No issues detected" in output


def test_max_pods_status_matches_issue_threshold():
    cluster = SimpleNamespace(network_profile=None)
    pools = [
        SimpleNamespace(name="moderate", max_pods=60, count=2),
        SimpleNamespace(name="dense", max_pods=110, count=2),
    ]
    config = ScanConfig(subscription_id="sub", resource_group="rg", cluster_name="aks")
    logger = setup_logger("test-max-pods", verbose=False)
    orchestrator = AKSDiagnosticOrchestrator(
        config, logger, FakeAzureCollector(cluster, pools)
    )
    builder = DiagnosticReportBuilder("aks", "rg", "sub")
    issues = orchestrator._run_max_pods(builder, pools)

    assert len(issues) == 1
    assert issues[0]["affected_resource"] == "dense"
    assert builder.data["diagnostics"]["max_pods_configuration"]["status"] == "WARNING"
    assert len(builder.data["issues"]) == 1


def test_non_failed_provisioning_state_is_warning_not_critical():
    cluster = SimpleNamespace(network_profile=None)
    pools = [SimpleNamespace(name="user", provisioning_state="Updating")]
    config = ScanConfig(subscription_id="sub", resource_group="rg", cluster_name="aks")
    logger = setup_logger("test-provisioning", verbose=False)
    orchestrator = AKSDiagnosticOrchestrator(
        config, logger, FakeAzureCollector(cluster, pools)
    )
    builder = DiagnosticReportBuilder("aks", "rg", "sub")
    issues = orchestrator._run_provisioning_state(builder, pools)
    diagnostic = builder.data["diagnostics"]["provisioning_state"]

    assert issues[0]["severity"] == "WARNING"
    assert diagnostic["status"] == "WARNING"
    assert diagnostic["risk_level"] == "MEDIUM"
