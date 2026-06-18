"""
Azure Network Client Module

This module provides an abstraction layer for interacting with Azure Network
resources, specifically for AKS IP diagnostic purposes. It handles:
- Virtual Network (VNet) operations
- Subnet queries and IP capacity analysis
- Network configuration validation

The client uses Azure's Network Management SDK and handles authentication,
error handling, and resource parsing.
"""

from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from typing import Optional, List, Dict


class NetworkClient:
    """
    Azure Network Management Client wrapper for AKS diagnostics.
    
    Provides methods to query and analyze Azure networking resources
    related to AKS clusters, including subnets, virtual networks,
    and IP address allocation.
    
    Authentication:
        Uses DefaultAzureCredential which attempts multiple authentication
        methods in order:
        1. Environment variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, etc.)
        2. Managed Identity (when running in Azure)
        3. Azure CLI credentials (az login)
        4. Interactive browser authentication
    
    Attributes:
        subscription_id: Azure subscription ID
        credential: Azure credential object for authentication
        network_client: Azure Network Management SDK client
    
    Example:
        client = NetworkClient("your-subscription-id")
        subnet = client.get_subnet("my-rg", "my-vnet", "default")
        print(f"Subnet CIDR: {subnet.address_prefix}")
    """
    
    def __init__(self, subscription_id):
        """
        Initialize the Network Client with Azure credentials.
        
        Args:
            subscription_id: Azure subscription ID where resources are located
            
        Raises:
            Exception: If authentication fails or SDK initialization fails
        """
        self.subscription_id = subscription_id
        
        # Initialize Azure credential
        # DefaultAzureCredential tries multiple authentication methods
        self.credential = DefaultAzureCredential()
        
        # Initialize Network Management client
        self.network_client = NetworkManagementClient(self.credential, subscription_id)

    def get_subnet(self, resource_group_name, virtual_network_name, subnet_name):
        """
        Retrieve a specific subnet from a virtual network.
        
        Queries Azure for subnet details including:
        - Address prefix (CIDR notation)
        - IP configurations (allocated IPs)
        - Network security groups
        - Route tables
        - Delegations (e.g., for AKS)
        
        Args:
            resource_group_name: Name of the Azure resource group
            virtual_network_name: Name of the virtual network containing the subnet
            subnet_name: Name of the subnet to retrieve
        
        Returns:
            Azure Subnet object if found, None if not found or on error
            Subnet object contains:
            - name: Subnet name
            - address_prefix: CIDR range (e.g., "10.240.0.0/16")
            - ip_configurations: List of IP allocations
            - provisioning_state: Succeeded, Failed, etc.
        
        Example:
            subnet = client.get_subnet("my-rg", "aks-vnet", "aks-subnet")
            if subnet:
                print(f"CIDR: {subnet.address_prefix}")
                print(f"Allocated IPs: {len(subnet.ip_configurations or [])}")
        
        Raises:
            No exceptions raised - errors are logged and None is returned
        """
        try:
            # Query Azure for subnet information
            return self.network_client.subnets.get(resource_group_name, virtual_network_name, subnet_name)
        except Exception as e:
            print(f"Failed to retrieve subnet: {e}")
            return None

    def list_subnets(self, resource_group_name, virtual_network_name):
        """
        List all subnets in a virtual network.
        
        Retrieves all subnets within a specific VNet, useful for:
        - Analyzing all subnets used by an AKS cluster
        - Capacity planning across multiple subnets
        - Network architecture review
        
        Args:
            resource_group_name: Name of the Azure resource group
            virtual_network_name: Name of the virtual network
        
        Returns:
            List of Azure Subnet objects (empty list on error)
            Each subnet object contains full configuration details
        
        Example:
            subnets = client.list_subnets("my-rg", "aks-vnet")
            for subnet in subnets:
                print(f"{subnet.name}: {subnet.address_prefix}")
        
        Raises:
            No exceptions raised - errors are logged and empty list returned
        """
        try:
            return list(self.network_client.subnets.list(resource_group_name, virtual_network_name))
        except Exception as e:
            print(f"Failed to list subnets: {e}")
            return []