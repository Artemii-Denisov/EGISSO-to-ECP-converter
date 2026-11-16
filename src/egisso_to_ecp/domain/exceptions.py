"""Domain exceptions for egisso-to-ecp."""

class AppBaseError(Exception):
    """Base exception for application domain errors."""
    pass


class ValidationError(AppBaseError):
    """Raised when record data fails schema or domain constraints."""
    pass


class FlkError(ValidationError):
    """Raised when Format-Logical Control rules are violated."""
    pass


class ParsingError(AppBaseError):
    """Raised when input files cannot be parsed."""
    pass


class ConfigurationError(AppBaseError):
    """Raised when application configuration or mapping is invalid."""
    pass
