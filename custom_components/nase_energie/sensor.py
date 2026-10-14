"""Diagnostic status: no hardware device or control entity is registered."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import callback


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ConnectionSensor(entry)])


class ConnectionSensor(SensorEntity):
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["waiting", "online", "offline", "invalid_auth", "paused", "no_data", "pv_strings_not_ready"]
    _attr_icon = "mdi:cloud-upload-outline"
    _attr_translation_key = "connection"

    def __init__(self, entry):
        self.sender = entry.runtime_data
        self._attr_unique_id = f"{entry.unique_id}_connection"
        self._attr_name = f"Naše energie {entry.title} připojení"

    @property
    def native_value(self):
        return self.sender.status

    @property
    def extra_state_attributes(self):
        return {"last_success": self.sender.last_success.isoformat() if self.sender.last_success else None,
                "queued_samples": len(self.sender.queue), "dropped_samples": self.sender.dropped,
                "mode": "monitoring"}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.sender.listeners.add(self.async_write_ha_state)
        self.async_on_remove(lambda: self.sender.listeners.discard(self.async_write_ha_state))

