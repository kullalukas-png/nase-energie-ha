"""Two hours of bounded in-memory retry history; never fabricate a sample."""
import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone

from .api import PortalClient, PortalError
from .const import QUEUE_LIMIT
from .telemetry import payload


class Sender:
    def __init__(self, hass, session, settings, auth_failed=None):
        self.hass = hass
        self.settings = settings
        self.client = PortalClient(session, settings["portal_url"])
        self.queue = deque(maxlen=QUEUE_LIMIT)
        self.status = "waiting"
        self.last_success = None
        self.dropped = 0
        self.failures = 0
        self.retry_at = datetime.min.replace(tzinfo=timezone.utc)
        self.listeners = set()
        self.unsubscribe = None
        self.task = None
        self.auth_failed = auth_failed

    def schedule(self, _now=None):
        if self.task is None or self.task.done():
            self.task = self.hass.async_create_task(self.tick())

    async def tick(self):
        now = datetime.now(timezone.utc)
        try:
            if not self.settings.get("enabled", True):
                self.status = "paused"
                return
            if self.status == "invalid_auth":
                return
            samples = {}
            for entities in self.settings["mapping"].values():
                for entity in entities:
                    state = self.hass.states.get(entity)
                    if state:
                        samples[entity] = {"value": state.state, "unit": state.attributes.get("unit_of_measurement")}
            for channel in self.settings.get("pv_strings", []):
                state = self.hass.states.get(channel["entity_id"])
                if state:
                    samples[channel["entity_id"]] = {"value": state.state, "unit": state.attributes.get("unit_of_measurement")}
            sample = payload(now.isoformat(timespec="seconds"), self.settings["mapping"], self.settings["signs"], samples,
                             self.settings.get("pv_strings"))
            if sample is not None:
                if len(self.queue) == QUEUE_LIMIT:
                    self.dropped += 1
                self.queue.append(sample)
            if now < self.retry_at:
                return
            if not self.queue:
                self.status = "no_data"
                return
            # Max 3 requests/minute (180/hour), below portal's 360/hour limit.
            for _ in range(min(3, len(self.queue))):
                await self.client.send(self.settings["token"], self.queue[0])
                self.queue.popleft()
                self.last_success = datetime.now(timezone.utc)
            self.status = "online" if sample is not None else "no_data"
            self.failures = 0
        except PortalError as error:
            self.status = error.code if error.code in ("invalid_auth", "pv_strings_not_ready") else "offline"
            self.failures = min(self.failures + 1, 8)
            delay = 15 * 60 if error.code in ("rate_limited", "pv_strings_not_ready") else min(60 * 2 ** (self.failures - 1), 15 * 60)
            self.retry_at = now + timedelta(seconds=delay)
            if error.code == "invalid_auth" and self.auth_failed is not None:
                # Stop sending and ask HA to repair this same entry exactly once.
                self.auth_failed()
        finally:
            for listener in tuple(self.listeners):
                listener()

    async def close(self):
        if self.unsubscribe:
            self.unsubscribe()
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.listeners.clear()
        self.queue.clear()

