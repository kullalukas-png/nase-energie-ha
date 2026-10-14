"""Pair locally, then confirm sensors before disclosing the one-use code."""
import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er, selector
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PortalClient, PortalError
from .const import CONFIG_MINOR_VERSION, CONFIG_VERSION, DEFAULT_URL, DOMAIN, METRICS
from .discovery import suggestions, suggested_sign, string_suggestions, string_channels
from .telemetry import portal_url, validate_mapping, validate_strings


def registry_rows(hass):
    devices = dr.async_get(hass)
    return [dict(entity_id=e.entity_id, platform=e.platform, unique_id=e.unique_id,
                 config_entry_id=e.config_entry_id, disabled=e.disabled_by is not None,
                 device_id=e.device_id,
                 device_name=(device.name_by_user or device.name) if (device := devices.async_get(e.device_id)) else None)
            for e in er.async_get(hass).entities.values()]


def current_samples(hass):
    return {s.entity_id: {"value": s.state, "unit": s.attributes.get("unit_of_measurement"),
                          "name": s.attributes.get("friendly_name")}
            for s in hass.states.async_all("sensor")}


def measurement_schema(hass, defaults):
    fields = {}
    for metric in METRICS:
        kwargs = {"default": defaults[metric]} if defaults.get(metric) else {}
        fields[vol.Optional(metric, **kwargs)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", multiple=metric == "pv_w"))
    fields[vol.Optional("pv_strings", default=defaults.get("pv_strings", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", multiple=True))
    return vol.Schema(fields)


def mapping_from(input_data):
    return {metric: (list(input_data.get(metric, [])) if metric == "pv_w"
                     else [input_data[metric]] if input_data.get(metric) else [])
            for metric in METRICS}


def confirmation_schema(signs, enabled=True):
    def sign_options(metric):
        return selector.SelectSelector(selector.SelectSelectorConfig(
            options=["1", "-1"], translation_key=metric,
            mode=selector.SelectSelectorMode.DROPDOWN))
    return vol.Schema({
        vol.Required("grid_sign", default=str(signs.get("grid_w", 1))): sign_options("grid_w"),
        vol.Required("battery_sign", default=str(signs.get("battery_w", 1))): sign_options("battery_w"),
        vol.Required("enabled", default=enabled): bool,
        vol.Required("consent", default=False): bool,
    })


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = CONFIG_VERSION
    MINOR_VERSION = CONFIG_MINOR_VERSION

    def __init__(self):
        self._url = DEFAULT_URL
        self._code = ""
        self._mapping = {}
        self._signs = {}
        self._strings = []

    async def async_step_reauth(self, entry_data):
        """Replace a revoked token in the existing entry; do not rediscover sensors."""
        self._code = ""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            if not user_input.get("consent"):
                errors["base"] = "consent_required"
            else:
                try:
                    code = user_input["pairing_code"].strip()
                    result = await PortalClient(async_get_clientsession(self.hass),
                                                entry.data["portal_url"]).pair(code)
                    # Never repoint an existing household to a different one.
                    if result["installation"]["id"] != entry.data["installation_id"]:
                        errors["base"] = "wrong_installation"
                    else:
                        await self.async_set_unique_id(entry.unique_id)
                        self._abort_if_unique_id_mismatch()
                        # The entry update listener performs exactly one reload.
                        # Credentials only: mappings/options/IDs/title are untouched.
                        return self.async_update_and_abort(
                            entry, data_updates={"token": result["token"]})
                except PortalError as error:
                    errors["base"] = error.code
        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({
            vol.Required("pairing_code"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            vol.Required("consent", default=False): bool,
        }), errors=errors, description_placeholders={"name": entry.title,
                                                     "portal_url": entry.data["portal_url"]})

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self._url = portal_url(user_input["portal_url"])
                code = user_input["pairing_code"].strip()
                if not re.fullmatch(r"ne_[A-Za-z0-9_-]{32}", code):
                    raise ValueError("invalid_pairing")
                self._code = code
                return await self.async_step_measurements()
            except ValueError as error:
                errors["base"] = str(error)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("portal_url", default=self._url): str,
            vol.Required("pairing_code"): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
        }), errors=errors)

    async def async_step_measurements(self, user_input=None):
        errors = {}
        rows = registry_rows(self.hass)
        defaults = suggestions(rows)
        defaults["pv_strings"] = string_suggestions(rows)
        if user_input is not None:
            defaults = user_input
            try:
                self._mapping = mapping_from(user_input)
                validate_mapping(self._mapping, current_samples(self.hass))
                selected = user_input.get("pv_strings", [])
                validate_strings(selected, self._mapping, current_samples(self.hass))
                self._strings = string_channels(selected, rows, current_samples(self.hass))
                self._signs = {m: suggested_sign(rows, self._mapping[m][0], m) if self._mapping[m] else 1
                               for m in ("grid_w", "battery_w")}
                return await self.async_step_confirm()
            except ValueError as error:
                errors["base"] = str(error)
        return self.async_show_form(step_id="measurements", data_schema=measurement_schema(self.hass, defaults), errors=errors)

    async def async_step_confirm(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._signs = {"grid_w": int(user_input["grid_sign"]), "battery_w": int(user_input["battery_sign"])}
            if not user_input.get("consent"):
                errors["base"] = "consent_required"
            else:
                try:
                    result = await PortalClient(async_get_clientsession(self.hass), self._url).pair(self._code)
                    self._code = ""
                    installation = result["installation"]
                    await self.async_set_unique_id(f"{self._url}|{installation['id']}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=installation["name"], data={
                        "portal_url": self._url, "token": result["token"],
                        "installation_id": installation["id"], "mapping": self._mapping,
                        "signs": self._signs, "enabled": user_input["enabled"],
                        "pv_strings": self._strings,
                    })
                except PortalError as error:
                    errors["base"] = error.code
        return self.async_show_form(step_id="confirm", data_schema=confirmation_schema(self._signs), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self):
        self._mapping = {}
        self._strings = []

    async def async_step_init(self, user_input=None):
        errors = {}
        settings = {**self.config_entry.data, **self.config_entry.options}
        defaults = {m: settings["mapping"].get(m, []) if m == "pv_w"
                    else next(iter(settings["mapping"].get(m, [])), "") for m in METRICS}
        # Missing legacy selection means no consent. Never auto-enable new uploads.
        defaults["pv_strings"] = [c["entity_id"] for c in settings.get("pv_strings", [])]
        if user_input is not None:
            defaults = user_input
            try:
                self._mapping = mapping_from(user_input)
                validate_mapping(self._mapping, current_samples(self.hass))
                selected = user_input.get("pv_strings", [])
                validate_strings(selected, self._mapping, current_samples(self.hass))
                self._strings = string_channels(selected, registry_rows(self.hass), current_samples(self.hass))
                return await self.async_step_confirm()
            except ValueError as error:
                errors["base"] = str(error)
        return self.async_show_form(step_id="init", data_schema=measurement_schema(self.hass, defaults), errors=errors)

    async def async_step_confirm(self, user_input=None):
        settings = {**self.config_entry.data, **self.config_entry.options}
        signs = {m: suggested_sign(registry_rows(self.hass), self._mapping[m][0], m) if self._mapping[m] else 1
                 for m in ("grid_w", "battery_w")}
        # Preserve deliberate sign overrides only when the source is unchanged.
        for metric in signs:
            if self._mapping[metric] == settings["mapping"].get(metric):
                signs[metric] = settings["signs"].get(metric, signs[metric])
        errors = {}
        if user_input is not None:
            if not user_input.get("consent"):
                errors["base"] = "consent_required"
            else:
                return self.async_create_entry(title="", data={**self.config_entry.options,
                    "mapping": self._mapping,
                    "pv_strings": self._strings,
                    "signs": {"grid_w": int(user_input["grid_sign"]), "battery_w": int(user_input["battery_sign"])},
                    "enabled": user_input["enabled"]})
        return self.async_show_form(step_id="confirm", data_schema=confirmation_schema(signs, settings.get("enabled", True)), errors=errors)

