"""skill.py — สกิลทั้งหมดของ Kai และ Nyx"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pygame

import settings as S
from component import State
from entities import Fighter, FloatingText, KunaiProjectile, SmokeScreen


class BaseSkill(ABC):
    NAME = "SKILL"
    DESCRIPTION = ""
    COOLDOWN = 3.0
    ENERGY_COST = 10.0
    ICON = "emptyImage.png"

    def __init__(self) -> None:
        self._cooldown_left = 0.0
        self.action = ""
        self.key_label = ""

    def bind(self, action: str, key_label: str) -> None:
        self.action, self.key_label = action, key_label

    @property
    def cooldown_left(self) -> float:
        return self._cooldown_left

    @property
    def cooldown_ratio(self) -> float:
        return self._cooldown_left / self.COOLDOWN if self.COOLDOWN else 0.0

    def can_cast(self, caster: Fighter) -> bool:
        return self._cooldown_left <= 0.0 and caster.energy >= self.ENERGY_COST

    def try_cast(self, caster: Fighter, target: Optional[Fighter]) -> bool:
        if target is None or not caster.state_machine.can_act or not self.can_cast(caster):
            return False
        caster.energy -= self.ENERGY_COST
        self._cooldown_left = self.COOLDOWN
        caster.dispatcher.emit("on_skill_cast", caster=caster, skill=self)
        self.execute(caster, target)
        return True

    def update(self, dt: float) -> None:
        self._cooldown_left = max(0.0, self._cooldown_left - dt)

    def reset(self) -> None:
        self._cooldown_left = 0.0

    @abstractmethod
    def execute(self, caster: Fighter, target: Fighter) -> None:
        pass


# ================================================================== KAI
class PlasmaHook(BaseSkill):
    NAME = "PLASMA HOOK"
    DESCRIPTION = "Launches an electrified high uppercut that wall-bounces opponents on clean hit."
    COOLDOWN = 3.0
    ENERGY_COST = 15.0
    ICON = "emptyImage.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.55)
        caster.hitbox.arm(
            damage=10 + 10 * caster.power, width=90, height=130, offset_x=55, offset_y=95,
            windup=0.12, active=0.18, knockback=(700, -620), stun=0.55,
            tags={"wall_bounce"},
        )
        caster.play_pose("uppercut", 0.5)
        caster.burst(10, S.P1_COLOR, 220)


class KineticCharge(BaseSkill):
    NAME = "KINETIC CHARGE"
    DESCRIPTION = "Absorbs incoming guard damage to supercharge frame data and forward dash speed."
    COOLDOWN = 6.0
    ENERGY_COST = 20.0
    ICON = "emptyImage.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.add_status("kinetic", 5.0)
        caster.state_machine.change(State.CAST, lock=0.25)
        caster.vel.x = caster.facing * 650.0
        caster.play_pose("rush", 0.25)
        caster.burst(16, S.WHITE, 260)


class OverdriveRush(BaseSkill):
    NAME = "OVERDRIVE RUSH"
    DESCRIPTION = "Devastating multi-hit bionic combo executing unblockable finisher damage."
    COOLDOWN = 10.0
    ENERGY_COST = 50.0
    ICON = "emptyImage.png"
    HITS = 5
    INTERVAL = 0.13

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._remaining = 0
        self._timer = 0.0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        self._caster, self._remaining, self._timer = caster, self.HITS, 0.0
        caster.state_machine.change(State.CAST, lock=self.HITS * self.INTERVAL + 0.25)
        caster.play_pose("rush", self.HITS * self.INTERVAL + 0.2)

    def update(self, dt: float) -> None:
        super().update(dt)
        c = self._caster
        if c is None or self._remaining <= 0:
            return
        if c.is_ko or c.state_machine.state == State.HIT:
            self._remaining = 0
            return
        self._timer -= dt
        if self._timer > 0:
            return
        self._timer = self.INTERVAL
        self._remaining -= 1
        final = self._remaining == 0
        dmg = (2.5 + 2.5 * c.power) * (1.8 if final else 1.0)
        c.hitbox.arm(
            damage=dmg, width=100, height=110, offset_x=60, offset_y=100,
            windup=0.0, active=0.12,
            knockback=(520, -520) if final else (90, -40), unblockable=True,
            stun=0.45 if final else 0.2, tags={"rush"},
        )
        c.vel.x = c.facing * (150.0 if final else 380.0)
        c.burst(5, S.P1_COLOR, 240)

    def reset(self) -> None:
        super().reset()
        self._remaining = 0


# ================================================================== NYX
class PhantomDash(BaseSkill):
    NAME = "PHANTOM DASH"
    DESCRIPTION = "Phases through projectiles with brief invulnerability frames, emerging behind the foe."
    COOLDOWN = 3.0
    ENERGY_COST = 15.0
    ICON = "emptyImage.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        old = caster.rect.center
        side = 1 if target.pos.x >= caster.pos.x else -1
        new_x = target.pos.x + side * 95
        new_x = max(S.ARENA.left + 50, min(S.ARENA.right - 50, new_x))
        caster.set_x(new_x)
        caster.facing = -side
        caster.vel.x = 0
        caster.add_status("invulnerable", 0.5)
        caster.state_machine.change(State.CAST, lock=0.15)
        if caster.world is not None:
            caster.world.spawn_particles(old[0], old[1], S.P2_COLOR, 18, 300)
        caster.burst(18, S.P2_COLOR, 300)


class NaniteKunai(BaseSkill):
    NAME = "NANITE KUNAI"
    DESCRIPTION = "Throws three energy daggers inflicting bleeding chip damage over 4 seconds."
    COOLDOWN = 5.0
    ENERGY_COST = 25.0
    ICON = "emptyImage.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.3)
        caster.play_pose("throw", 0.3)
        mult = caster.outgoing_damage_multiplier()
        for i, vy in enumerate((-60.0, 0.0, 60.0)):
            kunai = KunaiProjectile(
                caster,
                caster.rect.centerx + caster.facing * 45,
                caster.rect.bottom - 125 + i * 18,
                caster.facing * 820.0, vy, 2.5 * mult,
                bleed_dps=0.7, bleed_time=4.0,
            )
            if caster.world is not None:
                caster.world.spawn_projectile(kunai)


class ShadowVeil(BaseSkill):
    NAME = "SHADOW VEIL"
    DESCRIPTION = "Deploys a smoke screen that conceals hitboxes and guarantees critical counters."
    COOLDOWN = 12.0
    ENERGY_COST = 35.0
    ICON = "emptyImage.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.add_status("veiled", 5.0)
        caster.state_machine.change(State.CAST, lock=0.3)
        caster.play_pose("cast", 0.3)
        caster.burst(24, (90, 90, 100), 200)
        if caster.world is not None:
            caster.world.spawn_effect(SmokeScreen(caster))
