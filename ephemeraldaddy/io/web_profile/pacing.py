from __future__ import annotations

import random
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError



class RequestPacer:
    def __init__(self, minimum_interval=1.0, jitter=0.0, *, clock=time.monotonic, wait=None, random_fn=random.random):
        self.minimum_interval = float(minimum_interval); self.jitter = float(jitter)
        self.clock = clock; self.wait = wait or time.sleep; self.random_fn = random_fn; self._last = None

    def pace(self, cancel_event=None, retry_after=0.0) -> bool:
        now = self.clock()
        delay = max(float(retry_after or 0), 0 if self._last is None else self.minimum_interval + self.jitter * self.random_fn() - (now - self._last))
        if delay > 0:
            if cancel_event is not None and cancel_event.wait(delay): return False
            if cancel_event is None: self.wait(delay)
        self._last = self.clock(); return True


# Scoped to the lookup thread: interactive single-profile lookups retain their
# existing policy, while every nested HTTP request in a batch shares a pacer.
_request_policy = ContextVar("web_profile_request_policy", default=None)


class LookupCancelled(Exception):
    pass


@contextmanager
def paced_requests(cancel_event, pacer=None):
    token = _request_policy.set((pacer or RequestPacer(), cancel_event))
    try:
        yield
    finally:
        _request_policy.reset(token)


def pace_remote_request() -> None:
    """Pace an actual remote call when running inside a batch lookup policy."""
    policy = _request_policy.get()
    if policy is not None:
        pacer, cancelled = policy
        if cancelled.is_set() or not pacer.pace(cancelled):
            raise LookupCancelled("Lookup cancelled")


def _retry_delay(value):
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        try:
            deadline = parsedate_to_datetime(value)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            return max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 1.0


def paced_urlopen(opener, request, *, timeout):
    policy = _request_policy.get()
    if policy is None:
        return opener(request, timeout=timeout)
    pacer, cancelled = policy
    retry_after = 0.0
    for attempt in range(3):
        if cancelled.is_set() or not pacer.pace(cancelled, retry_after):
            raise LookupCancelled("Lookup cancelled")
        try:
            return opener(request, timeout=timeout)
        except HTTPError as exc:
            if exc.code not in (429, 503) or attempt == 2:
                raise
            retry_after = _retry_delay(exc.headers.get("Retry-After"))
            exc.close()
