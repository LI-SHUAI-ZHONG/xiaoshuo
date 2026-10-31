"""Non-streaming JSON HTTP requests; no retry or fallback generation."""
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        return None


def redact(value: Any, secret: str) -> Any:
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, '[REDACTED]')
    if isinstance(value, list):
        return [redact(v, secret) for v in value]
    if isinstance(value, dict):
        return {redact(k, secret): redact(v, secret) for k, v in value.items()}
    return value


def post(url: str, payload: dict, timeout: float, key: str = '') -> tuple[dict, str | None]:
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = f'Bearer {key}'
    request = Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers)
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            body = response.read().decode('utf-8')
    except HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        return redact({'http_status': exc.code, 'body': body}, key), 'http_error'
    except (URLError, TimeoutError, OSError) as exc:
        return {'error_type': type(exc).__name__}, 'transport_error'
    try:
        raw = json.loads(body)
        json.dumps(raw, allow_nan=False)  # Reject NaN/Infinity and overflowing numeric exponents.
        if not isinstance(raw, dict):
            raise ValueError('object required')
        return redact(raw, key), None
    except (ValueError, TypeError):
        return redact({'body': body}, key), 'invalid_json'
