"""Additive configuration migration: never reset mappings or opt into new data."""
from copy import deepcopy

from .const import CONFIG_MINOR_VERSION, CONFIG_VERSION


def migrate_settings(version, minor_version, data, options):
    """Return independent copies; reject future major schemas without altering them.

    Both 0.1.0 and 0.2.0 used config schema 1.1. A missing string selection
    means no consent, not an invitation to discover and upload new sensors.
    Unknown keys are retained for safe forward-compatible minor downgrades.
    """
    if version != CONFIG_VERSION:
        raise ValueError("unsupported_config_version")
    updated_data, updated_options = deepcopy(dict(data)), deepcopy(dict(options))
    if minor_version < CONFIG_MINOR_VERSION:
        if "pv_strings" not in updated_data and "pv_strings" not in updated_options:
            updated_data["pv_strings"] = []
    return updated_data, updated_options, max(minor_version, CONFIG_MINOR_VERSION)
