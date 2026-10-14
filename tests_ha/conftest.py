"""Real HA fixtures: isolated configuration, synthetic states, no live network."""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Use actual HA custom-integration loading, not the standalone API doubles."""
    yield


@pytest.fixture(autouse=True)
def no_live_telemetry():
    """All network boundaries are mocked; pytest-socket also denies outbound sockets."""
    with patch("custom_components.nase_energie.api.PortalClient.send", new_callable=AsyncMock) as send:
        yield send
