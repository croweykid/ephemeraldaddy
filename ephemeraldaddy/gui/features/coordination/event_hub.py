from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

Subscriber = Callable[[dict[str, Any]], None]
RequestHandler = Callable[[dict[str, Any]], Any]


class FeatureEventHub:
    """In-process coordination layer for feature modules.

    Keeps feature-to-feature communication local (signals/callbacks) so modules do not need
    file-based exchanges for lightweight coordination.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._request_handlers: dict[str, RequestHandler] = {}

    def subscribe(self, topic: str, callback: Subscriber) -> Callable[[], None]:
        listeners = self._subscribers[topic]
        listeners.append(callback)

        def _unsubscribe() -> None:
            if callback in listeners:
                listeners.remove(callback)

        return _unsubscribe

    def publish(self, topic: str, payload: dict[str, Any] | None = None) -> None:
        event = payload or {}
        for callback in list(self._subscribers.get(topic, [])):
            callback(event)

    def register_handler(self, topic: str, handler: RequestHandler) -> None:
        self._request_handlers[topic] = handler

    def request(self, topic: str, payload: dict[str, Any] | None = None) -> Any:
        handler = self._request_handlers.get(topic)
        if handler is None:
            raise KeyError(f"No request handler registered for topic '{topic}'")
        return handler(payload or {})
