"""component.py — ชิ้นส่วนย่อยที่ Fighter ประกอบเข้าด้วยกัน"""
from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Optional

import pygame

from events import HitInfo

if TYPE_CHECKING:
    from entities import Fighter


class State(Enum):
    IDLE = auto()
    WALK = auto()
    JUMP = auto()
    ATTACK = auto()
    CAST = auto()
    HIT = auto()
    KO = auto()


class StateMachine:
    def __init__(self) -> None:
        self._state = State.IDLE
        self._lock = 0.0
        self.elapsed = 0.0
        self._auto_recover = (State.ATTACK, State.CAST, State.HIT)

    @property
    def state(self) -> State:
        return self._state

    @property
    def can_act(self) -> bool:
        return self._state != State.KO and self._lock <= 0.0

    def change(self, new_state: State, lock: float = 0.0) -> None:
        self._state = new_state
        self._lock = max(0.0, lock)
        self.elapsed = 0.0

    def locomote(self, new_state: State) -> None:
        if self._lock <= 0.0 and self._state in (State.IDLE, State.WALK, State.JUMP):
            self._state = new_state

    def update(self, dt: float) -> None:
        self.elapsed += dt
        if self._lock > 0.0:
            self._lock -= dt
            if self._lock <= 0.0 and self._state in self._auto_recover:
                self._state = State.IDLE
                self.elapsed = 0.0


class Hitbox:
    def __init__(self) -> None:
        self._p: Optional[dict[str, Any]] = None
        self._timer = 0.0
        self._has_hit = False

    def arm(
        self,
        damage: float,
        width: int,
        height: int,
        offset_x: int,
        offset_y: int,
        windup: float,
        active: float,
        knockback: tuple[float, float] = (0.0, 0.0),
        unblockable: bool = False,
        stun: float = 0.3,
        tags: tuple[str, ...] | set[str] | frozenset[str] = (),
    ) -> None:
        self._p = dict(
            damage=damage, width=width, height=height, offset_x=offset_x,
            offset_y=offset_y, windup=windup, active=active, knockback=knockback,
            unblockable=unblockable, stun=stun, tags=frozenset(tags),
        )
        self._timer = 0.0
        self._has_hit = False

    def clear(self) -> None:
        self._p = None

    def update(self, dt: float) -> None:
        if self._p is None:
            return
        self._timer += dt
        if self._timer > self._p["windup"] + self._p["active"]:
            self._p = None

    @property
    def is_active(self) -> bool:
        if self._p is None or self._has_hit:
            return False
        return self._p["windup"] <= self._timer <= self._p["windup"] + self._p["active"]

    def mark_hit(self) -> None:
        self._has_hit = True

    def rect_for(self, owner: "Fighter") -> pygame.Rect:
        assert self._p is not None
        r = pygame.Rect(0, 0, self._p["width"], self._p["height"])
        r.center = (
            owner.rect.centerx + owner.facing * self._p["offset_x"],
            owner.rect.bottom - self._p["offset_y"],
        )
        return r

    def build_hit(self, owner: "Fighter") -> HitInfo:
        assert self._p is not None
        p = self._p

        # Critical hit when attacking in midair
        critical = not owner.on_ground

        damage = p["damage"] * owner.outgoing_damage_multiplier()

        if critical:
            damage *= 1.5

        tags = set(p["tags"])

        if critical:
            tags.add("critical")

        return HitInfo(
            attacker=owner,
            damage=damage,
            knockback=pygame.Vector2(p["knockback"]),
            direction=owner.facing,
            unblockable=p["unblockable"],
            stun=p["stun"],
            tags=frozenset(tags),
        )


class InputController:
    def __init__(self, keymap: dict[str, tuple[int, ...]], labels: dict[str, str]) -> None:
        self._keymap = keymap
        self._labels = labels

    def label(self, action: str) -> str:
        return self._labels.get(action, "?")

    def action_for_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type != pygame.KEYDOWN:
            return None
        for action, keys in self._keymap.items():
            if event.key in keys:
                return action
        return None

    def is_held(self, action: str, pressed: Any) -> bool:
        return any(pressed[k] for k in self._keymap.get(action, ()))


def make_player_one_controller() -> InputController:
    km = {
        "left": (pygame.K_a,), "right": (pygame.K_d,), "jump": (pygame.K_w,),
        "block": (pygame.K_s,), "attack": (pygame.K_f,),
        "skill1": (pygame.K_q,), "skill2": (pygame.K_e,), "skill3": (pygame.K_c,),
    }
    lb = {"attack": "F", "skill1": "Q", "skill2": "E", "skill3": "C"}
    return InputController(km, lb)


def make_player_two_controller() -> InputController:
    km = {
        "left": (pygame.K_LEFT,), "right": (pygame.K_RIGHT,), "jump": (pygame.K_UP,),
        "block": (pygame.K_DOWN,), "attack": (pygame.K_RSHIFT, pygame.K_KP0),
        "skill1": (pygame.K_KP1, pygame.K_1), "skill2": (pygame.K_KP2, pygame.K_2),
        "skill3": (pygame.K_KP3, pygame.K_3),
    }
    lb = {"attack": "NUM 0", "skill1": "NUM 1", "skill2": "NUM 2", "skill3": "NUM 3"}
    return InputController(km, lb)
