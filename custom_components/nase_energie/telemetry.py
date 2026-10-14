"""Pure validation and unit conversion, also usable without HA for tests."""
import math
from urllib.parse import urlsplit, urlunsplit

METRICS = ("pv_w", "load_w", "grid_w", "battery_w", "soc_pct")


def portal_url(value):
    """Never accept HTTP, credentials, fragments, query strings or redirects."""
    if not isinstance(value, str):
        raise ValueError("invalid_url")
    parsed = urlsplit(value.strip())
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment
            or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value):
        raise ValueError("invalid_url")
    try:
        parsed.port
    except ValueError as error:
        raise ValueError("invalid_url") from error
    if any(part in (".", "..") for part in parsed.path.split("/")):
        raise ValueError("invalid_url")
    return urlunsplit(("https", parsed.netloc.lower(), parsed.path.rstrip("/"), "", ""))


def validate_mapping(mapping, samples):
    selected = []
    for metric in METRICS:
        entities = mapping.get(metric, [])
        if not isinstance(entities, list) or (metric != "pv_w" and len(entities) > 1):
            raise ValueError("invalid_mapping")
        for entity in entities:
            sample = samples.get(entity)
            if not isinstance(entity, str) or not entity.startswith("sensor.") or sample is None:
                raise ValueError("missing_sensor")
            unit = sample.get("unit")
            if unit not in (("%",) if metric == "soc_pct" else ("W", "kW")):
                raise ValueError("invalid_unit")
            selected.append(entity)
    if not selected:
        raise ValueError("no_sensors")
    if len(selected) != len(set(selected)):
        raise ValueError("duplicate_sensor")


def validate_strings(entities, mapping, samples):
    if (not isinstance(entities, list) or len(entities) > 32
            or any(not isinstance(e, str) for e in entities) or len(set(entities)) != len(entities)):
        raise ValueError("invalid_mapping")
    for entity in entities:
        if not isinstance(entity, str) or not entity.startswith("sensor.") or entity not in samples:
            raise ValueError("missing_sensor")
        if samples[entity].get("unit") not in ("W", "kW"):
            raise ValueError("invalid_unit")
        # Reusing a string as a source of the PV total is valid; other metrics are not.
        if any(entity in mapping.get(m, []) for m in METRICS if m != "pv_w"):
            raise ValueError("duplicate_sensor")


def number(sample, metric):
    if not sample:
        return None
    raw = sample.get("value")
    if isinstance(raw, bool) or raw in (None, "unknown", "unavailable", ""):
        return None
    try:
        value = float(raw)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(value):
        return None
    unit = sample.get("unit")
    if metric == "soc_pct":
        return value if unit == "%" and 0 <= value <= 100 else None
    if unit not in ("W", "kW"):
        return None
    value *= 1000 if unit == "kW" else 1
    if abs(value) > 1_000_000 or (metric in ("pv_w", "load_w") and value < 0):
        return None
    return value


def payload(timestamp, mapping, signs, samples, channels=None):
    result = {"timestamp": timestamp}
    for metric in METRICS:
        entities = mapping.get(metric, [])
        values = [number(samples.get(e), metric) for e in entities]
        value = sum(values) if values and all(v is not None for v in values) else None
        if value is not None and metric in ("grid_w", "battery_w"):
            sign = signs.get(metric, 1)
            value = value * sign if type(sign) is int and sign in (-1, 1) else None
        if value is not None and abs(value) > (100 if metric == "soc_pct" else 1_000_000):
            value = None
        result[metric] = value
    if channels:
        result["pv_strings"] = [{k: c[k] for k in ("id", "name", "inverter_id", "inverter_name")} |
                                {"power_w": number(samples.get(c["entity_id"]), "pv_w")} for c in channels]
    available = any(result[m] is not None for m in METRICS) or any(
        c["power_w"] is not None for c in result.get("pv_strings", []))
    return result if available else None

