"""skill.py — สกิลทั้งหมดของ Kai และ Nyx"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pygame

import settings as S
from component import State
from entities import Fighter, FloatingText, KunaiProjectile, SmokeScreen, SoundwaveProjectile
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
    COOLDOWN = 5.0
    ENERGY_COST = 15.0
    ICON = "skill/jack_iconskill_1.png"
    DASH_SPEED = 1200.0
    DASH_TIME = 0.30
    SHEET_PATH = "imageFolder/jack_skill1.png"
    SHEET_TIME = 0.4

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
    COOLDOWN = 12.0
    ENERGY_COST = 20.0
    ICON = "skill/jack_iconskill_2.png"
    BUFF_TIME = 3.5
    HEAL = 8.0
    SHEET_PATH = "imageFolder/jack_skill2.png"
    SHEET_TIME = 1.2

    def execute(self, caster: Fighter, target: Fighter) -> None:
        # ใช้ status "kinetic" เดิม เพื่อให้โบนัสของ Jack (attack_speed,
        # move_speed_multiplier, ดูดซับดาเมจตอนการ์ด) ทำงานต่อเนื่อง
        caster.add_status("kinetic", self.BUFF_TIME)
        caster.hp += self.HEAL
        caster.stamina += self.ENERGY_COST
        caster.state_machine.change(State.CAST, lock=1.2)
        self.play_pose(caster, "cast", 1.2)
        caster.burst(20, S.WHITE, 240)


class GhostFrenzy(BaseSkill):
    NAME = "GHOST FRENZY"
    DESCRIPTION = "Devastating multi-hit bionic combo executing unblockable finisher damage."
    COOLDOWN = 10.0
    ENERGY_COST = 50.0
    ICON = "skill/jack_iconskill_3.png"
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

class CriticalRoast(BaseSkill):
    NAME = "CRITICAL ROAST"
    DESCRIPTION = "ยิงคลื่นเสียงจากคำพูดโจมตีศัตรู"
    COOLDOWN = 5.0
    ENERGY_COST = 25.0
    ICON = "skill/art_iconskill_1.png"
    SHEET_PATH = "imageFolder/art_skill1.png"
    SHEET_TIME = 0.3

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.3)
        self.play_pose(caster, "throw", 0.3)

        mult = caster.outgoing_damage_multiplier()

        # Fire 3 soundwaves at different angles
        for vy in (-200.0, 0.0, 200.0):
            soundwave = SoundwaveProjectile(
                caster,
                caster.rect.centerx,
                caster.rect.centery,
                vx=500 * caster.facing,
                vy=vy,
                damage=4.5 * mult,
                sprite="sound1_projectile.png",
                lifespan=0.5,
                size=(120, 70)
            )

            if caster.world is not None:
                caster.world.spawn_projectile(soundwave)

class ShutUp(BaseSkill):
    NAME = "Shut Up!"
    DESCRIPTION = "ตะโกนผลักศัตรูออกไป"
    COOLDOWN = 4.0
    ENERGY_COST = 20.0
    ICON = "skill/art_iconskill_2.png"
    SHEET_PATH = "imageFolder/art_skill2.png"
    SHEET_TIME = 0.35

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.35)
        caster.vel.x = -850 * caster.facing
        # คลื่นเสียง: hitbox กว้างด้านหน้า ดาเมจต่ำแต่ผลักแรง ป้องกันไม่ได้
        caster.hitbox.arm(
            damage=(3 + 3 * caster.power) * caster.outgoing_damage_multiplier(),
            width=160, height=140, offset_x=90, offset_y=100,
            windup=0.05, active=0.15,
            knockback=(1100, -700), unblockable=True,
            stun=0.5, tags={"shout"},
        )
        self.play_pose(caster, "cast", 0.35)
        caster.burst(22, S.WHITE, 340)


class EmotionalDamage(BaseSkill):
    NAME = "EMOTIONAL DAMAGE"
    DESCRIPTION = "ปล่อยคำพูดทำลายจิตใจพร้อมคลื่นเสียงรุนแรง"
    COOLDOWN = 8.0
    ENERGY_COST = 35.0
    ICON = "skill/art_iconskill_3.png"
    WAVE_SPEED = 700
    SHEET_PATH = "imageFolder/art_skill3.png"
    SHEET_TIME = 0.45

    def execute(self, caster: Fighter, target: Fighter) -> None:
        mult = caster.outgoing_damage_multiplier()
        caster.state_machine.change(State.CAST, lock=0.45)
        caster.vel.x = 0
        self.play_pose(caster, "cast", 0.45)

        # 1 คลื่นเสียงระยะประชิดหน้าตัวละคร
        caster.hitbox.arm(
            damage=(5 + 5 * caster.power) * mult,
            width=120, height=60, offset_x=70, offset_y=100,
            windup=0.1, active=0.15,
            knockback=(850, -200), unblockable=True,
            stun=0.5, tags={"shout"},
        )

        # 2 คลื่นเสียงลูกใหญ่พุ่งออกไปไกล
        soundwave = SoundwaveProjectile(
            caster,
            caster.rect.centerx,
            caster.rect.centery,
            vx=self.WAVE_SPEED * caster.facing,
            vy=0,
            damage=22.5 * mult,
            sprite="sound2_projectile.png",
            lifespan=1.5,
            size=(120, 60)
        )

        if caster.world is not None:
            caster.world.spawn_projectile(soundwave)
        
        #caster.world.spawn_projectile(wave)
        # ข้อความคำพูดลอยขึ้นเหนือหัว
        caster.world.spawn_effect(
            FloatingText("EMOTIONAL DAMAGE!", caster.rect.centerx,
                            caster.rect.top - 20, S.WHITE, 1.2)
        )

        caster.burst(30, S.WHITE, 380)


# ================================================================== Pao
class CPUSmash(BaseSkill):
    NAME = "CPU SMASH"
    DESCRIPTION = "ฟาด CPU ยักษ์ใส่ศัตรูอย่างแรง ทะลุการ์ดและกระแทกถอยหลัง"
    COOLDOWN = 9.0
    ENERGY_COST = 30.0
    ICON = "skill/pao_iconskill_1.png"
    SHEET_PATH = "imageFolder/cpu_smash_sheet.png"   # sprite sheet 1 แถว 4 เฟรม (ไม่ใส่ = ใช้ท่าต่อย)

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.6)
        caster.vel.x = 0
        caster.hitbox.arm(
            damage=(12 + 12 * caster.power) * caster.outgoing_damage_multiplier(),
            width=170, height=170, offset_x=80, offset_y=120,
            windup=0.25, active=0.2,
            knockback=(350, -500), unblockable=True,
            stun=0.7, tags={"cpu_smash"},
        )
        self.play_pose(caster, "cast", 0.6)
        caster.burst(20, S.WHITE, 320)

class OverclockCharge(BaseSkill):
    NAME = "Overclock Charge"
    DESCRIPTION = "เพิ่มพลังแล้วพุ่งชนศัตรู"
    COOLDOWN = 8.0
    ENERGY_COST = 25.0
    ICON = "skill/pao_iconskill_2.png"
    SHEET_PATH = None            # ใส่ path ของ sprite sheet ถ้ามี (ไม่ใส่ = ใช้ท่าต่อย)
    BUFF_STATUS = "kinetic"      # status ที่ให้โบนัสความเร็ว (Jack ใช้อยู่)
    BUFF_TIME = 4.0
    CHARGE_TIME = 0.4           # ช่วงชาร์จก่อนพุ่ง
    DASH_TIME = 0.35
    DASH_SPEED = 1000.0

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._charge_left = 0.0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        # จังหวะ 1: ชาร์จพลัง + บัฟ
        self._caster, self._charge_left = caster, self.CHARGE_TIME
        caster.add_status(self.BUFF_STATUS, self.BUFF_TIME)
        caster.vel.x = 0
        caster.state_machine.change(State.CAST, lock=self.CHARGE_TIME + self.DASH_TIME + 0.1)
        self.play_pose(caster, "cast", self.CHARGE_TIME)
        caster.burst(24, S.WHITE, 300)

    def update(self, dt: float) -> None:
        super().update(dt)
        c = self._caster
        if c is None or self._charge_left <= 0:
            return
        if c.is_ko or c.state_machine.state == State.HIT:   # ถูกขัดจังหวะ
            self._charge_left = 0.0
            return
        self._charge_left -= dt
        if self._charge_left > 0:
            return
        # จังหวะ 2: พุ่งชน
        c.vel.x = c.facing * self.DASH_SPEED
        c.hitbox.arm(
            damage=(13 + 13 * c.power) * c.outgoing_damage_multiplier() * 1.3,
            width=120, height=140, offset_x=60, offset_y=105,
            windup=0.0, active=self.DASH_TIME,
            knockback=(850, -500), stun=0.6,
            tags={"overclock"},
        )
        self.play_pose(c, "rush", self.DASH_TIME)
        c.burst(20, S.P1_COLOR, 340)

    def reset(self) -> None:
        super().reset()
        self._charge_left = 0.0

class BlueScreen_Crash(BaseSkill):
    NAME = "Blue Screen Crash"
    DESCRIPTION = "ทุบพื้นปล่อยคลื่นกระแทกวงกว้าง"
    COOLDOWN = 8.0
    ENERGY_COST = 30.0
    ICON = "skill/pao_iconskill_3.png"
    SHEET_PATH = None              # ใส่ path ของ sprite sheet ถ้ามี (ไม่ใส่ = ใช้ท่าต่อย)
    BLUE = (40, 90, 220)           # สีฟ้าแบบ Blue Screen

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.7)
        caster.vel.x = 0
        # คลื่นกระแทกวงกว้าง: hitbox กว้างครอบทั้งสองข้างของตัวละคร ต่ำติดพื้น
        caster.hitbox.arm(
            damage=(13 + 13 * caster.power) * caster.outgoing_damage_multiplier(),
            width=550, height=70, offset_x=0, offset_y=50,
            windup=0.3, active=0.15,
            knockback=(520, -420), unblockable=True,
            stun=1.0, tags={"blue_screen"},
        )
        self.play_pose(caster, "attack", 0.7)
        caster.burst(14, self.BLUE, 220)
        # คลื่นฝุ่นริมพื้นสองฝั่ง
        w = caster.world
        if w is not None:
            for side in (-1, 1):
                for i in range(1, 5):
                    w.spawn_particles(caster.pos.x + side * i * 70, S.GROUND_Y,
                                      self.BLUE, 6, 260)


# ================================================================== Piya
class PhantomDash(BaseSkill):
    NAME = "PHANTOM DASH"
    DESCRIPTION = "Phases through projectiles with brief invulnerability frames, emerging behind the foe."
    COOLDOWN = 3.0
    ENERGY_COST = 15.0
    ICON = "skill/piya_iconskill_1.png"

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

class SuckerPunch(BaseSkill):
    NAME = "Sucker Punch"
    DESCRIPTION = "หายตัวหลบแล้วสวนกลับ"
    COOLDOWN = 8.0
    ENERGY_COST = 30.0
    ICON = "skill/piya_iconskill_2.png"
    SHEET_PATH = None            # ใส่ path ของ sprite sheet ถ้ามี (ไม่ใส่ = ใช้ท่าต่อย)
    VANISH_TIME = 0.4            # ช่วงหายตัว (อมตะ)
    COUNTER_BONUS = 1.5          # ตัวคูณดาเมจเมื่อศัตรูกำลังโจมตีตอนโผล่

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._target: Optional[Fighter] = None
        self._vanish_left = 0.0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        # จังหวะ 1: หายตัว (โปร่งใส + อมตะ)
        self._caster, self._target, self._vanish_left = caster, target, self.VANISH_TIME
        caster.vel.x = 0
        caster.add_status("invulnerable", self.VANISH_TIME + 0.1)
        caster.state_machine.change(State.CAST, lock=self.VANISH_TIME + 0.4)
        self.play_pose(caster, "cast", self.VANISH_TIME)
        caster.burst(20, S.P2_COLOR, 300)

    def update(self, dt: float) -> None:
        super().update(dt)
        c, t = self._caster, self._target
        if c is None or t is None or self._vanish_left <= 0:
            return
        if c.is_ko or t.is_ko:
            self._vanish_left = 0.0
            return
        self._vanish_left -= dt
        if self._vanish_left > 0:
            return
        # จังหวะ 2: โผล่ด้านหลังศัตรูแล้วสวนกลับ
        old = c.rect.center
        side = 1 if t.pos.x >= c.pos.x else -1
        new_x = t.pos.x + side * 95
        new_x = max(S.ARENA.left + 50, min(S.ARENA.right - 50, new_x))
        c.set_x(new_x)
        c.facing = -side
        c.vel.x = 0
        counter = t.state_machine.state in (State.ATTACK, State.CAST)
        mult = self.COUNTER_BONUS if counter else 1.0
        c.hitbox.arm(
            damage=(8 + 8 * c.power) * c.outgoing_damage_multiplier() * mult,
            width=100, height=120, offset_x=55, offset_y=105,
            windup=0.05, active=0.15,
            knockback=(450, -300), stun=0.7, unblockable=True,
            tags={"counter"},
        )
        self.play_pose(c, "attack", 0.3)
        if c.world is not None:
            c.world.spawn_particles(old[0], old[1], S.P2_COLOR, 18, 300)
        c.burst(18, S.WHITE if counter else S.P2_COLOR, 320)

    def reset(self) -> None:
        super().reset()
        self._vanish_left = 0.0

class ShadowVeil(BaseSkill):
    NAME = "SHADOW VEIL"
    DESCRIPTION = "Deploys a smoke screen that conceals hitboxes and guarantees critical counters."
    COOLDOWN = 12.0
    ENERGY_COST = 35.0
    ICON = "skill/piya_iconskill_3.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.add_status("veiled", 5.0)
        caster.state_machine.change(State.CAST, lock=0.3)
        caster.play_pose("cast", 0.3)
        caster.burst(24, (90, 90, 100), 200)
        if caster.world is not None:
            caster.world.spawn_effect(SmokeScreen(caster))


# ================================================================== Oat
class MusclePunch(BaseSkill):
    NAME = "Muscle Punch"
    DESCRIPTION = "ชกด้วยกล้ามแขนสุดทรงพลัง สร้างความเสียหายสูง"
    COOLDOWN = 7.0
    ENERGY_COST = 35.0
    ICON = "skill/oat_iconskill_1.png"
    SHEET_PATH = None  

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.7)
        caster.vel.x = caster.facing * 120.0     # ก้าวเข้าหาเล็กน้อยตอนชก
        caster.hitbox.arm(
            damage=(18 + 18 * caster.power) * caster.outgoing_damage_multiplier(),
            width=110, height=100, offset_x=65, offset_y=110,
            windup=0.3, active=0.15,
            knockback=(800, -250), stun=0.7,
            tags={"wall_bounce"},
        )
        self.play_pose(caster, "punch", 0.5)
        caster.burst(18, S.WHITE, 300)

class ProteinShake(BaseSkill):
    NAME = "Protein Shake"
    DESCRIPTION = "ดื่มเวย์เพิ่่มพลังโจมตีและฟื้นฟู HP"
    COOLDOWN = 6.0
    ENERGY_COST = 20.0
    ICON = "skill/oat_iconskill_2.png"
    BUFF_TIME = 5.0
    HEAL = 8.0
    SHEET_PATH = "imageFolder/jack_skill2.png"
    SHEET_TIME = 0.8

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.add_status("protein", self.BUFF_TIME)   # เพิ่มพลังโจมตีชั่วคราว
        caster.hp += self.HEAL                         # ฟื้นฟู HP
        caster.state_machine.change(State.CAST, lock=0.4)
        self.play_pose(caster, "cast", self.SHEET_TIME)
        caster.burst(20, S.WHITE, 240)

class BeastMode(BaseSkill):
    NAME = "Beast Mode"
    DESCRIPTION = "เกร็งกล้ามเนื้อเพิ่มพลัง และปล่อยหมัดคอมโบต่อเนื่อง"
    COOLDOWN = 12.0
    ENERGY_COST = 50.0
    ICON = "skill/oat_iconskill_3.png"
    SHEET_PATH = None            # ใส่ path ของ sprite sheet ถ้ามี (ไม่ใส่ = ใช้ท่าต่อย)
    BUFF_STATUS = "kinetic"      # โบนัสความเร็วโจมตี/เคลื่อนที่ของ Jack
    BUFF_TIME = 6.0
    HITS = 6
    INTERVAL = 0.11

    def __init__(self) -> None:
        super().__init__()
        self._caster: Optional[Fighter] = None
        self._remaining = 0
        self._timer = 0.0

    def execute(self, caster: Fighter, target: Fighter) -> None:
        total = self.HITS * self.INTERVAL
        self._caster, self._remaining = caster, self.HITS
        caster.add_status(self.BUFF_STATUS, self.BUFF_TIME)
        caster.vel.x = 0
        caster.state_machine.change(State.CAST, lock=total + 0.2)
        self.play_pose(caster, "rush", total)
        caster.burst(28, S.WHITE, 320)
        self._strike(caster)              # หมัดแรกออกทันที
        self._timer = self.INTERVAL       # หมัดต่อไปรอตามจังหวะ

    def _strike(self, c: Fighter) -> None:
        self._remaining -= 1
        final = self._remaining == 0
        mult = c.outgoing_damage_multiplier() * (2.0 if final else 1.0)
        c.hitbox.arm(
            damage=(2.5 + 2.5 * c.power) * mult,
            width=105, height=110, offset_x=60, offset_y=105,
            windup=0.0, active=0.1,
            knockback=(650, -400) if final else (80, -30),
            stun=0.55 if final else 0.2,
            tags={"wall_bounce"} if final else {"beast"},
        )
        c.vel.x = c.facing * (200.0 if final else 320.0)
        c.burst(6, S.P1_COLOR, 260)

    def update(self, dt: float) -> None:
        super().update(dt)
        c = self._caster
        if c is None or self._remaining <= 0:
            return
        if c.is_ko or c.state_machine.state == State.HIT:   # ถูกขัดจังหวะ
            self._remaining = 0
            return
        self._timer -= dt
        if self._timer > 0:
            return
        self._timer = self.INTERVAL
        self._strike(c)

    def reset(self) -> None:
        super().reset()
        self._remaining = 0


# ================================================================== Jin
class BottleBomb(BaseSkill):
    NAME = "Bottle Bomb"
    DESCRIPTION = "ปาขวดใส่ศัตรูจากระยะไกล สร้างความเสียหายและทำให้ชะงัก"
    COOLDOWN = 9.0
    ENERGY_COST = 30.0
    ICON = "skill/jinn_iconskill_1.png"
    SHEET_PATH = "imageFolder/bottle_bomb_sheet.png"   # sprite sheet 1 แถว 4 เฟรม
    FREEZE_TIME = 3.0
    MIN_RANGE = 150.0      # ระยะใกล้สุดที่ขวดตก
    MAX_RANGE = 650.0      # ระยะไกลสุดที่ปาถึง
    FLIGHT_BASE = 0.2      # เวลาลอยพื้นฐาน
    FLIGHT_SPEED = 1500.0  # ยิ่งไกล ยิ่งลอยนานขึ้น

    def execute(self, caster: Fighter, target: Fighter) -> None:
        # วัดระยะถึงศัตรู ณ ตอนปา แล้วให้ขวดตกตรงนั้น
        dist = abs(target.pos.x - caster.pos.x)
        dist = max(self.MIN_RANGE, min(self.MAX_RANGE, dist))
        flight = self.FLIGHT_BASE + dist / self.FLIGHT_SPEED

        caster.state_machine.change(State.CAST, lock=flight + 0.25)
        caster.vel.x = 0
        caster.hitbox.arm(
            damage=(4 + 4 * caster.power) * caster.outgoing_damage_multiplier(),
            width=160, height=120, offset_x=dist, offset_y=110,
            windup=flight, active=0.12,
            knockback=(0, 0), unblockable=True,
            stun=self.FREEZE_TIME, tags={"bottle"},
        )
        self.play_pose(caster, "throw", flight)
        caster.burst(10, S.WHITE, 220)

class MotorcycleRush(BaseSkill):
    NAME = "Motorcycle Rush"
    DESCRIPTION = "ขี่มอเตอร์ไซค์พุ่งชนศัตรูอย่างรวดเร็ว"
    COOLDOWN = 3.0
    ENERGY_COST = 15.0
    ICON = "skill/jinn_iconskill_2.png"
    DASH_SPEED = 1100.0
    DASH_TIME = 0.30
    SHEET_PATH = "imageFolder/jack_skill1.png"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=self.DASH_TIME + 0.15)
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

class GansterDrift(BaseSkill):
    NAME = "Ganster Drift"
    DESCRIPTION = "ดริฟต์มอเตอร์ไซค์เป็นวงกว้าง สร้างความเสียหายรอบตัวและกระแทกศัตรูกระเด็น"
    COOLDOWN = 8.0
    ENERGY_COST = 35.0
    ICON = "skill/jinn_iconskill_3.png"
    SHEET_PATH = "imageFolder/gangster_drift_sheet.png"   # sprite sheet 1 แถว 4 เฟรม (ไม่ใส่ = ใช้ท่าต่อย)

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.6)
        caster.vel.x = caster.facing * 220.0      # ไถลไปข้างหน้าเล็กน้อยตอนดริฟต์
        # วงกว้างรอบตัว: ศูนย์กลางอยู่ที่ตัวละคร (offset_x=0)
        caster.hitbox.arm(
            damage=(9 + 9 * caster.power) * caster.outgoing_damage_multiplier(),
            width=420, height=150, offset_x=0, offset_y=110,
            windup=0.15, active=0.25,
            knockback=(800, -380), unblockable=True,
            stun=0.6, tags={"wall_bounce"},
        )
        self.play_pose(caster, "rush", 0.6)
        caster.burst(26, S.WHITE, 340)