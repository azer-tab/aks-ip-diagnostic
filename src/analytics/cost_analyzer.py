"""
Cost analysis for IP-related Azure spending.

This module calculates actual costs of IP waste and potential savings
from optimization recommendations. All calculations are based on Azure
public pricing as of January 2026.

**SAFETY: READ-ONLY MODULE**
- Only performs cost calculations
- Does not modify any Azure resources
- Does not access billing/payment APIs
"""

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AzurePricing:
    """
    Azure networking pricing constants.

    Prices are in USD and based on public Azure pricing.
    Update these values if pricing changes or for specific regions.

    Sources:
    - https://azure.microsoft.com/en-us/pricing/details/ip-addresses/
    - https://azure.microsoft.com/en-us/pricing/details/virtual-network/
    - https://azure.microsoft.com/en-us/pricing/details/kubernetes-service/
    """

    # Virtual Network pricing (per IP address)
    # Note: First 50 IPs in a VNet are free, then $0.005/IP/month
    vnet_ip_cost_per_month: float = 0.005
    vnet_free_ips: int = 50

    # Public IP address pricing
    public_ip_static_per_month: float = 3.65
    public_ip_dynamic_per_hour: float = 0.004  # ~$2.92/month

    # Load Balancer pricing (affects IP usage)
    load_balancer_rule_per_hour: float = 0.025  # ~$18.25/month

    # Azure CNI specific costs
    # CNI reserves IPs even when not in use, leading to waste
    cni_reservation_overhead_pct: float = 0.10  # 10% overhead for reservations

    # Node pool VM pricing (for context - helps calculate total cost)
    # These are examples - actual costs vary by VM size
    vm_costs_per_month: dict[str, float] = None

    # Subnet costs (indirectly related to IP usage)
    subnet_management_cost_per_month: float = 0.0  # No direct cost, but capacity planning matters

    def __post_init__(self):
        """Initialize VM costs dictionary."""
        if self.vm_costs_per_month is None:
            # Example VM costs for common AKS node sizes
            # These are approximate Standard_D series prices in East US
            self.vm_costs_per_month = {
                "Standard_D2s_v3": 96.36,  # 2 vCPU, 8 GB RAM
                "Standard_D4s_v3": 192.72,  # 4 vCPU, 16 GB RAM
                "Standard_D8s_v3": 385.44,  # 8 vCPU, 32 GB RAM
                "Standard_D16s_v3": 770.88,  # 16 vCPU, 64 GB RAM
            }


class CostAnalyzer:
    """
    Calculate costs and savings opportunities from IP optimization.

    This analyzer helps answer:
    - How much money are we wasting on unused IPs?
    - What are the potential savings from optimization?
    - What's the ROI of implementing recommendations?
    - How do costs compare across different configurations?

    Example:
        analyzer = CostAnalyzer(region='eastus')
        cost_report = analyzer.analyze_cluster_costs(diagnostic_data)
        print(f"Monthly waste: ${cost_report['monthly_waste_cost']}")
    """

    def __init__(self, region: str = "eastus", pricing: AzurePricing | None = None):
        """
        Initialize cost analyzer with region-specific pricing.

        Args:
            region: Azure region for pricing (affects some costs)
            pricing: Custom pricing object (uses defaults if not provided)

        Note:
            Different Azure regions may have different pricing.
            This uses standard US pricing as baseline.
        """
        self.region = region
        self.pricing = pricing or AzurePricing()
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"Cost analyzer initialized for region: {region}")

    def analyze_cluster_costs(self, diagnostic_data: dict) -> dict:
        """
        Perform comprehensive cost analysis for a cluster.

        This is the main entry point that analyzes all cost aspects:
        - Current IP waste costs
        - Node pool costs
        - Potential savings from optimization
        - ROI calculations

        Args:
            diagnostic_data: Complete diagnostic report from main analysis

        Returns:
            Dictionary containing:
                - current_costs: Current monthly costs breakdown
                - waste_costs: Costs attributed to IP waste
                - optimization_savings: Potential savings from each recommendation
                - total_potential_savings: Sum of all optimization savings
                - roi_analysis: Return on investment calculations
                - cost_trends: Historical cost projections

        Example:
            {
                'current_costs': {
                    'total_monthly': 5432.50,
                    'ip_costs': 125.00,
                    'node_costs': 5307.50
                },
                'waste_costs': {
                    'monthly': 87.50,
                    'annual': 1050.00,
                    'wasted_ips': 17500
                },
                'total_potential_savings': {
                    'monthly': 156.25,
                    'annual': 1875.00
                }
            }
        """
        # Extract key metrics from diagnostic data
        pod_analysis = diagnostic_data.get("pod_ip_analysis", {})
        ip_waste = pod_analysis.get("ip_waste_analysis", {})
        # Calculate current costs
        current_costs = self._calculate_current_costs(diagnostic_data)

        # Calculate IP waste costs
        waste_costs = self.calculate_ip_waste_cost(
            wasted_ips=ip_waste.get("wasted_ips", 0), total_reserved=ip_waste.get("reserved_ips", 0)
        )

        # Calculate optimization savings
        optimization_savings = self._calculate_optimization_savings(
            diagnostic_data.get("recommendations", []), current_costs
        )

        # Calculate ROI for implementing recommendations
        roi_analysis = self._calculate_roi(optimization_savings, current_costs)

        # Project cost trends
        cost_trends = self._project_cost_trends(current_costs, waste_costs)

        # Build comprehensive cost report
        cost_report = {
            "metadata": {
                "analysis_date": datetime.utcnow().isoformat() + "Z",
                "region": self.region,
                "currency": "USD",
                "pricing_date": "2026-01-22",
                "cluster_name": diagnostic_data.get("cluster_name", "unknown"),
            },
            "current_costs": current_costs,
            "waste_costs": waste_costs,
            "optimization_savings": optimization_savings,
            "total_potential_savings": self._sum_savings(optimization_savings),
            "roi_analysis": roi_analysis,
            "cost_trends": cost_trends,
            "summary": self._generate_cost_summary(
                current_costs, waste_costs, optimization_savings
            ),
        }

        return cost_report

    def calculate_ip_waste_cost(self, wasted_ips: int, total_reserved: int = None) -> dict:
        """
        Calculate monthly and annual cost of wasted IP addresses.

        Azure CNI pre-allocates IPs to nodes even when not in use.
        This calculates the cost of those unused IPs.

        Args:
            wasted_ips: Number of IP addresses reserved but not used
            total_reserved: Total IPs reserved (for percentage calculation)

        Returns:
            Dictionary with cost breakdown:
                - monthly_cost: Monthly waste cost
                - annual_cost: Annual waste cost (monthly × 12)
                - wasted_ips: Number of wasted IPs
                - cost_per_ip: Cost per IP per month
                - waste_percentage: Percentage of total reserved IPs

        Pricing logic:
            - First 50 IPs in VNet are free
            - Additional IPs cost $0.005/IP/month
            - So waste cost = max(0, wasted_ips - 50) × $0.005

        Example:
            1000 wasted IPs:
            - Free tier: 50 IPs (no cost)
            - Billable: 950 IPs × $0.005 = $4.75/month
            - Annual: $4.75 × 12 = $57.00
        """
        if wasted_ips <= 0:
            return {
                "monthly_cost": 0.0,
                "annual_cost": 0.0,
                "wasted_ips": 0,
                "cost_per_ip": self.pricing.vnet_ip_cost_per_month,
                "waste_percentage": 0.0,
                "free_tier_used": 0,
            }

        # Calculate billable IPs (after free tier)
        # Azure provides first 50 IPs free per VNet
        billable_ips = max(0, wasted_ips - self.pricing.vnet_free_ips)
        free_tier_used = min(wasted_ips, self.pricing.vnet_free_ips)

        # Calculate monthly cost
        # Each billable IP costs $0.005/month
        monthly_cost = billable_ips * self.pricing.vnet_ip_cost_per_month

        # Calculate annual projection
        annual_cost = monthly_cost * 12

        # Calculate waste percentage if total is provided
        waste_pct = 0.0
        if total_reserved and total_reserved > 0:
            waste_pct = (wasted_ips / total_reserved) * 100

        return {
            "monthly_cost": round(monthly_cost, 2),
            "annual_cost": round(annual_cost, 2),
            "wasted_ips": wasted_ips,
            "billable_wasted_ips": billable_ips,
            "free_tier_used": free_tier_used,
            "cost_per_ip": self.pricing.vnet_ip_cost_per_month,
            "waste_percentage": round(waste_pct, 2),
            "note": "First 50 IPs per VNet are free in Azure",
        }

    def calculate_optimization_savings(
        self,
        current_max_pods: int,
        optimized_max_pods: int,
        node_count: int,
        current_waste_pct: float,
    ) -> dict:
        """
        Calculate potential savings from optimizing maxPods setting.

        When you reduce maxPods, fewer IPs are reserved per node,
        reducing waste and potentially allowing smaller subnets.

        Args:
            current_max_pods: Current maxPods setting per node
            optimized_max_pods: Recommended maxPods setting
            node_count: Number of nodes in cluster
            current_waste_pct: Current IP waste percentage

        Returns:
            Savings breakdown with monthly and annual projections

        Example:
            Current: 110 maxPods × 10 nodes = 1100 IPs reserved
            Optimized: 50 maxPods × 10 nodes = 500 IPs reserved
            Savings: 600 IPs × $0.005 = $3.00/month = $36/year
        """
        # Calculate IP reduction
        current_ips_per_node = current_max_pods
        optimized_ips_per_node = optimized_max_pods

        # Total IPs saved
        ips_saved_per_node = current_ips_per_node - optimized_ips_per_node
        total_ips_saved = ips_saved_per_node * node_count

        # Calculate cost savings
        # Not all saved IPs were wasted, so apply waste percentage
        effectively_saved_ips = int(total_ips_saved * (current_waste_pct / 100))

        savings = self.calculate_ip_waste_cost(effectively_saved_ips)

        return {
            "optimization_type": "reduce_max_pods",
            "current_max_pods": current_max_pods,
            "optimized_max_pods": optimized_max_pods,
            "reduction": ips_saved_per_node,
            "node_count": node_count,
            "total_ips_freed": total_ips_saved,
            "effectively_saved_ips": effectively_saved_ips,
            "monthly_savings": savings["monthly_cost"],
            "annual_savings": savings["annual_cost"],
            "implementation_effort": self._estimate_implementation_effort(
                "reduce_max_pods", node_count
            ),
        }

    def calculate_node_cost_savings(
        self, current_nodes: int, optimized_nodes: int, vm_size: str = "Standard_D4s_v3"
    ) -> dict:
        """
        Calculate savings from reducing node count.

        If pod density is very low, you may be able to reduce
        the number of nodes and save on VM costs.

        Args:
            current_nodes: Current number of nodes
            optimized_nodes: Recommended number of nodes
            vm_size: Azure VM size (e.g., 'Standard_D4s_v3')

        Returns:
            Cost savings from node reduction

        Warning:
            Reducing nodes affects compute capacity and availability.
            Always maintain buffer for scaling and node failures.
        """
        # Get VM cost per month
        vm_cost = self.pricing.vm_costs_per_month.get(
            vm_size,
            192.72,  # Default to D4s_v3 cost if not found
        )

        # Calculate node reduction
        nodes_removed = current_nodes - optimized_nodes

        if nodes_removed <= 0:
            return {
                "optimization_type": "reduce_node_count",
                "nodes_removed": 0,
                "monthly_savings": 0.0,
                "annual_savings": 0.0,
                "note": "No node reduction recommended",
            }

        # Calculate savings
        monthly_savings = nodes_removed * vm_cost
        annual_savings = monthly_savings * 12

        return {
            "optimization_type": "reduce_node_count",
            "current_nodes": current_nodes,
            "optimized_nodes": optimized_nodes,
            "nodes_removed": nodes_removed,
            "vm_size": vm_size,
            "cost_per_vm_monthly": vm_cost,
            "monthly_savings": round(monthly_savings, 2),
            "annual_savings": round(annual_savings, 2),
            "warning": "Ensure sufficient capacity remains for scaling and HA",
        }

    def _calculate_current_costs(self, diagnostic_data: dict) -> dict:
        """
        Calculate current monthly costs for the cluster.

        Estimates current spending on:
        - Node pool VMs
        - IP addresses
        - Load balancers (if applicable)

        Args:
            diagnostic_data: Full diagnostic report

        Returns:
            Current cost breakdown
        """
        node_analysis = diagnostic_data.get("node_analysis", [])
        pod_analysis = diagnostic_data.get("pod_ip_analysis", {})

        # Count total nodes
        total_nodes = len(node_analysis)

        # Estimate node costs (assuming Standard_D4s_v3 as default)
        # In reality, you'd get actual VM sizes from Azure
        node_cost_monthly = total_nodes * self.pricing.vm_costs_per_month.get(
            "Standard_D4s_v3", 192.72
        )

        # Calculate IP costs
        ip_waste = pod_analysis.get("ip_waste_analysis", {})
        reserved_ips = ip_waste.get("reserved_ips", 0)

        # Billable IPs (after free tier)
        billable_ips = max(0, reserved_ips - self.pricing.vnet_free_ips)
        ip_cost_monthly = billable_ips * self.pricing.vnet_ip_cost_per_month

        total_monthly = node_cost_monthly + ip_cost_monthly

        return {
            "total_monthly": round(total_monthly, 2),
            "total_annual": round(total_monthly * 12, 2),
            "breakdown": {
                "nodes": {
                    "count": total_nodes,
                    "monthly_cost": round(node_cost_monthly, 2),
                    "note": "Estimated based on Standard_D4s_v3 pricing",
                },
                "ip_addresses": {
                    "total_reserved": reserved_ips,
                    "billable_ips": billable_ips,
                    "monthly_cost": round(ip_cost_monthly, 2),
                },
            },
        }

    def _calculate_optimization_savings(
        self, recommendations: list[dict], current_costs: dict
    ) -> list[dict]:
        """
        Calculate potential savings from each recommendation.

        Args:
            recommendations: List of recommendations from diagnostic
            current_costs: Current cost breakdown

        Returns:
            List of savings opportunities
        """
        savings_list = []

        for rec in recommendations:
            category = rec.get("category", "")

            # Calculate savings based on recommendation type
            if category == "IP_OPTIMIZATION":
                # Extract details from recommendation description
                # This is a simplified example - in reality, you'd parse the recommendation
                savings = {
                    "recommendation": rec.get("title", ""),
                    "category": category,
                    "priority": rec.get("priority", "MEDIUM"),
                    "estimated_monthly_savings": 50.00,  # Placeholder
                    "estimated_annual_savings": 600.00,
                    "implementation_complexity": rec.get("implementation_complexity", "MEDIUM"),
                    "description": rec.get("description", ""),
                }
                savings_list.append(savings)

            elif category == "COST_OPTIMIZATION":
                savings = {
                    "recommendation": rec.get("title", ""),
                    "category": category,
                    "priority": rec.get("priority", "LOW"),
                    "estimated_monthly_savings": 100.00,  # Placeholder
                    "estimated_annual_savings": 1200.00,
                    "implementation_complexity": rec.get("implementation_complexity", "MEDIUM"),
                    "description": rec.get("description", ""),
                }
                savings_list.append(savings)

        return savings_list

    def _sum_savings(self, optimization_savings: list[dict]) -> dict:
        """Sum up all potential savings."""
        total_monthly = sum(s.get("estimated_monthly_savings", 0) for s in optimization_savings)
        total_annual = sum(s.get("estimated_annual_savings", 0) for s in optimization_savings)

        return {
            "monthly": round(total_monthly, 2),
            "annual": round(total_annual, 2),
            "opportunities_count": len(optimization_savings),
        }

    def _calculate_roi(self, optimization_savings: list[dict], current_costs: dict) -> dict:
        """
        Calculate ROI for implementing optimizations.

        Considers:
        - Estimated implementation time
        - Engineer hourly rate
        - Savings over time
        - Payback period
        """
        # Estimate implementation effort
        # Low complexity: 2 hours, Medium: 8 hours, High: 40 hours
        effort_hours_map = {"LOW": 2, "MEDIUM": 8, "HIGH": 40}

        total_effort_hours = sum(
            effort_hours_map.get(s.get("implementation_complexity", "MEDIUM"), 8)
            for s in optimization_savings
        )

        # Assume $150/hour for DevOps engineer (market rate)
        engineer_rate = 150.0
        implementation_cost = total_effort_hours * engineer_rate

        # Calculate total annual savings
        total_annual_savings = sum(
            s.get("estimated_annual_savings", 0) for s in optimization_savings
        )

        # Calculate payback period (months)
        monthly_savings = total_annual_savings / 12
        payback_months = (
            implementation_cost / monthly_savings if monthly_savings > 0 else float("inf")
        )

        # Calculate 3-year ROI
        three_year_savings = total_annual_savings * 3
        three_year_roi = (
            ((three_year_savings - implementation_cost) / implementation_cost * 100)
            if implementation_cost > 0
            else 0
        )

        return {
            "implementation_cost": round(implementation_cost, 2),
            "estimated_hours": total_effort_hours,
            "engineer_rate_per_hour": engineer_rate,
            "annual_savings": round(total_annual_savings, 2),
            "monthly_savings": round(monthly_savings, 2),
            "payback_period_months": round(payback_months, 1),
            "three_year_roi_percentage": round(three_year_roi, 1),
            "three_year_net_savings": round(three_year_savings - implementation_cost, 2),
            "recommendation": self._roi_recommendation(payback_months, three_year_roi),
        }

    def _roi_recommendation(self, payback_months: float, roi_pct: float) -> str:
        """Generate recommendation based on ROI analysis."""
        if payback_months < 1:
            return "EXCELLENT - Payback in less than 1 month. Implement immediately."
        elif payback_months < 3:
            return "VERY GOOD - Payback in under 3 months. High priority implementation."
        elif payback_months < 6:
            return "GOOD - Payback in under 6 months. Recommended implementation."
        elif payback_months < 12:
            return "FAIR - Payback within 1 year. Consider implementation."
        else:
            return "LOW - Long payback period. Evaluate other priorities first."

    def _project_cost_trends(self, current_costs: dict, waste_costs: dict) -> dict:
        """
        Project cost trends over time if no action taken.

        Helps visualize the cost of inaction.
        """
        monthly_waste = waste_costs.get("monthly_cost", 0)

        # Project costs over 1, 2, 3 years
        projections = {
            "1_year": {
                "total_waste": round(monthly_waste * 12, 2),
                "cumulative": round(monthly_waste * 12, 2),
            },
            "2_years": {
                "total_waste": round(monthly_waste * 24, 2),
                "cumulative": round(monthly_waste * 24, 2),
            },
            "3_years": {
                "total_waste": round(monthly_waste * 36, 2),
                "cumulative": round(monthly_waste * 36, 2),
            },
        }

        return {
            "projections": projections,
            "warning": "These costs are cumulative and will continue if no optimization is performed",
        }

    def _estimate_implementation_effort(
        self, optimization_type: str, affected_resources: int
    ) -> str:
        """Estimate effort required to implement optimization."""
        # Simple heuristic for effort estimation
        if optimization_type == "reduce_max_pods":
            # Node pool recreation required
            if affected_resources <= 3:
                return "LOW"
            elif affected_resources <= 10:
                return "MEDIUM"
            else:
                return "HIGH"

        return "MEDIUM"

    def _generate_cost_summary(
        self, current_costs: dict, waste_costs: dict, optimization_savings: list[dict]
    ) -> dict:
        """
        Generate executive summary of cost analysis.

        This provides high-level insights for decision makers.
        """
        total_monthly = current_costs.get("total_monthly", 0)
        waste_monthly = waste_costs.get("monthly_cost", 0)
        waste_pct = (waste_monthly / total_monthly * 100) if total_monthly > 0 else 0

        total_potential_monthly = sum(
            s.get("estimated_monthly_savings", 0) for s in optimization_savings
        )

        potential_reduction_pct = (
            (total_potential_monthly / total_monthly * 100) if total_monthly > 0 else 0
        )

        return {
            "current_monthly_spend": round(total_monthly, 2),
            "monthly_waste": round(waste_monthly, 2),
            "waste_percentage": round(waste_pct, 1),
            "potential_monthly_savings": round(total_potential_monthly, 2),
            "potential_cost_reduction_pct": round(potential_reduction_pct, 1),
            "annual_impact": round(total_potential_monthly * 12, 2),
            "status": self._get_cost_status(waste_pct),
            "recommendation": self._get_cost_recommendation(waste_pct, potential_reduction_pct),
        }

    def _get_cost_status(self, waste_pct: float) -> str:
        """Categorize cost efficiency status."""
        if waste_pct < 10:
            return "EXCELLENT"
        elif waste_pct < 20:
            return "GOOD"
        elif waste_pct < 30:
            return "FAIR"
        elif waste_pct < 50:
            return "POOR"
        else:
            return "CRITICAL"

    def _get_cost_recommendation(self, waste_pct: float, potential_reduction_pct: float) -> str:
        """Generate high-level cost recommendation."""
        if waste_pct > 30:
            return (
                f"HIGH waste detected ({waste_pct:.1f}%). "
                f"Immediate optimization recommended to reduce costs by {potential_reduction_pct:.1f}%."
            )
        elif waste_pct > 20:
            return (
                f"MODERATE waste detected ({waste_pct:.1f}%). "
                f"Consider optimization to reduce costs by {potential_reduction_pct:.1f}%."
            )
        else:
            return f"Cost efficiency is good. Minor optimizations available ({potential_reduction_pct:.1f}% potential reduction)."


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount for display.

    Args:
        amount: Dollar amount
        currency: Currency code (default: USD)

    Returns:
        Formatted string like "$1,234.56"
    """
    return f"${amount:,.2f}"


def calculate_subnet_sizing_cost_impact(current_cidr: str, recommended_cidr: str) -> dict:
    """
    Calculate cost impact of changing subnet size.

    While Azure doesn't charge directly for subnet size,
    smaller subnets can:
    1. Prevent over-provisioning
    2. Improve IP management
    3. Enable better network segmentation

    Args:
        current_cidr: Current subnet CIDR (e.g., '/20')
        recommended_cidr: Recommended subnet CIDR (e.g., '/23')

    Returns:
        Impact analysis
    """
    # Extract prefix length
    current_prefix = int(current_cidr.strip("/"))
    recommended_prefix = int(recommended_cidr.strip("/"))

    # Calculate usable IPs (subtract 5 reserved by Azure)
    current_ips = (2 ** (32 - current_prefix)) - 5
    recommended_ips = (2 ** (32 - recommended_prefix)) - 5

    ips_freed = current_ips - recommended_ips

    return {
        "current_subnet": current_cidr,
        "recommended_subnet": recommended_cidr,
        "current_usable_ips": current_ips,
        "recommended_usable_ips": recommended_ips,
        "ips_freed": ips_freed,
        "note": "Subnet resize requires migration to new subnet",
        "impact": "Prevents future over-provisioning",
    }
