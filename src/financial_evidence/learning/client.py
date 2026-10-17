"""Explicit remote enrollment client. Construction sends nothing."""

from __future__ import annotations

import json
import hashlib
import time
from email.utils import parsedate_to_datetime
import urllib.error
import urllib.parse
import urllib.request

from .contracts import encode


class LearningDeliveryError(RuntimeError):
    """Submission failed; no false success or hidden fallback."""

    def __init__(self, message, *, status=None, retry_after=None):
        super().__init__(message)
        self.status, self.retry_after = status, retry_after


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        raise LearningDeliveryError("learning endpoint redirect rejected")


class RemoteLearningClient:
    def __init__(self, endpoint, credential, *, timeout=5):
        parsed = urllib.parse.urlsplit(endpoint)
        if (parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"})):
            raise ValueError("learning endpoint must use HTTPS (HTTP permitted only on loopback)")
        if not isinstance(credential, str) or not 32 <= len(credential) <= 128 or any(ch.isspace() for ch in credential):
            raise ValueError("invalid enrolled credential")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not .1 <= timeout <= 30:
            raise ValueError("timeout must be .1..30 seconds")
        self.endpoint, self._credential, self.timeout = endpoint.rstrip("/"), credential, timeout
        self._opener = urllib.request.build_opener(_NoRedirect)

    @property
    def destination_fingerprint(self):
        """Bind retries to the explicitly selected destination and credential."""
        return hashlib.sha256(encode({"endpoint": self.endpoint,
            "credential_hash": hashlib.sha256(self._credential.encode()).hexdigest()})).hexdigest()

    def _send(self, route, value=None, method="POST"):
        raw = encode(value) if value is not None else None
        if raw is not None and len(raw) > 65536:
            raise ValueError("learning record exceeds 64 KiB")
        request = urllib.request.Request(self.endpoint + route, data=raw, method=method,
                                         headers={"Authorization": "Bearer " + self._credential, "Content-Type": "application/json",
                                                  "User-Agent": "Financial-Evidence-Learning/0.1"})
        started = time.monotonic()
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                content = bytearray()
                # read1 returns available bytes instead of waiting to fill a buffer.
                # Elapsed-time checks prevent a drip response from indefinitely
                # renewing the socket timeout or outliving the delivery lease.
                read = getattr(response, "read1", response.read)
                while True:
                    if time.monotonic() - started >= self.timeout:
                        raise LearningDeliveryError("learning response exceeded its deadline")
                    chunk = read(min(65536, 1048577 - len(content)))
                    content.extend(chunk)
                    if len(content) > 1048576:
                        raise LearningDeliveryError("learning response exceeds its allowance")
                    if not chunk:
                        break
                if time.monotonic() - started >= self.timeout:
                    raise LearningDeliveryError("learning response exceeded its deadline")
                return json.loads(content)
        except LearningDeliveryError:
            raise
        except urllib.error.HTTPError as exc:
            status = exc.code
            retry_after = exc.headers.get("Retry-After", "")
            try:
                if retry_after.isdigit():
                    retry_after = min(86400, int(retry_after[:10]))
                else:
                    retry_after = min(86400, max(0, parsedate_to_datetime(retry_after).timestamp() - time.time()))
            except (TypeError, ValueError, OverflowError):
                retry_after = None
            exc.close()
            raise LearningDeliveryError("learning submission rejected; receipt not confirmed",
                                        status=status, retry_after=retry_after) from None
        except (OSError, ValueError, urllib.error.URLError):
            # Do not interpolate a URL, token, body or upstream response into logs.
            raise LearningDeliveryError("learning submission failed; receipt not confirmed") from None

    def record_tool(self, event):
        return self._send("/v1/events", event)

    def record_decision(self, decision):
        return self._send("/v1/decisions", decision)

    def record_outcome(self, outcome):
        return self._send("/v1/outcomes", outcome)

    def describe(self):
        return self._send("/v1/me", method="GET")

    def report(self):
        return self._send("/v1/report", method="GET")

    def withdraw(self, *, purposes=None, delete=False):
        return self._send("/v1/withdraw", {"purposes": purposes, "delete": delete})

    def delete(self):
        return self._send("/v1/me", method="DELETE")
