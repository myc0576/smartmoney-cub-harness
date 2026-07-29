from __future__ import annotations

# Lifecycle states for an individual plugin installation.
STATUS_NOT_INSTALLED = "not_installed"
STATUS_INSTALLING = "installing"
STATUS_INSTALLED_UNCONFIGURED = "installed_unconfigured"
STATUS_READY = "ready"
STATUS_DISABLED = "disabled"
STATUS_UPDATE_AVAILABLE = "update_available"
STATUS_DEPENDENCY_ERROR = "dependency_error"
STATUS_CREDENTIALS_MISSING = "credentials_missing"
STATUS_DATA_MISSING = "data_missing"
STATUS_MODEL_MISSING = "model_missing"
STATUS_INCOMPATIBLE = "incompatible"
STATUS_ERROR = "error"

PLUGIN_STATUSES = frozenset(
    {
        STATUS_NOT_INSTALLED,
        STATUS_INSTALLING,
        STATUS_INSTALLED_UNCONFIGURED,
        STATUS_READY,
        STATUS_DISABLED,
        STATUS_UPDATE_AVAILABLE,
        STATUS_DEPENDENCY_ERROR,
        STATUS_CREDENTIALS_MISSING,
        STATUS_DATA_MISSING,
        STATUS_MODEL_MISSING,
        STATUS_INCOMPATIBLE,
        STATUS_ERROR,
    }
)

# How far the host actually integrates a plugin. Catalog-only entries must
# never claim runtime integration.
INTEGRATION_RUNTIME = "runtime_integrated"
INTEGRATION_CATALOG = "catalog_available"
INTEGRATION_PLANNED = "adapter_planned"

INTEGRATION_LEVELS = frozenset(
    {INTEGRATION_RUNTIME, INTEGRATION_CATALOG, INTEGRATION_PLANNED}
)

CATALOG_ONLY_LEVELS = frozenset({INTEGRATION_CATALOG, INTEGRATION_PLANNED})
