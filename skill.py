"""skill.py — สกิลทั้งหมดของ Kai และ Nyx"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pygame

import settings as S
from component import State
from entities import Fighter, FloatingText, KunaiProjectile, SmokeScreen, Projectile
from ui import load_image


class BaseSkill(ABC):
    NAME = "SKILL"
    DESCRIPTION = ""
    COOLDOWN = 3.0
    ENERGY_COST = 10.0
    ICON = "emptyImage.png"
    SHEET_PATH: Optional[str] = None 
    SHEET_TIME: Optional[float] = None
    SHEET_COLUMNS = 4

    def __init__(self) -> None:
        self._cooldown_left = 0.0
        self.action = ""
        self.key_label = ""
        self._frames: Optional[list[pygame.Surface]] = None

    def bind(self, action: str, key_label: str) -> None:
        self.action, self.key_label = action, key_label

    def load_sprite(self) -> None:
        """โหลด sprite sheet ของสกิล (เรียกจาก Fighter หลังสร้างสกิล)"""
        if not self.SHEET_PATH:
            self._frames = None
            return
        sheet = load_image(self.SHEET_PATH)
        fw = sheet.get_width() // self.SHEET_COLUMNS
        fh = sheet.get_height()
        self._frames = [
            sheet.subsurface(pygame.Rect(i * fw, 0, fw, fh)).copy()
            for i in range(self.SHEET_COLUMNS)
        ]
    
    def play_pose(self, caster: Fighter, pose: str, length: float) -> None:
        if self._frames and self.SHEET_TIME:
            length = self.SHEET_TIME
        caster.play_pose(pose, length, frames=self._frames)

    
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


# ================================================================== Jack
class PacMan_Chomp(BaseSkill):
    NAME = "Pac-Man Chomp"
    DESCRIPTION = "พุ่งกัดศัตรูอย่างรวดเร็ว"
    COOLDOWN = 3.0
    ENERGY_COST = 15.0
    ICON = "emptyImage.png"
    DASH_SPEED = 1100.0
    DASH_TIME = 0.30
    SHEET_PATH = "imageFolder/jack_skill1.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=self.DASH_TIME + 0.15)
        # พุ่งไปทางที่หันหน้า แล้ว hitbox (ปากงับ) จะทำงานระหว่างพุ่ง
        caster.vel.x = caster.facing * self.DASH_SPEED
        caster.hitbox.arm(
            damage=(8 + 8 * caster.power) * caster.outgoing_damage_multiplier(),
            width=110, height=100, offset_x=60, offset_y=105,
            windup=0.05, active=self.DASH_TIME,
            knockback=(380, -260), stun=0.5,
            tags={"chomp"},
        )
        self.play_pose(caster, "rush", self.DASH_TIME + 0.1)
        caster.burst(14, S.YELLOW if hasattr(S, "YELLOW") else S.P1_COLOR, 260)


class Power_Pellet(BaseSkill):
    NAME = "Power Pellet"
    DESCRIPTION = "กินเม็ดพลังเพื่อเพิ่มความเร็ว"
    COOLDOWN = 6.0
    ENERGY_COST = 20.0
    ICON = "emptyImage.png"
    BUFF_TIME = 5.0
    HEAL = 8.0
    SHEET_PATH = "imageFolder/jack_skill2.png"
    SHEET_TIME = 0.8

    def execute(self, caster: Fighter, target: Fighter) -> None:
        # ใช้ status "kinetic" เดิม เพื่อให้โบนัสของ Jack (attack_speed,
        # move_speed_multiplier, ดูดซับดาเมจตอนการ์ด) ทำงานต่อเนื่อง
        caster.add_status("kinetic", self.BUFF_TIME)
        caster.hp += self.HEAL
        caster.stamina += self.ENERGY_COST
        caster.state_machine.change(State.CAST, lock=0.25)
        self.play_pose(caster, "cast", 0.8)
        caster.burst(20, S.WHITE, 240)


class GhostFrenzy(BaseSkill):
    NAME = "GHOST FRENZY"
    DESCRIPTION = "Devastating multi-hit bionic combo executing unblockable finisher damage."
    COOLDOWN = 10.0
    ENERGY_COST = 50.0
    ICON = "emptyImage.png"
    HITS = 7
    INTERVAL = 0.13

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._remaining = 0
        self._timer = 0.0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        self._caster, self._remaining, self._timer = caster, self.HITS, 0.0
        caster.state_machine.change(State.CAST, lock=self.HITS * self.INTERVAL + 0.25)
        self.play_pose(caster, "rush", self.HITS * self.INTERVAL + 0.2)

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


# ================================================================== Art
class ShutUp(BaseSkill):
    NAME = "Shut Up!"
    DESCRIPTION = "ตะโกนผลักศัตรูออกไป"
    COOLDOWN = 3.0
    ENERGY_COST = 15.0
    ICON = "emptyImage.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.35)
        caster.vel.x = 0
        # คลื่นเสียง: hitbox กว้างด้านหน้า ดาเมจต่ำแต่ผลักแรง ป้องกันไม่ได้
        caster.hitbox.arm(
            damage=(3 + 3 * caster.power) * caster.outgoing_damage_multiplier(),
            width=160, height=140, offset_x=90, offset_y=100,
            windup=0.08, active=0.15,
            knockback=(900, -120), unblockable=True,
            stun=0.4, tags={"shout"},
        )
        self.play_pose(caster, "cast", 0.35)
        caster.burst(22, S.WHITE, 340)


class CriticalRoast(BaseSkill):
    NAME = "CRITICAL ROAST"
    DESCRIPTION = "ยิงคลื่นเสียงจากคำพูดโจทตีศัตรู"
    COOLDOWN = 5.0
    ENERGY_COST = 25.0
    ICON = "emptyImage.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.3)
        self.play_pose(caster, "throw", 0.3)
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


class EmotionalDamage(BaseSkill):
    NAME = "EMOTIONAL DAMAGE"
    DESCRIPTION = "ปล่อยคำพูดทำลายจิตใจพร้อมคลื่นเสียงรุนแรง"
    COOLDOWN = 12.0
    ENERGY_COST = 35.0
    ICON = "emptyImage.png"
    WAVE_SPEED = 700

    def execute(self, caster: Fighter, target: Fighter) -> None:
        mult = caster.outgoing_damage_multiplier()
        caster.state_machine.change(State.CAST, lock=0.45)
        caster.vel.x = 0
        self.play_pose(caster, "cast", 0.45)

        # 1 คลื่นเสียงระยะประชิดหน้าตัวละคร
        caster.hitbox.arm(
            damage=(5 + 5 * caster.power) * mult,
            width=120, height=140, offset_x=70, offset_y=100,
            windup=0.1, active=0.15,
            knockback=(700, -200), unblockable=True,
            stun=0.5, tags={"shout"},
        )

        # 2 คลื่นเสียงลูกใหญ่พุ่งออกไปไกล
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
            
            #caster.world.spawn_projectile(wave)
            # ข้อความคำพูดลอยขึ้นเหนือหัว
            caster.world.spawn_effect(
                FloatingText("EMOTIONAL DAMAGE!", caster.rect.centerx,
                             caster.rect.top - 20, S.WHITE, 1.2)
            )

        caster.burst(30, S.WHITE, 380)

