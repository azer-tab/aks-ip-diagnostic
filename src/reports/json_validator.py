"""JSON validator for diagnostic reports."""
import json
import jsonschema
from typing import Dict, List, Tuple, Any
from pathlib import Path

from .json_schema import (
    DIAGNOSTIC_REPORT_SCHEMA,
    NODE_POOL_ANALYSIS_SCHEMA,
    SUBNET_ANALYSIS_SCHEMA
)


class ReportValidator:
    """Validator for diagnostic reports against JSON schemas."""
    
    @staticmethod
    def validate_diagnostic_report(report_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a diagnostic report against the schema.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            jsonschema.validate(instance=report_data, schema=DIAGNOSTIC_REPORT_SCHEMA)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [str(e)]
        except jsonschema.SchemaError as e:
            return False, [f"Schema error: {str(e)}"]
    
    @staticmethod
    def validate_node_pool_analysis(analysis_data: Dict) -> Tuple[bool, List[str]]:
        """Validate node pool analysis data."""
        try:
            jsonschema.validate(instance=analysis_data, schema=NODE_POOL_ANALYSIS_SCHEMA)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [str(e)]
    
    @staticmethod
    def validate_subnet_analysis(analysis_data: Dict) -> Tuple[bool, List[str]]:
        """Validate subnet analysis data."""
        try:
            jsonschema.validate(instance=analysis_data, schema=SUBNET_ANALYSIS_SCHEMA)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [str(e)]
    
    @staticmethod
    def validate_json_file(file_path: str, schema: Dict = None) -> Tuple[bool, List[str], Dict]:
        """
        Validate a JSON file.
        
        Returns:
            Tuple of (is_valid, list_of_errors, parsed_data)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if schema:
                jsonschema.validate(instance=data, schema=schema)
            else:
                # Try to auto-detect schema based on content
                if 'diagnostics' in data and 'cluster_info' in data:
                    jsonschema.validate(instance=data, schema=DIAGNOSTIC_REPORT_SCHEMA)
                elif 'node_pool_name' in data and 'metrics' in data:
                    jsonschema.validate(instance=data, schema=NODE_POOL_ANALYSIS_SCHEMA)
                elif 'subnet_name' in data and 'capacity' in data:
                    jsonschema.validate(instance=data, schema=SUBNET_ANALYSIS_SCHEMA)
            
            return True, [], data
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {str(e)}"], {}
        except jsonschema.ValidationError as e:
            return False, [f"Validation error: {str(e)}"], {}
        except Exception as e:
            return False, [f"Error: {str(e)}"], {}


class ReportEnricher:
    """Enrich report data with additional computed fields."""
    
    @staticmethod
    def enrich_node_pool_data(pool_data: Dict) -> Dict:
        """Add computed fields to node pool data."""
        enriched = pool_data.copy()
        
        # Calculate IP allocation if not present
        if 'ip_allocation' not in enriched and 'max_pods' in enriched and 'count' in enriched:
            max_pods = enriched['max_pods']
            node_count = enriched['count']
            
            # Azure CNI formula: (maxPods + 1) IPs per node
            ips_per_node = max_pods + 1
            total_ips = ips_per_node * node_count
            
            # Calculate surge requirements if upgrade settings exist
            surge_ips = 0
            if 'upgrade_settings' in enriched and enriched['upgrade_settings'].get('max_surge'):
                max_surge = enriched['upgrade_settings']['max_surge']
                if isinstance(max_surge, str) and '%' in max_surge:
                    surge_percentage = int(max_surge.rstrip('%'))
                    surge_nodes = max(1, int(node_count * surge_percentage / 100))
                else:
                    surge_nodes = int(max_surge)
                surge_ips = surge_nodes * ips_per_node
            
            enriched['ip_allocation'] = {
                'required_ips_per_node': ips_per_node,
                'total_required_ips': total_ips,
                'surge_ip_requirement': surge_ips,
                'potential_max_ips': total_ips + surge_ips
            }
        
        return enriched
    
    @staticmethod
    def enrich_subnet_data(subnet_data: Dict) -> Dict:
        """Add computed fields to subnet data."""
        enriched = subnet_data.copy()
        
        # Calculate usage percentage if not present
        if 'usage_percentage' not in enriched and 'available_ips' in enriched and 'address_space_size' in enriched:
            total = enriched['address_space_size']
            available = enriched['available_ips']
            used = total - available
            enriched['usage_percentage'] = round((used / total) * 100, 2) if total > 0 else 0
        
        # Calculate remaining capacity for common maxPods values
        if 'remaining_capacity' not in enriched and 'available_ips' in enriched:
            available = enriched['available_ips']
            enriched['remaining_capacity'] = {
                'additional_nodes_max_pods_30': available // 31,  # 30 + 1
                'additional_nodes_max_pods_50': available // 51,  # 50 + 1
                'additional_nodes_max_pods_100': available // 101  # 100 + 1
            }
        
        # Determine if subnet is full
        if 'is_full' not in enriched and 'usage_percentage' in enriched:
            enriched['is_full'] = enriched['usage_percentage'] >= 95
        
        return enriched
    
    @staticmethod
    def enrich_diagnostic_report(report_data: Dict) -> Dict:
        """Enrich complete diagnostic report with computed fields."""
        enriched = report_data.copy()
        
        # Enrich node pools
        if 'node_pools' in enriched:
            enriched['node_pools'] = [
                ReportEnricher.enrich_node_pool_data(pool)
                for pool in enriched['node_pools']
            ]
        
        # Enrich subnets
        if 'subnets' in enriched:
            enriched['subnets'] = [
                ReportEnricher.enrich_subnet_data(subnet)
                for subnet in enriched['subnets']
            ]
        
        return enriched


def save_json_report(report_data: Dict, output_path: str, 
                    validate: bool = True, enrich: bool = True,
                    pretty: bool = True) -> Tuple[bool, str]:
    """
    Save report data to JSON file with optional validation and enrichment.
    
    Args:
        report_data: Report data dictionary
        output_path: Path to save JSON file
        validate: Whether to validate before saving
        enrich: Whether to enrich data with computed fields
        pretty: Whether to pretty-print JSON
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Enrich if requested
        if enrich:
            report_data = ReportEnricher.enrich_diagnostic_report(report_data)
        
        # Validate if requested
        if validate:
            is_valid, errors = ReportValidator.validate_diagnostic_report(report_data)
            if not is_valid:
                return False, f"Validation failed: {', '.join(errors)}"
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(report_data, f, separators=(',', ':'), ensure_ascii=False)
        
        return True, f"Report saved successfully to {output_path}"
    
    except Exception as e:
        return False, f"Failed to save report: {str(e)}"


def load_json_report(input_path: str, validate: bool = True) -> Tuple[bool, str, Dict]:
    """
    Load and optionally validate JSON report.
    
    Returns:
        Tuple of (success, message, data)
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if validate:
            is_valid, errors = ReportValidator.validate_diagnostic_report(data)
            if not is_valid:
                return False, f"Validation failed: {', '.join(errors)}", {}
        
        return True, "Report loaded successfully", data
    
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}", {}
    except Exception as e:
        return False, f"Failed to load report: {str(e)}", {}
