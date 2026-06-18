"""
Main CLI entry point for AKS IP Diagnostic Tool.

This is the command-line interface that ties together all diagnostic modules
and provides flexible output formatting options.
"""

import sys
import argparse
import os
from pathlib import Path
from datetime import datetime

# Fix Windows terminal encoding for Unicode characters (emojis)
if sys.platform == "win32":
    try:
        import codecs

        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")
    except:
        pass  # If this fails, continue anyway

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import AKS clients
from aks_clients.aks_client import AKSClient
from aks_clients.network_client import NetworkClient

# Import diagnostic modules
from diagnostics.subnet_capacity import check_subnet_capacity
from diagnostics.ip_exhaustion import check_ip_exhaustion

# Import utilities
from utils.cost_calculator import (
    estimate_node_pool_cost,
    calculate_ip_waste_cost,
    calculate_health_score,
)

# Import report formatters
from reports.formatters import (
    DiagnosticReportBuilder,
    OutputFormat,
    format_report,
    create_issue,
    create_recommendation,
)

# Import utilities
from utils.logger import setup_logger


def get_report_path(
    cluster_name: str, output_format: str, custom_filename: str = None
) -> Path:
    """
    Generate report file path with timestamp in reports directory.

    Args:
        cluster_name: Name of the cluster being analyzed
        output_format: Output format (text, json, etc.)
        custom_filename: Optional custom filename (will still get timestamp and folder)

    Returns:
        Path object for the report file
    """
    # Create reports directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Determine file extension
    extension_map = {
        "text": "txt",
        "json": "json",
        "json-pretty": "json",
        "json-compact": "json",
        "yaml": "yaml",
        "markdown": "md",
        "html": "html",
    }
    extension = extension_map.get(output_format, "txt")

    # Generate filename
    if custom_filename:
        # Use custom filename but add timestamp before extension
        custom_path = Path(custom_filename)
        base_name = custom_path.stem
        filename = f"{base_name}_{timestamp}{custom_path.suffix or '.' + extension}"
    else:
        # Auto-generate filename
        filename = f"{cluster_name}_diagnostic_{timestamp}.{extension}"

    return reports_dir / filename


def check_provisioning_state(node_pools, logger):
    """Check node pool provisioning states."""
    issues = []

    try:
        for pool in node_pools:
            if pool.provisioning_state != "Succeeded":
                issues.append(
                    {
                        "title": f"Node pool '{pool.name}' in {pool.provisioning_state} state",
                        "description": f"Provisioning state: {pool.provisioning_state}",
                        "affected_resource": pool.name,
                        "severity": (
                            "CRITICAL"
                            if pool.provisioning_state == "Failed"
                            else "WARNING"
                        ),
                    }
                )
    except Exception as e:
        logger.error(f"Error checking provisioning state: {str(e)}")

    return issues


def check_max_pods(node_pools, logger):
    """
    Check maxPods configuration for potential IP waste.

    Args:
        node_pools: List of node pool objects
        logger: Logger instance

    Returns:
        List of issues found
    """
    issues = []

    try:
        for pool in node_pools:
            max_pods = pool.max_pods or 30

            if max_pods > 100:
                issues.append(
                    {
                        "title": f"High maxPods setting on '{pool.name}'",
                        "description": f"maxPods={max_pods} may waste IPs if not fully utilized",
                        "affected_resource": pool.name,
                        "severity": "WARNING",
                    }
                )
    except Exception as e:
        logger.error(f"Error checking maxPods: {str(e)}")

    return issues


def parse_arguments():
    """
    Parse and validate command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments object
    """
    parser = argparse.ArgumentParser(
        description="AKS IP Diagnostic Tool - Analyze and optimize IP usage in AKS clusters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic diagnostic
  python src/main.py --subscription-id xxx --resource-group my-rg --cluster-name my-cluster
  
  # With JSON output
  python src/main.py --subscription-id xxx --resource-group my-rg --cluster-name my-cluster \\
                     --format json-pretty --output report.json
  
  # With pod analysis
  python src/main.py --subscription-id xxx --resource-group my-rg --cluster-name my-cluster \\
                     --include-pod-analysis
  
  # With cost analysis
  python src/main.py --subscription-id xxx --resource-group my-rg --cluster-name my-cluster \\
                     --include-pod-analysis --include-cost-analysis --region eastus
        """,
    )

    # Azure Resource Identification
    parser.add_argument(
        "--subscription-id", required=True, help="Azure subscription ID"
    )
    parser.add_argument(
        "--resource-group",
        required=True,
        help="Azure resource group containing the AKS cluster",
    )
    parser.add_argument(
        "--cluster-name", required=True, help="Name of the AKS cluster to analyze"
    )

    # Output Format Options
    parser.add_argument(
        "--format",
        "-f",
        choices=[
            "text",
            "json",
            "json-pretty",
            "json-compact",
            "yaml",
            "markdown",
            "html",
        ],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output", "-o", help="Output file path. If not specified, writes to stdout."
    )

    # Analysis Options
    parser.add_argument(
        "--include-pod-analysis",
        action="store_true",
        help="Include pod-level IP usage analysis (requires kubectl access)",
    )
    parser.add_argument(
        "--include-cost-analysis",
        action="store_true",
        help="Include cost analysis for IP waste and optimization savings",
    )
    parser.add_argument(
        "--region",
        default="eastus",
        help="Azure region for cost analysis pricing (default: eastus)",
    )
    parser.add_argument(
        "--pod-lifecycle",
        action="store_true",
        help="Include pod lifecycle analysis (requires --include-pod-analysis)",
    )
    parser.add_argument(
        "--kubeconfig",
        help="Path to kubeconfig file (optional, uses default if not specified)",
    )

    # Logging
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose/debug logging output"
    )

    return parser.parse_args()


def run_diagnostic(args):
    """Run full diagnostic scan."""
    logger = setup_logger(__name__, verbose=args.verbose)

    try:
        cluster_name = args.cluster_name
        resource_group = args.resource_group
        subscription_id = args.subscription_id

        logger.info(f"Starting diagnostic for cluster: {cluster_name}")

        # Initialize Azure clients
        logger.info("Initializing Azure clients...")
        aks_client = AKSClient(subscription_id)
        network_client = NetworkClient(subscription_id)

        # Get cluster information
        logger.info(f"Fetching cluster data from Azure...")
        cluster = aks_client.get_cluster(resource_group, cluster_name)
        node_pools = list(aks_client.list_node_pools(resource_group, cluster_name))

        logger.info(f"Found {len(node_pools)} node pools")

        # Create report builder
        builder = DiagnosticReportBuilder(
            cluster_name=cluster_name,
            resource_group=resource_group,
            subscription_id=subscription_id,
        )

        # Add enhanced cluster details
        if hasattr(cluster, "location"):
            # Basic cluster details
            cluster_details = {
                "location": getattr(cluster, "location", None),
                "k8s_version": getattr(cluster, "kubernetes_version", None),
            }

            # Network configuration
            if hasattr(cluster, "network_profile") and cluster.network_profile:
                np = cluster.network_profile
                cluster_details["network_plugin"] = getattr(np, "network_plugin", None)
                cluster_details["network_mode"] = getattr(np, "network_mode", None)
                cluster_details["network_policy"] = getattr(np, "network_policy", None)
                cluster_details["dns_service_ip"] = getattr(np, "dns_service_ip", None)
                cluster_details["service_cidr"] = getattr(np, "service_cidr", None)
                cluster_details["pod_cidr"] = getattr(np, "pod_cidr", None)
                cluster_details["load_balancer_sku"] = getattr(
                    np, "load_balancer_sku", None
                )
                cluster_details["outbound_type"] = getattr(np, "outbound_type", None)

            # SKU information
            if hasattr(cluster, "sku") and cluster.sku:
                cluster_details["sku"] = {
                    "name": getattr(cluster.sku, "name", None),
                    "tier": getattr(cluster.sku, "tier", None),
                }

            # Identity
            if hasattr(cluster, "identity") and cluster.identity:
                cluster_details["identity"] = {
                    "type": getattr(cluster.identity, "type", None),
                    "principal_id": getattr(cluster.identity, "principal_id", None),
                }

            # API Server Access
            if (
                hasattr(cluster, "api_server_access_profile")
                and cluster.api_server_access_profile
            ):
                cluster_details["api_server_access"] = {
                    "authorized_ip_ranges": getattr(
                        cluster.api_server_access_profile, "authorized_ip_ranges", []
                    ),
                    "enable_private_cluster": getattr(
                        cluster.api_server_access_profile,
                        "enable_private_cluster",
                        False,
                    ),
                }

            # Auto-upgrade profile
            if (
                hasattr(cluster, "auto_upgrade_profile")
                and cluster.auto_upgrade_profile
            ):
                cluster_details["auto_upgrade_profile"] = {
                    "upgrade_channel": getattr(
                        cluster.auto_upgrade_profile, "upgrade_channel", None
                    )
                }

            # Features
            cluster_details["features"] = {
                "azure_rbac": (
                    getattr(cluster, "enable_rbac", False)
                    if hasattr(cluster, "enable_rbac")
                    else False
                ),
                "oidc_issuer_enabled": hasattr(cluster, "oidc_issuer_profile")
                and getattr(cluster, "oidc_issuer_profile", None) is not None,
                "defender_enabled": (
                    hasattr(cluster, "security_profile")
                    and getattr(cluster.security_profile, "defender", None)
                    if hasattr(cluster, "security_profile")
                    else False
                ),
            }

            # Tags
            if hasattr(cluster, "tags") and cluster.tags:
                cluster_details["tags"] = cluster.tags

            builder.set_cluster_details(**cluster_details)

        # Debug: Check cluster network profile for subnet information
        if hasattr(cluster, "network_profile") and cluster.network_profile:
            logger.debug(
                f"Cluster network_profile attributes: {dir(cluster.network_profile)}"
            )
            logger.debug(
                f"Cluster service_cidr: {getattr(cluster.network_profile, 'service_cidr', 'NOT_FOUND')}"
            )
            logger.debug(
                f"Cluster pod_cidr: {getattr(cluster.network_profile, 'pod_cidr', 'NOT_FOUND')}"
            )
            logger.debug(
                f"Cluster docker_bridge_cidr: {getattr(cluster.network_profile, 'docker_bridge_cidr', 'NOT_FOUND')}"
            )

        # Debug: Check if cluster has agent_pool_profiles with subnet info
        if hasattr(cluster, "agent_pool_profiles"):
            logger.debug(
                f"Cluster has {len(cluster.agent_pool_profiles)} agent pool profiles"
            )
            for profile in cluster.agent_pool_profiles:
                logger.debug(
                    f"Profile '{profile.name}' - vnet_subnet_id: {getattr(profile, 'vnet_subnet_id', 'NOT_FOUND')}"
                )

        # Add enhanced node pool information to report
        for pool in node_pools:
            # Debug: Log key attributes to understand what's available
            logger.debug(
                f"Node pool '{pool.name}' - vnet_subnet_id: {getattr(pool, 'vnet_subnet_id', 'NOT_FOUND')}"
            )
            logger.debug(
                f"Node pool '{pool.name}' - pod_subnet_id: {getattr(pool, 'pod_subnet_id', 'NOT_FOUND')}"
            )
            logger.debug(
                f"Node pool '{pool.name}' - network_profile: {getattr(pool, 'network_profile', 'NOT_FOUND')}"
            )

            # Basic pool data
            pool_data = {
                "name": pool.name,
                "mode": getattr(pool, "mode", "User"),
                "provisioning_state": pool.provisioning_state,
                "count": pool.count,
                "vm_size": pool.vm_size,
                "max_pods": pool.max_pods or 30,
            }

            # Autoscaling configuration
            pool_data["autoscaling"] = {
                "enabled": getattr(pool, "enable_auto_scaling", False),
                "min_count": getattr(pool, "min_count", None),
                "max_count": getattr(pool, "max_count", None),
            }

            # OS configuration
            pool_data["os_type"] = getattr(pool, "os_type", "Linux")
            pool_data["os_sku"] = getattr(pool, "os_sku", None)
            pool_data["os_disk_size_gb"] = getattr(pool, "os_disk_size_gb", 128)
            pool_data["os_disk_type"] = getattr(pool, "os_disk_type", "Managed")

            # Availability zones
            if hasattr(pool, "availability_zones") and pool.availability_zones:
                pool_data["availability_zones"] = pool.availability_zones

            # Node public IP setting
            pool_data["enable_node_public_ip"] = getattr(
                pool, "enable_node_public_ip", False
            )

            # Upgrade settings
            if hasattr(pool, "upgrade_settings") and pool.upgrade_settings:
                pool_data["upgrade_settings"] = {
                    "max_surge": getattr(pool.upgrade_settings, "max_surge", None)
                }

            # Node labels
            if hasattr(pool, "node_labels") and pool.node_labels:
                pool_data["node_labels"] = pool.node_labels

            # Node taints
            if hasattr(pool, "node_taints") and pool.node_taints:
                pool_data["node_taints"] = pool.node_taints

            # Cost estimation
            try:
                cost_estimate = estimate_node_pool_cost(
                    vm_size=pool.vm_size,
                    node_count=pool.count or 0,
                    os_disk_size_gb=getattr(pool, "os_disk_size_gb", 128),
                    enable_public_ip=getattr(pool, "enable_node_public_ip", False),
                )
                pool_data["cost_estimate"] = cost_estimate
            except Exception as e:
                logger.debug(f"Could not estimate cost for pool '{pool.name}': {e}")

            # Try multiple ways to get subnet information
            subnet_id = None

            # Method 1: Check vnet_subnet_id attribute
            if hasattr(pool, "vnet_subnet_id") and pool.vnet_subnet_id:
                subnet_id = pool.vnet_subnet_id
                pool_data["vnet_subnet_id"] = subnet_id
                logger.debug(
                    f"Found vnet_subnet_id for pool '{pool.name}': {subnet_id}"
                )
            # Method 2: Check network_profile
            elif hasattr(pool, "network_profile") and pool.network_profile:
                if (
                    hasattr(pool.network_profile, "vnet_subnet_id")
                    and pool.network_profile.vnet_subnet_id
                ):
                    subnet_id = pool.network_profile.vnet_subnet_id
                    pool_data["vnet_subnet_id"] = subnet_id
                    logger.debug(
                        f"Found subnet_id in network_profile for '{pool.name}': {subnet_id}"
                    )

            if subnet_id:
                parts = subnet_id.split("/")
                if len(parts) >= 11:
                    pool_data["subnet_name"] = parts[10]
                    pool_data["vnet_name"] = parts[8]
                    pool_data["subnet_resource_group"] = parts[4]
            else:
                logger.warning(
                    f"Node pool '{pool.name}' has no subnet ID - cluster may be using kubenet or Azure-managed VNET"
                )

            # Add error details if provisioning failed
            if pool.provisioning_state == "Failed":
                error_msg = getattr(pool, "provisioning_state_message", "Unknown error")
                pool_data["error_details"] = {
                    "code": "PROVISIONING_FAILED",
                    "message": error_msg,
                }

            builder.add_node_pool(pool_data)

        # Collect unique subnets from node pools
        subnets_to_check = {}

        # Method 1: Check each node pool for subnet ID
        for pool in node_pools:
            subnet_id = None

            # Try vnet_subnet_id attribute
            if hasattr(pool, "vnet_subnet_id") and pool.vnet_subnet_id:
                subnet_id = pool.vnet_subnet_id
            # Try agent_pool_profile
            elif hasattr(pool, "agent_pool_profile") and pool.agent_pool_profile:
                if hasattr(pool.agent_pool_profile, "vnet_subnet_id"):
                    subnet_id = pool.agent_pool_profile.vnet_subnet_id

            if subnet_id:
                parts = subnet_id.split("/")
                if len(parts) >= 11:
                    subnet_rg = parts[4]
                    vnet_name = parts[8]
                    subnet_name = parts[10]
                    subnet_key = f"{subnet_rg}/{vnet_name}/{subnet_name}"

                    if subnet_key not in subnets_to_check:
                        subnets_to_check[subnet_key] = {
                            "resource_group": subnet_rg,
                            "vnet_name": vnet_name,
                            "subnet_name": subnet_name,
                        }
                        logger.debug(f"Added subnet to check: {subnet_key}")

        # Method 2: Fallback to cluster's agent pool profiles if no subnets found
        if not subnets_to_check and hasattr(cluster, "agent_pool_profiles"):
            logger.info(
                "No subnets found from node pools, checking cluster agent pool profiles..."
            )
            for profile in cluster.agent_pool_profiles:
                if hasattr(profile, "vnet_subnet_id") and profile.vnet_subnet_id:
                    subnet_id = profile.vnet_subnet_id
                    parts = subnet_id.split("/")
                    if len(parts) >= 11:
                        subnet_rg = parts[4]
                        vnet_name = parts[8]
                        subnet_name = parts[10]
                        subnet_key = f"{subnet_rg}/{vnet_name}/{subnet_name}"

                        if subnet_key not in subnets_to_check:
                            subnets_to_check[subnet_key] = {
                                "resource_group": subnet_rg,
                                "vnet_name": vnet_name,
                                "subnet_name": subnet_name,
                            }
                            logger.info(
                                f"Found subnet in cluster profile for '{profile.name}': {subnet_name}"
                            )

        if not subnets_to_check:
            logger.warning(
                "No custom VNet subnets found - cluster may be using Azure-managed networking or overlay mode"
            )
            logger.info(
                "Will analyze pod CIDR capacity instead of VNet subnet capacity"
            )

            # For Azure-managed or overlay networking, add pod CIDR information
            if hasattr(cluster, "network_profile") and cluster.network_profile:
                pod_cidr = getattr(cluster.network_profile, "pod_cidr", None)
                service_cidr = getattr(cluster.network_profile, "service_cidr", None)

                if pod_cidr:
                    # Calculate pod CIDR capacity
                    if "/" in pod_cidr:
                        prefix_len = int(pod_cidr.split("/")[1])
                        total_ips = 2 ** (32 - prefix_len)

                        # Calculate current pod IP requirements
                        total_required_ips = 0
                        for pool in node_pools:
                            max_pods = pool.max_pods or 30
                            node_count = pool.count or 0
                            total_required_ips += max_pods * node_count

                        available_ips = total_ips - total_required_ips
                        utilization = (
                            (total_required_ips / total_ips * 100)
                            if total_ips > 0
                            else 0
                        )

                        # Determine status based on utilization
                        if utilization < 70:
                            status = "HEALTHY"
                        elif utilization < 85:
                            status = "WARNING"
                        else:
                            status = "CRITICAL"

                        subnet_data = {
                            "name": "pod-cidr (Azure-managed)",
                            "cidr": pod_cidr,
                            "resource_group": "system-managed",
                            "vnet_name": "azure-managed",
                            "total_ips": total_ips,
                            "used_ips": total_required_ips,
                            "available_ips": available_ips,
                            "utilization_percent": round(utilization, 2),
                            "status": status,
                            "threshold_warning": 70.0,
                            "threshold_critical": 85.0,
                            "associated_node_pools": [pool.name for pool in node_pools],
                            "node_count": sum(pool.count or 0 for pool in node_pools),
                            "ip_breakdown": {
                                "azure_reserved": 0,  # Overlay mode doesn't reserve IPs
                                "node_ips": 0,  # Nodes use separate Azure-managed subnet
                                "pod_ips_allocated": total_required_ips,
                                "service_ips": 0,
                                "available": available_ips,
                            },
                            "note": "Pod CIDR for overlay networking - nodes use separate Azure-managed subnet",
                        }

                        builder.add_subnet(subnet_data)
                        logger.info(
                            f"Added pod CIDR analysis: {total_required_ips}/{total_ips} IPs required ({utilization:.1f}% utilization)"
                        )

                if service_cidr:
                    logger.debug(
                        f"Service CIDR: {service_cidr} (used for Kubernetes services, not analyzed for capacity)"
                    )

        # Fetch and add subnet information
        for subnet_info in subnets_to_check.values():
            try:
                subnet = network_client.get_subnet(
                    subnet_info["resource_group"],
                    subnet_info["vnet_name"],
                    subnet_info["subnet_name"],
                )

                # Parse CIDR for IP calculation
                cidr = subnet.address_prefix
                if "/" in cidr:
                    prefix_len = int(cidr.split("/")[1])
                    total_ips = 2 ** (32 - prefix_len)
                    usable_ips = total_ips - 5  # Azure reserves 5 IPs

                    # Count used IPs from IP configurations
                    used_ips = (
                        len(subnet.ip_configurations) if subnet.ip_configurations else 0
                    )
                    available_ips = usable_ips - used_ips
                    utilization = (used_ips / usable_ips * 100) if usable_ips > 0 else 0

                    # Determine status based on utilization
                    if utilization < 70:
                        status = "HEALTHY"
                    elif utilization < 85:
                        status = "WARNING"
                    else:
                        status = "CRITICAL"

                    # Find associated node pools
                    associated_pools = []
                    node_count = 0
                    for pool in node_pools:
                        pool_subnet_id = getattr(pool, "vnet_subnet_id", None)
                        if (
                            pool_subnet_id
                            and subnet_info["subnet_name"] in pool_subnet_id
                        ):
                            associated_pools.append(pool.name)
                            node_count += pool.count or 0

                    subnet_data = {
                        "name": subnet_info["subnet_name"],
                        "cidr": cidr,
                        "resource_group": subnet_info["resource_group"],
                        "vnet_name": subnet_info["vnet_name"],
                        "total_ips": total_ips,
                        "used_ips": used_ips,
                        "available_ips": available_ips,
                        "utilization_percent": round(utilization, 2),
                        "status": status,
                        "threshold_warning": 70.0,
                        "threshold_critical": 85.0,
                        "associated_node_pools": associated_pools,
                        "node_count": node_count,
                        "ip_breakdown": {
                            "azure_reserved": 5,  # First 4 + last IP
                            "node_ips": node_count,  # Approximate
                            "pod_ips_allocated": (
                                used_ips - node_count if used_ips > node_count else 0
                            ),
                            "available": available_ips,
                        },
                    }

                    builder.add_subnet(subnet_data)
                    logger.debug(
                        f"Added subnet {subnet_info['subnet_name']}: {used_ips}/{usable_ips} IPs used ({utilization:.1f}%)"
                    )
            except Exception as e:
                logger.warning(
                    f"Could not fetch subnet details for {subnet_info['subnet_name']}: {str(e)}"
                )

        # Run diagnostics
        all_issues = []

        # 1. Check IP exhaustion
        logger.info("Checking for IP exhaustion...")
        ip_issues = check_ip_exhaustion(
            aks_client, cluster, node_pools, network_client, logger
        )
        for issue in ip_issues:
            builder.add_issue(issue)

        # Add IP exhaustion diagnostic result
        ip_status = "PASS" if len(ip_issues) == 0 else "FAIL"
        ip_risk = "LOW" if len(ip_issues) == 0 else "HIGH"
        builder.add_diagnostic_result(
            diagnostic_type="ip_exhaustion",
            status=ip_status,
            risk_level=ip_risk,
            issues=ip_issues,
            details={
                "total_checks": 1,
                "checks_passed": 1 if len(ip_issues) == 0 else 0,
                "checks_failed": len(ip_issues),
            },
        )

        # 2. Check provisioning state
        logger.info("Checking provisioning state...")
        prov_issues = check_provisioning_state(node_pools, logger)
        for issue in prov_issues:
            all_issues.append(
                create_issue(
                    severity=issue["severity"],
                    code="PROVISIONING_STATE",
                    message=issue["title"],
                    affected_resource=issue["affected_resource"],
                    details={"description": issue["description"]},
                )
            )

        # Add provisioning state diagnostic result
        failed_pools = [p for p in node_pools if p.provisioning_state != "Succeeded"]
        prov_status = "PASS" if len(failed_pools) == 0 else "FAIL"
        prov_risk = "CRITICAL" if len(failed_pools) > 0 else "LOW"
        builder.add_diagnostic_result(
            diagnostic_type="provisioning_state",
            status=prov_status,
            risk_level=prov_risk,
            issues=prov_issues,
            details={
                "total_pools": len(node_pools),
                "succeeded_pools": len(
                    [p for p in node_pools if p.provisioning_state == "Succeeded"]
                ),
                "failed_pools": len(failed_pools),
                "failed_pool_names": [p.name for p in failed_pools],
            },
        )

        # 3. Check subnet capacity
        logger.info("Checking subnet capacity...")
        subnet_issues = check_subnet_capacity(network_client, node_pools, logger)
        for issue in subnet_issues:
            builder.add_issue(issue)

        # Add subnet capacity diagnostic result
        subnets_data = builder.data.get("subnets", [])
        critical_subnets = [
            s for s in subnets_data if s.get("utilization_percent", 0) >= 85
        ]
        warning_subnets = [
            s for s in subnets_data if 70 <= s.get("utilization_percent", 0) < 85
        ]
        subnet_status = (
            "FAIL"
            if len(critical_subnets) > 0
            else ("WARNING" if len(warning_subnets) > 0 else "PASS")
        )
        subnet_risk = (
            "CRITICAL"
            if len(critical_subnets) > 0
            else ("MEDIUM" if len(warning_subnets) > 0 else "LOW")
        )
        builder.add_diagnostic_result(
            diagnostic_type="subnet_capacity",
            status=subnet_status,
            risk_level=subnet_risk,
            issues=subnet_issues,
            details={
                "total_subnets": len(subnets_data),
                "healthy_subnets": len(
                    [s for s in subnets_data if s.get("utilization_percent", 0) < 70]
                ),
                "warning_subnets": len(warning_subnets),
                "critical_subnets": len(critical_subnets),
                "max_utilization_percent": (
                    max([s.get("utilization_percent", 0) for s in subnets_data])
                    if subnets_data
                    else 0
                ),
            },
        )

        # 4. Check maxPods and add enhanced issue information
        logger.info("Checking maxPods configuration...")
        maxpods_issues = check_max_pods(node_pools, logger)
        for issue in maxpods_issues:
            # Calculate IP waste for impact
            pool = next(
                (p for p in node_pools if p.name == issue["affected_resource"]), None
            )
            if pool:
                max_pods = pool.max_pods or 30
                node_count = pool.count or 0
                allocated_ips = max_pods * node_count
                recommended_max_pods = 30  # Safe default

                # Enhanced issue with impact and remediation
                enhanced_issue = create_issue(
                    severity=issue["severity"],
                    code="MAX_PODS_HIGH",
                    message=issue["title"],
                    affected_resource=issue["affected_resource"],
                    details={
                        "description": issue["description"],
                        "current_max_pods": max_pods,
                        "node_count": node_count,
                        "allocated_ips": allocated_ips,
                        "recommended_max_pods": recommended_max_pods,
                        "potential_ip_savings": allocated_ips
                        - (recommended_max_pods * node_count),
                    },
                    remediation=f"Consider reducing maxPods from {max_pods} to {recommended_max_pods} for better IP efficiency. Create a new node pool with optimal settings.",
                )
                all_issues.append(enhanced_issue)
            else:
                all_issues.append(
                    create_issue(
                        severity=issue["severity"],
                        code="MAX_PODS_HIGH",
                        message=issue["title"],
                        affected_resource=issue["affected_resource"],
                        details={"description": issue["description"]},
                    )
                )

        # Add maxPods configuration diagnostic result
        high_maxpods_pools = [p for p in node_pools if (p.max_pods or 30) > 50]
        maxpods_status = "WARNING" if len(high_maxpods_pools) > 0 else "PASS"
        maxpods_risk = "MEDIUM" if len(high_maxpods_pools) > 0 else "LOW"
        builder.add_diagnostic_result(
            diagnostic_type="max_pods_configuration",
            status=maxpods_status,
            risk_level=maxpods_risk,
            issues=maxpods_issues,
            details={
                "total_pools": len(node_pools),
                "pools_with_high_maxpods": len(high_maxpods_pools),
                "pool_maxpods_settings": {p.name: p.max_pods or 30 for p in node_pools},
                "recommended_maxpods": 30,
                "note": "High maxPods values may waste IP addresses if pods are not fully utilized",
            },
        )

        # Add all issues to report
        for issue in all_issues:
            builder.add_issue(issue)

        # Pod-level analysis (optional)
        if args.include_pod_analysis:
            logger.warning("Pod-level analysis requested but not yet fully implemented")
            print("⚠️  Pod analysis feature coming soon")

        # Cost analysis (optional)
        if args.include_cost_analysis:
            logger.warning("Cost analysis requested but not yet fully implemented")
            print("⚠️  Cost analysis feature coming soon")

        # Determine overall status and calculate comprehensive metrics
        critical_issues = [i for i in all_issues if i.get("severity") == "CRITICAL"]
        warning_issues = [i for i in all_issues if i.get("severity") == "WARNING"]

        if critical_issues:
            overall_status = "CRITICAL"
            risk_level = "CRITICAL"
        elif warning_issues:
            overall_status = "WARNING"
            risk_level = "HIGH"
        else:
            overall_status = "HEALTHY"
            risk_level = "LOW"

        # Calculate subnet utilization and IP waste
        max_subnet_utilization = 0
        total_allocated_ips = 0
        total_used_ips = 0

        for subnet in builder.data.get("subnets", []):
            util = subnet.get("utilization_percent", 0)
            max_subnet_utilization = max(max_subnet_utilization, util)
            total_allocated_ips += subnet.get("total_ips", 0)
            total_used_ips += subnet.get("used_ips", 0)

        # Calculate pod capacity utilization
        total_max_pods = 0
        for pool in node_pools:
            max_pods = pool.max_pods or 30
            node_count = pool.count or 0
            total_max_pods += max_pods * node_count

        pod_utilization = (
            (total_used_ips / total_max_pods * 100) if total_max_pods > 0 else 0
        )
        ip_waste_percent = 100 - pod_utilization

        # Calculate health score
        health_score = calculate_health_score(
            issues=all_issues,
            warnings=len(warning_issues),
            critical=len(critical_issues),
            subnet_utilization=max_subnet_utilization,
            ip_waste_percent=ip_waste_percent,
        )

        # Calculate efficiency metrics
        efficiency_metrics = {
            "pod_capacity_utilization": round(pod_utilization, 2),
            "ip_waste_percent": round(ip_waste_percent, 2),
            "subnet_utilization": round(max_subnet_utilization, 2),
            "cost_efficiency_score": max(
                0, 100 - ip_waste_percent
            ),  # Simple: 100% - waste%
        }

        # Calculate cost impact
        total_monthly_cost = 0
        potential_savings = 0

        for pool_data in builder.data.get("node_pools", []):
            if "cost_estimate" in pool_data:
                total_monthly_cost += pool_data["cost_estimate"].get("total_monthly", 0)

        # Estimate potential savings from IP waste
        ip_waste_cost = calculate_ip_waste_cost(total_max_pods, total_used_ips)
        potential_savings = ip_waste_cost.get("monthly_cost", 0)

        cost_impact = {
            "current_monthly_estimated_usd": round(total_monthly_cost, 2),
            "potential_savings_usd": round(potential_savings, 2),
            "optimization_opportunity_percent": round(
                (
                    (potential_savings / total_monthly_cost * 100)
                    if total_monthly_cost > 0
                    else 0
                ),
                2,
            ),
        }

        # Calculate capacity outlook
        available_ips = total_allocated_ips - total_used_ips
        utilization_threshold_critical = 85
        can_upgrade = (
            max_subnet_utilization < utilization_threshold_critical
        )  # Simplified check

        capacity_outlook = {
            "can_upgrade_safely": can_upgrade,
            "headroom_percent": (
                round(100 - max_subnet_utilization, 2)
                if max_subnet_utilization > 0
                else 100
            ),
        }

        # Set comprehensive summary
        builder.set_summary(
            overall_status=overall_status,
            risk_level=risk_level,
            health_score=health_score,
            efficiency_metrics=efficiency_metrics,
            cost_impact=cost_impact,
            capacity_outlook=capacity_outlook,
        )

        # Add basic recommendations
        if critical_issues:
            builder.add_recommendation(
                create_recommendation(
                    priority="CRITICAL",
                    category="REMEDIATION",
                    title="Address critical issues immediately",
                    description=f"Found {len(critical_issues)} critical issues requiring immediate attention",
                    recommendation="Review issues and take corrective action",
                    steps=[
                        "Review each critical issue",
                        "Implement recommended fixes",
                        "Verify resolution",
                    ],
                )
            )

        # Build report
        report_data = builder.build()

        # Format output
        format_enum = OutputFormat(args.format)
        formatted_output = format_report(report_data, format_enum)

        # Save or print
        if args.output or args.format != "text":
            # Generate timestamped filename in reports directory
            output_path = get_report_path(
                cluster_name=cluster_name,
                output_format=args.format,
                custom_filename=args.output,
            )

            # Save to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(formatted_output)

            logger.info(f"Report saved to: {output_path}")
            print(f"✅ Report saved to: {output_path}")
        else:
            # Print to stdout for text format when no output file specified
            try:
                print(formatted_output)
            except UnicodeEncodeError:
                # Fallback for terminals that can't handle Unicode
                print(
                    formatted_output.encode("ascii", errors="replace").decode("ascii")
                )

        logger.info("Diagnostic completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Diagnostic failed: {str(e)}", exc_info=True)
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    args = parse_arguments()
    return run_diagnostic(args)


if __name__ == "__main__":
    sys.exit(main())
