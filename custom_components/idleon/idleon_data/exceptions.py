"""Custom exceptions for Idleon data loading and parsing."""

from __future__ import annotations


class IdleonDataError(Exception):
    """Base exception for Idleon data source failures."""


class IdleonCannotConnect(IdleonDataError):
    """Raised when the configured source cannot be read."""


class IdleonAuthFailed(IdleonDataError):
    """Raised when Idleon cloud authentication fails."""


class IdleonAuthPending(IdleonAuthFailed):
    """Raised when a device authorization flow is not complete yet."""


class IdleonInvalidJson(IdleonDataError):
    """Raised when the configured source does not return valid JSON."""


class IdleonInvalidSchema(IdleonDataError):
    """Raised when JSON cannot be parsed into supported Idleon models."""
