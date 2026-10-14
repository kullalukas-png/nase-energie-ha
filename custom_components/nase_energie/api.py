"""Bounded HTTPS requests; never log secrets or follow a redirect."""
import asyncio
import re


class PortalError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class PortalClient:
    def __init__(self, session, base_url):
        self.session = session
        self.url = base_url + "/api.php"

    async def request(self, route, data, token=None):
        headers = {"Authorization": "Bearer " + token} if token else {}
        try:
            async with asyncio.timeout(15):
                async with self.session.post(self.url, params={"route": route}, json=data,
                                             headers=headers, allow_redirects=False) as response:
                    if response.status in (401, 403):
                        raise PortalError("invalid_pairing" if route == "pairing_exchange" else "invalid_auth")
                    if response.status == 429:
                        raise PortalError("rate_limited")
                    if response.status not in (200, 503):
                        raise PortalError("cannot_connect")
                    # Do not allow unbounded memory use or expose response bodies.
                    chunks = []
                    size = 0
                    while True:
                        chunk = await response.content.read(min(8192, 65537 - size))
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > 65536:
                            raise PortalError("invalid_response")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                    import json
                    result = json.loads(raw)
                    if response.status == 503:
                        if isinstance(result, dict) and result.get("code") == "pv_strings_not_ready":
                            raise PortalError("pv_strings_not_ready")
                        raise PortalError("cannot_connect")
                    if not isinstance(result, dict) or result.get("ok") is not True:
                        raise PortalError("invalid_response")
                    return result
        except PortalError:
            raise
        except Exception as error:
            # CancelledError derives from BaseException and is deliberately not caught.
            raise PortalError("cannot_connect") from error

    async def pair(self, code):
        if not re.fullmatch(r"ne_[A-Za-z0-9_-]{32}", code):
            raise PortalError("invalid_pairing")
        result = await self.request("pairing_exchange", {"pairing_code": code})
        installation = result.get("installation", {})
        if (not re.fullmatch(r"fve_[A-Za-z0-9_-]{43}", str(result.get("token", "")))
                or not isinstance(installation, dict) or type(installation.get("id")) is not int
                or installation["id"] < 1 or not isinstance(installation.get("name"), str)
                or result.get("mode") != "monitoring"):
            raise PortalError("invalid_response")
        return result

    async def send(self, token, sample):
        result = await self.request("ingest", sample, token)
        if result.get("accepted") is not True and result.get("duplicate") is not True:
            raise PortalError("invalid_response")

