"""JSON schema definitions for AKS IP diagnostic reports."""

DIAGNOSTIC_REPORT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "AKS IP Diagnostic Report",
    "type": "object",
    "required": [
        "metadata",
        "cluster_info",
        "diagnostics",
        "node_pools",
        "subnets",
        "recommendations",
        "summary",
    ],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["version", "timestamp", "tool_version"],
            "properties": {
                "version": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "tool_version": {"type": "string"},
                "scan_duration_seconds": {"type": "number", "minimum": 0},
            },
        },
        "cluster_info": {
            "type": "object",
            "required": ["name", "resource_group", "subscription_id"],
            "properties": {
                "name": {"type": "string"},
                "resource_group": {"type": "string"},
                "subscription_id": {"type": "string"},
                "location": {"type": ["string", "null"]},
                "k8s_version": {"type": ["string", "null"]},
                "network_plugin": {"type": ["string", "null"]},
                "network_mode": {"type": ["string", "null"]},
                "network_policy": {"type": ["string", "null"]},
                "dns_service_ip": {"type": ["string", "null"]},
                "service_cidr": {"type": ["string", "null"]},
                "pod_cidr": {"type": ["string", "null"]},
            },
            "additionalProperties": True,
        },
        "diagnostics": {
            "type": "object",
            "required": ["provisioning_state", "ip_exhaustion", "subnet_capacity"],
            "anyOf": [
                {"required": ["max_pods_configuration"]},
                {"required": ["max_pods"]},
            ],
            "additionalProperties": {"$ref": "#/definitions/diagnostic_result"},
        },
        "node_pools": {
            "type": "array",
            "items": {"$ref": "#/definitions/node_pool"},
        },
        "subnets": {
            "type": "array",
            "items": {"$ref": "#/definitions/subnet"},
        },
        "recommendations": {
            "type": "array",
            "items": {"$ref": "#/definitions/recommendation"},
        },
        "issues": {
            "type": "array",
            "items": {"$ref": "#/definitions/issue"},
        },
        "summary": {
            "type": "object",
            "required": ["overall_status", "risk_level", "total_issues"],
            "properties": {
                "overall_status": {
                    "type": "string",
                    "enum": ["HEALTHY", "WARNING", "CRITICAL"],
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                },
                "total_issues": {"type": "integer", "minimum": 0},
                "critical_issues": {"type": "integer", "minimum": 0},
                "warnings": {"type": "integer", "minimum": 0},
                "healthy_checks": {"type": "integer", "minimum": 0},
                "health_score": {"type": ["number", "null"]},
                "health_grade": {"type": ["string", "null"]},
                "efficiency_metrics": {"type": "object"},
                "cost_impact": {"type": "object"},
                "capacity_outlook": {"type": "object"},
            },
            "additionalProperties": True,
        },
    },
    "definitions": {
        "diagnostic_result": {
            "type": "object",
            "required": ["status", "risk_level", "issues"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["PASS", "WARNING", "FAIL", "SKIPPED"],
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"],
                },
                "issues": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/issue"},
                },
                "details": {"type": "object"},
                "checked_at": {"type": "string", "format": "date-time"},
            },
            "additionalProperties": True,
        },
        "issue": {
            "type": "object",
            "required": ["severity"],
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["INFO", "WARNING", "ERROR", "CRITICAL"],
                },
                "code": {"type": "string"},
                "message": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "affected_resource": {"type": ["string", "null"]},
                "details": {"type": "object"},
                "remediation": {"type": "string"},
            },
            "anyOf": [{"required": ["message"]}, {"required": ["title"]}],
            "additionalProperties": True,
        },
        "node_pool": {
            "type": "object",
            "required": ["name", "provisioning_state", "count", "max_pods"],
            "properties": {
                "name": {"type": ["string", "null"]},
                "mode": {"type": ["string", "null"]},
                "provisioning_state": {"type": ["string", "null"]},
                "count": {"type": "integer", "minimum": 0},
                "vm_size": {"type": ["string", "null"]},
                "max_pods": {"type": "integer", "minimum": 0},
                "autoscaling": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "min_count": {"type": ["integer", "null"]},
                        "max_count": {"type": ["integer", "null"]},
                    },
                    "additionalProperties": True,
                },
                "upgrade_settings": {"type": "object"},
                "cost_estimate": {"type": "object"},
                "error_details": {"type": ["object", "null"]},
            },
            "additionalProperties": True,
        },
        "subnet": {
            "type": "object",
            "required": [
                "name",
                "cidr",
                "total_ips",
                "used_ips",
                "available_ips",
                "utilization_percent",
                "status",
            ],
            "properties": {
                "name": {"type": "string"},
                "cidr": {"type": "string"},
                "total_ips": {"type": "integer", "minimum": 0},
                "used_ips": {"type": "integer"},
                "available_ips": {"type": "integer"},
                "utilization_percent": {"type": "number"},
                "status": {
                    "type": "string",
                    "enum": ["HEALTHY", "WARNING", "CRITICAL"],
                },
                "associated_node_pools": {
                    "type": "array",
                    "items": {"type": ["string", "null"]},
                },
                "ip_breakdown": {"type": "object"},
            },
            "additionalProperties": True,
        },
        "recommendation": {
            "type": "object",
            "required": ["priority", "category", "title", "description"],
            "properties": {
                "priority": {
                    "type": "string",
                    "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                },
                "category": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "affected_resources": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "impact": {"type": "string"},
                "recommendation": {"type": "string"},
                "implementation_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "estimated_downtime": {"type": "string"},
                "automation_available": {"type": "boolean"},
                "documentation_links": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "additionalProperties": True,
        },
    },
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
