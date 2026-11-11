"""events.py — ระบบเหตุการณ์แบบ Observer"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable

import pygame

if TYPE_CHECKING:
    from entities import Fighter

Listener = Callable[..., None]


class EventDispatcher:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)

    def subscribe(self, event_name: str, listener: Listener) -> None:
        self._listeners[event_name].append(listener)

    def emit(self, event_name: str, **payload: Any) -> None:
        for listener in list(self._listeners[event_name]):
            listener(**payload)


class HitInfo:
    def __init__(
        self,
        attacker: "Fighter",
        damage: float,
        knockback: pygame.Vector2 | None = None,
        direction: int = 1,
        unblockable: bool = False,
        stun: float = 0.3,
        tags: frozenset[str] | None = None,
    ) -> None:
        self.attacker = attacker
        self.damage = damage
        self.knockback = knockback if knockback is not None else pygame.Vector2()
        self.direction = direction
        self.unblockable = unblockable
        self.stun = stun
        self.tags = tags if tags is not None else frozenset()
