"""Example: Pod-level IP usage analysis for AKS cluster."""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from azure.kubernetes_client import KubernetesClient
from azure.network_client import NetworkClient
from diagnostics.pod_ip_analysis import PodIPAnalyzer, analyze_pod_lifecycle_ip_usage
from reports.formatters import DiagnosticReportBuilder, format_report, OutputFormat


def run_pod_analysis(cluster_name: str, resource_group: str, subscription_id: str):
    """
    Run comprehensive pod-level IP analysis.
    
    Args:
        cluster_name: AKS cluster name
        resource_group: Azure resource group
        subscription_id: Azure subscription ID
    """
    print(f"🔍 Starting Pod-Level IP Analysis for {cluster_name}")
    print("=" * 80)
    
    # Initialize clients
    print("\n📡 Initializing Kubernetes client...")
    k8s_client = KubernetesClient(cluster_name=cluster_name)
    
    print("📡 Initializing Network client...")
    network_client = NetworkClient(subscription_id)
    
    # Create analyzer
    analyzer = PodIPAnalyzer(k8s_client, network_client)
    
    # Run analysis
    print(f"\n🔎 Analyzing pods in cluster: {cluster_name}")
    analysis = analyzer.analyze_cluster_pods(cluster_name, resource_group)
    
    # Display results
    print("\n" + "=" * 80)
    print("📊 POD ANALYSIS RESULTS")
    print("=" * 80)
    
    # Summary
    print(f"\n📈 Summary:")
    print(f"  Total Pods: {analysis['total_pods']}")
    print(f"  Total Nodes: {analysis['total_nodes']}")
    print(f"  Namespaces: {analysis['namespace_analysis']['total_namespaces']}")
    
    # IP Allocation
    ip_alloc = analysis['ip_allocation']
    print(f"\n💾 IP Allocation:")
    print(f"  IPs Allocated: {ip_alloc['total_ips_allocated']}")
    print(f"  Unique IPs: {ip_alloc['unique_ips']}")
    print(f"  Pods Without IP: {ip_alloc['pods_without_ip']}")
    print(f"  Allocation Rate: {ip_alloc['allocation_rate']}%")
    if ip_alloc['has_conflicts']:
        print(f"  ⚠️  IP CONFLICTS DETECTED: {len(ip_alloc['ip_conflicts'])}")
    
    # Pod Distribution
    distribution = analysis['pod_distribution']
    print(f"\n📍 Pod Distribution:")
    print(f"  Min Pods/Node: {distribution['min_pods_per_node']}")
    print(f"  Max Pods/Node: {distribution['max_pods_per_node']}")
    print(f"  Avg Pods/Node: {distribution['avg_pods_per_node']}")
    print(f"  Balanced: {'✅ Yes' if distribution['balanced'] else '❌ No'}")
    if not distribution['balanced']:
        print(f"  Imbalance: {distribution['imbalance_percentage']}%")
    
    # Pod Density
    density = analysis['pod_density']
    status_emoji = {
        'LOW': '🟢',
        'OPTIMAL': '🟢',
        'HIGH': '🟡',
        'CRITICAL': '🔴'
    }
    print(f"\n🎯 Pod Density:")
    print(f"  Status: {status_emoji.get(density['density_status'], '❓')} {density['density_status']}")
    print(f"  Pods/Node: {density['pods_per_node']}")
    print(f"  Recommendation: {density['recommendation']}")
    
    # IP Waste Analysis
    waste = analysis['ip_waste_analysis']
    print(f"\n💸 IP Waste Analysis:")
    print(f"  Level: {waste['waste_level']}")
    print(f"  Reserved IPs: {waste['reserved_ips']}")
    print(f"  Actual Pod IPs: {waste['actual_pod_ips']}")
    print(f"  Wasted IPs: {waste['wasted_ips']} ({waste['waste_percentage']}%)")
    print(f"  Cost Impact: {waste['cost_implication']}")
    
    # Top Namespaces
    print(f"\n📦 Top 5 Namespaces by Pod Count:")
    for ns in analysis['namespace_analysis']['namespaces'][:5]:
        print(f"  {ns['namespace']:<30} {ns['pod_count']:>4} pods | "
              f"{ns['running_pods']:>4} running | {ns['ip_count']:>4} IPs")
    
    # Node Analysis (top 5)
    print(f"\n🖥️  Top 5 Nodes by Utilization:")
    for node in analysis['node_analysis'][:5]:
        util_emoji = '🔴' if node['utilization_percentage'] > 90 else '🟡' if node['utilization_percentage'] > 70 else '🟢'
        print(f"  {util_emoji} {node['node_name']:<40} "
              f"{node['utilization_percentage']:>5.1f}% | "
              f"{node['pod_count']:>3}/{node['max_pods']:>3} pods | "
              f"Pool: {node['node_pool']}")
    
    # Special Cases
    multi_ip_pods = analysis['multi_ip_pods']
    if multi_ip_pods:
        print(f"\n🔀 Multi-IP Pods ({len(multi_ip_pods)}):")
        for pod in multi_ip_pods[:3]:
            print(f"  {pod['namespace']}/{pod['name']}")
            print(f"    IPs: {', '.join(pod['ip_addresses'])}")
            print(f"    Reason: {pod['reason']}")
    
    host_net_pods = analysis['host_network_pods']
    if host_net_pods:
        print(f"\n🌐 Host Network Pods ({len(host_net_pods)}):")
        for pod in host_net_pods[:3]:
            print(f"  {pod['namespace']}/{pod['name']} on {pod['node']}")
    
    # Issues
    if analysis['issues']:
        print(f"\n⚠️  ISSUES DETECTED ({len(analysis['issues'])}):")
        for issue in analysis['issues']:
            severity_emoji = {'CRITICAL': '🔴', 'WARNING': '🟡', 'INFO': 'ℹ️'}
            print(f"\n  {severity_emoji.get(issue['severity'], '❓')} [{issue['severity']}] {issue['title']}")
            print(f"     {issue['description']}")
            print(f"     Impact: {issue['impact']}")
    
    # Recommendations
    if analysis['recommendations']:
        print(f"\n💡 RECOMMENDATIONS ({len(analysis['recommendations'])}):")
        for rec in analysis['recommendations']:
            priority_emoji = {'CRITICAL': '🔴', 'HIGH': '🟡', 'MEDIUM': '🔵', 'LOW': '⚪'}
            print(f"\n  {priority_emoji.get(rec['priority'], '❓')} [{rec['priority']}] {rec['title']}")
            print(f"     {rec['description']}")
            print(f"     Action: {rec['action']}")
            print(f"     Benefit: {rec['expected_benefit']}")
    
    # Save to JSON
    output_file = f"pod-analysis-{cluster_name}.json"
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"\n💾 Full analysis saved to: {output_file}")
    
    print("\n" + "=" * 80)
    print("✅ Pod-Level IP Analysis Complete")
    print("=" * 80)
    
    return analysis


def analyze_pod_lifecycle(cluster_name: str):
    """Analyze pod lifecycle IP usage patterns."""
    print(f"\n🔄 Pod Lifecycle IP Analysis for {cluster_name}")
    print("=" * 80)
    
    k8s_client = KubernetesClient(cluster_name=cluster_name)
    pods = k8s_client.list_pods_all_namespaces()
    
    lifecycle_analysis = analyze_pod_lifecycle_ip_usage(pods)
    
    print("\n📊 Pod Phases:")
    for phase_info in lifecycle_analysis['lifecycle_analysis']:
        print(f"  {phase_info['phase']:<15} "
              f"{phase_info['total_pods']:>4} total | "
              f"{phase_info['pods_with_ip']:>4} with IP | "
              f"{phase_info['ip_allocation_rate']:>5.1f}%")
    
    stuck_pods = lifecycle_analysis['stuck_pods_with_ip']
    if stuck_pods:
        print(f"\n⚠️  Stuck Pods Holding IPs ({len(stuck_pods)}):")
        for pod in stuck_pods[:10]:
            print(f"  {pod['namespace']}/{pod['name']}")
            print(f"    Phase: {pod['phase']} | IP: {pod['ip_address']}")
            print(f"    Issue: {pod['issue']}")
    
    print(f"\n💸 Wasted IPs in Stuck Pods: {lifecycle_analysis['wasted_ips_in_stuck_pods']}")
    
    return lifecycle_analysis


def generate_pod_analysis_report(analysis: Dict, output_format: str = 'json-pretty'):
    """Generate formatted report from pod analysis."""
    # Create report builder
    builder = DiagnosticReportBuilder(
        cluster_name=analysis['cluster_name'],
        resource_group="",  # Add if available
        subscription_id=""   # Add if available
    )
    
    # Add pod-specific diagnostics
    issues_list = []
    for issue in analysis.get('issues', []):
        issues_list.append({
            "severity": issue['severity'],
            "code": issue['category'],
            "message": issue['title'],
            "affected_resource": ", ".join(issue.get('affected_resources', [])),
            "details": {
                "description": issue['description'],
                "impact": issue['impact']
            }
        })
    
    builder.add_diagnostic_result(
        "pod_ip_analysis",
        status="FAIL" if issues_list else "PASS",
        risk_level=analysis['ip_waste_analysis']['waste_level'],
        issues=issues_list,
        details={
            "total_pods": analysis['total_pods'],
            "total_nodes": analysis['total_nodes'],
            "pod_density": analysis['pod_density'],
            "ip_waste": analysis['ip_waste_analysis']
        }
    )
    
    # Set summary
    builder.set_summary(
        overall_status="CRITICAL" if analysis['ip_waste_analysis']['waste_level'] == 'CRITICAL' else "WARNING",
        risk_level=analysis['ip_waste_analysis']['waste_level']
    )
    
    report_data = builder.build()
    
    # Format and return
    format_enum = OutputFormat(output_format)
    return format_report(report_data, format_enum)


def main():
    """Main entry point for pod analysis demo."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pod-Level IP Usage Analysis for AKS')
    parser.add_argument('--cluster-name', required=True, help='AKS cluster name')
    parser.add_argument('--resource-group', required=True, help='Azure resource group')
    parser.add_argument('--subscription-id', required=True, help='Azure subscription ID')
    parser.add_argument('--lifecycle', action='store_true', help='Include lifecycle analysis')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--format', default='json-pretty', 
                       choices=['json', 'json-pretty', 'json-compact', 'yaml', 'text'],
                       help='Output format')
    
    args = parser.parse_args()
    
    try:
        # Run main analysis
        analysis = run_pod_analysis(
            args.cluster_name,
            args.resource_group,
            args.subscription_id
        )
        
        # Run lifecycle analysis if requested
        if args.lifecycle:
            lifecycle = analyze_pod_lifecycle(args.cluster_name)
            analysis['lifecycle_analysis'] = lifecycle
        
        # Generate formatted report if output specified
        if args.output:
            report = generate_pod_analysis_report(analysis, args.format)
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"\n📄 Formatted report saved to: {args.output}")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
