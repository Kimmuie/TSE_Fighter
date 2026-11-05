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
    from skill import BaseSkill


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

    def update(self, dt: float, *args: object) -> None:
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

    def update(self, dt: float, *args: object) -> None:
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

    def update(self, dt: float, *args: object) -> None:
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
        super().__init__(owner.pos.x, owner.pos.y, radius * 2, radius, gravity=0.0)
        self._owner = owner
        self._radius = radius
        self._puffs = [(random.uniform(-0.7, 0.7), random.uniform(0.0, 1.0), random.uniform(0.25, 0.5),
                        random.uniform(0.6, 1.6), random.uniform(0, 6.28)) for _ in range(14)]
        self._t = 0.0

    def update(self, dt: float, *args: object) -> None:
        self._t += dt
        self.pos.update(self._owner.pos.x, S.GROUND_Y)
        self._sync_rect()
        if not self._owner.has_status("veiled"):
            self.kill()

    def draw(self, surface: Surface) -> None:
        r = self._radius
        layer = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for ox, oy, size, speed, phase in self._puffs:
            cx = r + ox * r + math.sin(self._t * speed + phase) * 10
            cy = r * 2 - 40 - oy * 150 + math.cos(self._t * speed + phase) * 6
            pygame.draw.circle(layer, (60, 55, 75, 105), (int(cx), int(cy)), int(r * size))
        surface.blit(layer, (self.rect.centerx - r, S.GROUND_Y - r * 2))


class Projectile(GameObject):
    def __init__(self, owner: "Fighter", x: float, y: float, vx: float, vy: float,
                 damage: float, lifespan: float = 1.6, size: tuple[int, int] = (30, 8)) -> None:
        super().__init__(x, y, size[0], size[1], gravity=0.0)
        self.owner = owner
        self.vel.update(vx, vy)
        self.damage = damage
        self._life = lifespan

    def update(self, dt: float, *args: object) -> None:
        super().update(dt)
        self._life -= dt
        if self._life <= 0 or not S.ARENA.inflate(80, 200).colliderect(self.rect):
            self.kill()

    def build_hit(self) -> HitInfo:
        return HitInfo(attacker=self.owner, damage=self.damage,
                       knockback=pygame.Vector2(160, -90),
                       direction=1 if self.vel.x >= 0 else -1, stun=0.2)

    def on_hit(self, target: "Fighter") -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, self.owner.color, self.rect)


class KunaiProjectile(Projectile):
    def __init__(self, *args: object, bleed_dps: float = 0.7, bleed_time: float = 4.0, **kw: object) -> None:
        super().__init__(*args, **kw)  # type: ignore[arg-type]
        self._bleed_dps = bleed_dps
        self._bleed_time = bleed_time
        self._img = load_image(os.path.join(S.IMAGE_DIR, "kunai.png"), (40, 16))

    def on_hit(self, target: "Fighter") -> None:
        if not target.is_blocking:
            target.apply_bleed(self._bleed_dps, self._bleed_time, self.owner)

    def draw(self, surface: pygame.Surface) -> None:
        img = self._img
        if self.vel.x < 0:
            img = pygame.transform.flip(img, True, False)
        surface.blit(img, img.get_rect(center=self.rect.center))


class BaseFighter(ABC):
    @abstractmethod
    def create_skills(self) -> list["BaseSkill"]:
        pass

    @abstractmethod
    def on_damage_taken(self, hit: HitInfo, damage: float) -> None:
        pass

    @abstractmethod
    def on_hit_landed(self, hit: HitInfo, target: "Fighter") -> None:
        pass


class Fighter(GameObject, BaseFighter):
    NAME = "FIGHTER"
    TITLE = ""
    BASE_STATS: dict[str, int] = {"PWR": 50, "DEF": 50, "SPD": 50}
    SIZE = (70, 170)
    SHEET_PATH = "imageFolder/emptyImage.png"

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

        self._stats = {k: self._validate_percent(v) for k, v in self.BASE_STATS.items()}
        self._hp = S.MAX_HP
        self._energy = 50.0
        self._stamina = S.MAX_STAMINA
        self._status: dict[str, float] = {}
        self._bleeds: list[list[object]] = []
        self._blocking = False
        self._bounce_window = 0.0
        self._pose = "idle"
        self._pose_time = 0.0
        self._pose_len = 0.0
        self._frame = 0
        self._frame_timer = 0.0
        self._pose_frames: Optional[list[pygame.Surface]] = None

        self.state_machine = StateMachine()
        self.hitbox = Hitbox()
        self.skills: list["BaseSkill"] = self.create_skills()
        for i, skill in enumerate(self.skills, start=1):
            skill.bind(f"skill{i}", controller.label(f"skill{i}"))

        self._sheet = load_image(self.SHEET_PATH)
        self._frames = self._slice_sheet()
        for skill in self.skills:
            skill.load_sprite()



    def _slice_sheet(self) -> dict[str, list[pygame.Surface]]:
        poses = [
            "idle",
            "walk",
            "attack",
            "jumpattack",
            "guard",
            "jump",
            "hit",
            "ko"
        ]

        frames = {}

        fw = self._sheet.get_width() // 4
        fh = self._sheet.get_height() // len(poses)

        for row, pose in enumerate(poses):
            frames[pose] = []

            for col in range(4):
                rect = pygame.Rect(
                    col * fw,
                    row * fh,
                    fw,
                    fh
                )

                frames[pose].append(
                    self._sheet.subsurface(rect).copy()
                )

        return frames


    def _validate_percent(self, value: float) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("stat must be a number")
        if not 0 <= value <= 100:
            raise ValueError("stat must be within 0..100")
        return float(value)

    def _clamp_resource(self, value: float, upper: float, name: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{name} must be a number")
        return max(0.0, min(upper, float(value)))

    @property
    def hp(self) -> float:
        return self._hp

    @hp.setter
    def hp(self, value: float) -> None:
        self._hp = self._clamp_resource(value, S.MAX_HP, "hp")

    @property
    def energy(self) -> float:
        return self._energy

    @energy.setter
    def energy(self, value: float) -> None:
        self._energy = self._clamp_resource(value, S.MAX_ENERGY, "energy")

    @property
    def stamina(self) -> float:
        return self._stamina

    @stamina.setter
    def stamina(self, value: float) -> None:
        self._stamina = self._clamp_resource(value, S.MAX_STAMINA, "stamina")

    @property
    def power(self) -> float:
        return self._stats["PWR"] / 100.0

    @property
    def defense(self) -> float:
        return self._stats["DEF"] / 100.0

    @property
    def speed(self) -> float:
        return self._stats["SPD"] / 100.0

    @property
    def stats_percent(self) -> dict[str, int]:
        return {k: int(v) for k, v in self._stats.items()}

    @property
    def is_ko(self) -> bool:
        return self.state_machine.state == State.KO

    @property
    def is_blocking(self) -> bool:
        return self._blocking

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

    def add_status(self, name: str, duration: float) -> None:
        self._status[name] = max(self._status.get(name, 0.0), duration)

    def has_status(self, name: str) -> bool:
        return self._status.get(name, 0.0) > 0.0

    def apply_bleed(self, dps: float, duration: float, source: "Fighter") -> None:
        self._bleeds.append([duration, dps, source])

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
        self.energy = 50.0
        self.stamina = S.MAX_STAMINA
        self._status.clear()
        self._bleeds.clear()
        self._blocking = False
        self._bounce_window = 0.0
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

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.input_enabled or self.is_ko:
            return
        action = self.controller.action_for_event(event)
        if action is not None:
            self.perform(action)

    def perform(self, action: str) -> None:
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

    def update(self, dt: float, *args: object) -> None:
        self.state_machine.update(dt)
        self._pose_time += dt
        self._frame_timer += dt

        while self._frame_timer >= 0.12:
            self._frame_timer -= 0.12

            if self.is_ko:
                self._frame = min(self._frame + 1, 3)
            else:
                self._frame = (self._frame + 1) % 4
        if self._pose_time > self._pose_len:
            self._pose = "idle"
            self._pose_frames = None
        for name in list(self._status):
            self._status[name] -= dt
            if self._status[name] <= 0:
                del self._status[name]
        self._tick_bleeds(dt)

        if self.is_ko:
            self.vel.x *= 0.02 ** dt
            super().update(dt)
            self._handle_walls()
            return

        for skill in self.skills:
            skill.update(dt)
        self.energy += S.ENERGY_REGEN * dt
        self.stamina += S.STAMINA_REGEN * dt
        self._bounce_window = max(0.0, self._bounce_window - dt)
        self._handle_held_input(dt)
        self.hitbox.update(dt)
        if not self.state_machine.can_act and self.on_ground:
            self.vel.x *= 0.03 ** dt
        super().update(dt)
        self._handle_walls()
        if self.state_machine.can_act and self.opponent is not None:
            self.facing = 1 if self.opponent.pos.x >= self.pos.x else -1

    def _tick_bleeds(self, dt: float) -> None:
        if not self._bleeds or self.is_ko:
            return
        total, killer = 0.0, None
        for b in self._bleeds:
            b[0] = float(b[0]) - dt
            total += float(b[1])
            killer = b[2]
        self._bleeds = [b for b in self._bleeds if float(b[0]) > 0]
        self.hp -= total * dt
        if random.random() < dt * 9:
            self.burst(1, (170, 10, 30), 90)
        if self.hp <= 0 and killer is not None:
            self._die(killer)

    def _handle_walls(self) -> None:
        left, right = S.ARENA.left + 8, S.ARENA.right - 8
        touching = self.rect.left <= left or self.rect.right >= right
        if touching and self._bounce_window > 0 and abs(self.vel.x) > 60 and not self.is_ko:
            self.vel.x = -self.vel.x * 0.8
            self.vel.y = -380.0
            self._bounce_window = 0.0
            self.hp -= 4.0
            self.burst(14, S.WHITE, 300)
            if self.world is not None:
                self.world.spawn_effect(FloatingText("WALL BOUNCE!", self.pos.x, self.pos.y - 190, S.GOLD))
            if self.hp <= 0 and self.opponent is not None:
                self._die(self.opponent)
        if self.rect.left < left:
            self.pos.x += left - self.rect.left
        elif self.rect.right > right:
            self.pos.x -= self.rect.right - right
        self._sync_rect()

    def take_hit(self, hit: HitInfo) -> bool:
        if self.is_ko or self.has_status("invulnerable"):
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
            if "wall_bounce" in hit.tags:
                self._bounce_window = 0.9
        if self.hp <= 0:
            self._die(hit.attacker)
        else:
            self.on_damage_taken(hit, damage)
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

    def draw(self, surface: pygame.Surface) -> None:
        shadow = pygame.Rect(0, 0, 90, 14)
        shadow.center = (self.rect.centerx, S.GROUND_Y + 2)
        pygame.draw.ellipse(surface, (150, 100, 0), shadow)

        
        if self.is_ko:
            pose_key = "ko"

        elif not self.on_ground and self._pose in (
            "punch", "uppercut", "rush", "throw", "cast", "attack"
        ):
            pose_key = "jumpattack"

        elif self._pose in (
            "punch", "uppercut", "rush", "throw", "cast", "attack"
        ):
            pose_key = "attack"

        elif self._pose == "hit":
            pose_key = "hit"

        elif self._blocking:
            pose_key = "guard"

        elif not self.on_ground:
            pose_key = "jump"

        elif self.state_machine.state == State.WALK:
            pose_key = "walk"

        else:
            pose_key = "idle"

        if self._pose_frames and self._pose != "idle" and not self.is_ko:
            frames = self._pose_frames
        else:
            frames = self._frames.get(pose_key, self._frames["idle"])
        if not frames:
            return
        if frames is self._pose_frames and self._pose_len > 0:
            idx = min(int(self._pose_time / self._pose_len * len(frames)), len(frames) - 1)
        else:
            idx = self._frame % len(frames)
        frame = frames[idx]
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        alpha = 255
        if self.has_status("veiled"):
            alpha = 80
        elif self.has_status("invulnerable"):
            alpha = 110
        if alpha < 255:
            frame = frame.copy()
            frame.set_alpha(alpha)
        dest = frame.get_rect(midbottom=(self.rect.centerx, self.rect.bottom))
        surface.blit(frame, dest)

        img = get_font(11).render(f"{self.tag} • {self.NAME}", True, S.DARK)
        r = img.get_rect(center=(self.rect.centerx, self.rect.bottom - 190)).inflate(12, 6)
        pygame.draw.rect(surface, self.color, r)
        surface.blit(img, img.get_rect(center=r.center))


class Jack(Fighter):
    NAME = "T. Jack"
    TITLE = "God of Python"
    BASE_STATS = {"PWR": 85, "DEF": 65, "SPD": 95}
    SHEET_PATH = "imageFolder/kai_sheet.png"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._kinetic_bank = 0.0

    def create_skills(self) -> list["BaseSkill"]:
        from skill import Power_Pellet, GhostFrenzy, PacMan_Chomp
        return [PacMan_Chomp(), Power_Pellet(), GhostFrenzy()]

    def modify_incoming_damage(self, damage: float, hit: HitInfo, blocked: bool) -> float:
        if blocked and self.has_status("kinetic"):
            self._kinetic_bank = min(30.0, self._kinetic_bank + damage * 2)
            self.energy += damage * 2
            self.burst(6, S.WHITE, 200)
            return 0.0
        return damage

    def outgoing_damage_multiplier(self) -> float:
        return 1.0 + self._kinetic_bank / 40.0

    @property
    def attack_speed(self) -> float:
        return 1.5 if self.has_status("kinetic") else 1.0

    @property
    def move_speed_multiplier(self) -> float:
        return 1.45 if self.has_status("kinetic") else 1.0

    def on_damage_taken(self, hit: HitInfo, damage: float) -> None:
        self.energy += damage * 0.5

    def on_hit_landed(self, hit: HitInfo, target: Fighter) -> None:
        self.energy += 6
        self._kinetic_bank = 0.0

    def reset(self, x: float, facing: int) -> None:
        super().reset(x, facing)
        self._kinetic_bank = 0.0


class Art(Fighter):
    NAME = "T. Art"
    TITLE = "The Toxic Speaker"
    BASE_STATS = {"PWR": 90, "DEF": 60, "SPD": 75}
    SHEET_PATH = "imageFolder/nyx_sheet.png"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._counter_cd = 0.0

    def create_skills(self) -> list["BaseSkill"]:
        from skill import CriticalRoast, ShutUp, EmotionalDamage
        return [CriticalRoast(), ShutUp(), EmotionalDamage()]

    def update(self, dt: float, *args: object) -> None:
        self._counter_cd = max(0.0, self._counter_cd - dt)
        super().update(dt)

    def modify_incoming_damage(self, damage: float, hit: HitInfo, blocked: bool) -> float:
        return damage * 0.5 if self.has_status("veiled") else damage

    def outgoing_damage_multiplier(self) -> float:
        return 1.5 if self.has_status("veiled") else 1.0

    def on_damage_taken(self, hit: HitInfo, damage: float) -> None:
        if not self.has_status("veiled") or self._counter_cd > 0 or "counter" in hit.tags:
            return
        self._counter_cd = 0.6
        crit = (6 + 8 * self.power) * 2.0
        counter = HitInfo(
            attacker=self, damage=crit, knockback=pygame.Vector2(420, -320),
            direction=1 if hit.attacker.pos.x >= self.pos.x else -1,
            unblockable=True, stun=0.45, tags=frozenset({"counter", "crit"}),
        )
        if self.world is not None:
            self.world.spawn_effect(FloatingText("CRITICAL COUNTER!", self.pos.x, self.pos.y - 190, S.WHITE))
        hit.attacker.take_hit(counter)

    def on_hit_landed(self, hit: HitInfo, target: Fighter) -> None:
        self.energy += 5


class Pao(Fighter):
    NAME = "T. Pao"
    TITLE = "The CPU Destroyer"
    BASE_STATS = {"PWR": 100, "DEF": 95, "SPD": 40}
    SHEET_PATH = "imageFolder/nyx_sheet.png"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._counter_cd = 0.0

    def create_skills(self) -> list["BaseSkill"]:
        from skill import CPUSmash, OverclockCharge, BlueScreen_Crash
        return [CPUSmash(), OverclockCharge(), BlueScreen_Crash()]

    def update(self, dt: float, *args: object) -> None:
        self._counter_cd = max(0.0, self._counter_cd - dt)
        super().update(dt)

    def modify_incoming_damage(self, damage: float, hit: HitInfo, blocked: bool) -> float:
        return damage * 0.5 if self.has_status("veiled") else damage

    def outgoing_damage_multiplier(self) -> float:
        return 1.5 if self.has_status("veiled") else 1.0

    def on_damage_taken(self, hit: HitInfo, damage: float) -> None:
        if not self.has_status("veiled") or self._counter_cd > 0 or "counter" in hit.tags:
            return
        self._counter_cd = 0.6
        crit = (6 + 8 * self.power) * 2.0
        counter = HitInfo(
            attacker=self, damage=crit, knockback=pygame.Vector2(420, -320),
            direction=1 if hit.attacker.pos.x >= self.pos.x else -1,
            unblockable=True, stun=0.45, tags=frozenset({"counter", "crit"}),
        )
        if self.world is not None:
            self.world.spawn_effect(FloatingText("CRITICAL COUNTER!", self.pos.x, self.pos.y - 190, S.WHITE))
        hit.attacker.take_hit(counter)

    def on_hit_landed(self, hit: HitInfo, target: Fighter) -> None:
        self.energy += 5


class Piya(Fighter):
    NAME = "T. Piya"
    TITLE = "The Missing Teacher"
    BASE_STATS = {"PWR": 70, "DEF": 55, "SPD": 100}
    SHEET_PATH = "imageFolder/kai_sheet.png"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._kinetic_bank = 0.0

    def create_skills(self) -> list["BaseSkill"]:
        from skill import PhantomDash, VanishingCounter, ShadowVeil
        return [PhantomDash(), VanishingCounter(), ShadowVeil()]

    def modify_incoming_damage(self, damage: float, hit: HitInfo, blocked: bool) -> float:
        if blocked and self.has_status("kinetic"):
            self._kinetic_bank = min(30.0, self._kinetic_bank + damage * 2)
            self.energy += damage * 2
            self.burst(6, S.WHITE, 200)
            return 0.0
        return damage

    def outgoing_damage_multiplier(self) -> float:
        return 1.0 + self._kinetic_bank / 40.0

    @property
    def attack_speed(self) -> float:
        return 1.5 if self.has_status("kinetic") else 1.0

    @property
    def move_speed_multiplier(self) -> float:
        return 1.45 if self.has_status("kinetic") else 1.0

    def on_damage_taken(self, hit: HitInfo, damage: float) -> None:
        self.energy += damage * 0.5

    def on_hit_landed(self, hit: HitInfo, target: Fighter) -> None:
        self.energy += 6
        self._kinetic_bank = 0.0

    def reset(self, x: float, facing: int) -> None:
        super().reset(x, facing)
        self._kinetic_bank = 0.0


class Oat(Fighter):
    NAME = "Oat"
    TITLE = "Body Builder"
    BASE_STATS = {"PWR": 95, "DEF": 100, "SPD": 55}
    SHEET_PATH = "imageFolder/nyx_sheet.png"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._counter_cd = 0.0

    def create_skills(self) -> list["BaseSkill"]:
        from skill import MusclePunch, ProteinShake, BeastMode
        return [MusclePunch(), ProteinShake(), BeastMode()]

    def update(self, dt: float, *args: object) -> None:
        self._counter_cd = max(0.0, self._counter_cd - dt)
        super().update(dt)

    def modify_incoming_damage(self, damage: float, hit: HitInfo, blocked: bool) -> float:
        return damage * 0.5 if self.has_status("veiled") else damage

    def outgoing_damage_multiplier(self) -> float:
        return 1.5 if self.has_status("veiled") else 1.0

    def on_damage_taken(self, hit: HitInfo, damage: float) -> None:
        if not self.has_status("veiled") or self._counter_cd > 0 or "counter" in hit.tags:
            return
        self._counter_cd = 0.6
        crit = (6 + 8 * self.power) * 2.0
        counter = HitInfo(
            attacker=self, damage=crit, knockback=pygame.Vector2(420, -320),
            direction=1 if hit.attacker.pos.x >= self.pos.x else -1,
            unblockable=True, stun=0.45, tags=frozenset({"counter", "crit"}),
        )
        if self.world is not None:
            self.world.spawn_effect(FloatingText("CRITICAL COUNTER!", self.pos.x, self.pos.y - 190, S.WHITE))
        hit.attacker.take_hit(counter)

    def on_hit_landed(self, hit: HitInfo, target: Fighter) -> None:
        self.energy += 5


class Jin(Fighter):
    NAME = "Jin"
    TITLE = "Hole Destroyer"
    BASE_STATS = {"PWR": 90, "DEF": 65, "SPD": 100}
    SHEET_PATH = "imageFolder/nyx_sheet.png"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._counter_cd = 0.0

    def create_skills(self) -> list["BaseSkill"]:
        from skill import BottleBomb, MotorcycleRush, GansterDrift
        return [BottleBomb(), MotorcycleRush(), GansterDrift()]

    def update(self, dt: float, *args: object) -> None:
        self._counter_cd = max(0.0, self._counter_cd - dt)
        super().update(dt)

    def modify_incoming_damage(self, damage: float, hit: HitInfo, blocked: bool) -> float:
        return damage * 0.5 if self.has_status("veiled") else damage

    def outgoing_damage_multiplier(self) -> float:
        return 1.5 if self.has_status("veiled") else 1.0

    def on_damage_taken(self, hit: HitInfo, damage: float) -> None:
        if not self.has_status("veiled") or self._counter_cd > 0 or "counter" in hit.tags:
            return
        self._counter_cd = 0.6
        crit = (6 + 8 * self.power) * 2.0
        counter = HitInfo(
            attacker=self, damage=crit, knockback=pygame.Vector2(420, -320),
            direction=1 if hit.attacker.pos.x >= self.pos.x else -1,
            unblockable=True, stun=0.45, tags=frozenset({"counter", "crit"}),
        )
        if self.world is not None:
            self.world.spawn_effect(FloatingText("CRITICAL COUNTER!", self.pos.x, self.pos.y - 190, S.WHITE))
        hit.attacker.take_hit(counter)

    def on_hit_landed(self, hit: HitInfo, target: Fighter) -> None:
        self.energy += 5
