from types import SimpleNamespace

from src.diagnostics.ip_exhaustion import analyze_provisioning_failure, calculate_ip_deficit
from src.diagnostics.max_pods import evaluate_max_pods
from src.diagnostics.provisioning_state import flag_provisioning_failures
from src.diagnostics.subnet_capacity import (
    analyze_subnet_utilization,
    calculate_required_ips,
    calculate_subnet_ips,
)


def test_calculate_subnet_ips_accounts_for_azure_reserved_addresses():
    total, usable = calculate_subnet_ips("10.0.0.0/24")
    assert total == 256
    assert usable == 251


def test_calculate_required_ips_uses_max_autoscale_capacity():
    result = calculate_required_ips(node_count=3, max_pods=30, autoscaling=True, max_node_count=10)
    assert result == {"current_required": 93, "max_required": 310, "per_node": 31}


def test_analyze_subnet_utilization_flags_critical_capacity():
    result = analyze_subnet_utilization("10.0.0.0/24", allocated_ips=230, future_required_ips=30)
    assert result["status"] == "CRITICAL"
    assert result["can_accommodate_scaling"] is False


def test_ip_deficit_includes_buffer():
    result = calculate_ip_deficit(required_ips=200, available_ips=180, buffer_percent=20)
    assert result["has_deficit"] is True
    assert result["deficit_amount"] == 60
    assert result["recommended_capacity"] == 240


def test_provisioning_failure_detects_ip_related_errors():
    pool = SimpleNamespace(
        provisioning_state="Failed",
        provisioning_state_message="Subnet has insufficient IP address capacity",
    )
    result = analyze_provisioning_failure(pool)
    assert result["is_ip_related"] is True
    assert result["confidence"] in {"MEDIUM", "HIGH"}


def test_flag_provisioning_failures_returns_non_succeeded_pools():
    states = {"system": "Succeeded", "user": "Failed", "batch": "Updating"}
    assert flag_provisioning_failures(states) == ["user", "batch"]


def test_evaluate_max_pods_flags_high_values():
    issues = evaluate_max_pods(
        [{"name": "safe", "maxPods": 30}, {"name": "dense", "maxPods": 110}],
        max_pods_limit=100,
    )
    assert len(issues) == 1
    assert "dense" in issues[0]
