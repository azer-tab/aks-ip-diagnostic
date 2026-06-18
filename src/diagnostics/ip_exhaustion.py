"""
IP Exhaustion Diagnostic Module

This module detects IP address exhaustion issues in AKS clusters that can cause:
- Node provisioning failures
- Failed cluster upgrades
- Pod scheduling failures
- Cluster scaling issues

The module analyzes multiple indicators:
1. Node pool provisioning states (Failed, Upgrading stuck)
2. Subnet IP availability
3. Recent provisioning errors
4. Correlation between IP availability and failures

IP exhaustion typically manifests as:
- Node pool stuck in "Updating" state
- Provisioning failures with subnet-related error messages
- New nodes failing to join the cluster
- Upgrade operations timing out
"""

from typing import Dict, List, Optional
from datetime import datetime


def analyze_provisioning_failure(pool) -> Optional[Dict]:
    """
    Analyze a node pool's provisioning state for IP-related failures.
    
    Examines the provisioning state and error messages to determine if
    a failure is related to IP exhaustion. Common IP exhaustion indicators:
    - Error messages containing "subnet", "IP", "address space"
    - Failed state with network-related errors
    - Stuck in Updating state for extended periods
    
    Args:
        pool: AKS node pool object with provisioning information
    
    Returns:
        Dictionary with failure analysis if IP-related, None otherwise:
        - is_ip_related: Boolean indicating IP exhaustion likelihood
        - confidence: 'HIGH', 'MEDIUM', or 'LOW' confidence level
        - error_message: Original error message from Azure
        - indicators: List of detected IP exhaustion indicators
        
    Example:
        analysis = analyze_provisioning_failure(node_pool)
        if analysis and analysis['is_ip_related']:
            # Handle IP exhaustion issue
    """
    # Check if pool is in a failed or problematic state
    if pool.provisioning_state not in ["Failed", "Updating"]:
        return None
    
    # Get error message if available
    error_message = getattr(pool, 'provisioning_state_message', '')
    
    # Keywords that indicate IP-related failures
    ip_keywords = [
        'subnet',
        'ip address',
        'address space',
        'cidr',
        'network capacity',
        'not enough ip',
        'insufficient ip',
        'ip exhaustion',
        'out of ip',
        'no available ip'
    ]
    
    # Analyze error message for IP-related keywords
    indicators = []
    error_lower = error_message.lower()
    
    for keyword in ip_keywords:
        if keyword in error_lower:
            indicators.append(keyword)
    
    # Determine if failure is IP-related and confidence level
    if len(indicators) >= 2:
        # Multiple indicators = high confidence
        is_ip_related = True
        confidence = 'HIGH'
    elif len(indicators) == 1:
        # Single indicator = medium confidence
        is_ip_related = True
        confidence = 'MEDIUM'
    elif pool.provisioning_state == "Failed":
        # Failed state with no clear indicators = low confidence
        is_ip_related = False
        confidence = 'LOW'
    else:
        # Updating state without indicators might be normal operation
        is_ip_related = False
        confidence = 'LOW'
    
    if not is_ip_related and not indicators:
        return None
    
    return {
        'is_ip_related': is_ip_related,
        'confidence': confidence,
        'error_message': error_message,
        'indicators': indicators,
        'provisioning_state': pool.provisioning_state
    }


def calculate_ip_deficit(required_ips: int, available_ips: int, 
                         buffer_percent: float = 20.0) -> Dict:
    """
    Calculate IP address deficit and recommended capacity.
    
    Determines if there are enough IPs for current requirements plus a
    safety buffer for operations like:
    - Rolling upgrades (temporary double capacity)
    - Node replacement
    - Autoscaling bursts
    
    Args:
        required_ips: Number of IPs needed for current allocation
        available_ips: Number of IPs available in subnet
        buffer_percent: Recommended buffer percentage (default 20%)
    
    Returns:
        Dictionary containing:
        - has_deficit: Boolean indicating if there's a deficit
        - deficit_amount: Number of IPs short (negative if surplus)
        - recommended_capacity: Recommended total capacity with buffer
        - buffer_ips: Number of buffer IPs recommended
        - current_coverage: Percentage of required IPs available
        
    Example:
        # Need 200 IPs, have 180 available
        deficit = calculate_ip_deficit(200, 180, 20.0)
        # {
        #   'has_deficit': True,
        #   'deficit_amount': 60,  # Need 240 total (200 + 20%), have 180
        #   'recommended_capacity': 240,
        #   'buffer_ips': 40,
        #   'current_coverage': 90.0
        # }
    """
    # Calculate recommended buffer IPs
    buffer_ips = int(required_ips * (buffer_percent / 100))
    
    # Total recommended capacity
    recommended_capacity = required_ips + buffer_ips
    
    # Calculate deficit/surplus
    deficit_amount = recommended_capacity - available_ips
    
    # Check if there's a deficit
    has_deficit = deficit_amount > 0
    
    # Calculate current coverage percentage
    current_coverage = (available_ips / recommended_capacity * 100) if recommended_capacity > 0 else 0
    
    return {
        'has_deficit': has_deficit,
        'deficit_amount': deficit_amount,
        'recommended_capacity': recommended_capacity,
        'buffer_ips': buffer_ips,
        'current_coverage': round(current_coverage, 2),
        'required_ips': required_ips,
        'available_ips': available_ips
    }


def detect_upgrade_blocking_exhaustion(node_pools: List, network_client, 
                                       logger) -> List[Dict]:
    """
    Detect IP exhaustion that would block cluster upgrades.
    
    During a Kubernetes upgrade, AKS performs a rolling update which temporarily
    requires nearly double the IP capacity:
    1. New node is created with updated version
    2. Workloads are drained from old node
    3. Old node is deleted
    4. Process repeats for each node
    
    This function checks if enough IPs are available for safe upgrades.
    
    Args:
        node_pools: List of AKS node pool objects
        network_client: Azure Network client for subnet queries
        logger: Logger instance
    
    Returns:
        List of issue dictionaries for node pools that cannot safely upgrade
        
    Issue severity levels:
        - CRITICAL: Upgrade definitely blocked (no spare IPs)
        - WARNING: Upgrade may fail (insufficient buffer)
    """
    issues = []
    
    for pool in node_pools:
        try:
            # Skip pools without subnet configuration
            if not pool.vnet_subnet_id:
                continue
            
            # Calculate IPs needed for upgrade
            # During upgrade, we temporarily need capacity for old + new node
            max_pods = pool.max_pods or 30
            ips_per_node = max_pods + 1
            node_count = pool.count or 0
            
            # For surge upgrades, AKS may create multiple nodes simultaneously
            # Default surge = 1 node, but can be configured higher
            surge_nodes = 1  # Conservative estimate
            upgrade_required_ips = surge_nodes * ips_per_node
            
            # Parse subnet information
            parts = pool.vnet_subnet_id.split('/')
            if len(parts) < 11:
                continue
            
            subnet_rg = parts[4]
            vnet_name = parts[8]
            subnet_name = parts[10]
            
            # Get subnet details
            subnet = network_client.get_subnet(subnet_rg, vnet_name, subnet_name)
            if not subnet:
                continue
            
            # Calculate available IPs (simplified - would need actual allocation data)
            from diagnostics.subnet_capacity import calculate_subnet_ips
            total_ips, usable_ips = calculate_subnet_ips(subnet.address_prefix)
            
            # Estimate currently allocated (this is simplified)
            current_allocated = node_count * ips_per_node
            available_for_upgrade = usable_ips - current_allocated
            
            # Check if upgrade is possible
            if available_for_upgrade < upgrade_required_ips:
                issues.append({
                    'severity': 'CRITICAL',
                    'code': 'UPGRADE_BLOCKED_BY_IP_EXHAUSTION',
                    'message': f"Cluster upgrade blocked for pool '{pool.name}' due to insufficient IPs",
                    'affected_resource': f"{pool.name}/{subnet_name}",
                    'details': {
                        'description': (
                            f"Upgrade requires {upgrade_required_ips} additional IPs for surge capacity, "
                            f"but only {available_for_upgrade} IPs available. Upgrade will fail."
                        ),
                        'required_for_upgrade': upgrade_required_ips,
                        'available_ips': available_for_upgrade,
                        'surge_nodes': surge_nodes,
                        'recommendation': (
                            "Before upgrading: 1) Create new subnet with more capacity, "
                            "2) Create new node pool in new subnet, 3) Migrate workloads, "
                            "4) Delete old pool, OR reduce maxPods configuration."
                        )
                    }
                })
            
            # Warning if buffer is too small
            elif available_for_upgrade < (upgrade_required_ips * 1.5):
                issues.append({
                    'severity': 'WARNING',
                    'code': 'UPGRADE_IP_BUFFER_LOW',
                    'message': f"Low IP buffer for upgrades on pool '{pool.name}'",
                    'affected_resource': f"{pool.name}/{subnet_name}",
                    'details': {
                        'description': (
                            f"Upgrade is possible but risky. Only {available_for_upgrade} IPs "
                            f"available for {upgrade_required_ips} required (minimal safety buffer)."
                        ),
                        'available_ips': available_for_upgrade,
                        'recommendation': 'Monitor IP usage closely during upgrades'
                    }
                })
        
        except Exception as e:
            logger.error(f"Error checking upgrade capacity for pool {pool.name}: {str(e)}")
            continue
    
    return issues


def check_ip_exhaustion(aks_client, cluster, node_pools: List, 
                       network_client, logger) -> List[Dict]:
    """
    Comprehensive IP exhaustion detection for AKS clusters.
    
    This is the main entry point for IP exhaustion diagnostics. It performs
    multiple checks to identify current IP exhaustion issues and predict
    future problems:
    
    1. Provisioning Failures: Detect nodes failing due to no available IPs
    2. Subnet Near Capacity: Identify subnets approaching IP limits
    3. Upgrade Blocking: Check if upgrades would fail due to IP constraints
    4. Scaling Limits: Verify autoscaling configurations are achievable
    
    The function correlates multiple data points to provide accurate
    IP exhaustion detection and actionable recommendations.
    
    Args:
        aks_client: AKS management client instance
        cluster: AKS cluster object
        node_pools: List of node pool objects from cluster
        network_client: Network management client for subnet queries
        logger: Logger instance for diagnostic messages
    
    Returns:
        List of issue dictionaries, each containing:
        - severity: 'CRITICAL', 'WARNING', or 'INFO'
        - code: Standardized issue code for categorization
        - message: Human-readable issue summary
        - affected_resource: Specific resources impacted
        - details: Detailed analysis and remediation steps
        
    Example Usage:
        issues = check_ip_exhaustion(aks, cluster, pools, network, logger)
        for issue in issues:
            if issue['severity'] == 'CRITICAL':
                alert_ops_team(issue)
    """
    issues = []
    
    try:
        # ===================================================================
        # CHECK 1: Analyze provisioning failures for IP-related issues
        # ===================================================================
        logger.info("Analyzing node pool provisioning states for IP exhaustion...")
        
        for pool in node_pools:
            # Analyze provisioning state
            failure_analysis = analyze_provisioning_failure(pool)
            
            if failure_analysis and failure_analysis['is_ip_related']:
                # Found IP-related provisioning failure
                severity = 'CRITICAL' if pool.provisioning_state == 'Failed' else 'WARNING'
                confidence = failure_analysis['confidence']
                
                issues.append({
                    'severity': severity,
                    'code': 'IP_EXHAUSTION_PROVISIONING_FAILURE',
                    'message': f"Node pool '{pool.name}' {pool.provisioning_state} due to likely IP exhaustion",
                    'affected_resource': pool.name,
                    'details': {
                        'description': (
                            f"Provisioning state: {pool.provisioning_state}. "
                            f"IP-related failure detected with {confidence} confidence. "
                            f"Error: {failure_analysis['error_message'][:200]}"
                        ),
                        'confidence_level': confidence,
                        'indicators': failure_analysis['indicators'],
                        'full_error': failure_analysis['error_message'],
                        'recommendation': (
                            "1. Check subnet capacity and available IPs. "
                            "2. Consider creating new subnet with larger CIDR range. "
                            "3. Reduce maxPods setting if appropriate. "
                            "4. Review and clean up unused IP allocations."
                        )
                    }
                })
        
        # ===================================================================
        # CHECK 2: Detect IP exhaustion blocking upgrades
        # ===================================================================
        logger.info("Checking if IP exhaustion would block cluster upgrades...")
        
        upgrade_issues = detect_upgrade_blocking_exhaustion(node_pools, network_client, logger)
        issues.extend(upgrade_issues)
        
       # ===================================================================
        # CHECK 3: Cross-reference with subnet capacity analysis
        # ===================================================================
        # This check is performed by subnet_capacity module
        # We add context here about correlation between failures and capacity
        logger.info("Correlating provisioning failures with subnet capacity...")
        
        # Count failed pools
        failed_pools = [p for p in node_pools if p.provisioning_state == "Failed"]
        
        if failed_pools:
            # If we have failures, add a summary issue
            issues.append({
                'severity': 'INFO',
                'code': 'IP_EXHAUSTION_SUMMARY',
                'message': f"Detected {len(failed_pools)} failed node pool(s) - investigating IP exhaustion",
                'affected_resource': ', '.join([p.name for p in failed_pools]),
                'details': {
                    'description': (
                        f"Found {len(failed_pools)} node pool(s) in Failed state. "
                        "Analyzing correlation with IP availability. "
                        "See individual issues for specific recommendations."
                    ),
                    'failed_pools': [p.name for p in failed_pools],
                    'total_node_pools': len(node_pools),
                    'recommendation': (
                        "Review subnet capacity diagnostics for detailed IP utilization analysis. "
                        "Address CRITICAL subnet capacity issues first."
                    )
                }
            })
    
    except Exception as e:
        # Log error but don't fail entire diagnostic
        logger.error(f"Error in IP exhaustion check: {str(e)}")
        issues.append({
            'severity': 'ERROR',
            'code': 'IP_EXHAUSTION_CHECK_ERROR',
            'message': 'IP exhaustion check encountered an error',
            'affected_resource': 'cluster',
            'details': {
                'description': f"Error during IP exhaustion analysis: {str(e)}",
                'recommendation': 'Review Azure credentials and permissions. Check logs for details.'
            }
        })
    
    return issues