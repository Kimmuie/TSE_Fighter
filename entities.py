"""entities.py — วัตถุทั้งหมดที่อยู่ในสนาม (ใช้ SpriteSheet สำหรับตัวละคร)"""
from __future__ import annotations

import math
import os
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

import pygame

import settings as S
from component import Hitbox, InputController, State, StateMachine
from events import EventDispatcher, HitInfo
from ui import get_font, load_image

if TYPE_CHECKING:
    from combat import BattleWorld
    from skill import BaseSkill, SRS_Barrage


# ============================================================ Game objects
class GameObject(pygame.sprite.Sprite, ABC):
    def __init__(self, x: float, y: float, width: int, height: int, gravity: float = 0.0) -> None:
        super().__init__()
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.gravity = gravity
        self.on_ground = False
        self.rect = pygame.Rect(0, 0, width, height)
        self._sync_rect()

    def _sync_rect(self) -> None:
        self.rect.midbottom = (round(self.pos.x), round(self.pos.y))

    def set_x(self, x: float) -> None:
        self.pos.x = x
        self._sync_rect()

    def update(self, dt: float) -> None:
        if self.gravity:
            self.vel.y += self.gravity * dt
        self.pos += self.vel * dt
        if self.gravity and self.pos.y >= S.GROUND_Y:
            self.pos.y = S.GROUND_Y
            self.vel.y = 0.0
            self.on_ground = True
        elif self.gravity:
            self.on_ground = False
        self._sync_rect()

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        pass


class Particle(GameObject):
    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: tuple[int, int, int], life: float = 0.5, size: int = 6) -> None:
        super().__init__(x, y, size, size, gravity=900.0)
        self.vel.update(vx, vy)
        self._color = color
        self._life = self._max_life = life
        self._size = size

    def update(self, dt: float) -> None:
        super().update(dt)
        self._life -= dt
        if self._life <= 0:
            self.kill()

    def draw(self, surface: pygame.Surface) -> None:
        k = max(0.0, self._life / self._max_life)
        s = max(1, int(self._size * k) + 1)
        pygame.draw.rect(surface, self._color, (self.rect.centerx - s // 2, self.rect.centery - s // 2, s, s))


class FloatingText(GameObject):
    def __init__(self, text: str, x: float, y: float, color: tuple[int, int, int], life: float = 0.9) -> None:
        super().__init__(x, y, 1, 1)
        self.vel.update(0, -55)
        self._img = get_font(14).render(text, True, color)
        self._life = self._max_life = life

    def update(self, dt: float) -> None:
        super().update(dt)
        self._life -= dt
        if self._life <= 0:
            self.kill()

    def draw(self, surface: pygame.Surface) -> None:
        img = self._img.copy()
        img.set_alpha(int(255 * max(0.0, self._life / self._max_life)))
        surface.blit(img, img.get_rect(center=self.rect.midbottom))


class SmokeScreen(GameObject):
    def __init__(self, owner: "Fighter", radius: int = 150) -> None:
        super().__init__(owner.pos.x, owner.pos.y, radius * 2, radius)
        self._owner = owner
        self._radius = radius
        self._puffs = [(random.uniform(-0.7, 0.7), random.uniform(0.0, 1.0), random.uniform(0.25, 0.5),
                        random.uniform(0.6, 1.6), random.uniform(0, 6.28)) for _ in range(14)]
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        self.pos.update(self._owner.pos.x, S.GROUND_Y)
        self._sync_rect()
        if not self._owner.has_status("veiled"):
            self.kill()

    def draw(self, surface: pygame.Surface) -> None:
        r = self._radius
        layer = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for ox, oy, size, speed, phase in self._puffs:
            cx = r + ox * r + math.sin(self._t * speed + phase) * 10
            cy = r * 2 - 40 - oy * 150 + math.cos(self._t * speed + phase) * 6
            pygame.draw.circle(layer, (60, 55, 75, 105), (int(cx), int(cy)), int(r * size))
        surface.blit(layer, (self.rect.centerx - r, S.GROUND_Y - r * 2))


# ============================================================ Projectiles
class Projectile(GameObject):

    def __init__(self, owner: "Fighter", x: float, y: float, vx: float, vy: float,
                 damage: float, lifespan: float = 1.6, size: tuple[int, int] = (30, 8),
                knockback: tuple[float, float] = (0, 0),
                stun: float = 0.0) -> None:
        super().__init__(x, y, size[0], size[1])
        self.owner = owner
        self.vel.update(vx, vy)
        self.damage = damage
        self._life = lifespan
        self.knockback = knockback
        self.stun = stun

    def update(self, dt: float) -> None:
        super().update(dt)
        self._life -= dt
        if self._life <= 0 or not S.ARENA.inflate(80, 200).colliderect(self.rect):
            self.kill()

    def build_hit(self) -> HitInfo:
        return HitInfo(attacker=self.owner, damage=self.damage,
                       knockback=pygame.Vector2(self.knockback),
                       direction=1 if self.vel.x >= 0 else -1, stun=self.stun)

    def on_hit(self, target: "Fighter") -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, self.owner.color, self.rect)


class SpriteProjectile(Projectile):

    def __init__(self, owner: "Fighter", x: float, y: float, vx: float, vy: float, damage: float,
                 sprite: str, lifespan: float = 1.2, size: tuple[int, int] = (120, 70),
                 knockback: tuple[float, float] = (0, 0),
                 stun: float = 0.0) -> None:
        super().__init__(owner, x, y, vx, vy, damage, lifespan, size, knockback, stun)
        self._img = load_image(os.path.join(S.IMAGE_DIR, sprite), size)

    def draw(self, surface: pygame.Surface) -> None:
        img = pygame.transform.flip(self._img, True, False) if self.vel.x < 0 else self._img
        surface.blit(img, img.get_rect(center=self.rect.center))


class SoundwaveProjectile(SpriteProjectile):
    pass


class QuakeProjectile(SpriteProjectile):
    pass


class SparkProjectile(SpriteProjectile):
    pass


class SRSDocumentProjectile(SpriteProjectile):
    SPEED = 850.0

    def __init__(self, owner: "Fighter", skill: "SRS_Barrage", x: float, y: float, direction: int,
            damage: float, sprite: str, lifespan: float = 1.2,
            size: tuple[int, int] = (120, 70), vy: float = 0.0, 
            knockback: tuple[float, float] = (0, 0),
            stun: float = 0.0) -> None:
        super().__init__(owner, x, y, direction * self.SPEED, vy, damage, sprite, lifespan, size, knockback, stun)
        self.skill = skill

    def on_hit(self, target: "Fighter") -> None:
        self.skill.mark_target(target)


# ============================================================ Fighters
class Fighter(GameObject):
    NAME = "FIGHTER"
    TITLE = ""
    BASE_STATS: dict[str, int] = {"PWR": 50, "DEF": 50, "SPD": 50}
    SIZE = (70, 170)
    SHEET_PATH = "assets/emptyImage.png"
    PORTRAIT_PATH = "assets/emptyImage.png"
    PLAYABLE = True

    POSES = ("idle", "walk", "attack", "jumpattack", "guard", "jump", "hit", "ko")
    ATTACK_POSES = frozenset({"attack", "rush", "throw", "cast"})
    SHEET_COLUMNS = 4
    FRAME_TIME = 0.12

    # สีวงแหวนใต้เท้าของแต่ละสถานะ (สถานะที่ไม่อยู่ในรายการใช้สีเทา)
    STATUS_COLORS: dict[str, tuple[int, int, int]] = {
        "marked": S.PURPLE,
        "veiled": S.WHITE,
        "kinetic": S.BLUE,
        "creatine": S.RED,
    }
    DEFAULT_STATUS_COLOR = (190, 190, 190)

    def __init__(self, color: tuple[int, int, int], controller: InputController,
                 dispatcher: EventDispatcher, tag: str = "1P", x: float = 300.0, facing: int = 1) -> None:
        super().__init__(x, S.GROUND_Y, self.SIZE[0], self.SIZE[1], gravity=S.GRAVITY)
        self.color = color
        self.tag = tag
        self.controller = controller
        self.dispatcher = dispatcher
        self.facing = 1 if facing >= 0 else -1
        self.input_enabled = True
        self.opponent: Optional["Fighter"] = None
        self.world: Optional["BattleWorld"] = None

        self._hp = S.MAX_HP
        self._energy = S.START_ENERGY
        self._stamina = S.MAX_STAMINA
        self._status: dict[str, float] = {}
        self._blocking = False
        self._pose = "idle"
        self._pose_time = 0.0
        self._pose_len = 0.0
        self._pose_frames: Optional[list[pygame.Surface]] = None
        self._frame = 0
        self._frame_timer = 0.0

        self.state_machine = StateMachine()
        self.hitbox = Hitbox()
        self.skills: list["BaseSkill"] = self.create_skills()
        for i, skill in enumerate(self.skills, start=1):
            skill.bind(controller.label(f"skill{i}"))
            skill.load_sprite()

        self._frames = self._slice_sheet(load_image(self.SHEET_PATH))

    @abstractmethod
    def create_skills(self) -> list["BaseSkill"]:
        pass

    def _slice_sheet(self, sheet: pygame.Surface) -> dict[str, list[pygame.Surface]]:
        fw = sheet.get_width() // self.SHEET_COLUMNS
        fh = sheet.get_height() // len(self.POSES)
        return {
            pose: [sheet.subsurface(pygame.Rect(col * fw, row * fh, fw, fh)).copy()
                   for col in range(self.SHEET_COLUMNS)]
            for row, pose in enumerate(self.POSES)
        }

    # ------------------------------------------------------------ resources / stats
    @staticmethod
    def _clamp(value: float, upper: float) -> float:
        return max(0.0, min(upper, float(value)))

    @property
    def hp(self) -> float:
        return self._hp

    @hp.setter
    def hp(self, value: float) -> None:
        self._hp = self._clamp(value, S.MAX_HP)

    @property
    def energy(self) -> float:
        return self._energy

    @energy.setter
    def energy(self, value: float) -> None:
        self._energy = self._clamp(value, S.MAX_ENERGY)

    @property
    def stamina(self) -> float:
        return self._stamina

    @stamina.setter
    def stamina(self, value: float) -> None:
        self._stamina = self._clamp(value, S.MAX_STAMINA)

    @property
    def power(self) -> float:
        return self.BASE_STATS["PWR"] / 100.0

    @property
    def defense(self) -> float:
        return self.BASE_STATS["DEF"] / 100.0

    @property
    def speed(self) -> float:
        return self.BASE_STATS["SPD"] / 100.0

    @property
    def stats_percent(self) -> dict[str, int]:
        return dict(self.BASE_STATS)

    @property
    def is_ko(self) -> bool:
        return self.state_machine.state == State.KO

    # ------------------------------------------------------------ hooks (ตัวละครแต่ละตัว override ได้)
    def modify_incoming_damage(self, damage: float, hit: HitInfo, blocked: bool) -> float:
        return damage

    def outgoing_damage_multiplier(self) -> float:
        return 1.0

    @property
    def attack_speed(self) -> float:
        return 1.0

    @property
    def move_speed_multiplier(self) -> float:
        return 1.0

    # ------------------------------------------------------------ status
    def add_status(self, name: str, duration: float) -> None:
        self._status[name] = max(self._status.get(name, 0.0), duration)

    def has_status(self, name: str) -> bool:
        return self._status.get(name, 0.0) > 0.0

    def remove_status(self, name: str) -> None:
        self._status.pop(name, None)

    # ------------------------------------------------------------ animation / effects
    def play_pose(self, pose: str, length: float,
                  frames: Optional[list[pygame.Surface]] = None) -> None:
        self._pose, self._pose_time, self._pose_len = pose, 0.0, length
        self._pose_frames = frames
        self._frame = 0
        self._frame_timer = 0.0

    def burst(self, count: int, color: Optional[tuple[int, int, int]] = None, speed: float = 260.0) -> None:
        if self.world is not None:
            self.world.spawn_particles(self.rect.centerx, self.rect.centery, color or self.color, count, speed)

    def reset(self, x: float, facing: int) -> None:
        self.hp = S.MAX_HP
        self.energy = S.START_ENERGY
        self.stamina = S.MAX_STAMINA
        self._status.clear()
        self._blocking = False
        self.pos.update(x, S.GROUND_Y)
        self.vel.update(0, 0)
        self.facing = facing
        self.hitbox.clear()
        self.state_machine.change(State.IDLE)
        self.play_pose("idle", 0.0)
        self.input_enabled = True
        for skill in self.skills:
            skill.reset()
        self._sync_rect()

    # ------------------------------------------------------------ input / actions
    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.input_enabled or self.is_ko:
            return
        action = self.controller.action_for_event(event)
        if action is not None:
            self.perform(action)

    def perform(self, action: str) -> None:
        if action == "jump" and any(skill.on_jump(self) for skill in self.skills):
            return
        if not self.state_machine.can_act:
            return
        if action == "jump" and self.on_ground:
            self.vel.y = -950.0
            self.on_ground = False
        elif action == "attack":
            self.basic_attack()
        elif action.startswith("skill"):
            idx = int(action[5:]) - 1
            if 0 <= idx < len(self.skills):
                self.skills[idx].try_cast(self, self.opponent)

    def basic_attack(self) -> None:
        if self.stamina < 8:
            return
        self.stamina -= 8
        spd = self.attack_speed
        self.state_machine.change(State.ATTACK, lock=0.32 / spd)
        self.hitbox.arm(damage=4 + 6 * self.power, width=84, height=54, offset_x=58, offset_y=112,
                        windup=0.07 / spd, active=0.12, knockback=(260, -120), stun=0.28)
        self.play_pose("attack", 0.25 / spd)

    def _handle_held_input(self, dt: float) -> None:
        self._blocking = False
        sm = self.state_machine
        if not sm.can_act:
            return
        if not self.input_enabled:
            if self.on_ground:
                self.vel.x = 0
                sm.locomote(State.IDLE)
            return
        pressed = pygame.key.get_pressed()
        ctrl = self.controller
        axis = int(ctrl.is_held("right", pressed)) - int(ctrl.is_held("left", pressed))
        if ctrl.is_held("block", pressed) and self.on_ground and self.stamina > 1:
            self._blocking = True
            axis = 0
            self.stamina -= S.BLOCK_DRAIN * dt
        speed = (200 + 180 * self.speed) * self.move_speed_multiplier
        if self.on_ground:
            self.vel.x = axis * speed
            sm.locomote(State.WALK if axis else State.IDLE)
        else:
            if axis:
                self.vel.x = axis * speed * 0.85
            sm.locomote(State.JUMP)

    # ------------------------------------------------------------ update
    def update(self, dt: float) -> None:
        self.state_machine.update(dt)
        self._tick_animation(dt)
        self._tick_status(dt)

        if self.is_ko:
            self.vel.x *= 0.02 ** dt
            super().update(dt)
            self._handle_walls()
            return

        for skill in self.skills:
            skill.update(dt)
        self.energy += S.ENERGY_REGEN * dt
        self.stamina += S.STAMINA_REGEN * dt
        self._handle_held_input(dt)
        self.hitbox.update(dt)
        if not self.state_machine.can_act and self.on_ground:
            self.vel.x *= 0.03 ** dt
        super().update(dt)
        self._handle_walls()
        if self.state_machine.can_act and self.opponent is not None:
            self.facing = 1 if self.opponent.pos.x >= self.pos.x else -1

    def _tick_animation(self, dt: float) -> None:
        self._pose_time += dt
        self._frame_timer += dt
        while self._frame_timer >= self.FRAME_TIME:
            self._frame_timer -= self.FRAME_TIME
            last = self.SHEET_COLUMNS - 1
            self._frame = min(self._frame + 1, last) if self.is_ko else (self._frame + 1) % self.SHEET_COLUMNS
        if self._pose_time > self._pose_len:
            self._pose = "idle"
            self._pose_frames = None

    def _tick_status(self, dt: float) -> None:
        for name in list(self._status):
            self._status[name] -= dt
            if self._status[name] <= 0:
                del self._status[name]

    def _handle_walls(self) -> None:
        left, right = S.ARENA.left + 8, S.ARENA.right - 8
        if self.rect.left < left:
            self.pos.x += left - self.rect.left
        elif self.rect.right > right:
            self.pos.x -= self.rect.right - right
        self._sync_rect()

    # ------------------------------------------------------------ damage
    def take_hit(self, hit: HitInfo) -> bool:
        if self.is_ko:
            return False
        blocked = self._blocking and not hit.unblockable
        damage = hit.damage * (1.35 - 0.6 * self.defense)
        if blocked:
            damage *= 0.25
        damage = max(0.0, self.modify_incoming_damage(damage, hit, blocked))
        self.hp -= damage
        self.dispatcher.emit("on_hit", attacker=hit.attacker, target=self, damage=damage,
                             blocked=blocked, hit=hit)
        if blocked:
            self.vel.x = hit.direction * 120.0
        else:
            self.vel.update(hit.knockback.x * hit.direction, hit.knockback.y)
            if hit.knockback.y < 0:
                self.on_ground = False
            self.state_machine.change(State.HIT, lock=hit.stun)
            self.hitbox.clear()
            self.play_pose("hit", hit.stun)
        if self.hp <= 0:
            self._die(hit.attacker)
        return True

    def _die(self, killer: "Fighter") -> None:
        if self.is_ko:
            return
        self.hp = 0.0
        self._blocking = False
        self.hitbox.clear()
        self.state_machine.change(State.KO, lock=999.0)
        self.vel.update(-self.facing * 250.0, -500.0)
        self.on_ground = False
        self.play_pose("ko", 2.0)
        self.dispatcher.emit("on_ko", loser=self, winner=killer)

    # ------------------------------------------------------------ drawing
    def _pose_key(self) -> str:
        if self.is_ko:
            return "ko"
        if self._pose in self.ATTACK_POSES:
            return "attack" if self.on_ground else "jumpattack"
        if self._pose == "hit":
            return "hit"
        if self._blocking:
            return "guard"
        if not self.on_ground:
            return "jump"
        if self.state_machine.state == State.WALK:
            return "walk"
        return "idle"

    def _current_frame(self) -> Optional[pygame.Surface]:
        if self._pose_frames and self._pose != "idle" and not self.is_ko:
            frames = self._pose_frames
            if self._pose_len > 0:
                idx = min(int(self._pose_time / self._pose_len * len(frames)), len(frames) - 1)
                return frames[idx]
        else:
            frames = self._frames.get(self._pose_key(), self._frames["idle"])
        return frames[self._frame % len(frames)] if frames else None

    def draw(self, surface: pygame.Surface) -> None:
        shadow = pygame.Rect(0, 0, 90, 14)
        shadow.center = (self.rect.centerx, S.GROUND_Y - 17)
        pygame.draw.ellipse(surface, (31, 31, 31), shadow)

        pulse = int((math.sin(pygame.time.get_ticks() / 100.0) + 1) * 1.5)
        for i, name in enumerate(n for n, left in self._status.items() if left > 0.0):
            ring = shadow.inflate(18 + i * 14 + pulse * 2, 8 + i * 7 + pulse)
            pygame.draw.ellipse(surface, self.STATUS_COLORS.get(name, self.DEFAULT_STATUS_COLOR), ring, 2)

        frame = self._current_frame()
        if frame is None:
            return
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        if self.has_status("veiled"):
            frame = frame.copy()
            frame.set_alpha(80)
        surface.blit(frame, frame.get_rect(midbottom=(self.rect.centerx, self.rect.bottom)))

        img = get_font(11).render(f"{self.tag} • {self.NAME}", True, S.DARK)
        r = img.get_rect(center=(self.rect.centerx, self.rect.bottom - 190)).inflate(12, 6)
        pygame.draw.rect(surface, self.color, r)
        surface.blit(img, img.get_rect(center=r.center))


# ============================================================ Roster
class Jack(Fighter):
    NAME = "T. Jack"
    TITLE = "God of Python"
    BASE_STATS = {"PWR": 60, "DEF": 60, "SPD": 95}
    SHEET_PATH = "assets/jack_sheet.png"
    PORTRAIT_PATH = "assets/jack_portrait.png"

    def create_skills(self) -> list["BaseSkill"]:
        from skill import GhostFrenzy, PacMan_Chomp, Power_Pellet
        return [PacMan_Chomp(), Power_Pellet(), GhostFrenzy()]

    @property
    def attack_speed(self) -> float:
        return 1.5 if self.has_status("kinetic") else 1.0

    @property
    def move_speed_multiplier(self) -> float:
        return 1.45 if self.has_status("kinetic") else 1.0


class Art(Fighter):
    NAME = "T. Art"
    TITLE = "The Toxic Speaker"
    BASE_STATS = {"PWR": 95, "DEF": 60, "SPD": 75}
    SHEET_PATH = "assets/art_sheet.png"
    PORTRAIT_PATH = "assets/art_portrait.png"

    def create_skills(self) -> list["BaseSkill"]:
        from skill import CriticalRoast, EmotionalDamage, ShutUp
        return [CriticalRoast(), ShutUp(), EmotionalDamage()]


class Pao(Fighter):
    NAME = "T. Pao"
    TITLE = "The CPU Destroyer"
    BASE_STATS = {"PWR": 100, "DEF": 100, "SPD": 40}
    SHEET_PATH = "assets/pao_sheet.png"
    PORTRAIT_PATH = "assets/pao_portrait.png"

    def create_skills(self) -> list["BaseSkill"]:
        from skill import BlueScreen_Crash, CPUSmash, OverclockCharge
        return [CPUSmash(), OverclockCharge(), BlueScreen_Crash()]


class Piya(Fighter):
    NAME = "T. Piya"
    TITLE = "The Missing Teacher"
    BASE_STATS = {"PWR": 75, "DEF": 55, "SPD": 100}
    SHEET_PATH = "assets/piya_sheet.png"
    PORTRAIT_PATH = "assets/piya_portrait.png"

    def create_skills(self) -> list["BaseSkill"]:
        from skill import ShadowVeil, SRS_Barrage, SuckerPunch
        return [SRS_Barrage(), ShadowVeil(), SuckerPunch()]

    def modify_incoming_damage(self, damage: float, hit: HitInfo, blocked: bool) -> float:
        if self.has_status("veiled"):
            self.burst(6, S.RED, 200)
            return 0
        return damage
    
    def outgoing_damage_multiplier(self) -> float:
        return 0.8 if self.has_status("veiled") else 1.0


class Oat(Fighter):
    NAME = "Oat"
    TITLE = "The Body Builder"
    BASE_STATS = {"PWR": 85, "DEF": 80, "SPD": 50}
    SHEET_PATH = "assets/oat_sheet.png"
    PORTRAIT_PATH = "assets/oat_portrait.png"

    def create_skills(self) -> list["BaseSkill"]:
        from skill import Beastquake, CreatineShake, DoubleMuscle_Rush
        return [DoubleMuscle_Rush(), CreatineShake(), Beastquake()]

    def modify_incoming_damage(self, damage: float, hit: HitInfo, blocked: bool) -> float:
        if not self.has_status("creatine"):
            return damage
        if blocked:
            self.burst(6, S.WHITE, 200)
            return 0.1
        self.burst(6, S.RED, 200)
        return damage * 0.75

    def outgoing_damage_multiplier(self) -> float:
        return 1.75 if self.has_status("creatine") else 1.0


class Jin(Fighter):
    NAME = "Jinn"
    TITLE = "The Hole Penetration"
    BASE_STATS = {"PWR": 90, "DEF": 65, "SPD": 100}
    SHEET_PATH = "assets/jinn_sheet.png"
    PORTRAIT_PATH = "assets/jinn_portrait.png"

    def create_skills(self) -> list["BaseSkill"]:
        from skill import BottleBomb, GangsterCharm, HellRiderRush
        return [BottleBomb(), GangsterCharm(), HellRiderRush()]


class Night(Fighter):
    NAME = "Night"
    TITLE = "Coming Soon!"
    BASE_STATS = {"PWR": 100, "DEF": 100, "SPD": 100}
    PLAYABLE = False

    def create_skills(self) -> list["BaseSkill"]:
        return []


class Poom(Fighter):
    NAME = "Poom"
    TITLE = "Coming Soon!"
    BASE_STATS = {"PWR": 90, "DEF": 65, "SPD": 100}
    PLAYABLE = False

    def create_skills(self) -> list["BaseSkill"]:
        return []
