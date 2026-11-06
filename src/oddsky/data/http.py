"""One polite HTTP client with retries. Archives are shared public infrastructure."""

from __future__ import annotations

import logging
import time

import httpx

log = logging.getLogger("oddsky")

UA = "oddsky/0.1 (+https://github.com/oddsky; open-source astronomy)"


def request(method: str, url: str, *, retries: int = 3, timeout: float = 120.0, headers: dict | None = None,
            **kw) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = httpx.request(method, url, timeout=timeout, headers={"User-Agent": UA, **(headers or {})}, follow_redirects=True, **kw)
            if r.status_code >= 500:
                raise httpx.HTTPStatusError(f"{r.status_code}", request=r.request, response=r)
            r.raise_for_status()
            return r
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last = e
            wait = 2 ** attempt * 2
            log.warning("%s %s failed (%s); retry in %ss", method, url, e, wait)
            time.sleep(wait)
    raise RuntimeError(f"{url} unavailable after {retries} attempts: {last}")
