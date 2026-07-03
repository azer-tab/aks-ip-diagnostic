"""Diagnostic orchestration layer.

This file is the main architectural refactor.  The previous implementation put
argument parsing, Azure collection, diagnostic execution, summary calculation,
and report output into src/main.py.  The orchestrator below owns only the scan
workflow: it coordinates collectors, diagnostics, and report-building, then
returns plain report data for the CLI/reporting layer to format.
"""

from __future__ import annotations

from typing import Any

from aks_ip_diagnostic.collectors.azure import (
    AzureCollector,
    discover_subnets,
    parse_subnet_id,
    subnet_id_from_pool,
)
from aks_ip_diagnostic.models import ScanConfig
from aks_ip_diagnostic.status import capacity_status, status_from_issues
from diagnostics.ip_exhaustion import check_ip_exhaustion
from diagnostics.subnet_capacity import check_subnet_capacity
from reports.formatters import DiagnosticReportBuilder, create_issue, create_recommendation
from utils.cost_calculator import (
    calculate_health_score,
    calculate_ip_waste_cost,
    estimate_node_pool_cost,
)


class AKSDiagnosticOrchestrator:
    """Run a full AKS IP diagnostic scan and return structured report data.

    The class is deliberately split into small private methods.  Each method is
    responsible for one part of the report, which makes future unit tests and
    replacements much easier than editing one large procedural function.
    """

    def __init__(self, config: ScanConfig, logger, azure_collector: AzureCollector | None = None):
        self.config = config
        self.logger = logger
        self.azure = azure_collector or AzureCollector(config.subscription_id, logger)

    def run(self) -> dict[str, Any]:
        """Execute the diagnostic workflow and return a JSON-serializable report."""

        self.logger.info("Starting diagnostic for cluster: %s", self.config.cluster_name)
        cluster = self.azure.get_cluster(self.config.resource_group, self.config.cluster_name)
        node_pools = self.azure.list_node_pools(
            self.config.resource_group, self.config.cluster_name
        )

        builder = DiagnosticReportBuilder(
            cluster_name=self.config.cluster_name,
            resource_group=self.config.resource_group,
            subscription_id=self.config.subscription_id,
        )

        self._add_cluster_details(builder, cluster)
        self._add_node_pools(builder, node_pools)
        self._add_subnet_information(builder, cluster, node_pools)
        all_issues = self._run_diagnostics(builder, cluster, node_pools)
        self._add_optional_analysis_placeholders(builder)
        self._set_summary(builder, node_pools, all_issues)
        self._add_recommendations(builder, all_issues)

        return builder.build()

    def _add_cluster_details(self, builder: DiagnosticReportBuilder, cluster) -> None:
        """Add AKS cluster metadata while tolerating SDK-version differences."""

        cluster_details: dict[str, Any] = {
            "location": getattr(cluster, "location", None),
            "k8s_version": getattr(cluster, "kubernetes_version", None),
        }

        network_profile = getattr(cluster, "network_profile", None)
        if network_profile:
            for field in (
                "network_plugin",
                "network_mode",
                "network_policy",
                "dns_service_ip",
                "service_cidr",
                "pod_cidr",
                "load_balancer_sku",
                "outbound_type",
            ):
                cluster_details[field] = getattr(network_profile, field, None)

        sku = getattr(cluster, "sku", None)
        if sku:
            cluster_details["sku"] = {
                "name": getattr(sku, "name", None),
                "tier": getattr(sku, "tier", None),
            }

        identity = getattr(cluster, "identity", None)
        if identity:
            cluster_details["identity"] = {
                "type": getattr(identity, "type", None),
                "principal_id": getattr(identity, "principal_id", None),
            }

        api_server_access = getattr(cluster, "api_server_access_profile", None)
        if api_server_access:
            cluster_details["api_server_access"] = {
                "authorized_ip_ranges": getattr(api_server_access, "authorized_ip_ranges", []),
                "enable_private_cluster": getattr(
                    api_server_access, "enable_private_cluster", False
                ),
            }

        auto_upgrade = getattr(cluster, "auto_upgrade_profile", None)
        if auto_upgrade:
            cluster_details["auto_upgrade_profile"] = {
                "upgrade_channel": getattr(auto_upgrade, "upgrade_channel", None),
            }

        cluster_details["features"] = {
            "azure_rbac": getattr(cluster, "enable_rbac", False),
            "oidc_issuer_enabled": getattr(cluster, "oidc_issuer_profile", None) is not None,
            "defender_enabled": bool(
                getattr(getattr(cluster, "security_profile", None), "defender", None)
            ),
        }

        tags = getattr(cluster, "tags", None)
        if tags:
            cluster_details["tags"] = tags

        builder.set_cluster_details(**cluster_details)

    def _add_node_pools(self, builder: DiagnosticReportBuilder, node_pools: list) -> None:
        """Normalize node-pool SDK objects into stable report dictionaries."""

        for pool in node_pools:
            pool_data = {
                "name": getattr(pool, "name", None),
                "mode": getattr(pool, "mode", "User"),
                "provisioning_state": getattr(pool, "provisioning_state", None),
                "count": getattr(pool, "count", 0),
                "vm_size": getattr(pool, "vm_size", None),
                "max_pods": getattr(pool, "max_pods", None) or 30,
                "autoscaling": {
                    "enabled": getattr(pool, "enable_auto_scaling", False),
                    "min_count": getattr(pool, "min_count", None),
                    "max_count": getattr(pool, "max_count", None),
                },
                "os_type": getattr(pool, "os_type", "Linux"),
                "os_sku": getattr(pool, "os_sku", None),
                "os_disk_size_gb": getattr(pool, "os_disk_size_gb", 128),
                "os_disk_type": getattr(pool, "os_disk_type", "Managed"),
                "enable_node_public_ip": getattr(pool, "enable_node_public_ip", False),
            }

            for optional_field in ("availability_zones", "node_labels", "node_taints"):
                value = getattr(pool, optional_field, None)
                if value:
                    pool_data[optional_field] = value

            upgrade_settings = getattr(pool, "upgrade_settings", None)
            if upgrade_settings:
                pool_data["upgrade_settings"] = {
                    "max_surge": getattr(upgrade_settings, "max_surge", None),
                }

            self._add_pool_cost_estimate(pool_data, pool)
            self._add_pool_subnet_fields(pool_data, pool)

            if getattr(pool, "provisioning_state", None) == "Failed":
                pool_data["error_details"] = {
                    "code": "PROVISIONING_FAILED",
                    "message": getattr(pool, "provisioning_state_message", "Unknown error"),
                }

            builder.add_node_pool(pool_data)

    def _add_pool_cost_estimate(self, pool_data: dict[str, Any], pool) -> None:
        """Attach estimated node-pool cost without making the scan fail if pricing is unknown."""

        try:
            pool_data["cost_estimate"] = estimate_node_pool_cost(
                vm_size=getattr(pool, "vm_size", None),
                node_count=getattr(pool, "count", 0) or 0,
                os_disk_size_gb=getattr(pool, "os_disk_size_gb", 128),
                enable_public_ip=getattr(pool, "enable_node_public_ip", False),
            )
        except Exception as exc:  # Cost calculation is advisory only.
            self.logger.debug(
                "Could not estimate cost for pool %s: %s", getattr(pool, "name", "unknown"), exc
            )

    def _add_pool_subnet_fields(self, pool_data: dict[str, Any], pool) -> None:
        """Add parsed subnet fields to a node-pool report dictionary."""

        subnet_id = subnet_id_from_pool(pool)
        subnet_ref = parse_subnet_id(subnet_id)
        if not subnet_ref:
            self.logger.debug(
                "Node pool %s has no explicit subnet ID", getattr(pool, "name", "unknown")
            )
            return

        pool_data["vnet_subnet_id"] = subnet_id
        pool_data["subnet_name"] = subnet_ref.subnet_name
        pool_data["vnet_name"] = subnet_ref.vnet_name
        pool_data["subnet_resource_group"] = subnet_ref.resource_group

    def _add_subnet_information(
        self, builder: DiagnosticReportBuilder, cluster, node_pools: list
    ) -> None:
        """Add Azure subnet data, or fallback pod-CIDR data for managed/overlay networking."""

        subnet_refs = discover_subnets(cluster, node_pools, self.logger)
        if not subnet_refs:
            self._add_managed_pod_cidr(builder, cluster, node_pools)
            return

        for subnet_ref in subnet_refs.values():
            try:
                subnet = self.azure.get_subnet(subnet_ref)
                subnet_data = self._build_subnet_report(subnet_ref, subnet, node_pools)
                if subnet_data:
                    builder.add_subnet(subnet_data)
            except Exception as exc:
                self.logger.warning("Could not fetch subnet %s: %s", subnet_ref.key, exc)

    def _add_managed_pod_cidr(
        self, builder: DiagnosticReportBuilder, cluster, node_pools: list
    ) -> None:
        """Model pod CIDR capacity when custom VNet subnet data is unavailable."""

        self.logger.warning("No custom VNet subnets found; checking pod CIDR capacity instead")
        network_profile = getattr(cluster, "network_profile", None)
        pod_cidr = getattr(network_profile, "pod_cidr", None) if network_profile else None
        if not pod_cidr or "/" not in pod_cidr:
            return

        prefix_len = int(pod_cidr.split("/")[1])
        total_ips = 2 ** (32 - prefix_len)
        total_required_ips = sum(
            (getattr(pool, "max_pods", None) or 30) * (getattr(pool, "count", 0) or 0)
            for pool in node_pools
        )
        available_ips = total_ips - total_required_ips
        utilization = (total_required_ips / total_ips * 100) if total_ips > 0 else 0

        builder.add_subnet(
            {
                "name": "pod-cidr (Azure-managed)",
                "cidr": pod_cidr,
                "resource_group": "system-managed",
                "vnet_name": "azure-managed",
                "total_ips": total_ips,
                "used_ips": total_required_ips,
                "available_ips": available_ips,
                "utilization_percent": round(utilization, 2),
                "status": capacity_status(utilization),
                "threshold_warning": 70.0,
                "threshold_critical": 85.0,
                "associated_node_pools": [getattr(pool, "name", None) for pool in node_pools],
                "node_count": sum(getattr(pool, "count", 0) or 0 for pool in node_pools),
                "ip_breakdown": {
                    "azure_reserved": 0,
                    "node_ips": 0,
                    "pod_ips_allocated": total_required_ips,
                    "service_ips": 0,
                    "available": available_ips,
                },
                "note": "Pod CIDR for overlay or Azure-managed networking; node subnet capacity was not available from the cluster metadata.",
            }
        )

    def _build_subnet_report(self, subnet_ref, subnet, node_pools: list) -> dict[str, Any] | None:
        """Convert an Azure subnet SDK object into a report dictionary."""

        cidr = getattr(subnet, "address_prefix", None)
        if not cidr or "/" not in cidr:
            return None

        prefix_len = int(cidr.split("/")[1])
        total_ips = 2 ** (32 - prefix_len)
        usable_ips = total_ips - 5
        used_ips = len(getattr(subnet, "ip_configurations", None) or [])
        available_ips = usable_ips - used_ips
        utilization = (used_ips / usable_ips * 100) if usable_ips > 0 else 0

        associated_pools = []
        node_count = 0
        for pool in node_pools:
            pool_subnet_id = subnet_id_from_pool(pool)
            if pool_subnet_id and subnet_ref.subnet_name in pool_subnet_id:
                associated_pools.append(getattr(pool, "name", None))
                node_count += getattr(pool, "count", 0) or 0

        return {
            "name": subnet_ref.subnet_name,
            "cidr": cidr,
            "resource_group": subnet_ref.resource_group,
            "vnet_name": subnet_ref.vnet_name,
            "total_ips": total_ips,
            "used_ips": used_ips,
            "available_ips": available_ips,
            "utilization_percent": round(utilization, 2),
            "status": capacity_status(utilization),
            "threshold_warning": 70.0,
            "threshold_critical": 85.0,
            "associated_node_pools": associated_pools,
            "node_count": node_count,
            "ip_breakdown": {
                "azure_reserved": 5,
                "node_ips": node_count,
                "pod_ips_allocated": used_ips - node_count if used_ips > node_count else 0,
                "available": available_ips,
            },
        }

    def _run_diagnostics(
        self, builder: DiagnosticReportBuilder, cluster, node_pools: list
    ) -> list[dict[str, Any]]:
        """Run all implemented diagnostics and return normalized issues."""

        all_issues: list[dict[str, Any]] = []
        all_issues.extend(self._run_ip_exhaustion(builder, cluster, node_pools))
        all_issues.extend(self._run_provisioning_state(builder, node_pools))
        all_issues.extend(self._run_subnet_capacity(builder, node_pools))
        all_issues.extend(self._run_max_pods(builder, node_pools))
        return all_issues

    def _run_ip_exhaustion(self, builder, cluster, node_pools: list) -> list[dict[str, Any]]:
        self.logger.info("Checking for IP exhaustion")
        issues = check_ip_exhaustion(
            self.azure.aks_client, cluster, node_pools, self.azure.network_client, self.logger
        )
        for issue in issues:
            builder.add_issue(issue)
        builder.add_diagnostic_result(
            diagnostic_type="ip_exhaustion",
            status="PASS" if not issues else "FAIL",
            risk_level="LOW" if not issues else "HIGH",
            issues=issues,
            details={
                "total_checks": 1,
                "checks_passed": 1 if not issues else 0,
                "checks_failed": len(issues),
            },
        )
        return list(issues)

    def _run_provisioning_state(self, builder, node_pools: list) -> list[dict[str, Any]]:
        self.logger.info("Checking node-pool provisioning state")
        raw_issues = []
        for pool in node_pools:
            state = getattr(pool, "provisioning_state", None)
            if state != "Succeeded":
                raw_issues.append(
                    {
                        "title": f"Node pool '{getattr(pool, 'name', 'unknown')}' in {state} state",
                        "description": f"Provisioning state: {state}",
                        "affected_resource": getattr(pool, "name", "unknown"),
                        "severity": "CRITICAL" if state == "Failed" else "WARNING",
                    }
                )

        normalized = [
            create_issue(
                severity=issue["severity"],
                code="PROVISIONING_STATE",
                message=issue["title"],
                affected_resource=issue["affected_resource"],
                details={"description": issue["description"]},
            )
            for issue in raw_issues
        ]

        failed_pools = [
            pool for pool in node_pools if getattr(pool, "provisioning_state", None) != "Succeeded"
        ]
        builder.add_diagnostic_result(
            diagnostic_type="provisioning_state",
            status="PASS" if not failed_pools else "FAIL",
            risk_level="CRITICAL" if failed_pools else "LOW",
            issues=raw_issues,
            details={
                "total_pools": len(node_pools),
                "succeeded_pools": len(
                    [
                        pool
                        for pool in node_pools
                        if getattr(pool, "provisioning_state", None) == "Succeeded"
                    ]
                ),
                "failed_pools": len(failed_pools),
                "failed_pool_names": [getattr(pool, "name", None) for pool in failed_pools],
            },
        )
        return normalized

    def _run_subnet_capacity(self, builder, node_pools: list) -> list[dict[str, Any]]:
        self.logger.info("Checking subnet capacity")
        issues = check_subnet_capacity(self.azure.network_client, node_pools, self.logger)
        for issue in issues:
            builder.add_issue(issue)

        subnets = builder.data.get("subnets", [])
        critical_subnets = [
            subnet for subnet in subnets if subnet.get("utilization_percent", 0) >= 85
        ]
        warning_subnets = [
            subnet for subnet in subnets if 70 <= subnet.get("utilization_percent", 0) < 85
        ]
        builder.add_diagnostic_result(
            diagnostic_type="subnet_capacity",
            status="FAIL" if critical_subnets else ("WARNING" if warning_subnets else "PASS"),
            risk_level="CRITICAL" if critical_subnets else ("MEDIUM" if warning_subnets else "LOW"),
            issues=issues,
            details={
                "total_subnets": len(subnets),
                "healthy_subnets": len(
                    [subnet for subnet in subnets if subnet.get("utilization_percent", 0) < 70]
                ),
                "warning_subnets": len(warning_subnets),
                "critical_subnets": len(critical_subnets),
                "max_utilization_percent": max(
                    [subnet.get("utilization_percent", 0) for subnet in subnets]
                )
                if subnets
                else 0,
            },
        )
        return list(issues)

    def _run_max_pods(self, builder, node_pools: list) -> list[dict[str, Any]]:
        self.logger.info("Checking maxPods configuration")
        issues: list[dict[str, Any]] = []
        raw_issues: list[dict[str, Any]] = []

        for pool in node_pools:
            max_pods = getattr(pool, "max_pods", None) or 30
            if max_pods <= 100:
                continue

            raw_issues.append(
                {
                    "title": f"High maxPods setting on '{getattr(pool, 'name', 'unknown')}'",
                    "description": f"maxPods={max_pods} may waste IPs if not fully utilized",
                    "affected_resource": getattr(pool, "name", "unknown"),
                    "severity": "WARNING",
                }
            )

            node_count = getattr(pool, "count", 0) or 0
            recommended_max_pods = 30
            issues.append(
                create_issue(
                    severity="WARNING",
                    code="MAX_PODS_HIGH",
                    message=f"High maxPods setting on '{getattr(pool, 'name', 'unknown')}'",
                    affected_resource=getattr(pool, "name", "unknown"),
                    details={
                        "current_max_pods": max_pods,
                        "node_count": node_count,
                        "allocated_ips": max_pods * node_count,
                        "recommended_max_pods": recommended_max_pods,
                        "potential_ip_savings": (max_pods - recommended_max_pods) * node_count,
                    },
                    remediation=(
                        f"Consider reducing maxPods from {max_pods} to {recommended_max_pods}. "
                        "AKS requires a new node pool to change this setting safely."
                    ),
                )
            )

        high_maxpods_pools = [
            pool for pool in node_pools if (getattr(pool, "max_pods", None) or 30) > 50
        ]
        builder.add_diagnostic_result(
            diagnostic_type="max_pods_configuration",
            status="WARNING" if high_maxpods_pools else "PASS",
            risk_level="MEDIUM" if high_maxpods_pools else "LOW",
            issues=raw_issues,
            details={
                "total_pools": len(node_pools),
                "pools_with_high_maxpods": len(high_maxpods_pools),
                "pool_maxpods_settings": {
                    getattr(pool, "name", "unknown"): getattr(pool, "max_pods", None) or 30
                    for pool in node_pools
                },
                "recommended_maxpods": 30,
                "note": "High maxPods values may waste IP addresses when pod density is low.",
            },
        )
        return issues

    def _add_optional_analysis_placeholders(self, builder: DiagnosticReportBuilder) -> None:
        """Record optional analyses that are requested but not implemented yet.

        This is cleaner than printing warnings from the engine.  The report now
        tells automation exactly which optional features were skipped.
        """

        if self.config.include_pod_analysis:
            builder.add_diagnostic_result(
                diagnostic_type="pod_analysis",
                status="SKIPPED",
                risk_level="UNKNOWN",
                issues=[],
                details={"reason": "Pod-level analysis is not implemented in this refactor yet."},
            )
        if self.config.include_cost_analysis:
            builder.add_diagnostic_result(
                diagnostic_type="cost_analysis",
                status="SKIPPED",
                risk_level="UNKNOWN",
                issues=[],
                details={
                    "reason": "Detailed cost analysis is not implemented in this refactor yet."
                },
            )

    def _set_summary(
        self, builder: DiagnosticReportBuilder, node_pools: list, all_issues: list[dict[str, Any]]
    ) -> None:
        """Calculate final status, health, efficiency, and capacity summary."""

        overall_status, risk_level = status_from_issues(all_issues)
        subnets = builder.data.get("subnets", [])
        max_subnet_utilization = max(
            [subnet.get("utilization_percent", 0) for subnet in subnets], default=0
        )
        total_allocated_ips = sum(subnet.get("total_ips", 0) for subnet in subnets)
        total_used_ips = sum(subnet.get("used_ips", 0) for subnet in subnets)
        total_max_pods = sum(
            (getattr(pool, "max_pods", None) or 30) * (getattr(pool, "count", 0) or 0)
            for pool in node_pools
        )
        pod_utilization = (total_used_ips / total_max_pods * 100) if total_max_pods > 0 else 0
        ip_waste_percent = max(0, 100 - pod_utilization)
        critical_count = len([issue for issue in all_issues if issue.get("severity") == "CRITICAL"])
        warning_count = len([issue for issue in all_issues if issue.get("severity") == "WARNING"])

        health_score = calculate_health_score(
            issues=all_issues,
            warnings=warning_count,
            critical=critical_count,
            subnet_utilization=max_subnet_utilization,
            ip_waste_percent=ip_waste_percent,
        )

        total_monthly_cost = sum(
            pool.get("cost_estimate", {}).get("total_monthly", 0)
            for pool in builder.data.get("node_pools", [])
        )
        ip_waste_cost = calculate_ip_waste_cost(total_max_pods, total_used_ips)
        potential_savings = ip_waste_cost.get("monthly_cost", 0)

        builder.set_summary(
            overall_status=overall_status,
            risk_level=risk_level,
            health_score=health_score,
            efficiency_metrics={
                "pod_capacity_utilization": round(pod_utilization, 2),
                "ip_waste_percent": round(ip_waste_percent, 2),
                "subnet_utilization": round(max_subnet_utilization, 2),
                "cost_efficiency_score": max(0, round(100 - ip_waste_percent, 2)),
            },
            cost_impact={
                "current_monthly_estimated_usd": round(total_monthly_cost, 2),
                "potential_savings_usd": round(potential_savings, 2),
                "optimization_opportunity_percent": round(
                    (potential_savings / total_monthly_cost * 100) if total_monthly_cost > 0 else 0,
                    2,
                ),
            },
            capacity_outlook={
                "can_upgrade_safely": max_subnet_utilization < 85,
                "headroom_percent": round(100 - max_subnet_utilization, 2)
                if max_subnet_utilization > 0
                else 100,
                "available_ips": total_allocated_ips - total_used_ips,
            },
        )

    def _add_recommendations(
        self, builder: DiagnosticReportBuilder, all_issues: list[dict[str, Any]]
    ) -> None:
        """Add concise remediation guidance based on final issue severity."""

        critical_issues = [issue for issue in all_issues if issue.get("severity") == "CRITICAL"]
        warning_issues = [issue for issue in all_issues if issue.get("severity") == "WARNING"]

        if critical_issues:
            builder.add_recommendation(
                create_recommendation(
                    priority="CRITICAL",
                    category="REMEDIATION",
                    title="Address critical AKS IP capacity issues immediately",
                    description=f"Found {len(critical_issues)} critical issue(s) that may block scaling, upgrades, or node provisioning.",
                    recommendation="Review the critical findings first, then expand subnet capacity or move workloads to a larger subnet/node pool design.",
                    steps=[
                        "Review critical findings",
                        "Confirm subnet capacity",
                        "Create replacement node pools if maxPods or subnet changes are required",
                        "Retest after remediation",
                    ],
                )
            )
        elif warning_issues:
            builder.add_recommendation(
                create_recommendation(
                    priority="HIGH",
                    category="OPTIMIZATION",
                    title="Plan AKS IP capacity optimization",
                    description=f"Found {len(warning_issues)} warning(s) that are not immediately blocking but should be remediated before growth or upgrades.",
                    recommendation="Review maxPods settings, subnet utilization, and upgrade headroom before the next scaling event.",
                    steps=[
                        "Review warning findings",
                        "Estimate growth for the next 90 days",
                        "Adjust node-pool or subnet design as needed",
                    ],
                )
            )
