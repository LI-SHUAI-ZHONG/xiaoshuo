"""Bounded HTTP transport. No implicit retries, redirects, proxies or payload logging."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx2 as httpx

from accos.modules.models.invocation import ModelRuntimeError
from accos.modules.models.registry import ProviderProfile


class ModelHttpTransport:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def documents(
        self,
        profile: ProviderProfile,
        path: str,
        body: dict[str, Any],
        credential: str | None,
        *,
        streaming: bool = False,
        ndjson: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if credential:
            headers["Authorization"] = f"Bearer {credential}"
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                trust_env=False,
                follow_redirects=False,
                timeout=profile.timeout_seconds,
            ) as client:
                async with client.stream(
                    "POST", profile.endpoint + path, json=body, headers=headers
                ) as response:
                    code = response.status_code
                    if code == 429:
                        raise ModelRuntimeError("PROVIDER_RATE_LIMITED", retryable=True)
                    if code in {400, 401, 403, 404, 405, 413, 422}:
                        raise ModelRuntimeError("PROVIDER_REJECTED")
                    if code >= 500 or code in {408, 409}:
                        raise ModelRuntimeError("PROVIDER_RESULT_UNKNOWN", uncertain=True)
                    if code < 200 or code >= 300:
                        raise ModelRuntimeError("PROVIDER_REDIRECT_OR_ERROR")
                    if not streaming:
                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > profile.max_response_bytes:
                                raise ModelRuntimeError("RESPONSE_TOO_LARGE", uncertain=True)
                        yield _document(data)
                        return
                    # Incremental byte framing bounds even a malicious unterminated line.
                    pending = b""
                    event_data: list[str] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        pending += chunk
                        if total > profile.max_response_bytes:
                            raise ModelRuntimeError("RESPONSE_TOO_LARGE", uncertain=True)
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            line = line.rstrip(b"\r")
                            if ndjson:
                                if line:
                                    yield _document(line)
                            elif line.startswith(b"data:"):
                                event_data.append(line[5:].lstrip().decode("utf-8"))
                            elif not line and event_data:
                                value = "\n".join(event_data)
                                event_data.clear()
                                if value == "[DONE]":
                                    yield {"_done": True}
                                else:
                                    yield _document(value)
                    if ndjson and pending.strip():
                        yield _document(pending)
                    elif pending.strip() or event_data:
                        raise ModelRuntimeError("STREAM_TRUNCATED", uncertain=True)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            raise ModelRuntimeError("PROVIDER_CONNECT_FAILED", retryable=True) from None
        except (httpx.HTTPError, UnicodeError, ValueError):
            raise ModelRuntimeError("PROVIDER_RESULT_UNKNOWN", uncertain=True) from None


def _document(data: bytes | bytearray | str) -> dict[str, Any]:
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ModelRuntimeError("INVALID_RESPONSE", uncertain=True)
    return value
