"""
Subnet Capacity Diagnostic Module

This module analyzes Azure Virtual Network subnet capacity for AKS clusters.
It calculates IP address utilization, predicts exhaustion, and identifies
capacity planning issues before they cause node provisioning failures.

Key Checks:
- Total IPs available in subnet (based on CIDR range)
- IPs currently allocated to resources
- IP utilization percentage and trends
- Remaining capacity for scaling operations
- Reserved IP addresses (Azure reserves 5 IPs per subnet)
"""

import ipaddress
from typing import Dict, List, Tuple, Optional


def calculate_subnet_ips(cidr: str) -> Tuple[int, int]:
    """
    Calculate total and usable IP addresses in a subnet based on CIDR notation.
    
    Azure reserves 5 IP addresses in each subnet:
    - Network address (first IP)
    - Default gateway (second IP)
    - Azure DNS (third and fourth IPs)
    - Broadcast address (last IP)
    
    Args:
        cidr: Subnet CIDR notation (e.g., "10.0.0.0/24")
    
    Returns:
        Tuple of (total_ips, usable_ips)
        
    Example:
        cidr = "10.0.0.0/24"
        total, usable = calculate_subnet_ips(cidr)
        # total = 256, usable = 251 (256 - 5 reserved)
    """
    try:
        # Parse CIDR to get network object
        network = ipaddress.ip_network(cidr, strict=False)
        
        # Total IPs in the range (2^(32-prefix_length))
        total_ips = network.num_addresses
        
        # Azure reserves 5 IPs per subnet
        azure_reserved_ips = 5
        
        # Usable IPs = Total - Reserved
        usable_ips = total_ips - azure_reserved_ips
        
        return total_ips, usable_ips
    
    except ValueError as e:
        # Invalid CIDR notation
        raise ValueError(f"Invalid CIDR notation '{cidr}': {str(e)}")


def calculate_required_ips(node_count: int, max_pods: int, autoscaling: bool = False,
                          max_node_count: Optional[int] = None) -> Dict[str, int]:
    """
    Calculate IP addresses required for an AKS node pool.
    
    Each AKS node with Azure CNI networking requires:
    - 1 IP for the node itself
    - maxPods IPs for pod allocation (even if pods aren't running)
    
    Args:
        node_count: Current number of nodes in the pool
        max_pods: Maximum pods per node configuration
        autoscaling: Whether autoscaling is enabled
        max_node_count: Maximum node count if autoscaling is enabled
    
    Returns:
        Dictionary with IP requirements:
        - current_required: IPs needed for current node count
        - max_required: IPs needed for max scale (if autoscaling)
        - per_node: IPs required per node
        
    Example:
        # Node pool: 3 nodes, maxPods=30, autoscale to 10
        ips = calculate_required_ips(3, 30, True, 10)
        # ips = {
        #   'current_required': 93,  # 3 * (30 + 1)
        #   'max_required': 310,     # 10 * (30 + 1)
        #   'per_node': 31
        # }
    """
    # IPs per node = 1 (node IP) + maxPods (pod IPs)
    ips_per_node = 1 + max_pods
    
    # Calculate current requirement
    current_required = node_count * ips_per_node
    
    # Calculate max requirement for autoscaling
    if autoscaling and max_node_count:
        max_required = max_node_count * ips_per_node
    else:
        max_required = current_required
    
    return {
        'current_required': current_required,
        'max_required': max_required,
        'per_node': ips_per_node
    }


def analyze_subnet_utilization(subnet_cidr: str, allocated_ips: int, 
                               future_required_ips: int = 0) -> Dict[str, any]:
    """
    Analyze subnet IP utilization and capacity status.
    
    Determines if subnet has sufficient capacity for current usage plus
    any planned scaling operations. Calculates utilization percentage
    and provides status assessment.
    
    Args:
        subnet_cidr: Subnet CIDR notation (e.g., "10.240.0.0/16")
        allocated_ips: Number of IPs currently allocated/in use
        future_required_ips: Additional IPs needed for scaling (optional)
    
    Returns:
        Dictionary containing:
        - total_ips: Total IPs in subnet
        - usable_ips: IPs available for allocation (after Azure reservation)
        - allocated_ips: IPs currently allocated
        - available_ips: IPs still available
        - utilization_percent: Current utilization percentage
        - projected_utilization: Utilization after planned scaling
        - status: 'HEALTHY', 'WARNING', or 'CRITICAL'
        - can_accommodate_scaling: Boolean indicating if scaling is possible
        
    Status Thresholds:
        - HEALTHY: < 70% utilization
        - WARNING: 70-85% utilization
        - CRITICAL: > 85% utilization
    """
    # Calculate total and usable IPs from CIDR
    total_ips, usable_ips = calculate_subnet_ips(subnet_cidr)
    
    # Calculate available IPs
    available_ips = usable_ips - allocated_ips
    
    # Calculate utilization percentage
    utilization_percent = (allocated_ips / usable_ips * 100) if usable_ips > 0 else 100
    
    # Calculate projected utilization with future requirements
    projected_allocated = allocated_ips + future_required_ips
    projected_utilization = (projected_allocated / usable_ips * 100) if usable_ips > 0 else 100
    
    # Determine capacity status based on utilization thresholds
    if utilization_percent >= 85:
        status = 'CRITICAL'
    elif utilization_percent >= 70:
        status = 'WARNING'
    else:
        status = 'HEALTHY'
    
    # Check if subnet can accommodate planned scaling
    can_accommodate_scaling = (projected_allocated <= usable_ips)
    
    return {
        'total_ips': total_ips,
        'usable_ips': usable_ips,
        'allocated_ips': allocated_ips,
        'available_ips': available_ips,
        'utilization_percent': round(utilization_percent, 2),
        'projected_utilization': round(projected_utilization, 2),
        'status': status,
        'can_accommodate_scaling': can_accommodate_scaling,
        'future_required_ips': future_required_ips
    }


def check_subnet_capacity(network_client, node_pools: List, logger) -> List[Dict]:
    """
    Comprehensive subnet capacity check for all node pools in an AKS cluster.
    
    Analyzes each subnet used by node pools to identify:
    - High IP utilization (risk of exhaustion)
    - Insufficient capacity for autoscaling
    - Subnets approaching full capacity
    - Over-provisioned subnets with wasted IPs
    
    The function extracts subnet information from node pool vnet_subnet_id,
    calculates IP requirements, and assesses capacity status.
    
    Args:
        network_client: Azure Network Management Client for subnet queries
        node_pools: List of AKS node pool objects
        logger: Logger instance for diagnostic messages
    
    Returns:
        List of issue dictionaries, each containing:
        - severity: 'CRITICAL', 'WARNING', or 'INFO'
        - code: Issue classification code
        - message: Human-readable issue description
        - affected_resource: Resource(s) impacted
        - details: Detailed metrics and recommendations
        
    Example Issue:
        {
            'severity': 'CRITICAL',
            'code': 'SUBNET_NEAR_CAPACITY',
            'message': 'Subnet systempool-subnet is 92% full',
            'affected_resource': 'systempool/systempool-subnet',
            'details': {
                'utilization': 92.5,
                'available_ips': 45,
                'required_for_scaling': 93,
                'recommendation': 'Create new subnet for additional capacity'
            }
        }
    """
    issues = []
    
    # Track processed subnets to avoid duplicate analysis
    # Key: subnet_id, Value: analysis result
    processed_subnets = {}
    
    try:
        for pool in node_pools:
            # Skip pools without subnet configuration
            if not pool.vnet_subnet_id:
                logger.debug(f"Node pool '{pool.name}' has no vnet_subnet_id, skipping")
                continue
            
            # Check if we already processed this subnet
            subnet_id = pool.vnet_subnet_id
            if subnet_id in processed_subnets:
                # Use cached result
                continue
            
            # Parse Azure resource ID to extract subnet details
            # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/{subnet}
            parts = subnet_id.split('/')
            if len(parts) < 11:
                logger.warning(f"Invalid subnet ID format for pool '{pool.name}': {subnet_id}")
                continue
            
            # Extract components from resource ID
            subnet_rg = parts[4]          # Resource group name
            vnet_name = parts[8]          # Virtual network name
            subnet_name = parts[10]       # Subnet name
            
            try:
                # Query Azure for subnet information
                subnet = network_client.get_subnet(subnet_rg, vnet_name, subnet_name)
                
                if not subnet:
                    logger.warning(f"Subnet not found: {subnet_name}")
                    continue
                
                # Get subnet CIDR range
                subnet_cidr = subnet.address_prefix
                
                # Calculate IP requirements for this node pool
                max_pods = pool.max_pods or 30  # Default maxPods if not specified
                node_count = pool.count or 0
                
                # Check if autoscaling is enabled
                autoscaling = pool.enable_auto_scaling or False
                max_node_count = pool.max_count if autoscaling else node_count
                
                # Calculate required IPs
                ip_requirements = calculate_required_ips(
                    node_count=node_count,
                    max_pods=max_pods,
                    autoscaling=autoscaling,
                    max_node_count=max_node_count
                )
                
                # Analyze subnet utilization
                # Note: We use current_required for allocated, and calculate future needs
                future_ips = ip_requirements['max_required'] - ip_requirements['current_required']
                
                analysis = analyze_subnet_utilization(
                    subnet_cidr=subnet_cidr,
                    allocated_ips=ip_requirements['current_required'],
                    future_required_ips=future_ips
                )
                
                # Store result to avoid re-processing
                processed_subnets[subnet_id] = analysis
                
                # Generate issues based on analysis
                utilization = analysis['utilization_percent']
                
                # CRITICAL: Subnet near capacity (>85% utilization)
                if utilization >= 85:
                    issues.append({
                        'severity': 'CRITICAL',
                        'code': 'SUBNET_NEAR_CAPACITY',
                        'message': f"Subnet '{subnet_name}' critically high utilization at {utilization:.1f}%",
                        'affected_resource': f"{pool.name}/{subnet_name}",
                        'details': {
                            'description': (
                                f"Subnet has only {analysis['available_ips']} IPs remaining out of "
                                f"{analysis['usable_ips']} usable IPs. Node provisioning may fail."
                            ),
                            'utilization_percent': utilization,
                            'available_ips': analysis['available_ips'],
                            'allocated_ips': analysis['allocated_ips'],
                            'subnet_cidr': subnet_cidr,
                            'recommendation': (
                                "Immediate action required: Create a new subnet with larger CIDR range "
                                "and migrate node pools, or reduce maxPods configuration."
                            )
                        }
                    })
                
                # WARNING: High utilization (70-85%)
                elif utilization >= 70:
                    issues.append({
                        'severity': 'WARNING',
                        'code': 'SUBNET_HIGH_UTILIZATION',
                        'message': f"Subnet '{subnet_name}' has high utilization at {utilization:.1f}%",
                        'affected_resource': f"{pool.name}/{subnet_name}",
                        'details': {
                            'description': (
                                f"Subnet utilization is approaching capacity. "
                                f"{analysis['available_ips']} IPs remaining."
                            ),
                            'utilization_percent': utilization,
                            'available_ips': analysis['available_ips'],
                            'subnet_cidr': subnet_cidr,
                            'recommendation': (
                                "Plan for additional capacity. Consider creating a new subnet "
                                "or optimizing maxPods configuration."
                            )
                        }
                    })
                
                # WARNING: Cannot accommodate autoscaling
                if autoscaling and not analysis['can_accommodate_scaling']:
                    issues.append({
                        'severity': 'WARNING',
                        'code': 'INSUFFICIENT_CAPACITY_FOR_SCALING',
                        'message': f"Subnet '{subnet_name}' cannot accommodate autoscaling for pool '{pool.name}'",
                        'affected_resource': f"{pool.name}/{subnet_name}",
                        'details': {
                            'description': (
                                f"Node pool configured to scale to {max_node_count} nodes, "
                                f"requiring {ip_requirements['max_required']} IPs, but subnet only "
                                f"has {analysis['usable_ips']} usable IPs."
                            ),
                            'current_nodes': node_count,
                            'max_nodes': max_node_count,
                            'required_ips': ip_requirements['max_required'],
                            'usable_ips': analysis['usable_ips'],
                            'recommendation': (
                                f"Reduce max_count to {analysis['usable_ips'] // ip_requirements['per_node']} nodes "
                                f"or create larger subnet for scaling."
                            )
                        }
                    })
                
                # INFO: Log healthy subnets for completeness
                if utilization < 70:
                    logger.info(
                        f"Subnet '{subnet_name}' is healthy: {utilization:.1f}% utilization, "
                        f"{analysis['available_ips']} IPs available"
                    )
                
            except Exception as subnet_error:
                # Log error but continue processing other subnets
                logger.error(f"Error analyzing subnet {subnet_name}: {str(subnet_error)}")
                issues.append({
                    'severity': 'WARNING',
                    'code': 'SUBNET_ANALYSIS_ERROR',
                    'message': f"Could not analyze subnet '{subnet_name}'",
                    'affected_resource': f"{pool.name}/{subnet_name}",
                    'details': {
                        'description': f"Error querying subnet: {str(subnet_error)}",
                        'recommendation': 'Verify network permissions and subnet configuration'
                    }
                })
    
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Error in subnet capacity check: {str(e)}")
        issues.append({
            'severity': 'ERROR',
            'code': 'SUBNET_CHECK_FAILED',
            'message': 'Subnet capacity check failed',
            'affected_resource': 'all_subnets',
            'details': {
                'description': str(e),
                'recommendation': 'Check Azure credentials and network permissions'
            }
        })
    
    return issues