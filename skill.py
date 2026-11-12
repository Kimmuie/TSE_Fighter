"""skill.py — สกิลทั้งหมดของตัวละครในเกม"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

import pygame

import settings as S
from component import State
from entities import (Fighter, FloatingText, QuakeProjectile, SmokeScreen, SoundwaveProjectile,
                      SparkProjectile, SRSDocumentProjectile)
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
        self.key_label = ""
        self._frames: Optional[list[pygame.Surface]] = None
        self._timers: list[dict] = []

    def bind(self, key_label: str) -> None:
        self.key_label = key_label

    def load_sprite(self) -> None:
        """โหลด sprite sheet ของสกิล (เรียกจาก Fighter หลังสร้างสกิล)"""
        if not self.SHEET_PATH:
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

    # ------------------------------------------------------------ timers
    def start_timer(self, delay: float, callback: Callable[[], None],
                    key: Optional[str] = None) -> None:
        """เรียก callback หนึ่งครั้งหลังผ่านไป `delay` วินาที (นับใน update)"""
        self._timers.append({"left": delay, "cb": callback, "key": key})

    def cancel_timers(self, key: str) -> None:
        self._timers = [t for t in self._timers if t["key"] != key]

    def _tick_timers(self, dt: float) -> None:
        if not self._timers:
            return
        for t in self._timers:
            t["left"] -= dt
        due = [t for t in self._timers if t["left"] <= 0.0]
        self._timers = [t for t in self._timers if t["left"] > 0.0]
        # เรียกหลังสร้าง list ใหม่ เพื่อให้ callback เรียก start_timer ซ้อนได้
        for t in due:
            t["cb"]()

    # ------------------------------------------------------------ casting
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
        self._tick_timers(dt)

    def reset(self) -> None:
        self._cooldown_left = 0.0
        self._timers.clear()

    def on_jump(self, caster: Fighter) -> bool:
        """Hook — คืน True ถ้าสกิลดักรับปุ่ม Jump ไว้ (ไม่กระโดดตามปกติ)"""
        return False

    @abstractmethod
    def execute(self, caster: Fighter, target: Fighter) -> None:
        pass


# ================================================================== Jack
class PacMan_Chomp(BaseSkill):
    NAME = "Pac-Man Chomp"
    DESCRIPTION = "Dashes rapidly toward an enemy and bites them with a powerful attack, dealing instant damage."
    COOLDOWN = 5.0
    ENERGY_COST = 15.0
    ICON = "skill/jack_iconskill_1.png"
    SHEET_PATH = "assets/jack_skill1.png"
    SHEET_TIME = 0.4
    DASH_SPEED = 1200.0
    DASH_DISTANCE = 300.0
    _DASH_DURATION = DASH_DISTANCE / DASH_SPEED

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=self._DASH_DURATION)
        # พุ่งไปทางที่หันหน้า แล้ว hitbox (ปากงับ) จะทำงานระหว่างพุ่ง
        caster.vel.x = caster.facing * self.DASH_SPEED
        caster.hitbox.arm(
            damage=(8 + 8 * caster.power) * caster.outgoing_damage_multiplier(),
            width=110, height=100, offset_x=60, offset_y=105,
            windup=0.05, active=self.SHEET_TIME,
            knockback=(380, -260), stun=0.5,
            tags={"chomp"},
        )
        self.play_pose(caster, "rush", self.SHEET_TIME)
        caster.burst(14, S.P1_COLOR, 260)


class Power_Pellet(BaseSkill):
    NAME = "Power Pellet"
    DESCRIPTION = "Consumes a Power Pellet to temporarily boost movement speed and increase combat mobility."
    COOLDOWN = 12.0
    ENERGY_COST = 20.0
    ICON = "skill/jack_iconskill_2.png"
    BUFF_STATUS = "kinetic"
    BUFF_TIME = 3.5
    HEAL = 8.0
    SHEET_PATH = "assets/jack_skill2.png"
    SHEET_TIME = 1.2

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.add_status(self.BUFF_STATUS, self.BUFF_TIME)
        caster.hp += self.HEAL
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        self.play_pose(caster, "cast", self.SHEET_TIME)
        caster.burst(20, S.WHITE, 240)


class GhostFrenzy(BaseSkill):
    NAME = "Ghost Frenzy"
    DESCRIPTION = "Enters a ghost-like state, dashing through enemies while delivering multiple consecutive attacks."
    COOLDOWN = 10.0
    ENERGY_COST = 50.0
    ICON = "skill/jack_iconskill_3.png"
    HITS = 5
    INTERVAL = 0.13

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._remaining = 0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        self.cancel_timers("frenzy")
        self._caster, self._remaining = caster, self.HITS
        caster.state_machine.change(State.CAST, lock=self.HITS * self.INTERVAL + 0.25)
        self.play_pose(caster, "rush", self.HITS * self.INTERVAL + 0.2)
        # ฟันครั้งแรกทันที (delay 0) แล้วต่อด้วยทุก INTERVAL
        self.start_timer(0.0, self._hit, key="frenzy")

    def _hit(self) -> None:
        c = self._caster
        if c is None or c.is_ko or c.state_machine.state == State.HIT:
            return
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
        if not final:
            self.start_timer(self.INTERVAL, self._hit, key="frenzy")


# ================================================================== Art
class CriticalRoast(BaseSkill):
    NAME = "Critical Roast"
    DESCRIPTION = "Fires a powerful sound wave through a devastating verbal roast, damaging enemies from distance."
    COOLDOWN = 5.0
    ENERGY_COST = 25.0
    ICON = "skill/art_iconskill_1.png"
    SHEET_PATH = "assets/art_skill1.png"
    SHEET_TIME = 0.3
    WAVE_SPEED = 500
    PROJ_KNOCKBACK = (260, -50)
    PROJ_STUN = 0.3

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        self.play_pose(caster, "throw", self.SHEET_TIME)
        if caster.world is None:
            return
        mult = caster.outgoing_damage_multiplier()
        # ยิงคลื่นเสียง 3 ลูกคนละมุม
        for vy in (-200.0, 0.0, 200.0):
            caster.world.spawn_projectile(SoundwaveProjectile(
                caster, caster.rect.centerx, caster.rect.centery,
                vx=self.WAVE_SPEED * caster.facing, vy=vy,
                damage=4.5 * mult, sprite="sound1_projectile.png",
                lifespan=0.5, size=(120, 70),
                knockback=self.PROJ_KNOCKBACK,
                stun=self.PROJ_STUN,
            ))


class ShutUp(BaseSkill):
    NAME = "Shut Up!"
    DESCRIPTION = "Release a thunderous shout that pushes nearby enemies away with tremendous force."
    COOLDOWN = 4.0
    ENERGY_COST = 20.0
    ICON = "skill/art_iconskill_2.png"
    SHEET_PATH = "assets/art_skill2.png"
    SHEET_TIME = 0.35

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        caster.vel.x = -850 * caster.facing
        # คลื่นเสียง: hitbox กว้างด้านหน้า ดาเมจต่ำแต่ผลักแรง ป้องกันไม่ได้
        caster.hitbox.arm(
            damage=(3 + 3 * caster.power) * caster.outgoing_damage_multiplier(),
            width=160, height=140, offset_x=90, offset_y=100,
            windup=0.05, active=0.15,
            knockback=(1100, -700), unblockable=True,
            stun=0.5, tags={"shout"},
        )
        self.play_pose(caster, "cast", self.SHEET_TIME)
        caster.burst(22, S.WHITE, 340)


class EmotionalDamage(BaseSkill):
    NAME = "Emotional Damage"
    DESCRIPTION = "Unleashes a devastating verbal assault combined with powerful sound waves, dealing heavy damage to enemies."
    COOLDOWN = 8.0
    ENERGY_COST = 35.0
    ICON = "skill/art_iconskill_3.png"
    WAVE_SPEED = 700
    SHEET_PATH = "assets/art_skill3.png"
    SHEET_TIME = 0.45
    PROJ_KNOCKBACK = (260, -50)
    PROJ_STUN = 0.3

    def execute(self, caster: Fighter, target: Fighter) -> None:
        mult = caster.outgoing_damage_multiplier()
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        caster.vel.x = 0
        self.play_pose(caster, "cast", self.SHEET_TIME)

        # 1) คลื่นเสียงระยะประชิดหน้าตัวละคร
        caster.hitbox.arm(
            damage=(5 + 5 * caster.power) * mult,
            width=120, height=60, offset_x=70, offset_y=70,
            windup=0.1, active=0.15,
            knockback=(850, -200), unblockable=True,
            stun=0.5, tags={"shout"},
        )

        # 2) คลื่นเสียงลูกใหญ่พุ่งออกไปไกล + ข้อความลอยเหนือหัว
        if caster.world is not None:
            caster.world.spawn_projectile(SoundwaveProjectile(
                caster, caster.rect.centerx, caster.rect.centery + 20,
                vx=self.WAVE_SPEED * caster.facing, vy=0,
                damage=22.5 * mult, sprite="sound2_projectile.png",
                lifespan=1.5, size=(120, 60),
                knockback=self.PROJ_KNOCKBACK,
                stun=self.PROJ_STUN,
            ))
            caster.world.spawn_effect(
                FloatingText("EMOTIONAL DAMAGE!", caster.rect.centerx, caster.rect.top - 20, S.WHITE, 1.2)
            )
        caster.burst(30, S.WHITE, 380)


# ================================================================== Pao
class CPUSmash(BaseSkill):
    NAME = "CPU Smash"
    DESCRIPTION = "Summons a giant CPU and slams it down on an enemy, dealing massive physical damage."
    COOLDOWN = 9.0
    ENERGY_COST = 30.0
    ICON = "skill/pao_iconskill_1.png"
    SHEET_PATH = "assets/pao_skill1.png"
    SHEET_TIME = 0.6

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.5)
        caster.vel.x = 0
        caster.hitbox.arm(
            damage=(13 + 13 * caster.power) * caster.outgoing_damage_multiplier(),
            width=65, height=170, offset_x=80, offset_y=120,
            windup=0.25, active=0.3,
            knockback=(350, -500), unblockable=True,
            stun=0.9, tags={"cpu_smash"},
        )
        self.play_pose(caster, "cast", self.SHEET_TIME)
        caster.burst(20, S.WHITE, 320)


class OverclockCharge(BaseSkill):
    NAME = "Overclock Charge"
    DESCRIPTION = "Overclocks his internal power to increase strength before charging forward and crushing enemies."
    COOLDOWN = 8.0
    ENERGY_COST = 25.0
    ICON = "skill/pao_iconskill_2.png"
    SHEET_PATH = "assets/pao_skill2.png"
    CHARGE_TIME = 0.8
    SHEET_TIME = CHARGE_TIME * 1.3
    DASH_SPEED = 800.0
    DASH_DISTANCE = 350.0
    _DASH_DURATION = DASH_DISTANCE / DASH_SPEED

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._charging = False
        self._dashing = False
        self._dash_start_x = 0.0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        self.cancel_timers("overclock")
        self._caster = caster
        self._charging = True
        self._dashing = False
        caster.vel.x = 0
        caster.state_machine.change(State.CAST, lock=self.CHARGE_TIME + self._DASH_DURATION + 0.1)
        self.play_pose(caster, "cast", self.SHEET_TIME)
        caster.burst(24, S.WHITE, 300)
        # Phase 1: Charge จบแล้วค่อยพุ่ง
        self.start_timer(self.CHARGE_TIME, self._start_dash, key="overclock")

    def _start_dash(self) -> None:
        c = self._caster
        if c is None or not self._charging:
            return
        self._charging = False
        self._dashing = True
        self._dash_start_x = c.pos.x
        c.vel.x = c.facing * self.DASH_SPEED
        c.hitbox.arm(
            damage=(13 + 13 * c.power) * c.outgoing_damage_multiplier() * 1.3,
            width=120, height=140, offset_x=60, offset_y=105,
            windup=0.0, active=self._DASH_DURATION, knockback=(850, -500),
            stun=0.6, tags={"overclock"},
        )
        c.burst(20, S.P1_COLOR, 340)

    def _end(self) -> None:
        c = self._caster
        if c is not None and c.state_machine.state != State.HIT:
            c.vel.x = 0
        self.cancel_timers("overclock")
        self._charging = False
        self._dashing = False
        self._caster = None

    def update(self, dt: float) -> None:
        super().update(dt)
        c = self._caster
        if c is None:
            return
        # ถูกตีระหว่าง charge หรือพุ่ง = ยกเลิก
        if c.state_machine.state == State.HIT:
            self._end()
            return
        # Phase 2: Dash (เช็คระยะทางทุกเฟรม)
        if self._dashing:
            c.vel.x = c.facing * self.DASH_SPEED
            if abs(c.pos.x - self._dash_start_x) >= self.DASH_DISTANCE:
                self._end()

    def reset(self) -> None:
        super().reset()
        self._end()


class BlueScreen_Crash(BaseSkill):
    NAME = "Blue Screen Crash"
    DESCRIPTION = "Smashes the ground with overwhelming force, releasing a massive shockwave that damages all nearby enemies."
    COOLDOWN = 8.0
    ENERGY_COST = 30.0
    ICON = "skill/pao_iconskill_3.png"
    SHEET_PATH = "assets/pao_skill3.png"
    SHEET_TIME = 0.8
    CHARGE_TIME = SHEET_TIME / 4
    HIT_TIME = (SHEET_TIME / 4) * 3
    DASH_SPEED = 350.0
    BLUE = (67, 255, 255)

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None

    def execute(self, caster: Fighter, target: Fighter) -> None:
        self._caster = caster
        caster.vel.x = 0
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        caster.hitbox.arm(
            damage=(13 + 13 * caster.power) * caster.outgoing_damage_multiplier(),
            width=550, height=30, offset_x=0, offset_y=50,
            windup=0.6, active=0.15,
            knockback=(520, -200), unblockable=True,
            stun=1.0, tags={"blue_screen"},
        )
        self.play_pose(caster, "attack", self.SHEET_TIME)
        caster.burst(14, self.BLUE, 220)
        self.start_timer(self.CHARGE_TIME, self._dash)
        self.start_timer(self.HIT_TIME, self._shockwave)

    def _dash(self) -> None:
        if self._caster is not None:
            self._caster.vel.x = self._caster.facing * self.DASH_SPEED

    def _shockwave(self) -> None:
        # คลื่นฝุ่นริมพื้นสองฝั่ง
        c = self._caster
        if c is None or c.world is None:
            return
        for side in (-1, 1):
            for i in range(1, 5):
                c.world.spawn_particles(c.pos.x + side * i * 70, S.GROUND_Y, self.BLUE, 6, 260)


# ================================================================== Piya
class SRS_Barrage(BaseSkill):
    NAME = "SRS Barrage"
    DESCRIPTION = "Throws three SRS documents in a spread. If one hits, Piya becomes Marked for 5 seconds. Press Jump while Marked to teleport behind the enemy."
    COOLDOWN = 3.0
    ENERGY_COST = 15.0
    ICON = "skill/piya_iconskill_1.png"
    SHEET_PATH = "assets/piya_skill1.png"
    SHEET_TIME = 0.3
    SPAWN_OFFSET = 100.0
    DOCUMENT_DAMAGE = 4.0
    BUFF_STATUS = "marked"
    BUFF_TIME = 5.0
    PROJ_KNOCKBACK = (0, -20)
    PROJ_STUN = 0.65

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._pending_target: Optional[Fighter] = None

    def execute(self, caster: Fighter, target: Fighter) -> None:
        self._caster = caster
        self._pending_target = None
        caster.remove_status(self.BUFF_STATUS)
        direction = caster.facing
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        self.play_pose(caster, "throw", self.SHEET_TIME)

        if caster.world is not None:
            caster.world.spawn_projectile(SRSDocumentProjectile(
                caster, self,
                caster.rect.centerx + direction * self.SPAWN_OFFSET,
                caster.rect.centery - 35,
                direction,
                damage=self.DOCUMENT_DAMAGE * caster.outgoing_damage_multiplier(),
                sprite="document_projectile.png",
                size=(120, 60),
                lifespan=1.5,
                knockback=self.PROJ_KNOCKBACK,
                stun=self.PROJ_STUN,
            ))

    def mark_target(self, target: Fighter) -> None:
        caster = self._caster
        if caster is None or caster.is_ko:
            return
        first_hit = not caster.has_status(self.BUFF_STATUS)
        self._pending_target = target
        caster.add_status(self.BUFF_STATUS, self.BUFF_TIME)
        if first_hit:
            caster.burst(18, S.GOLD, 260)

    def update(self, dt: float) -> None:
        super().update(dt)
        if self._caster is not None and not self._caster.has_status(self.BUFF_STATUS):
            self._pending_target = None

    def on_jump(self, caster: Fighter) -> bool:
        if not caster.has_status(self.BUFF_STATUS):
            return False

        target = self._pending_target
        caster.remove_status(self.BUFF_STATUS)
        self._pending_target = None
        if target is None or target.is_ko:
            return False

        old = caster.rect.center
        new_x = target.pos.x - target.facing * 85
        caster.set_x(max(S.ARENA.left + 45, min(S.ARENA.right - 45, new_x)))
        caster.facing = target.facing
        caster.vel.update(0, 0)

        caster.burst(22, S.GOLD, 320)
        if caster.world is not None:
            caster.world.spawn_particles(old[0], old[1], S.GOLD, 20, 300)
        return True

    def reset(self) -> None:
        super().reset()
        if self._caster is not None:
            self._caster.remove_status(self.BUFF_STATUS)
        self._pending_target = None


class ShadowVeil(BaseSkill):
    NAME = "Shadow Veil"
    DESCRIPTION = "Creates a cloud of smoke to conceal his movements, allowing him to strike enemies repeatedly from the shadows."
    COOLDOWN = 12.0
    ENERGY_COST = 35.0
    ICON = "skill/piya_iconskill_2.png"
    BUFF_STATUS = "veiled"
    BUFF_TIME = 2.0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.add_status(self.BUFF_STATUS, self.BUFF_TIME)
        caster.state_machine.change(State.CAST, lock=0.3)
        caster.play_pose("cast", 0.3)
        caster.burst(24, (90, 90, 100), 200)
        if caster.world is not None:
            caster.world.spawn_effect(SmokeScreen(caster))


class SuckerPunch(BaseSkill):
    NAME = "Sucker Punch"
    DESCRIPTION = "Disappears just before an incoming attack, then reappears to counterattack with precision."
    COOLDOWN = 8.0
    ENERGY_COST = 30.0
    ICON = "skill/piya_iconskill_3.png"
    SHEET_PATH = "assets/piya_skill3.png"
    SHEET_TIME = 0.8
    BUFF_STATUS = "veiled"
    BUFF_TIME = 0.4
    COUNTER_BONUS = 1.5

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._target: Optional[Fighter] = None

    def execute(self, caster: Fighter, target: Fighter) -> None:
        self.cancel_timers("sucker")
        self._caster, self._target = caster, target
        caster.vel.x = 0
        caster.add_status(self.BUFF_STATUS, self.BUFF_TIME)
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        caster.burst(20, S.P2_COLOR, 300)
        # จังหวะ 2: หายตัวครบ BUFF_TIME แล้วโผล่ด้านหลังศัตรู
        self.start_timer(self.BUFF_TIME, self._reappear, key="sucker")

    def _reappear(self) -> None:
        c, t = self._caster, self._target
        if c is None or t is None or c.is_ko or t.is_ko:
            return
        old = c.rect.center
        side = 1 if t.pos.x >= c.pos.x else -1
        new_x = t.pos.x + side * 95
        c.set_x(max(S.ARENA.left + 50, min(S.ARENA.right - 50, new_x)))
        c.facing = -side
        c.vel.x = 0
        counter = t.state_machine.state in (State.ATTACK, State.CAST)
        c.hitbox.arm(
            damage=(8 + 8 * c.power) * c.outgoing_damage_multiplier() * (self.COUNTER_BONUS if counter else 1.0),
            width=100, height=120, offset_x=55, offset_y=105,
            windup=0.05, active=0.15,
            knockback=(450, -300), stun=0.7, unblockable=True,
            tags={"counter"},
        )
        self.play_pose(c, "attack", self.SHEET_TIME)
        if c.world is not None:
            c.world.spawn_particles(old[0], old[1], S.P2_COLOR, 18, 300)
        c.burst(18, S.WHITE if counter else S.P2_COLOR, 320)


# ================================================================== Oat
class DoubleMuscle_Rush(BaseSkill):
    NAME = "Double Muscle Rush"
    DESCRIPTION = "Flexes his massive muscles before performing two powerful forward charges, smashing into enemies with overwhelming strength."
    COOLDOWN = 7.0
    ENERGY_COST = 35.0
    ICON = "skill/oat_iconskill_1.png"
    SHEET_PATH = "assets/oat_skill1.png"
    SHEET_TIME = 2.3
    HITS = 2
    HIT_DISTANCE = 500.0
    INTERVAL = 1.0

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._remaining = 0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        self.cancel_timers("rush")
        self._caster, self._remaining = caster, self.HITS
        caster.state_machine.change(State.CAST, lock=self.HITS * self.INTERVAL)
        self.play_pose(caster, "rush", self.SHEET_TIME)
        self.start_timer(0.0, self._hit, key="rush")

    def _hit(self) -> None:
        c = self._caster
        if c is None or c.is_ko:
            return
        self._remaining -= 1
        final = self._remaining == 0
        dmg = (3.25 + 3.25 * c.power) * (2.0 if final else 1.0)
        c.hitbox.arm(
            damage=dmg, width=100, height=110, offset_x=60, offset_y=100,
            windup=0.0, active=0.12,
            knockback=(520, -520) if final else (90, -40), unblockable=True,
            stun=0.45 if final else 0.2, tags={"rush"},
        )
        c.vel.x = c.facing * self.HIT_DISTANCE
        c.burst(5, S.RED, 240)
        if not final:
            self.start_timer(self.INTERVAL, self._hit, key="rush")


class CreatineShake(BaseSkill):
    NAME = "Creatine Shake"
    DESCRIPTION = "Drinks a creatine shake to restore HP and temporarily increase attack and defense."
    COOLDOWN = 13.0
    ENERGY_COST = 40.0
    ICON = "skill/oat_iconskill_2.png"
    BUFF_STATUS = "creatine"
    BUFF_TIME = 6.0
    HEAL = 14.0
    SHEET_PATH = "assets/oat_skill2.png"
    SHEET_TIME = 1.5

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.add_status(self.BUFF_STATUS, self.BUFF_TIME)
        caster.hp += self.HEAL
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        self.play_pose(caster, "cast", self.SHEET_TIME)
        caster.burst(20, S.WHITE, 240)


class Beastquake(BaseSkill):
    NAME = "Beastquake"
    DESCRIPTION = "Lifts a heavy barbell and slams it into the ground, creating a powerful shockwave that travels forward and damages enemies in its path."
    COOLDOWN = 12.0
    ENERGY_COST = 30.0
    ICON = "skill/oat_iconskill_3.png"
    WAVE_SPEED = 400
    SHEET_PATH = "assets/oat_skill3.png"
    SHEET_TIME = 1.0
    PROJ_KNOCKBACK = (260, -50)
    PROJ_STUN = 0.8

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._damage = 0.0
        self._cancelled = False

    def execute(self, caster: Fighter, target: Fighter) -> None:
        self.cancel_timers("beastquake")

        mult = caster.outgoing_damage_multiplier()
        self._caster = caster
        self._damage = 11 * mult
        self._cancelled = False

        caster.vel.x = 0
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        self.play_pose(caster, "cast", self.SHEET_TIME)

        caster.hitbox.arm(
            damage=(5 + 5 * caster.power) * mult,
            width=85, height=60, offset_x=70, offset_y=70,
            windup=0.1, active=0.15,
            knockback=(850, -200), unblockable=True,
            stun=1.0, tags={"cast"},
        )

        caster.burst(30, S.WHITE, 380)

        self.start_timer(self.SHEET_TIME, self._spawn_quake,key="beastquake")

    def update(self, dt: float) -> None:
        caster = self._caster
        if caster is not None and not self._cancelled:
            if caster.is_ko or caster.state_machine.state == State.HIT:
                self._cancelled = True
                self.cancel_timers("beastquake")

        super().update(dt)

    def _spawn_quake(self) -> None:
        caster = self._caster

        if (
            self._cancelled
            or caster is None
            or caster.is_ko
            or caster.world is None
        ):
            return

        caster.world.spawn_projectile(QuakeProjectile(
            caster,
            caster.rect.centerx + caster.facing * 60,
            caster.rect.bottom,
            vx=self.WAVE_SPEED * caster.facing,
            vy=0,
            damage=self._damage,
            sprite="quake_projectile.png",
            lifespan=10.0,
            size=(140, 80),
            knockback=self.PROJ_KNOCKBACK,
            stun=self.PROJ_STUN,
        ))

        caster.burst(20, S.WHITE, 300)

    def reset(self) -> None:
        super().reset()
        self._cancelled = True
        self._caster = None

# ================================================================== Jin
class BottleBomb(BaseSkill):
    NAME = "Bottle Bomb"
    DESCRIPTION = "Splash a bottle at an enemy head, dealing damage and briefly stunning the target."
    COOLDOWN = 9.0
    ENERGY_COST = 30.0
    ICON = "skill/jinn_iconskill_1.png"
    SHEET_PATH = "assets/jinn_skill1.png"
    SHEET_TIME = 0.6
    STUN_TIME = 1.4

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        caster.hitbox.arm(
            damage=(8 + 8 * caster.power) * caster.outgoing_damage_multiplier(),
            width=80, height=120, offset_x=60, offset_y=105,
            windup=0.05, active=0.12, unblockable=True,
            knockback=(300, -150), stun=self.STUN_TIME,
            tags={"chomp"},
        )
        self.play_pose(caster, "throw", self.SHEET_TIME)
        caster.burst(10, S.WHITE, 220)


class GangsterCharm(BaseSkill):
    NAME = "Gangster Charm"
    DESCRIPTION = "Performs Jin’s signature hair flip, releasing a mysterious aura that pulls nearby enemies toward him, inflicting a debuff and briefly stunning"
    COOLDOWN = 5.0
    ENERGY_COST = 35.0
    ICON = "skill/jinn_iconskill_3.png"
    SHEET_PATH = "assets/jinn_skill2.png"
    SHEET_TIME = 1.0
    BUFF_STATUS = "charmed"
    BUFF_TIME = 3.0
    WAVE_SPEED = 800
    PROJ_KNOCKBACK = (-1200, -500)
    PROJ_STUN = 1.0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=self.SHEET_TIME)
        self.play_pose(caster, "rush", self.SHEET_TIME)
        caster.add_status(self.BUFF_STATUS, self.BUFF_TIME)
        if caster.world is not None:
            for vy in range(-150, 151, 30):
                caster.world.spawn_projectile(SparkProjectile(
                    caster, caster.rect.centerx, caster.rect.centery,
                    vx=self.WAVE_SPEED * caster.facing, vy=vy,
                    damage=caster.power / 5, sprite="spark_projectile.png",
                    lifespan=25.0, size=(20, 20),
                    knockback=self.PROJ_KNOCKBACK,
                    stun=self.PROJ_STUN,
                ))
        caster.burst(26, S.WHITE, 340)


class HellRiderRush(BaseSkill):
    NAME = "Hell Rider Rush"
    DESCRIPTION = "Mounts his motorcycle and charges forward at incredible speed, crashing into enemies along the way."
    COOLDOWN = 7.0
    ENERGY_COST = 30.0
    ICON = "skill/jinn_iconskill_2.png"
    SHEET_PATH = "assets/jinn_skill3.png"
    SHEET_TIME = 1.0
    DASH_SPEED = 600.0
    DASH_DISTANCE = 750.0
    JUMP_HEIGHT = 900.0
    _DASH_DURATION = DASH_DISTANCE / DASH_SPEED

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=self._DASH_DURATION)
        caster.vel.x = caster.facing * self.DASH_SPEED
        caster.vel.y = -self.JUMP_HEIGHT
        caster.hitbox.arm(
            damage=(7.5 + 7.5 * caster.power) * caster.outgoing_damage_multiplier(),
            width=110, height=100, offset_x=60, offset_y=105,
            windup=0.05, active=self.SHEET_TIME,
            knockback=(520, -260), stun=0.75, unblockable=True,
            tags={"chomp"},
        )
        self.play_pose(caster, "rush", self.SHEET_TIME)
        caster.burst(14, S.P1_COLOR, 260)
