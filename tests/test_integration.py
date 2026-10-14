"""Standalone tests for the actual pure modules and sender, without HA installed."""
import asyncio
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

if sys.platform == "win32":
    # The local sandbox does not expose Windows IOCP; HA itself runs on Linux.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

package = ModuleType("ne_test")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/nase_energie")]
sys.modules["ne_test"] = package
t = importlib.import_module("ne_test.telemetry")
d = importlib.import_module("ne_test.discovery")
a = importlib.import_module("ne_test.api")
s = importlib.import_module("ne_test.sender")


def row(metric, name, entry="one", platform="goodwe", disabled=False):
    return {"entity_id": "sensor." + name, "unique_id": f"goodwe-{d.GOODWE_KEYS[metric]}-{entry}",
            "config_entry_id": entry, "platform": platform, "disabled": disabled}


class Normalization(unittest.TestCase):
    def test_https_url(self):
        self.assertEqual(t.portal_url("https://EXAMPLE.test/sub/"), "https://example.test/sub")
        for url in ("http://example.test", "https://u:p@example.test", "https://e/?x=1", "https://e/#a", "https://e/a/../b", "https://e:bad", "https://e\\evil", "https://e/ x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                t.portal_url(url)

    def test_bad_numbers_not_zero(self):
        for raw in (None, "unavailable", "unknown", "", True, float("nan"), float("inf"), "NaN", "bad", -1, 1_000_001):
            with self.subTest(raw=raw):
                self.assertIsNone(t.number({"value": raw, "unit": "W"}, "pv_w"))

    def test_units_and_polarity(self):
        p = t.payload("2026-10-13T10:00:00Z", {"pv_w": ["a", "b"], "grid_w": ["g"], "battery_w": ["c"], "soc_pct": ["soc"]},
                      {"grid_w": -1, "battery_w": -1}, {"a": {"value": "2", "unit": "kW"}, "b": {"value": "500", "unit": "W"},
                      "g": {"value": "1000", "unit": "W"}, "c": {"value": "-2", "unit": "kW"}, "soc": {"value": "60", "unit": "%"}})
        self.assertEqual([p[m] for m in ("pv_w", "grid_w", "battery_w", "soc_pct")], [2500, -1000, 2000, 60])

    def test_partial_pv_never_pretends_total(self):
        self.assertIsNone(t.payload("t", {"pv_w": ["a", "missing"]}, {}, {"a": {"value": "100", "unit": "W"}}))

    def test_zero_is_valid(self):
        self.assertEqual(t.payload("t", {"pv_w": ["a"]}, {}, {"a": {"value": "0", "unit": "W"}})["pv_w"], 0)

    def test_soc_range_and_wrong_units(self):
        for value, unit in [(101, "%"), (-1, "%"), (2, "kWh"), (50, "W")]:
            self.assertIsNone(t.number({"value": value, "unit": unit}, "soc_pct"))
        self.assertIsNone(t.number({"value": 5, "unit": "kWh"}, "load_w"))

    def test_mapping_validation(self):
        samples = {"sensor.pv": {"unit": "W"}, "sensor.soc": {"unit": "%"}}
        t.validate_mapping({"pv_w": ["sensor.pv"], "soc_pct": ["sensor.soc"]}, samples)
        for mapping in ({}, {"pv_w": ["sensor.pv", "sensor.pv"]}, {"pv_w": ["sensor.pv"], "load_w": ["sensor.pv"]}, {"pv_w": ["sensor.soc"]}, {"pv_w": ["sensor.no"]}):
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                t.validate_mapping(mapping, samples)


class Discovery(unittest.TestCase):
    def test_strings_renamed_and_grouped(self):
        rows = [{"entity_id": "sensor.renamed", "platform": "goodwe", "unique_id": "goodwe-ppv1-serial",
                 "config_entry_id": "entry", "device_id": "device", "device_name": "GoodWe 1"},
                {"entity_id": "sensor.voltage", "platform": "goodwe", "unique_id": "goodwe-vpv1-serial"},
                {"entity_id": "sensor.fake", "platform": "template", "unique_id": "goodwe-ppv1-serial"}]
        self.assertEqual(d.string_suggestions(rows), ["sensor.renamed"])
        a = d.string_channels(["sensor.renamed"], rows, {"sensor.renamed": {"name": "Garáž"}})[0]
        self.assertEqual(a["name"], "Garáž")
        self.assertEqual(a["inverter_name"], "GoodWe 1")
        self.assertNotIn("serial", a["id"])
        rows[0]["entity_id"] = "sensor.new_name"
        b = d.string_channels(["sensor.new_name"], rows, {})[0]
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(a["inverter_id"], b["inverter_id"])

    def test_string_power_not_added_to_total(self):
        c = {"entity_id": "sensor.s", "id": "s_demo", "name": "Test", "inverter_id": None, "inverter_name": None}
        p = t.payload("t", {"pv_w": ["sensor.total"]}, {},
                      {"sensor.total": {"value": 5000, "unit": "W"}, "sensor.s": {"value": 2, "unit": "kW"}}, [c])
        self.assertEqual(p["pv_w"], 5000)
        self.assertEqual(p["pv_strings"][0]["power_w"], 2000)
        self.assertNotIn("entity_id", p["pv_strings"][0])

    def test_unavailable_strings_null_not_zero(self):
        channels = [{"entity_id": "sensor.missing", "id": "s_missing", "name": "Missing", "inverter_id": None, "inverter_name": None}]
        p = t.payload("t", {"pv_w": ["sensor.total"]}, {}, {"sensor.total": {"value": 0, "unit": "W"}}, channels)
        self.assertIsNone(p["pv_strings"][0]["power_w"])

    def test_validate_strings(self):
        samples = {"sensor.s": {"unit": "W"}, "sensor.v": {"unit": "V"}}
        t.validate_strings(["sensor.s"], {"pv_w": ["sensor.s"]}, samples)
        for entities, mapping in [(["sensor.s"]*2, {}), (["sensor.v"], {}), (["sensor.no"], {}), (["sensor.s"], {"load_w": ["sensor.s"]})]:
            with self.assertRaises(ValueError):
                t.validate_strings(entities, mapping, samples)
    def test_renamed_goodwe_entities(self):
        rows = [row(m, "renamed_" + m) for m in d.GOODWE_KEYS]
        found = d.suggestions(rows)
        self.assertEqual(found["grid_w"], "sensor.renamed_grid_w")
        self.assertEqual(found["pv_w"], ["sensor.renamed_pv_w"])
        self.assertEqual(d.suggested_sign(rows, found["grid_w"], "grid_w"), -1)

    def test_two_inverters_no_shared_sum(self):
        rows = [row(m, e + m, e) for e in ("one", "two") for m in ("pv_w", "grid_w", "load_w")]
        found = d.suggestions(rows)
        self.assertEqual(len(found["pv_w"]), 2)
        self.assertNotIn("load_w", found)
        self.assertNotIn("grid_w", found)

    def test_single_battery_and_disabled(self):
        rows = [row("pv_w", "a", "one"), row("pv_w", "b", "two"), row("soc_pct", "soc", "one"),
                row("battery_w", "bat", "one"), row("pv_w", "disabled", "three", disabled=True)]
        self.assertEqual(d.suggestions(rows)["battery_w"], "sensor.bat")
        self.assertEqual(len(d.suggestions(rows)["pv_w"]), 2)

    def test_no_name_guessing(self):
        r = row("grid_w", "goodwe_grid", platform="template")
        self.assertNotIn("grid_w", d.suggestions([r]))
        self.assertEqual(d.suggested_sign([r], r["entity_id"], "grid_w"), 1)


class Response:
    def __init__(self, status=200, body=None):
        self.status = status
        self.raw = body if isinstance(body, bytes) else json.dumps(body or {"ok": True, "accepted": True}).encode()
        self.content = self

    async def read(self, count):
        # Deliberately fragmented to exercise stream parsing.
        count = min(count, 13)
        chunk, self.raw = self.raw[:count], self.raw[count:]
        return chunk

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class APITests(unittest.IsolatedAsyncioTestCase):
    async def test_extension_not_ready(self):
        with self.assertRaises(a.PortalError) as caught:
            await a.PortalClient(Session(Response(503, {"ok": False, "code": "pv_strings_not_ready"})), "https://e").send("x", {})
        self.assertEqual(caught.exception.code, "pv_strings_not_ready")
    async def test_send_https_without_redirects(self):
        session = Session(Response())
        await a.PortalClient(session, "https://portal.test/sub").send("synthetic", {"pv_w": 0})
        self.assertFalse(session.calls[0][1]["allow_redirects"])
        self.assertEqual(session.calls[0][0], "https://portal.test/sub/api.php")
        self.assertEqual(session.calls[0][1]["headers"], {"Authorization": "Bearer synthetic"})

    async def test_duplicate_success(self):
        await a.PortalClient(Session(Response(body={"ok": True, "duplicate": True})), "https://e").send("x", {})

    async def test_errors(self):
        for status, code in [(401, "invalid_auth"), (403, "invalid_auth"), (429, "rate_limited"), (302, "cannot_connect"), (500, "cannot_connect")]:
            with self.subTest(status=status), self.assertRaises(a.PortalError) as caught:
                await a.PortalClient(Session(Response(status)), "https://e").send("x", {})
            self.assertEqual(caught.exception.code, code)

    async def test_response_bound(self):
        with self.assertRaises(a.PortalError) as caught:
            await a.PortalClient(Session(Response(body=b"x" * 65537)), "https://e").request("ingest", {})
        self.assertEqual(caught.exception.code, "invalid_response")

    async def test_pair_and_validate(self):
        session = Session(Response(body={"ok": True, "token": "fve_" + "a" * 43, "installation": {"id": 1, "name": "Demo"}, "mode": "monitoring"}))
        await a.PortalClient(session, "https://e").pair("ne_" + "b" * 32)
        self.assertEqual(session.calls[0][1]["headers"], {})
        with self.assertRaises(a.PortalError):
            await a.PortalClient(session, "https://e").pair("bad")

    async def test_pair_bad_response(self):
        with self.assertRaises(a.PortalError):
            await a.PortalClient(Session(Response(body={"ok": True, "token": "bad"})), "https://e").pair("ne_" + "c" * 32)


class SenderTests(unittest.IsolatedAsyncioTestCase):
    def make_sender(self, enabled=True):
        state = SimpleNamespace(state="1.5", attributes={"unit_of_measurement": "kW"})
        hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity: state), async_create_task=asyncio.create_task)
        sender = s.Sender(hass, None, {"portal_url": "https://e", "token": "synthetic", "mapping": {"pv_w": ["sensor.pv"]}, "signs": {}, "enabled": enabled})
        sender.sent = []
        async def send(token, sample):
            sender.sent.append(sample)
        sender.client.send = send
        return sender

    async def test_read_and_send(self):
        sender = self.make_sender()
        await sender.tick()
        self.assertEqual(sender.sent[0]["pv_w"], 1500)
        self.assertEqual(sender.status, "online")
        self.assertEqual(len(sender.queue), 0)

    async def test_send_strings_same_request(self):
        sender = self.make_sender()
        sender.settings["pv_strings"] = [{"entity_id": "sensor.string", "id": "s_demo", "name": "Demo", "inverter_id": None, "inverter_name": None}]
        await sender.tick()
        self.assertEqual(len(sender.sent), 1)
        self.assertEqual(sender.sent[0]["pv_w"], 1500)
        self.assertEqual(sender.sent[0]["pv_strings"][0]["power_w"], 1500)

    async def test_pause(self):
        sender = self.make_sender(False)
        await sender.tick()
        self.assertEqual(sender.status, "paused")
        self.assertEqual(sender.sent, [])

    async def test_outage_retries_same_timestamp(self):
        sender = self.make_sender()
        async def fail(*args):
            raise a.PortalError("cannot_connect")
        sender.client.send = fail
        await sender.tick()
        original = sender.queue[0]
        self.assertEqual(sender.status, "offline")
        async def recover(token, sample):
            sender.sent.append(sample)
        sender.client.send = recover
        sender.retry_at = sender.retry_at.replace(year=2000)
        await sender.tick()
        self.assertIs(sender.sent[0], original)
        self.assertEqual(sender.status, "online")

    async def test_bounded_queue(self):
        sender = self.make_sender()
        sender.retry_at = sender.retry_at.replace(year=2099)
        for _ in range(125):
            await sender.tick()
        self.assertEqual(len(sender.queue), 120)
        self.assertEqual(sender.dropped, 5)

    async def test_invalid_auth_no_repeated_requests(self):
        sender = self.make_sender()
        async def fail(*args):
            sender.sent.append(True)
            raise a.PortalError("invalid_auth")
        sender.client.send = fail
        await sender.tick()
        await sender.tick()
        self.assertEqual(sender.status, "invalid_auth")
        self.assertEqual(len(sender.sent), 1)

    async def test_invalid_auth_starts_one_repair(self):
        sender = self.make_sender()
        repairs = []
        sender.auth_failed = lambda: repairs.append(True)
        async def fail(*args):
            raise a.PortalError("invalid_auth")
        sender.client.send = fail
        await sender.tick()
        await sender.tick()
        self.assertEqual(repairs, [True])

    async def test_network_error_does_not_start_repair(self):
        sender = self.make_sender()
        repairs = []
        sender.auth_failed = lambda: repairs.append(True)
        async def fail(*args):
            raise a.PortalError("cannot_connect")
        sender.client.send = fail
        await sender.tick()
        self.assertEqual(repairs, [])

    async def test_no_data_is_not_zero(self):
        sender = self.make_sender()
        sender.hass.states.get = lambda eid: None
        await sender.tick()
        self.assertEqual(sender.status, "no_data")
        self.assertEqual(sender.sent, [])

    async def test_unload_cancels_and_unsubscribes(self):
        sender = self.make_sender()
        cancelled = []
        sender.unsubscribe = lambda: cancelled.append(True)
        async def block(*args):
            await asyncio.sleep(100)
        sender.client.send = block
        sender.schedule()
        await asyncio.sleep(0)
        await sender.close()
        self.assertTrue(sender.task.cancelled())
        self.assertEqual(cancelled, [True])
        self.assertEqual(len(sender.queue), 0)


if __name__ == "__main__":
    unittest.main()
