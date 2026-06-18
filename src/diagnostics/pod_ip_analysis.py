"""
Pod-level IP usage analysis for AKS clusters.

This module provides detailed analysis of IP address usage at the pod level,
helping identify waste, inefficiencies, and optimization opportunities.
"""

import ipaddress
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime, timedelta


class PodIPAnalyzer:
    """
    Analyzer for pod-level IP usage patterns and anomalies.
    
    This class performs comprehensive analysis of how pods consume IP addresses
    in an AKS cluster, including:
    - Pod distribution across nodes
    - IP allocation patterns
    - Namespace-level usage
    - Waste detection and optimization opportunities
    """
    
    def __init__(self, k8s_client, network_client):
        """
        Initialize the pod IP analyzer with required clients.
        
        Args:
            k8s_client: Kubernetes API client for retrieving pod and node information
            network_client: Azure Network API client for subnet and IP allocation data
        
        Example:
            analyzer = PodIPAnalyzer(k8s_client, network_client)
            results = analyzer.analyze_cluster_pods("my-cluster", "my-rg")
        """
        self.k8s_client = k8s_client
        self.network_client = network_client
    
    def analyze_cluster_pods(self, cluster_name: str, resource_group: str) -> Dict:
        """
        Perform comprehensive pod-level IP analysis for an entire cluster.
        
        This is the main entry point that orchestrates all pod-level analysis
        including distribution, allocation, waste detection, and recommendations.
        
        Args:
            cluster_name: Name of the AKS cluster to analyze
            resource_group: Azure resource group containing the cluster
        
        Returns:
            Dictionary containing:
                - timestamp: When the analysis was performed
                - total_pods: Number of pods in cluster
                - total_nodes: Number of nodes in cluster
                - pod_distribution: How evenly pods are distributed
                - ip_allocation: IP usage statistics
                - namespace_analysis: Per-namespace breakdown
                - node_analysis: Per-node metrics
                - pod_density: Pods per node calculations
                - ip_waste_analysis: Wasted IP detection
                - multi_ip_pods: Pods with multiple IPs
                - host_network_pods: Pods using host network
                - issues: List of detected problems
                - recommendations: Suggested actions
        
        Example:
            analysis = analyzer.analyze_cluster_pods("prod-cluster", "prod-rg")
            print(f"IP Waste: {analysis['ip_waste_analysis']['waste_percentage']}%")
        """
        # Get all pods and nodes from the cluster
        # This provides the raw data we'll analyze
        pods = self.get_all_pods()
        nodes = self.get_all_nodes()
        
        # Build the comprehensive analysis structure
        # Each analysis function examines a different aspect of IP usage
        analysis = {
            # When the analysis was performed (UTC timestamp in ISO format)
            "timestamp": datetime.utcnow().isoformat() + "Z",
            
            # Basic cluster information
            "cluster_name": cluster_name,
            "total_pods": len(pods),
            "total_nodes": len(nodes),
            
            # Detailed analysis results from various perspectives
            "pod_distribution": self.analyze_pod_distribution(pods, nodes),     # How evenly pods are spread
            "ip_allocation": self.analyze_ip_allocation(pods),                  # IP usage patterns
            "namespace_analysis": self.analyze_by_namespace(pods),              # Per-namespace breakdown
            "node_analysis": self.analyze_by_node(pods, nodes),                # Per-node metrics
            "pod_density": self.calculate_pod_density(pods, nodes),            # Pods per node ratio
            "ip_waste_analysis": self.analyze_ip_waste(pods, nodes),           # Wasted IPs
            "multi_ip_pods": self.identify_multi_ip_pods(pods),                # Pods with >1 IP
            "host_network_pods": self.identify_host_network_pods(pods),        # Pods not using pod IPs
            
            # Issues and recommendations will be populated below
            "issues": [],
            "recommendations": []
        }
        
        # Detect issues based on the analysis results
        # This examines all metrics and flags problems like high waste, imbalance, etc.
        analysis["issues"] = self.detect_issues(analysis)
        
        # Generate actionable recommendations based on detected issues
        # These provide specific steps to fix problems
        analysis["recommendations"] = self.generate_recommendations(analysis)
        
        return analysis
    
    def get_all_pods(self) -> List[Dict]:
        """evenly pods are distributed across nodes.
        
        Unbalanced distribution can indicate:
        - Poor scheduler configuration
        - Node affinity issues
        - Resource hotspots
        - Inefficient resource utilization
        
        Args:
            pods: List of all pods in the cluster
            nodes: List of all nodes in the cluster
        
        Returns:
            Dictionary with distribution metrics:
                - min_pods_per_node: Minimum pods on any node
                - max_pods_per_node: Maximum pods on any node
                - avg_pods_per_node: Average pods per node
                - std_deviation: Standard deviation of pod counts
                - balanced: True if distribution is even (std_dev < 20% of mean)
                - imbalance_percentage: How unbalanced the distribution is
                - nodes_with_pods: Number of nodes running pods
                - node_utilization_percentage: % of nodes actually running pods
        
        Example:
            If one node has 50 pods and another has 10 pods,
            this indicates an imbalanced distribution that may cause issues.
        """
        # Count how many pods are on each node
        # defaultdict(int) automatically initializes missing keys to 0
        node_pod_count = defaultdict(int)
        
        # Iterate through all pods and count them per node
        for pod in pods:
            # Get the node this pod is scheduled on
            node_name = pod.get('spec', {}).get('nodeName')
            if node_name:
                node_pod_count[node_name] += 1
        
        # Extract just the pod counts (removing node names) for statistical calculation
        pod_counts = list(node_pod_count.values())
        
        # Handle edge case: no pods scheduled yet
        if not pod_counts:
            return {
                "min_pods_per_node": 0,
                "max_pods_per_node": 0,
                "avg_pods_per_node": 0,
                "std_deviation": 0,
                "balanced": True  # Empty cluster is technically "balanced"
            }
        
        # Calculate basic statistics
        min_pods = min(pod_counts)  # Least loaded node
        max_pods = max(pod_counts)  # Most loaded node
        avg_pods = sum(pod_counts) / len(pod_counts)  # Average across all nodes
        
        # Calculate standard deviation to measure distribution variance
        # Higher std_dev = more unbalanced distribution
        # Formula: sqrt(average of squared differences from mean)
        variance = sum((x - avg_pods) ** 2 for x in pod_counts) / len(pod_counts)
        std_dev = variance ** 0.5
        
        # Check if distribution is balanced
        # Rule: Balanced if standard deviation is less than 20% of the mean
        # This means pod counts are relatively similar across nodes
        # Example: avg=30, std_dev=5 → 5 < 6 (20% of 30) = balanced
        # Example: avg=30, std_dev=10 → 10 > 6 = not balanced
        is_balanced = std_dev < (avg_pods * 0.2) if avg_pods > 0 else True
        
        # Calculate imbalance percentage to show severity
        # This normalizes the std_dev as a percentage of the mean
        # Higher percentage = more severe imbalance
        imbalance_pct = (std_dev / avg_pods * 100) if avg_pods > 0 else 0
        
        # Calculate node utilization
        # This tells us what percentage of nodes actually have pods scheduled
        # Low utilization might indicate scaling or scheduling issues
        nodes_running_pods = len(node_pod_count)
        total_nodes = len(nodes)
        utilization_pct = (nodes_running_pods / total_nodes * 100) if total_nodes > 0 else 0
        
        return {
            "min_pods_per_node": min_pods,
            "max_pods_per_node": max_pods,
            "avg_pods_per_node": round(avg_pods, 2),
            "std_deviation": round(std_dev, 2),
            "balanced": is_balanced,
            "imbalance_percentage": round(imbalance_pct, 2),
            "nodes_with_pods": nodes_running_pods,
            "total_nodes": total_nodes,
            "node_utilization_percentage": round(utilization_pct, 2)
        }
    
    def analyze_ip_allocation(self, pods: List[Dict]) -> Dict:
        """
        Analyze IP allocation patterns across pods.
        
        This helps understand:
        - How many pods successfully got IPs
        - Which IP ranges are being used
        - Whether there are IP conflicts (rare but serious)
        - Pod readiness status
        
        Args:
            pods: List of all pods in the cluster
        
        Returns:
            Dictionary containing:
                - pods_with_ip: Count of pods that have an IP assigned
                - pods_without_ip: Count of pods missing IPs (usually pending)
                - ip_ranges: Distribution of IPs across subnets (/16 networks)
                - duplicate_ips: List of IPs assigned to multiple pods (error condition)
                - allocation_rate: Percentage of pods with IPs
                - unique_ips_used: Number of unique IP addresses in use
        
        Note:
            Pods without IPs are typically in Pending or Init state.
            Duplicate IPs indicate a serious networking problem.
        """
        # Track all IPs and count successful allocations
        ip_addresses = []
        pods_with_ip = 0
        pods_without_ip = 0
        
        # Group pods by IP subnet to understand network distribution
        # This uses /16 subnets (e.g., 10.244.0.0/16)
        ip_ranges = defaultdict(int)
        
        for pod in pods:
            # Get the pod's IP from its status
            # Note: podIP is only set when pod is Running or Ready
            pod_ip = pod.get('status', {}).get('podIP')
            
            if pod_ip:
                pods_with_ip += 1
                ip_addresses.append(pod_ip)
                
                # Categorize by IP range (first two octets form a /16 subnet)
                # This helps identify which subnets are being used
                try:
                    ip_obj = ipaddress.ip_address(pod_ip)
                    parts = str(ip_obj).split('.')
                    # Group by /16: e.g., 10.244.x.x becomes 10.244.0.0/16
                    ip_range = f"{parts[0]}.{parts[1]}.0.0/16"
                    ip_ranges[ip_range] += 1
                except ValueError:
                    # Invalid IP format - skip but don't fail
                    pass
            else:
                # Pod doesn't have an IP yet (Pending, Init, or Failed state)
                pods_without_ip += 1
        
        # Check for IP conflicts - same IP assigned to multiple pods
        # This should NEVER happen and indicates a serious CNI bug
        # Counter counts occurrences of each IP
        ip_counts = Counter(ip_addresses)
        # Find IPs that appear more than once (count > 1)
        duplicates = {ip: count for ip, count in ip_counts.items() if count > 1}
        
        # Calculate allocation success rate
        # This tells us what percentage of pods successfully got an IP
        total_pods = len(pods)
        allocation_rate = (pods_with_ip / total_pods * 100) if total_pods > 0 else 0
        
        return {
            "total_ips_allocated": pods_with_ip,
            "pods_without_ip": pods_without_ip,
            "unique_ips": len(set(ip_addresses)),  # Count of distinct IPs (should equal pods_with_ip)
            "ip_ranges": dict(ip_ranges),           # Which /16 subnets are in use
            "ip_conflicts": duplicates,             # Any duplicate IPs found
            "has_conflicts": len(duplicates) > 0,   # Quick boolean check
            "allocation_rate": round(allocation_rate, 2)  # Percentage success
        }
    
    def analyze_by_namespace(self, pods: List[Dict]) -> Dict:
        """
        Analyze pod and IP usage grouped by namespace.
        
        Namespaces help organize workloads. This analysis shows:
        - Which namespaces consume the most IPs
        - Health status per namespace
        - System vs application namespaces
        
        Args:
            pods: List of all pods in the cluster
        
        Returns:
            Dictionary containing:
                - total_namespaces: Count of unique namespaces
                - namespaces: List of namespace metrics sorted by pod count
                - top_namespace: Namespace with most pods
                - system_namespaces: List of kube-* system namespaces
        
        Example:
            Might show that "production" namespace has 200 pods,
            while "kube-system" has only 50 pods.
        """
        # Create a dictionary to track stats for each namespace
        # lambda creates default structure automatically for new namespaces
        namespace_stats = defaultdict(lambda: {
            "pod_count": 0,
            "running_pods": 0,
            "pending_pods": 0,
            "failed_pods": 0,
            "pods_with_ip": 0,
            "pods_without_ip": 0,
            "ip_addresses": []  # Track actual IPs for this namespace
        })
        
        # Iterate through all pods and categorize by namespace
        for pod in pods:
            # Get namespace (default to 'default' if not specified)
            namespace = pod.get('metadata', {}).get('namespace', 'default')
            stats = namespace_stats[namespace]
            
            # Increment total pod count for this namespace
            stats["pod_count"] += 1
            
            # Count pods by their current phase (lifecycle state)
            # Phase indicates whether pod is running, starting, or failed
            phase = pod.get('status', {}).get('phase', 'Unknown')
            if phase == 'Running':
                stats["running_pods"] += 1
            elif phase == 'Pending':
                stats["pending_pods"] += 1
            elif phase == 'Failed':
                stats["failed_pods"] += 1
            
            # Track IP allocation for this namespace
            # Pods get IPs once they're scheduled and starting to run
            pod_ip = pod.get('status', {}).get('podIP')
            if pod_ip:
                stats["pods_with_ip"] += 1
                stats["ip_addresses"].append(pod_ip)
            else:
                stats["pods_without_ip"] += 1
        
        # Convert dictionary to list format and add calculated metrics
        namespace_list = []
        for ns, stats in namespace_stats.items():
            # Calculate IP allocation rate (how many pods got IPs)
            ip_alloc_rate = (stats["pods_with_ip"] / stats["pod_count"] * 100) if stats["pod_count"] > 0 else 0
            
            # Calculate health percentage (how many pods are running successfully)
            health_pct = (stats["running_pods"] / stats["pod_count"] * 100) if stats["pod_count"] > 0 else 0
            
            namespace_list.append({
                "namespace": ns,
                "pod_count": stats["pod_count"],
                "running_pods": stats["running_pods"],
                "pending_pods": stats["pending_pods"],
                "failed_pods": stats["failed_pods"],
                "ip_count": stats["pods_with_ip"],
                "ip_allocation_rate": round(ip_alloc_rate, 2),
                "health_percentage": round(health_pct, 2)
            })
        
        # Sort by pod count descending (largest namespaces first)
        # This makes it easy to identify which namespaces consume most resources
        namespace_list.sort(key=lambda x: x["pod_count"], reverse=True)
        
        return {
            "total_namespaces": len(namespace_stats),
            "namespaces": namespace_list,
            # Top namespace is first in sorted list
            "top_namespace": namespace_list[0]["namespace"] if namespace_list else None,
            # Identify system namespaces (those starting with 'kube-')
            "system_namespaces": [ns for ns in namespace_stats.keys() if ns.startswith('kube-')]
        }
    
    def analyze_by_node(self, pods: List[Dict], nodes: List[Dict]) -> List[Dict]:
        """
        Analyze pod and IP usage for each individual node.
        
        Node-level analysis helps identify:
        - Which nodes are heavily loaded
        - Nodes approaching pod limit (maxPods)
        - Nodes with high IP consumption
        - Uneven distribution across nodes
        
        Args:
            pods: List of all pods in the cluster
            nodes: List of all nodes in the cluster
        
        Returns:
            List of dictionaries, one per node, containing:
                - node_name: Name of the node
                - pod_count: Total pods on this node
                - running_pods: Pods in Running state
                - ip_count: Pods with allocated IPs
                - allocatable_pods: Maximum pods allowed (from node capacity)
                - utilization_percentage: Current/max pods ratio
                - namespace_count: How many different namespaces on this node
                - pod_density: Classification (LOW/OPTIMAL/HIGH/CRITICAL)
        
        Note:
            Utilization above 90% indicates node is near capacity.
            Azure CNI reserves IPs even for empty nodes.
        """
        # Track statistics per node using defaultdict
        node_stats = defaultdict(lambda: {
            "pod_count": 0,
            "running_pods": 0,
            "ip_count": 0,
            "pod_names": [],
            "namespaces": set()  # Using set to track unique namespaces
        })
        
        # First, collect node capacity information from node objects
        # This tells us the maximum pods each node can handle
        node_info = {}
        for node in nodes:
            node_name = node.get('metadata', {}).get('name')
            node_info[node_name] = {
                # allocatable = actual limit enforced by kubelet
                "allocatable_pods": int(node.get('status', {}).get('allocatable', {}).get('pods', 0)),
                # capacity = theoretical maximum from node resources
                "capacity_pods": int(node.get('status', {}).get('capacity', {}).get('pods', 0)),
                "labels": node.get('metadata', {}).get('labels', {}),
                "conditions": node.get('status', {}).get('conditions', [])
            }
        
        # Now analyze pods and group them by node
        for pod in pods:
            node_name = pod.get('spec', {}).get('nodeName')
            # Skip pods that aren't scheduled yet (no nodeName)
            # These are typically in Pending state waiting for scheduling
            if not node_name:
                continue
            
            stats = node_stats[node_name]
            stats["pod_count"] += 1
            
            # Track running pods specifically
            # Only Running pods are actively using resources
            phase = pod.get('status', {}).get('phase', 'Unknown')
            if phase == 'Running':
                stats["running_pods"] += 1
            
            # Count pods that have been allocated an IP
            # This is slightly different from running - pods can have IPs in Init state
            if pod.get('status', {}).get('podIP'):
                stats["ip_count"] += 1
            
            # Track which pods are on this node (for debugging)
            pod_name = pod.get('metadata', {}).get('name')
            namespace = pod.get('metadata', {}).get('namespace')
            stats["pod_names"].append(f"{namespace}/{pod_name}")
            # Track unique namespaces on this node
            stats["namespaces"].add(namespace)
        
        # Build comprehensive node analysis list
        node_analysis = []
        for node_name, stats in node_stats.items():
            # Get node capacity info we collected earlier
            info = node_info.get(node_name, {})
            # Calculate utilization percentage
            # This shows how close the node is to its pod limit
            # Values above 90% indicate node is near capacity
            utilization = (stats["pod_count"] / allocatable * 100) if allocatable > 0 else 0
            
            # Calculate remaining capacity on this node
            remaining = allocatable - stats["pod_count"] if allocatable > 0 else 0
            
            # Check if this is a system node (master/control-plane)
            # System nodes typically don't run user workloads
            labels = info.get('labels', {})
            is_system = ('node-role.kubernetes.io/master' in labels or 
                        'node-role.kubernetes.io/control-plane' in labels)
            
            # Get the node pool name (Azure specific label)
            # This groups nodes into pools for capacity planning
            node_pool = labels.get('agentpool', 'unknown')
            
            node_analysis.append({
                "node_name": node_name,
                "pod_count": stats["pod_count"],
                "running_pods": stats["running_pods"],
                "ip_count": stats["ip_count"],
                "namespace_count": len(stats["namespaces"]),
                "max_pods": allocatable,
                "utilization_percentage": round(utilization, 2),
                "remaining_capacity": remaining,
                "is_system_node": is_system,
                "node_pool": node_pool
            })
        
        # Sort by utilization percentage descending
        # This makes highly loaded nodes appear first for quick identification
        node_analysis.sort(key=lambda x: x["utilization_percentage"], reverse=True)
        
        return node_analysis
    
    def calculate_pod_density(self, pods: List[Dict], nodes: List[Dict]) -> Dict:
        """
        Calculate overall pod density metrics for the cluster.
        
        Pod density (pods per node) affects:
        - Resource utilization efficiency
        - Blast radius (how many apps affected if node fails)
        - IP address consumption
        - Network performance
        
        Args:
            pods: List of all pods in the cluster
            nodes: List of all nodes in the cluster
        
        Returns:
            Dictionary containing:
                - total_running_pods: Count of pods in Running state
                - total_nodes: Count of nodes in cluster
                - pods_per_node: Average pods per node
                - density_status: Classification (LOW/OPTIMAL/HIGH/CRITICAL)
                - recommendation: Suggested action based on density
        
        Density thresholds:
            - LOW (<10): Under-utilized, wasting resources
            - OPTIMAL (10-30): Good balance
            - HIGH (30-50): Getting crowded, monitor closely
            - CRITICAL (>50): Overloaded, add nodes urgently
        
        Example:
            100 running pods / 5 nodes = 20 pods/node = OPTIMAL
        """
        # Count only Running pods (exclude Pending, Failed, Succeeded)
        total_nodes = len(nodes)
        
        if total_nodes == 0:
            return {
                "pods_per_node": 0,
                "density_status": "N/A",
                "recommendation": "No nodes found"
            }
        
        pods_per_node = total_pods / total_nodes
        
        # Determine density status
        if pods_per_node < 10:
            status = "LOW"
            recommendation = "Cluster is under-utilized. Consider reducing node count or scaling workloads."
        elif pods_per_node < 30:
            status = "OPTIMAL"
            recommendation = "Pod density is within optimal range."
        elif pods_per_node < 50:
            status = "HIGH"
            recommendation = "Pod density is high. Monitor performance and consider adding nodes."
        else:
            status = "CRITICAL"
            recommendation = "Pod density is critically high. Add nodes immediately to prevent issues."
        
        return {
            "total_running_pods": total_pods,
            "total_nodes": total_nodes,
            "pods_per_node": round(pods_per_node, 2),
            "density_status": status,
            "recommendation": recommendation
        }
    
    def analyze_ip_waste(self, pods: List[Dict], nodes: List[Dict]) -> Dict:
        """
        Analyze potential IP address waste from over-provisioning.
        
        Azure CNI pre-allocates IP addresses to nodes even when pods aren't running.
        This function identifies waste to help optimize subnet sizing.
        
        IP Allocation in Azure CNI:
        - Each node reserves (maxPods + 1) IP addresses
        - IPs are reserved whether pods are running or not
        - This can lead to significant waste if nodes are under-utilized
        
        Args:
            pods: List of all pods in the cluster
            nodes: List of all nodes in the cluster
        
        Returns:
            Dictionary containing:
                - actual_pod_ips: IPs currently in use by running pods
                - reserved_ips: Total IPs reserved by CNI
                - wasted_ips: Difference (reserved - actual)
                - waste_percentage: Waste as percentage of reserved
                - waste_level: Classification (LOW/MEDIUM/HIGH/CRITICAL)
                - cost_implication: Relative cost impact
        
        Example:
            10 nodes × 31 IPs/node = 310 reserved IPs
            50 actual pods = 50 IPs in use
            260 wasted IPs = 83.9% waste = CRITICAL
        
        Note:
            Waste >30% indicates significant over-provisioning.
        """
        # Count pods that actually have IPs allocated
        # These are the IPs actively in use
        actual_pod_ips = len([p for p in pods if p.get('status', {}).get('podIP')])
        
        # Calculate theoretical maximum based on node maxPods settings
        # Azure CNI reserves maxPods IPs per node
        max_possible_pods = 0
        for node in nodes:
            # Get the max pods setting for this node (typically 30 or 110)
            max_pods = int(node.get('status', {}).get('capacity', {}).get('pods', 0))
            max_possible_pods += max_pods
        
        # Initialize waste metrics
        waste_percentage = 0
        wasted_ips = 0
        
        # Calculate waste if we have reserved IPs
        if max_possible_pods > 0:
            # Waste percentage = (reserved - actual) / reserved * 100
            waste_percentage = round((1 - actual_pod_ips / max_possible_pods) * 100, 2)
            wasted_ips = max_possible_pods - actual_pod_ips
        
        # Categorize waste level based on percentage
        # These thresholds help prioritize optimization efforts
        if waste_percentage < 20:
            # Minimal waste - acceptable overhead
            waste_level = "LOW"
            impact = "Minimal IP waste, efficient utilization"
        elif waste_percentage < 40:
            # Moderate waste - watch but not urgent
            waste_level = "MEDIUM"
            impact = "Moderate IP waste, room for optimization"
        elif waste_percentage < 60:
            # Significant waste - should optimize
            waste_level = "HIGH"
            impact = "Significant IP waste, consider reducing maxPods or scaling down nodes"
        else:
            # Severe waste - urgent action needed
            waste_level = "CRITICAL"
            impact = "Severe IP waste, immediate optimization needed to reduce costs"
        
        # Estimate cost implication
        # High waste can lead to subnet exhaustion and wasted cloud costs
        cost_impact = "High" if waste_percentage > 50 else "Medium" if waste_percentage > 30 else "Low"
        
        return {
            "actual_pod_ips": actual_pod_ips,
            "reserved_ips": max_possible_pods,
            "wasted_ips": wasted_ips,
            "waste_percentage": waste_percentage,
            "waste_level": waste_level,
            "impact": impact,
            "cost_implication": cost_impact
        }
    
    def identify_multi_ip_pods(self, pods: List[Dict]) -> List[Dict]:
        """
        Identify pods with multiple IP addresses (e.g., using secondary networks).
        
        Some pods may have multiple IPs for reasons like:
        - Dual-stack networking (IPv4 + IPv6)
        - Multiple CNI networks (using Multus or similar)
        - Service mesh sidecar with separate network
        
        Args:
            pods: List of all pods in the cluster
        
        Returns:
            List of dictionaries, each containing:
                - name: Pod name
                - namespace: Pod namespace
                - node: Node the pod is running on
                - ip_addresses: List of all IPs assigned to this pod
                - ip_count: Number of IPs (>1)
                - reason: Why this pod has multiple IPs
        
        Note:
            Multi-IP pods consume extra IPs from the subnet.
            This is important for accurate capacity planning.
        """
        multi_ip_pods = []
        
        for pod in pods:
            pod_ips = []
            
            # Get the primary IP (single IP field)
            # This is the main pod IP address
            primary_ip = pod.get('status', {}).get('podIP')
            if primary_ip:
                pod_ips.append(primary_ip)
            
            # Get additional IPs from the podIPs array
            # This field was introduced in Kubernetes 1.20 for dual-stack support
            # It contains all IPs including the primary one
            additional_ips = pod.get('status', {}).get('podIPs', [])
            for ip_info in additional_ips:
                ip = ip_info.get('ip')
                # Add only if it's not already in our list (avoid duplicates)
                if ip and ip not in pod_ips:
                    pod_ips.append(ip)
            
            # If pod has more than one IP, it's interesting for our analysis
            if len(pod_ips) > 1:
                multi_ip_pods.append({
                    "name": pod.get('metadata', {}).get('name'),
                    "namespace": pod.get('metadata', {}).get('namespace'),
                    "node": pod.get('spec', {}).get('nodeName'),
                    "ip_addresses": pod_ips,
                    "ip_count": len(pod_ips),
                    # Try to determine why this pod has multiple IPs
                    "reason": self._determine_multi_ip_reason(pod)
                })
        
        return multi_ip_pods
    
    def identify_host_network_pods(self, pods: List[Dict]) -> List[Dict]:
        """
        Identify pods using host network mode.
        
        Pods with hostNetwork=true use the node's network namespace instead
        of getting their own pod network. They don't consume pod IPs.
        
        Common uses:
        - System daemonsets (kube-proxy, CNI agents)
        - Monitoring agents that need node-level network access
        - Network utilities and troubleshooting pods
        
        Args:
            pods: List of all pods in the cluster
        
        Returns:
            List of host network pods with:
                - name: Pod name
                - namespace: Namespace (often kube-system)
                - node: Node where pod is running
                - host_ip: The node's IP address
                - pod_ip: Pod's IP (usually same as host_ip)
                - uses_host_ip: Boolean indicating if podIP == hostIP
        
        Note:
            These pods don't count toward IP exhaustion since they
            don't consume pod network IPs. However, they do increase
            pod count toward maxPods limit.
        """
        host_network_pods = []
        
        for pod in pods:
            # Check if pod is configured with hostNetwork
            # This is a boolean field in pod.spec
            if pod.get('spec', {}).get('hostNetwork', False):
                host_network_pods.append({
                    "name": pod.get('metadata', {}).get('name'),
                    "namespace": pod.get('metadata', {}).get('namespace'),
                    "node": pod.get('spec', {}).get('nodeName'),
                    "host_ip": pod.get('status', {}).get('hostIP'),
                    "pod_ip": pod.get('status', {}).get('podIP'),
                    # Verify that pod is actually using the host IP
                    # They should match if hostNetwork is working correctly
                    "uses_host_ip": pod.get('status', {}).get('podIP') == pod.get('status', {}).get('hostIP')
                })
        
        return host_network_pods
    
    def _determine_multi_ip_reason(self, pod: Dict) -> str:
        """
        Determine why a pod has multiple IP addresses.
        
        Args:
            pod: Pod dictionary from Kubernetes API
        
        Returns:
            String describing the reason for multiple IPs
        
        Possible reasons:
            - "IPv4/IPv6 dual-stack": Pod has both v4 and v6 addresses
            - "Multiple CNI networks": Using Multus or similar multi-network CNI
            - "Unknown": Reason couldn't be determined
        """
        # Check for IPv4/IPv6 dual stack configuration
        # This is the most common reason for multiple IPs
        pod_ips = pod.get('status', {}).get('podIPs', [])
        if len(pod_ips) >= 2:
            try:
                # Parse first two IPs to check their versions
                ip1 = ipaddress.ip_address(pod_ips[0].get('ip'))
                ip2 = ipaddress.ip_address(pod_ips[1].get('ip'))
                # If one is IPv4 and one is IPv6, it's dual-stack
                if (ip1.version == 4 and ip2.version == 6) or (ip1.version == 6 and ip2.version == 4):
                    return "IPv4/IPv6 dual-stack"
            except (ValueError, AttributeError):
                # Invalid IP format - continue to next check
                pass
        
        # Check for multiple CNI network annotations
        # Multus CNI and similar solutions use annotations to define additional networks
        annotations = pod.get('metadata', {}).get('annotations', {})
        if any('network' in key.lower() for key in annotations.keys()):
            return "Multiple CNI networks (e.g., Multus)"
        
        # Couldn't determine reason
        return "Unknown - requires investigation"
    
    def detect_issues(self, analysis: Dict) -> List[Dict]:
        """
        Detect issues from the pod-level analysis results.
        
        This function examines all metrics collected and flags problems that
        need attention. Each issue includes severity, description, and impact.
        
        Args:
            analysis: Complete analysis dictionary from analyze_cluster_pods()
        
        Returns:
            List of issue dictionaries, each containing:
                - severity: WARNING or CRITICAL
                - category: Type of issue (POD_DISTRIBUTION, IP_WASTE, etc.)
                - title: Short description
                - description: Detailed explanation with metrics
                - impact: What problems this causes
                - affected_resources: What's affected
                - cost_impact: (optional) Financial implications
        
        Issue categories checked:
            - POD_DISTRIBUTION: Unbalanced pods across nodes
            - IP_WASTE: High percentage of unused reserved IPs
            - POD_DENSITY: Too many pods per node
            - IP_ALLOCATION: Pods failing to get IPs
            - IP_CONFLICTS: Duplicate IP assignments
            - NODE_UTILIZATION: Nodes near capacity
        
        Example:
            issues = analyzer.detect_issues(analysis_results)
            critical = [i for i in issues if i['severity'] == 'CRITICAL']
        """
        issues = []
        
        # Check pod distribution balance across nodes
        # Unbalanced distribution can cause resource hotspots and reduce reliability
        distribution = analysis.get("pod_distribution", {})
        if not distribution.get("balanced", True):
            # Calculate severity based on imbalance percentage
            # Higher imbalance = more severe issue
            imbalance = distribution.get('imbalance_percentage', 0)
            severity = "CRITICAL" if imbalance > 50 else "WARNING"
            
            issues.append({
                "severity": severity,
                "category": "POD_DISTRIBUTION",
                "title": "Unbalanced pod distribution across nodes",
                "description": f"Pod distribution shows {imbalance}% imbalance. "
                              f"Min: {distribution.get('min_pods_per_node')} pods, "
                              f"Max: {distribution.get('max_pods_per_node')} pods per node",
                "impact": "Some nodes may be overloaded while others are underutilized, "
                         "leading to inefficient resource usage and potential performance issues",
                "affected_resources": ["cluster-wide"]
            })
        
        # Check for IP waste from over-provisioning
        # High waste indicates subnet is larger than needed or nodes are under-utilized
        waste = analysis.get("ip_waste_analysis", {})
        if waste.get("waste_level") in ["HIGH", "CRITICAL"]:
            issues.append({
                "severity": "WARNING" if waste.get("waste_level") == "HIGH" else "CRITICAL",
                "category": "IP_WASTE",
                "title": f"{waste.get('waste_level')} IP address waste detected",
                "description": f"{waste.get('waste_percentage')}% of reserved IPs are unused. "
                              f"Wasting {waste.get('wasted_ips')} IP addresses out of {waste.get('reserved_ips')} reserved.",
                "impact": waste.get("impact", "Inefficient IP usage may lead to subnet exhaustion and increased costs"),
                "affected_resources": ["cluster-wide"],
                "cost_impact": waste.get("cost_implication", "Unknown")
            })
        
        # Check pod density (pods per node ratio)
        # High density increases blast radius and can cause cascading failures
        density = analysis.get("pod_density", {})
        if density.get("density_status") in ["HIGH", "CRITICAL"]:
            issues.append({
                "severity": "WARNING" if density.get("density_status") == "HIGH" else "CRITICAL",
                "category": "POD_DENSITY",
                "title": f"{density.get('density_status')} pod density detected",
                "description": f"Average {density.get('pods_per_node')} pods per node. "
                              f"{density.get('total_running_pods')} pods on {density.get('total_nodes')} nodes.",
                "impact": "High pod density can lead to resource contention, increased blast radius if node fails, "
                         "and potential network performance degradation",
                "affected_resources": ["cluster-wide"]
            })
        
        # Check for IP allocation conflicts (critical issue)
        # This should NEVER happen and indicates CNI problems
        ip_alloc = analysis.get("ip_allocation", {})
        if ip_alloc.get("has_conflicts", False):
            conflicts = ip_alloc.get('ip_conflicts', {})
            issues.append({
                "severity": "CRITICAL",
                "category": "IP_CONFLICT",
                "title": "IP address conflicts detected",
                "description": f"Found {len(conflicts)} duplicate IP assignments. "
                              f"Multiple pods assigned same IP.",
                "impact": "Network connectivity issues, pod failures, and unpredictable behavior. "
                         "This indicates a serious CNI plugin malfunction.",
                "affected_resources": list(conflicts.keys())
            })
        
        # Check for nodes approaching capacity
        # Nodes at >90% capacity can't accept new pods or handle rescheduling
        node_analysis = analysis.get("node_analysis", [])
        overloaded_nodes = [n for n in node_analysis if n.get("utilization_percentage", 0) > 90]
        if overloaded_nodes:
            node_names = [n["node_name"] for n in overloaded_nodes]
            issues.append({
                "severity": "WARNING",
                "category": "NODE_CAPACITY",
                "title": f"{len(overloaded_nodes)} nodes near capacity",
                "description": f"Nodes running at >90% pod capacity: {', '.join(node_names[:3])}{'...' if len(node_names) > 3 else ''}",
                "impact": "Limited room for new pods, pod rescheduling failures, and inability to handle node failures",
                "affected_resources": node_names
            })
        
        return issues
    
    def generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """
        Generate actionable recommendations based on detected issues.
        
        This function examines the analysis results and provides specific,
        actionable recommendations to optimize IP usage and cluster configuration.
        
        Args:
            analysis: Complete analysis dictionary from analyze_cluster_pods()
        
        Returns:
            List of recommendation dictionaries, each containing:
                - priority: CRITICAL/HIGH/MEDIUM/LOW urgency level
                - category: Type of recommendation
                - title: Short action description
                - description: Why this recommendation matters
                - action: Specific steps to take
                - expected_benefit: What improvement to expect
                - implementation_complexity: LOW/MEDIUM/HIGH effort required
        
        Recommendation categories:
            - IP_OPTIMIZATION: Reduce wasted IP addresses
            - SCALING: Add or remove nodes
            - COST_OPTIMIZATION: Reduce cloud costs
            - WORKLOAD_DISTRIBUTION: Balance pods across nodes
            - NETWORK_DESIGN: Improve network configuration
        
        Example:
            recs = analyzer.generate_recommendations(analysis_results)
            critical_recs = [r for r in recs if r['priority'] == 'CRITICAL']
        """
        recommendations = []
        
        # Recommendation for high IP waste
        # Reducing maxPods can free up significant IP address space
        waste = analysis.get("ip_waste_analysis", {})
        if waste.get("waste_percentage", 0) > 30:
            # Higher waste = higher priority
            priority = "HIGH" if waste.get("waste_percentage") > 50 else "MEDIUM"
            wasted = waste.get('wasted_ips', 0)
            waste_pct = waste.get('waste_percentage', 0)
            
            recommendations.append({
                "priority": priority,
                "category": "IP_OPTIMIZATION",
                "title": "Reduce maxPods setting to match actual usage",
                "description": f"Currently wasting {wasted} IPs ({waste_pct}% waste rate). "
                              f"This means you're reserving far more IPs than you're actually using.",
                "action": "1. Analyze actual peak pod count per node\n"
                         "2. Set maxPods to peak + 20% buffer\n"
                         "3. Recreate node pools with new maxPods setting\n"
                         "4. Update cluster autoscaler configuration",
                "expected_benefit": f"Free up approximately {wasted} IP addresses for other uses or reduce subnet size",
                "implementation_complexity": "Medium - requires node pool recreation with potential downtime"
            })
        
        # Recommendations for pod density issues
        density = analysis.get("pod_density", {})
        
        if density.get("density_status") == "CRITICAL":
            # Critical density - need to add nodes immediately
            pods_per_node = density.get('pods_per_node', 0)
            recommendations.append({
                "priority": "CRITICAL",
                "category": "SCALING",
                "title": "Add nodes immediately to reduce pod density",
                "description": f"Current pod density ({pods_per_node} pods/node) is critically high. "
                              f"This increases risk of cascading failures and resource exhaustion.",
                "action": "1. Scale up node pool immediately (add 2-3 nodes)\n"
                         "2. Enable cluster autoscaler if not already enabled\n"
                         "3. Set appropriate min/max node counts\n"
                         "4. Monitor and adjust based on load patterns",
                "expected_benefit": "Improved stability, reduced blast radius, better performance, "
                                   "and increased capacity for pod rescheduling",
                "implementation_complexity": "Low - simple scale operation via Azure Portal or CLI"
            })
            
        elif density.get("density_status") == "LOW":
            # Low density - potentially wasting money on unused nodes
            pods_per_node = density.get('pods_per_node', 0)
            total_nodes = density.get('total_nodes', 0)
            recommendations.append({
                "priority": "LOW",
                "category": "COST_OPTIMIZATION",
                "title": "Consider reducing node count to optimize costs",
                "description": f"Pod density ({pods_per_node} pods/node) indicates over-provisioning. "
                              f"You have {total_nodes} nodes but could likely run on fewer.",
                "action": "1. Review workload patterns over past 30 days\n"
                         "2. Calculate minimum nodes needed for peak load + buffer\n"
                         "3. Gradually reduce node pool size\n"
                         "4. Configure cluster autoscaler with appropriate limits",
                "expected_benefit": "Significant cost savings without impacting performance or reliability",
                "implementation_complexity": "Medium - requires careful capacity planning and gradual reduction"
            })
        
        # Recommendation for unbalanced pod distribution
        # Uneven distribution can cause performance hotspots
        distribution = analysis.get("pod_distribution", {})
        if not distribution.get("balanced", True) and distribution.get("imbalance_percentage", 0) > 30:
            imbalance = distribution.get("imbalance_percentage", 0)
            recommendations.append({
                "priority": "MEDIUM",
                "category": "WORKLOAD_DISTRIBUTION",
                "title": "Balance pod distribution across nodes",
                "description": f"Pod distribution shows {imbalance}% imbalance. "
                              f"Some nodes are overloaded while others are underutilized.",
                "action": "1. Review pod affinity/anti-affinity rules\n"
                         "2. Check for node selectors forcing pods to specific nodes\n"
                         "3. Review scheduler configuration and policies\n"
                         "4. Consider using pod topology spread constraints\n"
                         "5. Manually drain and rebalance if necessary",
                "expected_benefit": "More even resource utilization, reduced hotspots, "
                                   "better resilience to node failures",
                "implementation_complexity": "Medium - requires workload analysis and potential configuration changes"
            })
        
        # Recommendation for excessive host network pods
        # Too many host network pods can indicate security or design issues
        host_net_pods = analysis.get("host_network_pods", [])
        if len(host_net_pods) > 10:
            recommendations.append({
                "priority": "LOW",
                "category": "NETWORK_DESIGN",
                "title": "Review excessive host network pod usage",
                "description": f"{len(host_net_pods)} pods using host network mode. "
                              f"While these don't consume pod IPs, they reduce security isolation.",
                "action": "1. Audit each host network pod and document justification\n"
                         "2. Evaluate if host network is truly required\n"
                         "3. Consider alternatives like hostPort or service networking\n"
                         "4. Update pod specs to remove hostNetwork where possible",
                "expected_benefit": "Better security isolation, improved network management, "
                                   "and reduced dependency on node network namespace",
                "implementation_complexity": "High - may require application architecture changes"
            })
        
        return recommendations


def analyze_pod_lifecycle_ip_usage(pods: List[Dict]) -> Dict:
    """
    Analyze IP usage patterns based on pod lifecycle phases.
    
    Pod lifecycle phases:
        - Pending: Pod accepted but not yet running (waiting for scheduling/pulling images)
        - Running: Pod is running on a node
        - Succeeded: Pod completed successfully (terminated with exit code 0)
        - Failed: Pod terminated with error (non-zero exit code)
        - Unknown: Pod status couldn't be determined
    
    This analysis helps identify:
    - Stuck pods holding IPs unnecessarily
    - Whether IPs are allocated to non-running pods
    - Lifecycle patterns that waste IPs
    
    Args:
        pods: List of all pods in the cluster
    
    Returns:
        Dictionary containing:
            - lifecycle_phases: List of IP usage per lifecycle phase
            - stuck_pods: Pods in non-running state but holding IPs for long time
            - ip_efficiency: Overall efficiency of IP allocation
    
    Example:
        If you have many "Succeeded" pods still holding IPs,
        they're preventing reuse until garbage collection runs.
    """
    # Count pods by their lifecycle phase
    phase_counts = Counter()
    # Track IP allocation status per phase
    phase_with_ip = defaultdict(int)
    phase_without_ip = defaultdict(int)
    
    for pod in pods:
        # Get the current lifecycle phase
        phase = pod.get('status', {}).get('phase', 'Unknown')
        phase_counts[phase] += 1
        
        # Check if this pod has an IP allocated
        if pod.get('status', {}).get('podIP'):
            phase_with_ip[phase] += 1
        else:
            phase_without_ip[phase] += 1
    
    # Build detailed analysis for each phase
    lifecycle_analysis = []
    for phase in ['Pending', 'Running', 'Succeeded', 'Failed', 'Unknown']:
        if phase in phase_counts:
            total = phase_counts[phase]
            with_ip = phase_with_ip[phase]
            without_ip = phase_without_ip[phase]
            
            # Calculate what percentage of pods in this phase have IPs
            # Running pods should have ~100%, Pending should have ~0%
            ip_rate = (with_ip / total * 100) if total > 0 else 0
            
            lifecycle_analysis.append({
                "phase": phase,
                "total_pods": total,
                "pods_with_ip": with_ip,
                "pods_without_ip": without_ip,
                "ip_allocation_rate": round(ip_rate, 2)
            })
    
    # Identify pods that are stuck in non-running states but holding IPs
    # These are wasting IP addresses that could be used elsewhere
    stuck_pods = []
    for pod in pods:
        phase = pod.get('status', {}).get('phase', 'Unknown')
        pod_ip = pod.get('status', {}).get('podIP')
        
        # Pods that are not Running but have an IP allocated
        # This is wasteful - they're holding IPs without doing useful work
        # Common causes: CrashLoopBackOff, ImagePullBackOff, Failed jobs
        if phase in ['Pending', 'Failed', 'Unknown'] and pod_ip:
            creation_time = pod.get('metadata', {}).get('creationTimestamp')
            stuck_pods.append({
                "name": pod.get('metadata', {}).get('name'),
                "namespace": pod.get('metadata', {}).get('namespace'),
                "phase": phase,
                "ip_address": pod_ip,
                "creation_time": creation_time,
                "issue": f"{phase} pod holding IP address unnecessarily"
            })
    
    return {
        "lifecycle_analysis": lifecycle_analysis,
        "stuck_pods_with_ip": stuck_pods,
        "stuck_pod_count": len(stuck_pods),
        "wasted_ips_in_stuck_pods": len(stuck_pods)  # Each stuck pod = 1 wasted IP
    }


def _classify_pod_density(pod_count: int, max_pods: int) -> str:
    """
    Classify pod density level on a node.
    
    This helper function determines whether a node's pod count is:
    - LOW: Under-utilized, wasting resources
    - OPTIMAL: Good balance
    - HIGH: Getting crowded
    - CRITICAL: Dangerously close to limit
    
    Args:
        pod_count: Current number of pods on the node
        max_pods: Maximum pods the node can handle (from allocatable.pods)
    
    Returns:
        String classification: "LOW", "OPTIMAL", "HIGH", or "CRITICAL"
    
    Thresholds:
        - <30% of max = LOW (under-utilized)
        - 30-70% of max = OPTIMAL (good range)
        - 70-90% of max = HIGH (getting crowded)
        - >90% of max = CRITICAL (near capacity)
    
    Example:
        Node with 15 pods and maxPods=110
        → 15/110 = 13.6% → LOW density
        
        Node with 50 pods and maxPods=60
        → 50/60 = 83.3% → HIGH density
    """
    # Handle edge cases
    if max_pods == 0:
        return "UNKNOWN"
    if pod_count == 0:
        return "LOW"
    
    # Calculate utilization percentage
    utilization = (pod_count / max_pods) * 100
    
    # Classify based on percentage thresholds
    if utilization < 30:
        # Very low utilization - node is mostly empty
        return "LOW"
    elif utilization < 70:
        # Sweet spot - good balance between utilization and headroom
        return "OPTIMAL"
    elif utilization < 90:
        # Getting crowded - still acceptable but monitoring needed
        return "HIGH"
    else:
        # Near or at capacity - critical situation
        return "CRITICAL"
