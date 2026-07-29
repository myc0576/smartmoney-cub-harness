from __future__ import annotations


class PluginError(Exception):
    """Base error for the plugin subsystem."""

    code = "plugin_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class ManifestValidationError(PluginError):
    code = "manifest_invalid"


class UnknownPluginError(PluginError):
    code = "unknown_plugin"


class PluginNotInstalledError(PluginError):
    code = "plugin_not_installed"


class PluginDisabledError(PluginError):
    code = "plugin_disabled"


class ConsentRequiredError(PluginError):
    code = "consent_required"


class PluginSecurityError(PluginError):
    code = "plugin_security_violation"


class PluginRuntimeError(PluginError):
    code = "plugin_runtime_error"
