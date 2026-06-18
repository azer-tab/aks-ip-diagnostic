from diagnostics.ip_exhaustion import check_ip_exhaustion
from diagnostics.provisioning_state import evaluate_provisioning_state
from diagnostics.subnet_capacity import assess_subnet_capacity
from diagnostics.max_pods import evaluate_max_pods

def generate_report(diagnostic_results):
    report_lines = []
    
    report_lines.append("Azure Kubernetes Service Diagnostic Report")
    report_lines.append("=" * 50)
    
    if diagnostic_results['ip_exhaustion']:
        report_lines.append("IP Exhaustion Issues:")
        for issue in diagnostic_results['ip_exhaustion']:
            report_lines.append(f"- {issue}")
    else:
        report_lines.append("No IP exhaustion issues detected.")
    
    if diagnostic_results['provisioning_state']:
        report_lines.append("\nProvisioning State Issues:")
        for issue in diagnostic_results['provisioning_state']:
            report_lines.append(f"- {issue}")
    else:
        report_lines.append("All node pools are in a healthy provisioning state.")
    
    if diagnostic_results['subnet_capacity']:
        report_lines.append("\nSubnet Capacity Issues:")
        for issue in diagnostic_results['subnet_capacity']:
            report_lines.append(f"- {issue}")
    else:
        report_lines.append("All subnets have sufficient capacity.")
    
    if diagnostic_results['max_pods']:
        report_lines.append("\nMax Pods Configuration Issues:")
        for issue in diagnostic_results['max_pods']:
            report_lines.append(f"- {issue}")
    else:
        report_lines.append("All maxPods configurations are within safe limits.")
    
    return "\n".join(report_lines)

def run_diagnostics():
    diagnostic_results = {
        'ip_exhaustion': check_ip_exhaustion(),
        'provisioning_state': evaluate_provisioning_state(),
        'subnet_capacity': assess_subnet_capacity(),
        'max_pods': evaluate_max_pods(),
    }
    
    report = generate_report(diagnostic_results)
    print(report)