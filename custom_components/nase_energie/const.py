"""Read-only telemetry integration. No device services or incoming commands."""
DOMAIN = "nase_energie"
INTEGRATION_VERSION = "0.3.0"
CONFIG_VERSION = 1
CONFIG_MINOR_VERSION = 2
DEFAULT_URL = "https://fve.konska-osuvky.cz"
METRICS = ("pv_w", "load_w", "grid_w", "battery_w", "soc_pct")
INTERVAL = 60
QUEUE_LIMIT = 120

