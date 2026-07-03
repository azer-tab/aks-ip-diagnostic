"""Kubernetes API client for read-only pod and node diagnostics."""

from __future__ import annotations

import logging
from typing import Any

from kubernetes import client, config
from kubernetes.client.rest import ApiException


class KubernetesClient:
    """Small read-only wrapper around the official Kubernetes Python client."""

    def __init__(self, cluster_name: str | None = None, kubeconfig_path: str | None = None):
        self.cluster_name = cluster_name
        self.logger = logging.getLogger(__name__)

        try:
            if kubeconfig_path:
                self.logger.info("Loading kubeconfig from explicit path")
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                try:
                    config.load_incluster_config()
                    self.logger.info("Using in-cluster Kubernetes configuration")
                except config.ConfigException:
                    config.load_kube_config()
                    self.logger.info("Using default kubeconfig")

            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
        except Exception as exc:
            self.logger.error("Failed to initialize Kubernetes client: %s", exc)
            raise

    def list_pods_all_namespaces(
        self,
        field_selector: str | None = None,
        label_selector: str | None = None,
        timeout_seconds: int = 30,
    ) -> list[dict[str, Any]]:
        """List all pods across all namespaces."""
        try:
            pods = self.core_v1.list_pod_for_all_namespaces(
                field_selector=field_selector,
                label_selector=label_selector,
                _request_timeout=timeout_seconds,
            )
            return [self._pod_to_dict(pod) for pod in pods.items]
        except ApiException as exc:
            self.logger.error("Error listing pods: %s", exc)
            return []

    def list_pods_in_namespace(
        self, namespace: str, timeout_seconds: int = 30
    ) -> list[dict[str, Any]]:
        """List pods in a namespace."""
        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=namespace,
                _request_timeout=timeout_seconds,
            )
            return [self._pod_to_dict(pod) for pod in pods.items]
        except ApiException as exc:
            self.logger.error("Error listing pods in namespace %s: %s", namespace, exc)
            return []

    def list_nodes(
        self, label_selector: str | None = None, timeout_seconds: int = 30
    ) -> list[dict[str, Any]]:
        """List cluster nodes."""
        try:
            nodes = self.core_v1.list_node(
                label_selector=label_selector,
                _request_timeout=timeout_seconds,
            )
            return [self._node_to_dict(node) for node in nodes.items]
        except ApiException as exc:
            self.logger.error("Error listing nodes: %s", exc)
            return []

    def get_pod(
        self, name: str, namespace: str, timeout_seconds: int = 30
    ) -> dict[str, Any] | None:
        """Get one pod by name and namespace."""
        try:
            pod = self.core_v1.read_namespaced_pod(
                name=name,
                namespace=namespace,
                _request_timeout=timeout_seconds,
            )
            return self._pod_to_dict(pod)
        except ApiException as exc:
            self.logger.error("Error reading pod %s/%s: %s", namespace, name, exc)
            return None

    def get_node(self, name: str, timeout_seconds: int = 30) -> dict[str, Any] | None:
        """Get one node by name."""
        try:
            node = self.core_v1.read_node(name=name, _request_timeout=timeout_seconds)
            return self._node_to_dict(node)
        except ApiException as exc:
            self.logger.error("Error reading node %s: %s", name, exc)
            return None

    def list_namespaces(self, timeout_seconds: int = 30) -> list[str]:
        """List namespace names."""
        try:
            namespaces = self.core_v1.list_namespace(_request_timeout=timeout_seconds)
            return [item.metadata.name for item in namespaces.items]
        except ApiException as exc:
            self.logger.error("Error listing namespaces: %s", exc)
            return []

    def get_pod_metrics(self) -> dict[str, Any]:
        """Placeholder for metrics-server integration; returns an empty result when unavailable."""
        return {}

    def get_node_metrics(self) -> dict[str, Any]:
        """Placeholder for metrics-server integration; returns an empty result when unavailable."""
        return {}

    @staticmethod
    def _pod_to_dict(pod: Any) -> dict[str, Any]:
        metadata = getattr(pod, "metadata", None)
        spec = getattr(pod, "spec", None)
        status = getattr(pod, "status", None)
        return {
            "metadata": {
                "name": getattr(metadata, "name", None),
                "namespace": getattr(metadata, "namespace", None),
                "labels": getattr(metadata, "labels", None) or {},
                "creation_timestamp": str(getattr(metadata, "creation_timestamp", ""))
                if metadata
                else None,
            },
            "spec": {
                "node_name": getattr(spec, "node_name", None),
                "host_network": getattr(spec, "host_network", False),
            },
            "status": {
                "phase": getattr(status, "phase", None),
                "pod_ip": getattr(status, "pod_ip", None),
                "pod_ips": [
                    getattr(ip, "ip", None) for ip in (getattr(status, "pod_ips", None) or [])
                ],
                "host_ip": getattr(status, "host_ip", None),
            },
        }

    @staticmethod
    def _node_to_dict(node: Any) -> dict[str, Any]:
        metadata = getattr(node, "metadata", None)
        spec = getattr(node, "spec", None)
        status = getattr(node, "status", None)
        return {
            "metadata": {
                "name": getattr(metadata, "name", None),
                "labels": getattr(metadata, "labels", None) or {},
            },
            "spec": {
                "pod_cidr": getattr(spec, "pod_cidr", None),
                "pod_cidrs": getattr(spec, "pod_cidrs", None) or [],
            },
            "status": {
                "capacity": getattr(status, "capacity", None) or {},
                "allocatable": getattr(status, "allocatable", None) or {},
                "conditions": [
                    {
                        "type": getattr(condition, "type", None),
                        "status": getattr(condition, "status", None),
                        "reason": getattr(condition, "reason", None),
                    }
                    for condition in (getattr(status, "conditions", None) or [])
                ],
                "addresses": [
                    {
                        "type": getattr(address, "type", None),
                        "address": getattr(address, "address", None),
                    }
                    for address in (getattr(status, "addresses", None) or [])
                ],
            },
        }
