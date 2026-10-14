"""Naše energie: outbound sensor telemetry only."""
from datetime import timedelta
import logging
from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import INTERVAL
from .migrations import migrate_settings
from .sender import Sender

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass, entry):
    """Keep credentials, IDs and every user setting across code updates."""
    try:
        data, options, minor_version = migrate_settings(
            entry.version, entry.minor_version, entry.data, entry.options)
    except ValueError:
        _LOGGER.error("Unsupported configuration schema %s.%s; configuration was not changed",
                      entry.version, entry.minor_version)
        return False
    if minor_version != entry.minor_version or data != entry.data or options != entry.options:
        hass.config_entries.async_update_entry(
            entry, data=data, options=options, version=entry.version, minor_version=minor_version)
    return True


async def async_setup_entry(hass, entry):
    sender = Sender(hass, async_get_clientsession(hass), {**entry.data, **entry.options},
                    auth_failed=lambda: entry.async_start_reauth(hass))
    entry.runtime_data = sender
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    @callback
    def schedule(now=None):
        sender.schedule(now)
    sender.unsubscribe = async_track_time_interval(hass, schedule, timedelta(seconds=INTERVAL))
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    schedule()
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR]):
        await entry.runtime_data.close()
        return True
    return False

