from __future__ import annotations

import random
import time


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
