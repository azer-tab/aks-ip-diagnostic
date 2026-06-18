"""
Cost calculation utilities for AKS resources.

This module provides functions to estimate Azure costs for:
- VM instances
- Public IPs
- Managed disks
- IP address allocation
"""
from typing import Dict, Optional


# Azure VM pricing (USD per month) - France Central region
# Source: https://azure.microsoft.com/pricing/details/virtual-machines/linux/
VM_PRICING = {
    'Standard_B2s': 37.96,
    'Standard_B2ms': 75.92,
    'Standard_D2s_v3': 96.36,
    'Standard_D4s_v3': 192.72,
    'Standard_DS2_v2': 142.35,
    'Standard_DS3_v2': 284.70,
    'Standard_DS4_v2': 569.40,
    'Standard_D8s_v3': 385.44,
    'Standard_D16s_v3': 770.88,
    'Standard_E2s_v3': 146.00,
    'Standard_E4s_v3': 292.00,
    'Standard_F2s_v2': 85.41,
    'Standard_F4s_v2': 170.82,
}

# IP address pricing (USD per month)
# Source: https://azure.microsoft.com/pricing/details/ip-addresses/
IP_PRICING = {
    'public_ip_static': 3.65,  # Per IP per month
    'public_ip_dynamic': 2.74,  # Per IP per month
    'private_ip_overhead': 0.036,  # Estimated overhead per IP (not directly charged but included in VNet costs)
}

# Managed disk pricing (USD per month) - France Central
# Source: https://azure.microsoft.com/pricing/details/managed-disks/
DISK_PRICING = {
    'Premium_SSD_P10': 19.71,   # 128 GB
    'Premium_SSD_P15': 38.40,   # 256 GB
    'Premium_SSD_P20': 73.73,   # 512 GB
    'Premium_SSD_P30': 135.17,  # 1024 GB
    'Standard_SSD_E10': 5.86,   # 128 GB
    'Standard_SSD_E15': 11.68,  # 256 GB
    'Standard_SSD_E20': 23.04,  # 512 GB
}


def estimate_vm_cost(vm_size: str, count: int = 1, region: str = 'francecentral') -> float:
    """
    Estimate monthly cost for VM instances.
    
    Args:
        vm_size: Azure VM size (e.g., 'Standard_DS3_v2')
        count: Number of VMs
        region: Azure region (currently only francecentral supported)
        
    Returns:
        Estimated monthly cost in USD
    """
    base_cost = VM_PRICING.get(vm_size, 100.0)  # Default to $100/month if unknown
    return base_cost * count


def estimate_disk_cost(disk_size_gb: int, disk_type: str = 'Premium_SSD') -> float:
    """
    Estimate monthly cost for managed disk.
    
    Args:
        disk_size_gb: Disk size in GB
        disk_type: Disk type (Premium_SSD, Standard_SSD, Standard_HDD)
        
    Returns:
        Estimated monthly cost in USD
    """
    # Map disk size to pricing tier
    if disk_size_gb <= 128:
        tier = 'P10' if disk_type == 'Premium_SSD' else 'E10'
    elif disk_size_gb <= 256:
        tier = 'P15' if disk_type == 'Premium_SSD' else 'E15'
    elif disk_size_gb <= 512:
        tier = 'P20' if disk_type == 'Premium_SSD' else 'E20'
    else:
        tier = 'P30' if disk_type == 'Premium_SSD' else 'E20'
    
    key = f"{disk_type}_{tier}"
    return DISK_PRICING.get(key, 20.0)  # Default to $20/month


def estimate_ip_cost(ip_count: int, ip_type: str = 'private') -> float:
    """
    Estimate monthly cost for IP addresses.
    
    Args:
        ip_count: Number of IPs
        ip_type: Type of IP (private, public_static, public_dynamic)
        
    Returns:
        Estimated monthly cost in USD
    """
    if ip_type == 'private':
        # Private IPs have overhead cost (VNet pricing)
        return ip_count * IP_PRICING['private_ip_overhead']
    elif ip_type == 'public_static':
        return ip_count * IP_PRICING['public_ip_static']
    elif ip_type == 'public_dynamic':
        return ip_count * IP_PRICING['public_ip_dynamic']
    else:
        return 0.0


def estimate_node_pool_cost(vm_size: str, node_count: int, 
                           os_disk_size_gb: int = 128,
                           enable_public_ip: bool = False) -> Dict[str, float]:
    """
    Estimate total monthly cost for a node pool.
    
    Args:
        vm_size: Azure VM size
        node_count: Number of nodes
        os_disk_size_gb: OS disk size in GB
        enable_public_ip: Whether nodes have public IPs
        
    Returns:
        Dictionary with cost breakdown
    """
    vm_cost = estimate_vm_cost(vm_size, node_count)
    disk_cost = estimate_disk_cost(os_disk_size_gb) * node_count
    ip_cost = 0.0
    
    if enable_public_ip:
        ip_cost = estimate_ip_cost(node_count, 'public_static')
    
    return {
        'vm_cost_monthly': round(vm_cost, 2),
        'disk_cost_monthly': round(disk_cost, 2),
        'ip_cost_monthly': round(ip_cost, 2),
        'total_monthly': round(vm_cost + disk_cost + ip_cost, 2),
        'total_annual': round((vm_cost + disk_cost + ip_cost) * 12, 2)
    }


def calculate_ip_waste_cost(allocated_ips: int, used_ips: int) -> Dict[str, float]:
    """
    Calculate cost of wasted IP addresses.
    
    Args:
        allocated_ips: Total IPs allocated
        used_ips: IPs actually in use
        
    Returns:
        Dictionary with waste metrics
    """
    wasted_ips = allocated_ips - used_ips
    waste_percent = (wasted_ips / allocated_ips * 100) if allocated_ips > 0 else 0
    
    # Estimate cost impact (small per-IP overhead)
    monthly_waste_cost = wasted_ips * IP_PRICING['private_ip_overhead']
    annual_waste_cost = monthly_waste_cost * 12
    
    return {
        'wasted_ips': wasted_ips,
        'waste_percent': round(waste_percent, 2),
        'monthly_cost': round(monthly_waste_cost, 2),
        'annual_cost': round(annual_waste_cost, 2)
    }


def calculate_health_score(issues: list, warnings: int, critical: int, 
                          subnet_utilization: float, ip_waste_percent: float) -> Dict[str, any]:
    """
    Calculate overall cluster health score (0-100).
    
    Scoring factors:
    - Critical issues: -20 points each
    - Warnings: -10 points each
    - Subnet utilization >70%: -5 to -15 points
    - IP waste >50%: -5 to -15 points
    
    Args:
        issues: List of issues
        warnings: Number of warnings
        critical: Number of critical issues
        subnet_utilization: Subnet utilization percentage
        ip_waste_percent: IP waste percentage
        
    Returns:
        Dictionary with health score and grade
    """
    score = 100
    
    # Deduct points for issues
    score -= critical * 20
    score -= warnings * 10
    
    # Deduct points for high subnet utilization
    if subnet_utilization > 85:
        score -= 15
    elif subnet_utilization > 70:
        score -= 5
    
    # Deduct points for IP waste
    if ip_waste_percent > 80:
        score -= 15
    elif ip_waste_percent > 50:
        score -= 10
    elif ip_waste_percent > 30:
        score -= 5
    
    # Ensure score is between 0-100
    score = max(0, min(100, score))
    
    # Calculate grade
    if score >= 90:
        grade = 'A'
    elif score >= 80:
        grade = 'B'
    elif score >= 70:
        grade = 'C'
    elif score >= 60:
        grade = 'D'
    else:
        grade = 'F'
    
    return {
        'score': score,
        'grade': grade
    }
