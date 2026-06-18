"""Example usage of enhanced JSON output formats."""
import json
from datetime import datetime
from reports.formatters import (
    DiagnosticReportBuilder,
    OutputFormat,
    format_report,
    create_issue,
    create_recommendation
)
from reports.json_validator import save_json_report, ReportValidator


def create_example_report():
    """Create an example diagnostic report with all features."""
    
    # Initialize report builder
    builder = DiagnosticReportBuilder(
        cluster_name="production-aks-cluster",
        resource_group="aks-prod-rg",
        subscription_id="12345678-1234-1234-1234-123456789abc"
    )
    
    # Set cluster details
    builder.set_cluster_details(
        location="eastus",
        k8s_version="1.28.3",
        network_plugin="azure",
        dns_service_ip="10.0.0.10",
        service_cidr="10.0.0.0/16",
        pod_cidr=None
    )
    
    # Add provisioning state diagnostic
    provisioning_issues = [
        create_issue(
            severity="CRITICAL",
            code="SubnetIsFull",
            message="Subnet systempool-sn with address prefix 10.53.0.0/24 does not have enough capacity for 99 IP addresses",
            affected_resource="sysnodepool",
            details={
                "subnet": "systempool-sn",
                "required_ips": 99,
                "address_prefix": "10.53.0.0/24"
            },
            remediation="Migrate node pool to a larger subnet (recommended: /22 or /23)"
        ),
        create_issue(
            severity="CRITICAL",
            code="ProvisioningFailed",
            message="Node pool provisioning failed due to insufficient IP capacity",
            affected_resource="webnodepool0",
            details={
                "error_code": "SubnetIsFull",
                "provisioning_state": "Failed"
            }
        )
    ]
    
    builder.add_diagnostic_result(
        "provisioning_state",
        status="FAIL",
        risk_level="CRITICAL",
        issues=provisioning_issues,
        details={
            "total_pools_checked": 2,
            "failed_pools": 2,
            "blocked_operations": ["upgrade", "scale", "reconcile"]
        }
    )
    
    # Add IP exhaustion diagnostic
    ip_issues = [
        create_issue(
            severity="ERROR",
            code="IP_NEAR_EXHAUSTION",
            message="Subnet IP utilization at 95%, critical threshold reached",
            affected_resource="systempool-sn",
            details={
                "used_ips": 240,
                "available_ips": 11,
                "utilization_percentage": 95.6
            },
            remediation="Immediate action required: migrate to larger subnet"
        )
    ]
    
    builder.add_diagnostic_result(
        "ip_exhaustion",
        status="FAIL",
        risk_level="CRITICAL",
        issues=ip_issues
    )
    
    # Add subnet capacity diagnostic
    subnet_issues = [
        create_issue(
            severity="WARNING",
            code="INSUFFICIENT_HEADROOM",
            message="Subnet has insufficient IP headroom for safe operations",
            affected_resource="systempool-sn",
            details={
                "recommended_headroom_percentage": 20,
                "actual_headroom_percentage": 4.4
            }
        )
    ]
    
    builder.add_diagnostic_result(
        "subnet_capacity",
        status="FAIL",
        risk_level="HIGH",
        issues=subnet_issues,
        details={
            "total_subnets_checked": 2,
            "capacity_warnings": 1
        }
    )
    
    # Add maxPods diagnostic
    maxpods_issues = [
        create_issue(
            severity="WARNING",
            code="MAX_PODS_TOO_HIGH",
            message="maxPods=100 is dangerously high for Standard_D2s_v3 nodes",
            affected_resource="sysnodepool",
            details={
                "configured_max_pods": 100,
                "recommended_max_pods": 30,
                "vm_size": "Standard_D2s_v3"
            },
            remediation="Reduce maxPods to 30-50 for optimal performance and safety"
        )
    ]
    
    builder.add_diagnostic_result(
        "max_pods",
        status="FAIL",
        risk_level="MEDIUM",
        issues=maxpods_issues
    )
    
    # Add node pools
    builder.add_node_pool({
        "name": "sysnodepool",
        "mode": "System",
        "provisioning_state": "Failed",
        "count": 2,
        "vm_size": "Standard_D2s_v3",
        "max_pods": 100,
        "enable_auto_scaling": True,
        "min_count": 1,
        "max_count": 3,
        "subnet_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourceGroups/aks-prod-rg/providers/Microsoft.Network/virtualNetworks/aks-vnet/subnets/systempool-sn",
        "subnet_name": "systempool-sn",
        "upgrade_settings": {
            "max_surge": "10%",
            "max_unavailable": 0
        },
        "ip_allocation": {
            "required_ips_per_node": 101,
            "total_required_ips": 202,
            "current_ip_usage": 202,
            "potential_max_ips": 303
        },
        "error_details": {
            "code": "SubnetIsFull",
            "message": "Subnet systempool-sn with address prefix 10.53.0.0/24 does not have enough capacity for 99 IP addresses"
        }
    })
    
    builder.add_node_pool({
        "name": "webnodepool0",
        "mode": "User",
        "provisioning_state": "Failed",
        "count": 1,
        "vm_size": "Standard_D2s_v3",
        "max_pods": 100,
        "enable_auto_scaling": True,
        "min_count": 1,
        "max_count": 3,
        "subnet_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourceGroups/aks-prod-rg/providers/Microsoft.Network/virtualNetworks/aks-vnet/subnets/userpool-sn0",
        "subnet_name": "userpool-sn0",
        "upgrade_settings": {
            "max_surge": "10%",
            "max_unavailable": 0
        },
        "ip_allocation": {
            "required_ips_per_node": 101,
            "total_required_ips": 101,
            "current_ip_usage": 101,
            "potential_max_ips": 101
        }
    })
    
    # Add subnets
    builder.add_subnet({
        "name": "systempool-sn",
        "id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourceGroups/aks-prod-rg/providers/Microsoft.Network/virtualNetworks/aks-vnet/subnets/systempool-sn",
        "address_prefix": "10.53.0.0/24",
        "address_space_size": 256,
        "available_ips": 11,
        "used_ips": 240,
        "reserved_ips": 5,
        "usage_percentage": 95.6,
        "attached_node_pools": ["sysnodepool"],
        "is_full": True,
        "remaining_capacity": {
            "additional_nodes_max_pods_30": 0,
            "additional_nodes_max_pods_50": 0,
            "additional_nodes_max_pods_100": 0
        }
    })
    
    builder.add_subnet({
        "name": "userpool-sn0",
        "id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourceGroups/aks-prod-rg/providers/Microsoft.Network/virtualNetworks/aks-vnet/subnets/userpool-sn0",
        "address_prefix": "10.53.1.0/24",
        "address_space_size": 256,
        "available_ips": 145,
        "used_ips": 106,
        "reserved_ips": 5,
        "usage_percentage": 43.6,
        "attached_node_pools": ["webnodepool0"],
        "is_full": False,
        "remaining_capacity": {
            "additional_nodes_max_pods_30": 4,
            "additional_nodes_max_pods_50": 2,
            "additional_nodes_max_pods_100": 1
        }
    })
    
    # Add recommendations
    builder.add_recommendation(create_recommendation(
        priority="CRITICAL",
        category="IP_EXHAUSTION",
        title="Migrate system node pool to larger subnet",
        description="The system node pool is in Failed state due to subnet IP exhaustion. This blocks all cluster operations including upgrades and scaling.",
        affected_resources=["sysnodepool", "systempool-sn"],
        impact="Cluster is in degraded state. Cannot perform upgrades, scaling, or node replacements.",
        recommendation="Create a new subnet with /22 CIDR (1024 IPs) and migrate the node pool.",
        steps=[
            "Create new subnet with 10.53.4.0/22 address space",
            "Create new system node pool 'sysnodepool-v2' in new subnet with maxPods=30",
            "Cordon and drain nodes from old pool",
            "Delete old 'sysnodepool' once drained",
            "Update cluster to use new pool as primary system pool"
        ],
        downtime="Zero downtime with proper migration sequence",
        automation=True,
        docs=[
            "https://docs.microsoft.com/azure/aks/use-multiple-node-pools",
            "https://docs.microsoft.com/azure/aks/configure-azure-cni"
        ]
    ))
    
    builder.add_recommendation(create_recommendation(
        priority="HIGH",
        category="MAX_PODS",
        title="Reduce maxPods configuration to safe levels",
        description="Current maxPods=100 is too high for Standard_D2s_v3 VM size and causes excessive IP consumption.",
        affected_resources=["sysnodepool", "webnodepool0"],
        impact="Increased risk of IP exhaustion, poor node performance, difficult troubleshooting.",
        recommendation="Set maxPods to 30-50 based on VM size and workload requirements.",
        steps=[
            "Analyze current pod density per node",
            "Create new node pools with maxPods=30",
            "Migrate workloads to new pools",
            "Remove old pools with high maxPods"
        ],
        downtime="Minimal with rolling migration",
        automation=False,
        docs=[
            "https://docs.microsoft.com/azure/aks/configure-azure-cni#maximum-pods-per-node"
        ]
    ))
    
    builder.add_recommendation(create_recommendation(
        priority="MEDIUM",
        category="CONFIGURATION",
        title="Use maxUnavailable instead of maxSurge for upgrades",
        description="Current upgrade settings use maxSurge which requires additional IP addresses. With limited subnet capacity, use maxUnavailable instead.",
        affected_resources=["sysnodepool", "webnodepool0"],
        impact="Upgrade operations may fail due to IP exhaustion even with adequate cluster capacity.",
        recommendation="Configure upgrade settings to use maxUnavailable=1 and maxSurge=null.",
        steps=[
            "Update node pool upgrade settings via Azure CLI or Portal",
            "Set maxUnavailable to 1 or 33%",
            "Set maxSurge to null or 0",
            "Test upgrade process in non-production environment"
        ],
        downtime="None for configuration change",
        automation=True,
        docs=[
            "https://docs.microsoft.com/azure/aks/upgrade-cluster"
        ]
    ))
    
    # Set summary
    builder.set_summary(
        overall_status="CRITICAL",
        risk_level="CRITICAL"
    )
    
    return builder.build()


def main():
    """Demonstrate all JSON output formats."""
    print("=== Generating Example Diagnostic Report ===\n")
    
    # Create example report
    report_data = create_example_report()
    
    # 1. JSON Pretty (default)
    print("\n1. JSON PRETTY FORMAT:")
    print("-" * 80)
    pretty_json = format_report(report_data, OutputFormat.JSON_PRETTY)
    print(pretty_json[:500] + "...\n")
    
    # 2. JSON Compact
    print("\n2. JSON COMPACT FORMAT:")
    print("-" * 80)
    compact_json = format_report(report_data, OutputFormat.JSON_COMPACT)
    print(compact_json[:200] + "...\n")
    
    # 3. YAML
    print("\n3. YAML FORMAT:")
    print("-" * 80)
    yaml_output = format_report(report_data, OutputFormat.YAML)
    print(yaml_output[:500] + "...\n")
    
    # 4. Text
    print("\n4. TEXT FORMAT:")
    print("-" * 80)
    text_output = format_report(report_data, OutputFormat.TEXT)
    print(text_output[:800] + "...\n")
    
    # 5. Markdown
    print("\n5. MARKDOWN FORMAT:")
    print("-" * 80)
    markdown_output = format_report(report_data, OutputFormat.MARKDOWN)
    print(markdown_output[:800] + "...\n")
    
    # Save to files
    print("\n=== Saving Reports to Files ===\n")
    
    # Save JSON with validation
    success, message = save_json_report(
        report_data, 
        "example_report.json",
        validate=True,
        enrich=True,
        pretty=True
    )
    print(f"JSON Report: {message}")
    
    # Validate the saved report
    print("\n=== Validating Saved Report ===\n")
    is_valid, errors = ReportValidator.validate_diagnostic_report(report_data)
    if is_valid:
        print("✓ Report is valid according to schema")
    else:
        print("✗ Report validation failed:")
        for error in errors:
            print(f"  - {error}")
    
    # Show summary
    summary = report_data['summary']
    print("\n=== Report Summary ===")
    print(f"Overall Status: {summary['overall_status']}")
    print(f"Risk Level: {summary['risk_level']}")
    print(f"Total Issues: {summary['total_issues']}")
    print(f"Critical Issues: {summary['critical_issues']}")
    print(f"Recommendations: {len(report_data['recommendations'])}")


if __name__ == "__main__":
    main()
