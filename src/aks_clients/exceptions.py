"""Typed exceptions used by Azure and Kubernetes client wrappers."""


class DiagnosticClientError(RuntimeError):
    """Base exception for external API/client failures."""


class AzureDiagnosticError(DiagnosticClientError):
    """Base exception for Azure SDK access failures."""


class AzureResourceLookupError(AzureDiagnosticError):
    """Raised when an Azure resource cannot be read."""


class KubernetesDiagnosticError(DiagnosticClientError):
    """Base exception for Kubernetes API access failures."""
