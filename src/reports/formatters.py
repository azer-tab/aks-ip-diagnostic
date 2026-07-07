"""Enhanced report formatters with multiple output format support."""

import json
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats."""

    TEXT = "text"
    JSON = "json"
    JSON_PRETTY = "json-pretty"
    JSON_COMPACT = "json-compact"
    YAML = "yaml"
    MARKDOWN = "markdown"
    HTML = "html"


class JSONFormatter:
    """Enhanced JSON formatter with multiple style options."""

    @staticmethod
    def format_compact(data: Dict[str, Any]) -> str:
        """Format as compact JSON (single line)."""
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def format_pretty(data: Dict[str, Any], indent: int = 2) -> str:
        """Format as pretty-printed JSON with indentation."""
        return json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=False)

    @staticmethod
    def format_sorted(data: Dict[str, Any], indent: int = 2) -> str:
        """Format as pretty-printed JSON with sorted keys."""
        return json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def format_minimal(data: Dict[str, Any]) -> str:
        """Format with minimal whitespace but remain readable."""
        return json.dumps(
            data, indent=None, separators=(", ", ": "), ensure_ascii=False
        )


class DiagnosticReportBuilder:
    """Builder for creating structured diagnostic reports."""

    def __init__(self, cluster_name: str, resource_group: str, subscription_id: str):
        self.cluster_name = cluster_name
        self.resource_group = resource_group
        self.subscription_id = subscription_id
        self.scan_start_time = datetime.utcnow()
        self.data = {
            "metadata": {
                "version": "1.0",
                "timestamp": self.scan_start_time.isoformat() + "Z",
                "tool_version": "1.0.0",
                "scan_duration_seconds": 0,
            },
            "cluster_info": {
                "name": cluster_name,
                "resource_group": resource_group,
                "subscription_id": subscription_id,
            },
            "diagnostics": {},
            "node_pools": [],
            "subnets": [],
            "recommendations": [],
            "summary": {
                "overall_status": "UNKNOWN",
                "risk_level": "UNKNOWN",
                "total_issues": 0,
                "critical_issues": 0,
                "warnings": 0,
                "healthy_checks": 0,
            },
        }

    def set_cluster_details(self, **kwargs):
        """
        Set additional cluster details dynamically.

        Accepts any keyword arguments and adds them to cluster_info.
        Common fields: location, k8s_version, network_plugin, network_mode,
        network_policy, dns_service_ip, service_cidr, pod_cidr, sku, identity,
        api_server_access, auto_upgrade_profile, features, tags, etc.
        """
        for key, value in kwargs.items():
            if value is not None:  # Only add non-None values
                self.data["cluster_info"][key] = value
        return self

    def add_diagnostic_result(
        self,
        diagnostic_type: str,
        status: str,
        risk_level: str,
        issues: List[Dict],
        details: Dict = None,
    ):
        """Add a diagnostic result."""
        self.data["diagnostics"][diagnostic_type] = {
            "status": status,
            "risk_level": risk_level,
            "issues": issues,
            "details": details or {},
            "checked_at": datetime.utcnow().isoformat() + "Z",
        }
        return self

    def add_node_pool(self, node_pool_data: Dict):
        """Add node pool information."""
        self.data["node_pools"].append(node_pool_data)
        return self

    def add_subnet(self, subnet_data: Dict):
        """Add subnet information."""
        self.data["subnets"].append(subnet_data)
        return self

    def add_recommendation(self, recommendation: Dict):
        """Add a recommendation."""
        self.data["recommendations"].append(recommendation)
        return self

    def add_issue(self, issue: Dict):
        """Add an issue to the diagnostics section."""
        # Store issues in a general issues list if it doesn't exist
        if "issues" not in self.data:
            self.data["issues"] = []
        self.data["issues"].append(issue)
        return self

    def set_summary(
        self,
        overall_status: str,
        risk_level: str,
        health_score: Dict = None,
        efficiency_metrics: Dict = None,
        cost_impact: Dict = None,
        capacity_outlook: Dict = None,
    ):
        """Set comprehensive summary information with health scoring and efficiency metrics."""
        # Calculate issue counts from diagnostics
        total_issues = 0
        critical_issues = 0
        warnings = 0
        healthy_checks = 0

        # Count issues from diagnostics section
        for diagnostic in self.data["diagnostics"].values():
            if diagnostic["status"] == "FAIL":
                issues = diagnostic.get("issues", [])
                total_issues += len(issues)
                for issue in issues:
                    severity = issue.get("severity", "WARNING")
                    if severity == "CRITICAL" or severity == "ERROR":
                        critical_issues += 1
                    elif severity == "WARNING":
                        warnings += 1
            elif diagnostic["status"] == "PASS":
                healthy_checks += 1

        # Also count issues from the general issues array
        if "issues" in self.data and self.data["issues"]:
            for issue in self.data["issues"]:
                total_issues += 1
                severity = issue.get("severity", "WARNING")
                if severity == "CRITICAL" or severity == "ERROR":
                    critical_issues += 1
                elif severity == "WARNING":
                    warnings += 1

        # Build summary with all metrics
        self.data["summary"] = {
            "overall_status": overall_status,
            "risk_level": risk_level,
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "warnings": warnings,
            "healthy_checks": healthy_checks,
        }

        # Add health score if provided
        if health_score:
            self.data["summary"]["health_score"] = health_score.get("score")
            self.data["summary"]["health_grade"] = health_score.get("grade")

        # Add efficiency metrics if provided
        if efficiency_metrics:
            self.data["summary"]["efficiency_metrics"] = efficiency_metrics

        # Add cost impact if provided
        if cost_impact:
            self.data["summary"]["cost_impact"] = cost_impact

        # Add capacity outlook if provided
        if capacity_outlook:
            self.data["summary"]["capacity_outlook"] = capacity_outlook

        # Update scan duration
        scan_end_time = datetime.utcnow()
        duration = (scan_end_time - self.scan_start_time).total_seconds()
        self.data["metadata"]["scan_duration_seconds"] = round(duration, 2)

        return self

    def build(self) -> Dict:
        """Build and return the complete report data."""
        return self.data


def create_issue(
    severity: str,
    code: str,
    message: str,
    affected_resource: str = None,
    details: Dict = None,
    remediation: str = None,
) -> Dict:
    """Create a structured issue object."""
    issue = {"severity": severity, "code": code, "message": message}
    if affected_resource:
        issue["affected_resource"] = affected_resource
    if details:
        issue["details"] = details
    if remediation:
        issue["remediation"] = remediation
    return issue


def create_recommendation(
    priority: str,
    category: str,
    title: str,
    description: str,
    affected_resources: List[str] = None,
    impact: str = None,
    recommendation: str = None,
    steps: List[str] = None,
    downtime: str = None,
    automation: bool = False,
    docs: List[str] = None,
) -> Dict:
    """Create a structured recommendation object."""
    rec = {
        "priority": priority,
        "category": category,
        "title": title,
        "description": description,
    }
    if affected_resources:
        rec["affected_resources"] = affected_resources
    if impact:
        rec["impact"] = impact
    if recommendation:
        rec["recommendation"] = recommendation
    if steps:
        rec["implementation_steps"] = steps
    if downtime:
        rec["estimated_downtime"] = downtime
    rec["automation_available"] = automation
    if docs:
        rec["documentation_links"] = docs
    return rec


def format_report(
    report_data: Dict, output_format: OutputFormat = OutputFormat.JSON_PRETTY
) -> str:
    """Format report data according to specified output format."""
    if output_format == OutputFormat.JSON_COMPACT:
        return JSONFormatter.format_compact(report_data)
    elif output_format == OutputFormat.JSON_PRETTY:
        return JSONFormatter.format_pretty(report_data)
    elif output_format == OutputFormat.JSON:
        return JSONFormatter.format_sorted(report_data)
    elif output_format == OutputFormat.YAML:
        return yaml.dump(report_data, default_flow_style=False, sort_keys=False)
    elif output_format == OutputFormat.TEXT:
        return format_text_report(report_data)
    elif output_format == OutputFormat.MARKDOWN:
        return format_markdown_report(report_data)
    elif output_format == OutputFormat.HTML:
        return format_html_report(report_data)
    else:
        return JSONFormatter.format_pretty(report_data)


def _format_cost_analysis_text(cost_data: Dict) -> List[str]:
    """Helper function to format cost analysis section for text reports.

    Extracts cost information from the diagnostic details and formats it
    in a human-readable way with currency symbols and percentages.

    Args:
        cost_data: Cost analysis diagnostic data from report builder

    Returns:
        List of formatted text lines ready to append to report
    """
    lines = []
    details = cost_data.get("details", {})

    lines.append("\nCOST ANALYSIS:")
    lines.append(
        f"  Status: {cost_data.get('status')} (Financial Impact: {cost_data.get('risk_level')})"
    )

    # Current costs - shows baseline monthly/annual spending
    current_costs = details.get("current_costs", {})
    if current_costs:
        lines.append("\n  Current Monthly Costs:")
        lines.append(f"    IP Addresses: ${current_costs.get('ip_monthly', 0):.2f}")
        lines.append(f"    VM Compute:   ${current_costs.get('vm_monthly', 0):.2f}")
        lines.append(f"    Total:        ${current_costs.get('total_monthly', 0):.2f}")
        lines.append(f"    Annual Total: ${current_costs.get('total_annual', 0):.2f}")

    # Waste costs - money spent on unused IPs
    # This is the key metric that shows financial impact of inefficiency
    waste_costs = details.get("waste_costs", {})
    if waste_costs:
        waste_pct = waste_costs.get("waste_percentage", 0)
        lines.append("\n  💰 IP Waste Costs:")
        lines.append(
            f"    Unused IPs:   {waste_costs.get('unused_ip_count', 0)} ({waste_pct:.1f}% waste)"
        )
        lines.append(f"    Monthly Cost: ${waste_costs.get('monthly_cost', 0):.2f}")
        lines.append(f"    Annual Cost:  ${waste_costs.get('annual_cost', 0):.2f}")

        # Alert if waste exceeds 20% threshold (same as pod analysis warning level)
        if waste_pct > 20:
            lines.append(
                f"    ⚠️  High waste detected - over 20% of IP costs are wasted!"
            )

    # Total potential savings - combines all optimization opportunities
    total_savings = details.get("total_potential_savings", {})
    if total_savings and total_savings.get("monthly", 0) > 0:
        lines.append("\n  💡 Total Potential Savings:")
        lines.append(f"    Monthly:  ${total_savings.get('monthly', 0):.2f}")
        lines.append(f"    Annual:   ${total_savings.get('annual', 0):.2f}")
        lines.append(f"    3-Year:   ${total_savings.get('three_year', 0):.2f}")

    # ROI analysis - helps justify optimization work
    # Shows payback period and implementation effort estimate
    roi = details.get("roi_analysis", {})
    if roi:
        lines.append("\n  📊 ROI Analysis:")
        payback = roi.get("payback_period_months", 0)
        if payback > 0:
            lines.append(f"    Payback Period: {payback:.1f} months")
        lines.append(
            f"    3-Year ROI:     {roi.get('three_year_roi_percentage', 0):.0f}%"
        )

        impl_effort = roi.get("implementation_effort", "Unknown")
        lines.append(f"    Implementation: {impl_effort}")

    # Executive summary - high-level takeaway
    summary = details.get("summary", {})
    if summary:
        message = summary.get("message", "")
        if message:
            lines.append(f"\n  Summary: {message}")

    return lines


def format_text_report(report_data: Dict) -> str:
    """Format report as human-readable text."""
    lines = [
        "AKS IP Diagnostic Report",
        "",
        "Executive summary",
    ]
    # lines = []
    lines.append("=" * 80)
    lines.append("AKS IP EXHAUSTION DIAGNOSTIC REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Cluster info
    cluster = report_data.get("cluster_info", {})
    lines.append(f"Cluster: {cluster.get('name')}")
    lines.append(f"Resource Group: {cluster.get('resource_group')}")
    lines.append(f"Subscription: {cluster.get('subscription_id')}")
    if cluster.get("location"):
        lines.append(f"Location: {cluster.get('location')}")
    if cluster.get("kubernetes_version"):
        lines.append(f"Kubernetes Version: {cluster.get('kubernetes_version')}")
    lines.append("")

    # Metadata
    metadata = report_data.get("metadata", {})
    lines.append(f"Scan Timestamp: {metadata.get('timestamp')}")
    lines.append(f"Scan Duration: {metadata.get('scan_duration_seconds')}s")
    lines.append("")

    # Summary with visual status indicators
    summary = report_data.get("summary", {})
    overall_status = summary.get("overall_status")
    status_icon = (
        "✅"
        if overall_status == "HEALTHY"
        else "⚠️" if overall_status == "WARNING" else "❌"
    )

    lines.append("-" * 80)
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"{status_icon} Overall Status: {overall_status}")
    lines.append(f"   Risk Level: {summary.get('risk_level')}")
    lines.append(f"   Total Issues: {summary.get('total_issues')}")
    if summary.get("critical_issues", 0) > 0:
        lines.append(f"     ❌ Critical: {summary.get('critical_issues')}")
    if summary.get("warnings", 0) > 0:
        lines.append(f"     ⚠️  Warnings: {summary.get('warnings')}")
    if summary.get("healthy_checks", 0) > 0:
        lines.append(f"     ✅ Healthy Checks: {summary.get('healthy_checks')}")
    lines.append("")

    # All Issues (top-level issues array)
    all_issues = report_data.get("issues", [])
    if all_issues:
        lines.append("-" * 80)
        lines.append("ISSUES DETECTED")
        lines.append("-" * 80)
        for i, issue in enumerate(all_issues, 1):
            severity = issue.get("severity", "UNKNOWN")
            icon = (
                "❌"
                if severity == "CRITICAL"
                else "⚠️" if severity == "WARNING" else "ℹ️"
            )

            lines.append(
                f"\n{i}. {icon} [{severity}] {issue.get('message', 'No message')}"
            )
            if issue.get("affected_resource"):
                lines.append(f"   Resource: {issue.get('affected_resource')}")
            if issue.get("code"):
                lines.append(f"   Code: {issue.get('code')}")

            # Display details if available
            details = issue.get("details", {})
            if details:
                if isinstance(details, dict):
                    if details.get("description"):
                        lines.append(f"   Details: {details['description']}")
                    # Display subnet capacity details
                    if details.get("subnet_cidr"):
                        lines.append(f"   Subnet CIDR: {details['subnet_cidr']}")
                    if details.get("allocated_ips") is not None:
                        lines.append(f"   Allocated IPs: {details['allocated_ips']}")
                    if details.get("total_ips") is not None:
                        lines.append(f"   Total IPs: {details['total_ips']}")
                    if details.get("utilization_percent") is not None:
                        lines.append(
                            f"   Utilization: {details['utilization_percent']:.1f}%"
                        )
                    if details.get("available_ips") is not None:
                        lines.append(f"   Available IPs: {details['available_ips']}")
                    # Display recommendations
                    if details.get("recommendation"):
                        lines.append(
                            f"   💡 Recommendation: {details['recommendation']}"
                        )
        lines.append("")

    # Diagnostics
    diagnostics = report_data.get("diagnostics", {})
    if diagnostics:
        lines.append("-" * 80)
        lines.append("DIAGNOSTIC RESULTS")
        lines.append("-" * 80)
        for diag_name, diag_data in diagnostics.items():
            # Special formatting for cost analysis
            if diag_name == "cost_analysis":
                lines.extend(_format_cost_analysis_text(diag_data))
                continue

            lines.append(f"\n{diag_name.upper().replace('_', ' ')}:")
            lines.append(f"  Status: {diag_data.get('status')}")
            lines.append(f"  Risk Level: {diag_data.get('risk_level')}")
            issues = diag_data.get("issues", [])
            if issues:
                lines.append("  Issues:")
                for issue in issues:
                    severity = issue.get("severity", "UNKNOWN")
                    icon = (
                        "❌"
                        if severity == "CRITICAL"
                        else "⚠️" if severity == "WARNING" else "ℹ️"
                    )
                    lines.append(f"    {icon} [{severity}] {issue.get('message')}")
                    if issue.get("affected_resource"):
                        lines.append(
                            f"       Resource: {issue.get('affected_resource')}"
                        )
            else:
                lines.append("  ✅ No issues found")
        lines.append("")

    # Subnets
    subnets = report_data.get("subnets", [])
    if subnets:
        lines.append("-" * 80)
        lines.append("SUBNET INFORMATION")
        lines.append("-" * 80)
        for subnet in subnets:
            lines.append(f"\n{subnet.get('name')}:")
            lines.append(f"  CIDR: {subnet.get('cidr')}")
            if subnet.get("total_ips") is not None:
                lines.append(f"  Total IPs: {subnet.get('total_ips')}")
            if subnet.get("used_ips") is not None:
                lines.append(f"  Used IPs: {subnet.get('used_ips')}")
            if subnet.get("available_ips") is not None:
                lines.append(f"  Available IPs: {subnet.get('available_ips')}")
            if subnet.get("utilization_percent") is not None:
                util = subnet["utilization_percent"]
                util_icon = "✅" if util < 70 else "⚠️" if util < 85 else "❌"
                lines.append(f"  {util_icon} Utilization: {util:.1f}%")
            if subnet.get("resource_group"):
                lines.append(f"  Resource Group: {subnet.get('resource_group')}")
            if subnet.get("vnet_name"):
                lines.append(f"  VNet: {subnet.get('vnet_name')}")
            # Display note if present (explains networking mode)
            if subnet.get("note"):
                lines.append(f"  ℹ️  Note: {subnet.get('note')}")
        lines.append("")

    # Node Pools
    node_pools = report_data.get("node_pools", [])
    if node_pools:
        lines.append("-" * 80)
        lines.append("NODE POOLS")
        lines.append("-" * 80)
        for pool in node_pools:
            state = pool.get("provisioning_state", "Unknown")
            state_icon = (
                "✅" if state == "Succeeded" else "❌" if state == "Failed" else "⚠️"
            )

            lines.append(f"\n{state_icon} {pool.get('name')}:")
            lines.append(f"  Mode: {pool.get('mode')}")
            lines.append(f"  Provisioning State: {state}")
            lines.append(f"  Node Count: {pool.get('count')}")
            lines.append(f"  VM Size: {pool.get('vm_size')}")
            lines.append(f"  Max Pods: {pool.get('max_pods')}")

            # Calculate required IPs
            max_pods = pool.get("max_pods", 30)
            node_count = pool.get("count", 0)
            required_ips = (max_pods + 1) * node_count
            lines.append(
                f"  Required IPs: {required_ips} [{max_pods} pods + 1 node] × {node_count} nodes"
            )

            if pool.get("subnet_name"):
                lines.append(f"  Subnet: {pool.get('subnet_name')}")

            if pool.get("error_details"):
                error = pool["error_details"]
                lines.append(
                    f"  ❌ ERROR: [{error.get('code')}] {error.get('message')}"
                )
        lines.append("")

    # Recommendations
    recommendations = report_data.get("recommendations", [])
    if recommendations:
        lines.append("-" * 80)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        for i, rec in enumerate(recommendations, 1):
            priority = rec.get("priority", "MEDIUM")
            icon = (
                "❌" if priority == "CRITICAL" else "⚠️" if priority == "HIGH" else "💡"
            )

            lines.append(f"\n{i}. {icon} [{priority}] {rec.get('title')}")
            lines.append(f"   {rec.get('description')}")

            if rec.get("affected_resources"):
                resources = rec.get("affected_resources")
                if isinstance(resources, list):
                    lines.append(f"   Affected Resources: {', '.join(resources)}")
                else:
                    lines.append(f"   Affected Resources: {resources}")

            if rec.get("impact"):
                lines.append(f"   Impact: {rec.get('impact')}")

            if rec.get("recommendation"):
                lines.append(f"   💡 Action: {rec.get('recommendation')}")

            if rec.get("implementation_steps"):
                lines.append("   Implementation Steps:")
                for step_num, step in enumerate(rec["implementation_steps"], 1):
                    lines.append(f"     {step_num}. {step}")

            if rec.get("estimated_downtime"):
                lines.append(
                    f"   ⏱️  Estimated Downtime: {rec.get('estimated_downtime')}"
                )

            if rec.get("automation_available"):
                lines.append(f"   🤖 Automation: Available")
        lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def format_markdown_report(report_data: Dict) -> str:
    """Format report as Markdown."""
    lines = []
    lines.append("# AKS IP Exhaustion Diagnostic Report")
    lines.append("")

    # Cluster info
    cluster = report_data.get("cluster_info", {})
    lines.append("## Cluster Information")
    lines.append("")
    lines.append(f"- **Cluster**: {cluster.get('name')}")
    lines.append(f"- **Resource Group**: {cluster.get('resource_group')}")
    lines.append(f"- **Subscription**: {cluster.get('subscription_id')}")
    if cluster.get("kubernetes_version"):
        lines.append(f"- **Kubernetes Version**: {cluster.get('kubernetes_version')}")
    lines.append("")

    # Summary
    summary = report_data.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    status_emoji = (
        "🟢"
        if summary.get("overall_status") == "HEALTHY"
        else "🔴" if summary.get("overall_status") == "CRITICAL" else "🟡"
    )
    lines.append(f"{status_emoji} **Overall Status**: {summary.get('overall_status')}")
    lines.append(f"- **Risk Level**: {summary.get('risk_level')}")
    lines.append(f"- **Total Issues**: {summary.get('total_issues')}")
    lines.append(f"  - Critical: {summary.get('critical_issues')}")
    lines.append(f"  - Warnings: {summary.get('warnings')}")
    lines.append("")

    # Diagnostics
    lines.append("## Diagnostic Results")
    lines.append("")
    diagnostics = report_data.get("diagnostics", {})
    for diag_name, diag_data in diagnostics.items():
        status_badge = "✅" if diag_data.get("status") == "PASS" else "❌"
        lines.append(f"### {status_badge} {diag_name.replace('_', ' ').title()}")
        lines.append(f"**Risk Level**: {diag_data.get('risk_level')}")
        lines.append("")
        issues = diag_data.get("issues", [])
        if issues:
            for issue in issues:
                severity_emoji = (
                    "🔴"
                    if issue.get("severity") in ["CRITICAL", "ERROR"]
                    else "🟡" if issue.get("severity") == "WARNING" else "ℹ️"
                )
                lines.append(f"- {severity_emoji} {issue.get('message')}")
        else:
            lines.append("No issues detected.")
        lines.append("")

    # Recommendations
    recommendations = report_data.get("recommendations", [])
    if recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for rec in recommendations:
            priority_emoji = (
                "🔴"
                if rec.get("priority") == "CRITICAL"
                else "🟡" if rec.get("priority") == "HIGH" else "🔵"
            )
            lines.append(f"### {priority_emoji} {rec.get('title')}")
            lines.append(f"**Priority**: {rec.get('priority')}")
            lines.append("")
            lines.append(rec.get("description"))
            lines.append("")
            if rec.get("implementation_steps"):
                lines.append("**Implementation Steps**:")
                for step in rec["implementation_steps"]:
                    lines.append(f"1. {step}")
                lines.append("")

    return "\n".join(lines)


def format_html_report(report_data: Dict) -> str:
    """Format report as HTML."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>AKS IP Diagnostic Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #0078d4; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .critical {{ color: #d13438; }}
        .warning {{ color: #ff8c00; }}
        .healthy {{ color: #107c10; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #0078d4; color: white; }}
    </style>
</head>
<body>
    <h1>AKS IP Exhaustion Diagnostic Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Cluster:</strong> {report_data['cluster_info']['name']}</p>
        <p><strong>Overall Status:</strong> <span class="{'healthy' if report_data['summary']['overall_status'] == 'HEALTHY' else 'critical'}">{report_data['summary']['overall_status']}</span></p>
        <p><strong>Total Issues:</strong> {report_data['summary']['total_issues']}</p>
    </div>
</body>
</html>"""
    return html


# Legacy functions for backward compatibility
def format_ip_exhaustion_report(ip_exhaustion_issues):
    if not ip_exhaustion_issues:
        return "No IP exhaustion issues detected."

    report = "IP Exhaustion Issues:\n"
    for issue in ip_exhaustion_issues:
        report += f"- {issue}\n"
    return report


def format_provisioning_state_report(provisioning_state_issues):
    if not provisioning_state_issues:
        return "All node pools are in a healthy provisioning state."

    report = "Provisioning State Issues:\n"
    for issue in provisioning_state_issues:
        report += f"- {issue}\n"
    return report


def format_subnet_capacity_report(subnet_capacity_issues):
    if not subnet_capacity_issues:
        return "All subnets have sufficient capacity."

    report = "Subnet Capacity Issues:\n"
    for issue in subnet_capacity_issues:
        report += f"- {issue}\n"
    return report


def format_max_pods_report(max_pods_issues):
    if not max_pods_issues:
        return "All maxPods configurations are within safe limits."

    report = "Max Pods Configuration Issues:\n"
    for issue in max_pods_issues:
        report += f"- {issue}\n"
    return report
