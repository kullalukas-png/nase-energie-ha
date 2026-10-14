"""Only operational counters; credentials, sensors and household name omitted."""
from .const import INTEGRATION_VERSION


async def async_get_config_entry_diagnostics(hass, entry):
    sender = getattr(entry, "runtime_data", None)
    if sender is None:
        return {"integration_version": INTEGRATION_VERSION, "mode": "monitoring", "status": "not_loaded"}
    return {"integration_version": INTEGRATION_VERSION, "mode": "monitoring", "status": sender.status,
            "pv_string_count": len(sender.settings.get("pv_strings", [])),
            "queued_samples": len(sender.queue), "dropped_samples": sender.dropped,
            "enabled": sender.settings.get("enabled", True)}

