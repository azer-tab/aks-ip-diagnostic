"""JSON schema definitions for AKS IP diagnostic reports."""

DIAGNOSTIC_REPORT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "AKS IP Diagnostic Report",
    "type": "object",
    "required": ["metadata", "cluster_info", "diagnostics", "summary"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["version", "timestamp", "tool_version"],
            "properties": {
                "version": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "tool_version": {"type": "string"},
                "scan_duration_seconds": {"type": "number"}
            }
        },
        "cluster_info": {
            "type": "object",
            "required": ["name", "resource_group", "subscription_id"],
            "properties": {
                "name": {"type": "string"},
                "resource_group": {"type": "string"},
                "subscription_id": {"type": "string"},
                "location": {"type": "string"},
                "kubernetes_version": {"type": "string"},
                "network_plugin": {"type": "string", "enum": ["azure", "kubenet"]},
                "dns_service_ip": {"type": "string"},
                "service_cidr": {"type": "string"},
                "pod_cidr": {"type": ["string", "null"]}
            }
        },
        "diagnostics": {
            "type": "object",
            "required": ["provisioning_state", "ip_exhaustion", "subnet_capacity", "max_pods"],
            "properties": {
                "provisioning_state": {"$ref": "#/definitions/diagnostic_result"},
                "ip_exhaustion": {"$ref": "#/definitions/diagnostic_result"},
                "subnet_capacity": {"$ref": "#/definitions/diagnostic_result"},
                "max_pods": {"$ref": "#/definitions/diagnostic_result"}
            }
        },
        "node_pools": {
            "type": "array",
            "items": {"$ref": "#/definitions/node_pool"}
        },
        "subnets": {
            "type": "array",
            "items": {"$ref": "#/definitions/subnet"}
        },
        "recommendations": {
            "type": "array",
            "items": {"$ref": "#/definitions/recommendation"}
        },
        "summary": {
            "type": "object",
            "required": ["overall_status", "risk_level", "total_issues"],
            "properties": {
                "overall_status": {"type": "string", "enum": ["HEALTHY", "WARNING", "CRITICAL"]},
                "risk_level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                "total_issues": {"type": "integer"},
                "critical_issues": {"type": "integer"},
                "warnings": {"type": "integer"},
                "healthy_checks": {"type": "integer"}
            }
        }
    },
    "definitions": {
        "diagnostic_result": {
            "type": "object",
            "required": ["status", "risk_level", "issues"],
            "properties": {
                "status": {"type": "string", "enum": ["PASS", "WARNING", "FAIL"]},
                "risk_level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                "issues": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/issue"}
                },
                "details": {"type": "object"},
                "checked_at": {"type": "string", "format": "date-time"}
            }
        },
        "issue": {
            "type": "object",
            "required": ["severity", "code", "message"],
            "properties": {
                "severity": {"type": "string", "enum": ["INFO", "WARNING", "ERROR", "CRITICAL"]},
                "code": {"type": "string"},
                "message": {"type": "string"},
                "affected_resource": {"type": "string"},
                "details": {"type": "object"},
                "remediation": {"type": "string"}
            }
        },
        "node_pool": {
            "type": "object",
            "required": ["name", "provisioning_state", "count"],
            "properties": {
                "name": {"type": "string"},
                "mode": {"type": "string", "enum": ["System", "User"]},
                "provisioning_state": {"type": "string"},
                "count": {"type": "integer"},
                "vm_size": {"type": "string"},
                "max_pods": {"type": "integer"},
                "enable_auto_scaling": {"type": "boolean"},
                "min_count": {"type": ["integer", "null"]},
                "max_count": {"type": ["integer", "null"]},
                "subnet_id": {"type": "string"},
                "subnet_name": {"type": "string"},
                "upgrade_settings": {
                    "type": "object",
                    "properties": {
                        "max_surge": {"type": ["string", "integer"]},
                        "max_unavailable": {"type": ["string", "integer"]}
                    }
                },
                "ip_allocation": {
                    "type": "object",
                    "properties": {
                        "required_ips_per_node": {"type": "integer"},
                        "total_required_ips": {"type": "integer"},
                        "current_ip_usage": {"type": "integer"},
                        "potential_max_ips": {"type": "integer"}
                    }
                },
                "error_details": {
                    "type": ["object", "null"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"}
                    }
                }
            }
        },
        "subnet": {
            "type": "object",
            "required": ["name", "address_prefix", "available_ips"],
            "properties": {
                "name": {"type": "string"},
                "id": {"type": "string"},
                "address_prefix": {"type": "string"},
                "address_space_size": {"type": "integer"},
                "available_ips": {"type": "integer"},
                "used_ips": {"type": "integer"},
                "reserved_ips": {"type": "integer"},
                "usage_percentage": {"type": "number"},
                "attached_node_pools": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "is_full": {"type": "boolean"},
                "remaining_capacity": {
                    "type": "object",
                    "properties": {
                        "additional_nodes_max_pods_30": {"type": "integer"},
                        "additional_nodes_max_pods_50": {"type": "integer"},
                        "additional_nodes_max_pods_100": {"type": "integer"}
                    }
                }
            }
        },
        "recommendation": {
            "type": "object",
            "required": ["priority", "category", "title", "description"],
            "properties": {
                "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                "category": {"type": "string", "enum": ["IP_EXHAUSTION", "SUBNET_CAPACITY", "MAX_PODS", "PROVISIONING", "CONFIGURATION"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "affected_resources": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "impact": {"type": "string"},
                "recommendation": {"type": "string"},
                "implementation_steps": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "estimated_downtime": {"type": "string"},
                "automation_available": {"type": "boolean"},
                "documentation_links": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }
    }
}

NODE_POOL_ANALYSIS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Node Pool Analysis",
    "type": "object",
    "required": ["node_pool_name", "analysis_timestamp", "metrics", "issues"],
    "properties": {
        "node_pool_name": {"type": "string"},
        "analysis_timestamp": {"type": "string", "format": "date-time"},
        "metrics": {
            "type": "object",
            "properties": {
                "current_node_count": {"type": "integer"},
                "target_node_count": {"type": "integer"},
                "max_pods_per_node": {"type": "integer"},
                "total_ip_requirement": {"type": "integer"},
                "surge_ip_requirement": {"type": "integer"},
                "subnet_available_ips": {"type": "integer"},
                "ip_headroom_percentage": {"type": "number"}
            }
        },
        "issues": {
            "type": "array",
            "items": {"$ref": "#/definitions/issue"}
        },
        "health_score": {"type": "number", "minimum": 0, "maximum": 100}
    }
}

SUBNET_ANALYSIS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Subnet Analysis",
    "type": "object",
    "required": ["subnet_name", "analysis_timestamp", "capacity", "utilization"],
    "properties": {
        "subnet_name": {"type": "string"},
        "subnet_id": {"type": "string"},
        "analysis_timestamp": {"type": "string", "format": "date-time"},
        "capacity": {
            "type": "object",
            "properties": {
                "total_ips": {"type": "integer"},
                "usable_ips": {"type": "integer"},
                "reserved_azure_ips": {"type": "integer"},
                "allocated_ips": {"type": "integer"},
                "available_ips": {"type": "integer"}
            }
        },
        "utilization": {
            "type": "object",
            "properties": {
                "percentage": {"type": "number"},
                "status": {"type": "string", "enum": ["HEALTHY", "WARNING", "CRITICAL"]},
                "trend": {"type": "string", "enum": ["STABLE", "INCREASING", "DECREASING"]}
            }
        },
        "node_pools": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "ip_consumption": {"type": "integer"}
                }
            }
        }
    }
}
