"""
Kubernetes API client for retrieving pod and node information.

This module provides a wrapper around the official Kubernetes Python client
to simplify common operations needed for IP diagnostics.
"""
from typing import List, Dict, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging


class KubernetesClient:
    """
    Client for interacting with Kubernetes API.
    
    This class handles authentication, API calls, and data transformation
    for querying Kubernetes resources. It supports both in-cluster and
    out-of-cluster configurations.
    
    Usage:
        # Using default kubeconfig
        k8s = KubernetesClient("my-cluster")
        pods = k8s.list_pods_all_namespaces()
        
        # Using specific kubeconfig file
        k8s = KubernetesClient("my-cluster", kubeconfig_path="/path/to/config")
        nodes = k8s.list_nodes()
    """
    
    def __init__(self, cluster_name: str = None, kubeconfig_path: str = None):
        """
        Initialize Kubernetes API client with authentication.
        
        Authentication priority:
        1. If kubeconfig_path provided, use that file
        2. Try in-cluster config (for pods running inside cluster)
        3. Fall back to default kubeconfig (~/.kube/config)
        
        Args:
            cluster_name: Name of the AKS cluster (for logging/identification)
            kubeconfig_path: Path to kubeconfig file. If None, uses default location.
        
        Raises:
            Exception: If authentication fails or kubeconfig is invalid
        
        Example:
            # Use default config
            client = KubernetesClient("prod-cluster")
            
            # Use specific config file
            client = KubernetesClient("dev-cluster", kubeconfig_path="./dev-kubeconfig")
        """
        self.cluster_name = cluster_name
        self.logger = logging.getLogger(__name__)
        
        try:
            # Load Kubernetes configuration based on priority
            if kubeconfig_path:
                # User specified a kubeconfig file - use it
                self.logger.info(f"Loading kubeconfig from: {kubeconfig_path}")
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                # Try in-cluster config first (for when running inside K8s)
                # This uses service account mounted at /var/run/secrets/kubernetes.io/
                try:
                    self.logger.info("Attempting in-cluster configuration")
                    config.load_incluster_config()
                    self.logger.info("Using in-cluster configuration")
                except config.ConfigException:
                    # Not running in cluster, use default kubeconfig
                    self.logger.info("Loading default kubeconfig from ~/.kube/config")
                    config.load_kube_config()
            
            # Initialize API clients for different resource types
            # CoreV1Api handles pods, nodes, namespaces, services, etc.
            self.core_v1 = client.CoreV1Api()
            # AppsV1Api handles deployments, statefulsets, daemonsets
            self.apps_v1 = client.AppsV1Api()
            
            self.logger.info(f"Kubernetes client initialized successfully for cluster: {cluster_name}")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize Kubernetes client: {str(e)}")
            raise
    
    def list_pods_all_namespaces(self, field_selector: str = None, 
                                 label_selector: str = None) -> List[Dict]:
        """
        List all pods across all namespaces in the cluster.
    def list_pods_all_namespaces(self, field_selector: str = None, 
                                 label_selector: str = None) -> List[Dict]:
        """
        List all pods across all namespaces in the cluster.
        
        This is useful for cluster-wide analysis and getting a complete
        view of pod IP usage across the entire cluster.
        
        Args:
            field_selector: Filter pods by field (e.g., "status.phase=Running")
                          See: https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/
            label_selector: Filter pods by labels (e.g., "app=nginx,tier=frontend")
                          See: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/
        
        Returns:
            List of pod dictionaries containing metadata, spec, and status.
            Returns empty list if API call fails.
        
        Example:
            # Get all pods
            all_pods = client.list_pods_all_namespaces()
            
            # Get only running pods
            running = client.list_pods_all_namespaces(field_selector="status.phase=Running")
            
            # Get pods with specific label
            app_pods = client.list_pods_all_namespaces(label_selector="app=myapp")
        
        Note:
            Requires 'pods/list' permission across all namespaces.
        """
        try:
            # Call Kubernetes API to list pods
            # This returns a V1PodList object
            pods = self.core_v1.list_pod_for_all_namespaces(
                field_selector=field_selector,
                label_selector=label_selector
            )
            
            # Convert each pod object to a dictionary for easier processing
            # _pod_to_dict extracts relevant fields we need for analysis
            return [self._pod_to_dict(pod) for pod in pods.items]
        
        except ApiException as e:
            # Log error but don't crash - return empty list to allow graceful degradation
            self.logger.error(f"Error listing pods: {str(e)}")
            return []
    
    def list_pods_in_namespace(self, namespace: str) -> List[Dict]:
        """
        List pods in a specific namespace only.
        
        More efficient than filtering all pods when you only need one namespace.
        
        Args:
            namespace: Kubernetes namespace to query (e.g., "default", "kube-system")
        
        Returns:
            List of pod dictionaries in the specified namespace.
            Returns empty list if namespace doesn't exist or API call fails.
        
        Example:
            # Get pods in kube-system namespace
            system_pods = client.list_pods_in_namespace("kube-system")
            
            # Count pods in production namespace
            prod_pods = client.list_pods_in_namespace("production")
            print(f"Production has {len(prod_pods)} pods")
        
        Note:
            Requires 'pods/list' permission in the specified namespace.
        """
        try:
            # Query pods only in the specified namespace
            pods = self.core_v1.list_namespaced_pod(namespace=namespace)
            return [self._pod_to_dict(pod) for pod in pods.items]
        
        except ApiException as e:
            self.logger.error(f"Error listing pods in namespace {namespace}: {str(e)}")
            return []
    
    def list_nodes(self, label_selector: str = None) -> List[Dict]:
        """
        List all nodes in the cluster.
        
        Nodes are the worker machines (VMs) that run pods. This method
        retrieves node information including capacity, allocatable resources,
        and current status.
        
        Args:
            label_selector: Filter nodes by labels (e.g., "agentpool=nodepool1")
                          Useful for analyzing specific node pools.
        
        Returns:
            List of node dictionaries containing metadata, spec, and status.
            Returns empty list if API call fails.
        
        Example:
            # Get all nodes
            all_nodes = client.list_nodes()
            
            # Get nodes in specific node pool (Azure specific)
            pool_nodes = client.list_nodes(label_selector="agentpool=userpool")
            
            # Get only Linux nodes
            linux_nodes = client.list_nodes(label_selector="kubernetes.io/os=linux")
        
        Note:
            Requires 'nodes/list' permission.
            Node information includes maxPods limit needed for IP analysis.
        """
        try:
            # Call Kubernetes API to list nodes
            nodes = self.core_v1.list_node(label_selector=label_selector)
            
            # Convert each node object to dictionary
            # _node_to_dict extracts capacity, allocatable, labels, conditions, etc.
            return [self._node_to_dict(node) for node in nodes.items]
        
        except ApiException as e:
            self.logger.error(f"Error listing nodes: {str(e)}")
            return []
    
    def get_pod(self, name: str, namespace: str) -> Optional[Dict]:
        """
        Get detailed information about a specific pod.
        
        Args:
            name: Pod name (e.g., "nginx-deployment-66b6c48dd5-abcde")
            namespace: Namespace where the pod exists
        
        Returns:
            Pod dictionary with complete details, or None if not found/error.
        
        Example:
            # Get specific pod
            pod = client.get_pod("myapp-pod-123", "production")
            if pod:
                print(f"Pod IP: {pod['status']['podIP']}")
        
        Note:
            Requires 'pods/get' permission in the specified namespace.
        """
        try:
            # Read specific pod from API
            pod = self.core_v1.read_namespaced_pod(name=name, namespace=namespace)
            return self._pod_to_dict(pod)
        
        except ApiException as e:
            self.logger.error(f"Error getting pod {namespace}/{name}: {str(e)}")
            return None
    
    def get_node(self, name: str) -> Optional[Dict]:
        """
        Get detailed information about a specific node.
        
        Args:
            name: Node name (e.g., "aks-nodepool1-12345678-vmss000000")
        
        Returns:
            Node dictionary with complete details, or None if not found/error.
        
        Example:
            # Get specific node
            node = client.get_node("aks-nodepool1-vmss000000")
            if node:
                max_pods = node['status']['capacity']['pods']
                print(f"Node can handle {max_pods} pods")
        
        Note:
            Requires 'nodes/get' permission.
        """
        try:
            # Read specific node from API
            node = self.core_v1.read_node(name=name)
            return self._node_to_dict(node)
        
        except ApiException as e:
            self.logger.error(f"Error getting node {name}: {str(e)}")
            return None
    
    def get_namespaces(self) -> List[str]:
        """
        Get list of all namespace names in the cluster.
        
        Namespaces provide logical separation of resources in Kubernetes.
        Common namespaces include default, kube-system, kube-public.
        
        Returns:
            List of namespace names (strings).
            Returns empty list if API call fails.
        
        Example:
            # Get all namespaces
            namespaces = client.get_namespaces()
            print(f"Cluster has {len(namespaces)} namespaces: {namespaces}")
            
            # Check if namespace exists
            if "production" in client.get_namespaces():
                print("Production namespace exists")
        
        Note:
            Requires 'namespaces/list' permission.
        """
        try:
            # List all namespaces
            namespaces = self.core_v1.list_namespace()
            # Extract just the names
            return [ns.metadata.name for ns in namespaces.items]
        
        except ApiException as e:
            self.logger.error(f"Error listing namespaces: {str(e)}")
            return []
    
    def get_pod_metrics(self) -> Dict:
        """
        Get pod resource usage metrics (CPU, memory).
        
        This method retrieves actual resource consumption from the Metrics API.
        Requires metrics-server to be installed in the cluster.
        
        Returns:
            Metrics dictionary containing CPU and memory usage per pod.
            Returns empty dict if metrics-server is not available.
        
        Example:
            metrics = client.get_pod_metrics()
            # Check if metrics available
            if metrics:
                print("Metrics server is available")
        
        Note:
            - Requires metrics-server deployed in cluster
            - Metrics are sampled, not real-time
            - Used for HPA (Horizontal Pod Autoscaler)
            - Not critical for IP diagnostics
        """
        try:
            # Import CustomObjectsApi for custom resources
            # Metrics API is a custom resource, not part of core API
            from kubernetes import client
            custom_api = client.CustomObjectsApi()
            
            # Query the metrics.k8s.io API
            # This returns current CPU/memory usage for all pods
            metrics = custom_api.list_cluster_custom_object(
                group="metrics.k8s.io",      # API group
                version="v1beta1",            # API version
                plural="pods"                 # Resource type
            )
            
            return metrics
        
        except Exception as e:
            # Metrics server might not be installed - this is not critical
            # Use warning instead of error since it's optional
            self.logger.warning(f"Could not get pod metrics (metrics-server may not be installed): {str(e)}")
            return {}
    
    def get_node_metrics(self) -> Dict:
        """
        Get node resource usage metrics (CPU, memory).
        
        Similar to pod metrics but for nodes. Shows actual resource
        consumption on each node.
        
        Returns:
            Metrics dictionary containing CPU and memory usage per node.
            Returns empty dict if metrics-server is not available.
        
        Example:
            node_metrics = client.get_node_metrics()
            # Useful for understanding node load
        
        Note:
            - Requires metrics-server deployed in cluster
            - Shows node-level resource consumption
            - Useful for capacity planning
        """
        try:
            from kubernetes import client
            custom_api = client.CustomObjectsApi()
            
            # Query node metrics from metrics API
            metrics = custom_api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"                # Query nodes instead of pods
            )
            
            return metrics
        
        except Exception as e:
            self.logger.warning(f"Could not get node metrics (metrics-server may not be installed): {str(e)}")
            return {}
    
    def _pod_to_dict(self, pod) -> Dict:
        """
        Convert Kubernetes V1Pod object to a plain dictionary.
        
        The Kubernetes Python client returns complex objects with many nested
        attributes. This method extracts the essential information we need
        for IP diagnostics into a simple dictionary structure.
        
        Args:
            pod: V1Pod object from Kubernetes API
        
        Returns:
            Dictionary with simplified pod structure containing:
                - metadata: name, namespace, labels, annotations, timestamps
                - spec: nodeName, hostNetwork, container definitions
                - status: phase, IPs, conditions, container statuses
        
        Why we need this:
            - Simplifies access to nested attributes
            - Serializable (can be converted to JSON)
            - Easier to pass between functions
            - Handles None values gracefully
        """
        return {
            # Metadata section - identifying information
            "metadata": {
                "name": pod.metadata.name,                      # Pod name (e.g., "nginx-abc123")
                "namespace": pod.metadata.namespace,            # Namespace (e.g., "default")
                "uid": pod.metadata.uid,                        # Unique ID across cluster
                "labels": pod.metadata.labels or {},            # Key-value labels for selection
                "annotations": pod.metadata.annotations or {},  # Additional metadata
                "creationTimestamp": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
            },
            # Spec section - desired state configuration
            "spec": {
                "nodeName": pod.spec.node_name,                # Which node is pod scheduled on
                "hostNetwork": pod.spec.host_network or False, # Using host network? (important for IP analysis)
                # Extract container definitions
                "containers": [
                    {
                        "name": container.name,
                        "image": container.image,
                        # Resource requests and limits
                        "resources": {
                            "requests": container.resources.requests or {} if container.resources else {},
                            "limits": container.resources.limits or {} if container.resources else {}
                        }
                    }
                    for container in (pod.spec.containers or [])
                ]
            },
            # Status section - current state
            "status": {
                "phase": pod.status.phase,                    # Running, Pending, Failed, etc.
                "podIP": pod.status.pod_ip,                   # Primary IP address (CRITICAL for IP analysis)
                "hostIP": pod.status.host_ip,                 # Node's IP address
                "podIPs": [{"ip": ip.ip} for ip in (pod.status.pod_ips or [])],  # All IPs (dual-stack support)
                # Pod conditions (Ready, ContainersReady, etc.)
                "conditions": [
                    {
                        "type": cond.type,
                        "status": cond.status,
                        "reason": cond.reason,
                        "message": cond.message
                    }
                    for cond in (pod.status.conditions or [])
                ],
                # Container statuses within the pod
                "containerStatuses": [
                    {
                        "name": cs.name,
                        "ready": cs.ready,
                        "restartCount": cs.restart_count,
                        "state": self._container_state_to_dict(cs.state)
                    }
                    for cs in (pod.status.container_statuses or [])
                ]
            }
        }
    
    def _node_to_dict(self, node) -> Dict:
        """
        Convert Kubernetes V1Node object to a plain dictionary.
        
        Similar to _pod_to_dict, this extracts essential node information
        needed for IP diagnostics and capacity analysis.
        
        Args:
            node: V1Node object from Kubernetes API
        
        Returns:
            Dictionary with simplified node structure containing:
                - metadata: name, labels, annotations
                - spec: providerID, taints
                - status: capacity, allocatable, conditions, addresses
        
        Key fields for IP analysis:
            - status.capacity.pods: Maximum pods this node can run
            - status.allocatable.pods: Actually available for scheduling
            - metadata.labels.agentpool: Azure node pool name
        """
        return {
            # Node metadata - identification and organization
            "metadata": {
                "name": node.metadata.name,                    # Node name (e.g., "aks-nodepool1-vmss000000")
                "uid": node.metadata.uid,
                "labels": node.metadata.labels or {},          # Important: includes agentpool label in AKS
                "annotations": node.metadata.annotations or {},
                "creationTimestamp": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else None
            },
            # Node spec - configuration
            "spec": {
                "providerID": node.spec.provider_id,          # Azure-specific ID (e.g., azure:///subscriptions/.../vmss/0)
                # Taints prevent pods from scheduling unless they have tolerations
                "taints": [
                    {
                        "key": taint.key,
                        "value": taint.value,
                        "effect": taint.effect              # NoSchedule, PreferNoSchedule, NoExecute
                    }
                    for taint in (node.spec.taints or [])
                ]
            },
            # Node status - current state and capacity
            "status": {
                # Capacity = total resources on node
                "capacity": node.status.capacity or {},        # Includes "pods": "110" or "30" etc.
                # Allocatable = resources available for pods (capacity minus system reservations)
                "allocatable": node.status.allocatable or {}, # This is the actual limit enforced
                # Node conditions indicate health
                "conditions": [
                    {
                        "type": cond.type,                    # Ready, MemoryPressure, DiskPressure, etc.
                        "status": cond.status,                # True/False/Unknown
                        "reason": cond.reason,
                        "message": cond.message
                    }
                    for cond in (node.status.conditions or [])
                ],
                # Node network addresses
                "addresses": [
                    {
                        "type": addr.type,                    # InternalIP, ExternalIP, Hostname
                        "address": addr.address
                    }
                    for addr in (node.status.addresses or [])
                ],
                # Node system information
                "nodeInfo": {
                    "kubeletVersion": node.status.node_info.kubelet_version,
                    "containerRuntimeVersion": node.status.node_info.container_runtime_version,
                    "osImage": node.status.node_info.os_image,
                    "kernelVersion": node.status.node_info.kernel_version
                } if node.status.node_info else {}
            }
        }
    
    def _container_state_to_dict(self, state) -> Dict:
        """
        Convert container state object to dictionary.
        
        A container can be in one of three states:
        - Running: Container is executing normally
        - Waiting: Container hasn't started yet (pulling image, crashing, etc.)
        - Terminated: Container has finished or failed
        
        Args:
            state: V1ContainerState object
        
        Returns:
            Dictionary with state information, or empty dict if state is None.
        
        Example states:
            {"running": {"startedAt": "2024-01-01T10:00:00Z"}}
            {"waiting": {"reason": "ImagePullBackOff", "message": "..."}}
            {"terminated": {"exitCode": 137, "reason": "OOMKilled"}}
        """
        if not state:
            return {}
        
        result = {}
        
        # Check which state the container is in
        if state.running:
            # Container is running successfully
            result["running"] = {
                "startedAt": state.running.started_at.isoformat() if state.running.started_at else None
            }
        elif state.waiting:
            # Container is waiting to start (common reasons: ImagePullBackOff, CrashLoopBackOff)
            result["waiting"] = {
                "reason": state.waiting.reason,
                "message": state.waiting.message
            }
        elif state.terminated:
            # Container has terminated (may restart depending on restart policy)
            result["terminated"] = {
                "exitCode": state.terminated.exit_code,      # 0 = success, non-zero = error
                "reason": state.terminated.reason,           # Completed, Error, OOMKilled, etc.
                "message": state.terminated.message,
                "startedAt": state.terminated.started_at.isoformat() if state.terminated.started_at else None,
                "finishedAt": state.terminated.finished_at.isoformat() if state.terminated.finished_at else None
            }
        
        return result
