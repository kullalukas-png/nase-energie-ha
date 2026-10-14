"""Conservative, registry-based discovery; names are labels, not evidence."""
from collections import defaultdict
import hashlib
import re

GOODWE_KEYS = {
    "pv_w": "ppv", "load_w": "house_consumption", "grid_w": "active_power",
    "battery_w": "pbattery1", "soc_pct": "battery_soc",
}


def goodwe_key(row):
    if row.get("platform") != "goodwe":
        return None
    uid = row.get("unique_id", "")
    for metric, key in GOODWE_KEYS.items():
        if uid.startswith(f"goodwe-{key}-"):
            return metric
    return None


def suggestions(rows):
    """PV can be summed. Shared household/grid must not be blindly summed."""
    groups = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if not row.get("disabled") and (key := goodwe_key(row)):
            groups[row.get("config_entry_id")][key].append(row["entity_id"])
    result = {"pv_w": sorted({eid for g in groups.values() for eid in g["pv_w"]})}
    if len(groups) == 1:
        for metric in ("load_w", "grid_w", "battery_w", "soc_pct"):
            found = next(iter(groups.values()))[metric]
            if len(found) == 1:
                result[metric] = found[0]
    else:
        # Only a single battery-bearing inverter is unambiguous for SOC/battery.
        batteries = [g for g in groups.values() if g["soc_pct"]]
        if len(batteries) == 1:
            for metric in ("soc_pct", "battery_w"):
                if len(batteries[0][metric]) == 1:
                    result[metric] = batteries[0][metric][0]
    return result


def suggested_sign(rows, entity_id, metric):
    # GoodWe ET uses positive export and positive battery discharge.
    return -1 if any(r["entity_id"] == entity_id and goodwe_key(r) == metric for r in rows) else 1


def string_suggestions(rows):
    """Only documented GoodWe PV power registers, never voltage/current/name guesses."""
    return sorted(r["entity_id"] for r in rows if not r.get("disabled")
                  and r.get("platform") == "goodwe"
                  and re.match(r"^goodwe-ppv[1-4]-", r.get("unique_id", "")))


def string_channels(entities, rows, samples):
    """Stable anonymous identifiers survive an HA entity rename. No serials sent."""
    by_id = {r["entity_id"]: r for r in rows}
    result = []
    for entity in entities:
        row = by_id.get(entity, {})
        identity = row.get("unique_id") or entity
        group = row.get("device_id") or row.get("config_entry_id")
        result.append({
            "entity_id": entity,
            "id": "s_" + hashlib.sha256((row.get("platform", "sensor") + "|" + identity).encode()).hexdigest()[:24],
            "name": (samples.get(entity, {}).get("name") or entity.split(".")[-1])[:80],
            "inverter_id": "i_" + hashlib.sha256(str(group).encode()).hexdigest()[:24] if group else None,
            "inverter_name": (row.get("device_name") or "Střídač")[:80] if group else None,
        })
    return result

