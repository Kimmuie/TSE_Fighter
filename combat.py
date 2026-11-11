"""combat.py — เอนจินชน และโลกของการต่อสู้"""
from __future__ import annotations

import math
import random
from typing import Iterable

import pygame

from entities import Fighter, GameObject, Particle, Projectile
from events import EventDispatcher


class CollisionEngine:
    def resolve(self, fighters: list[Fighter], projectiles: Iterable[Projectile]) -> None:
        self._melee(fighters)
        self._projectiles(fighters, projectiles)
        self._separate(fighters)

    def _melee(self, fighters: list[Fighter]) -> None:
        for attacker in fighters:
            if attacker.is_ko or not attacker.hitbox.is_active:
                continue
            box = attacker.hitbox.rect_for(attacker)
            for defender in fighters:
                if defender is attacker or defender.is_ko:
                    continue
                if box.colliderect(defender.rect) and defender.take_hit(attacker.hitbox.build_hit(attacker)):
                    attacker.hitbox.mark_hit()
                    break

    def _projectiles(self, fighters: list[Fighter], projectiles: Iterable[Projectile]) -> None:
        for proj in list(projectiles):
            for target in fighters:
                if target is proj.owner or target.is_ko:
                    continue
                if proj.rect.colliderect(target.rect) and target.take_hit(proj.build_hit()):
                    proj.on_hit(target)
                    proj.kill()
                    break

    def _separate(self, fighters: list[Fighter]) -> None:
        if len(fighters) < 2:
            return
        a, b = fighters[0], fighters[1]
        if a.is_ko or b.is_ko or not a.rect.colliderect(b.rect) or not (a.on_ground and b.on_ground):
            return
        overlap = min(a.rect.right, b.rect.right) - max(a.rect.left, b.rect.left)
        push = overlap / 2 + 1
        d = 1 if b.pos.x >= a.pos.x else -1
        a.set_x(a.pos.x - d * push)
        b.set_x(b.pos.x + d * push)


class BattleWorld:
    def __init__(self, dispatcher: EventDispatcher) -> None:
        self.dispatcher = dispatcher
        self.fighters = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.effects = pygame.sprite.Group()
        self.collisions = CollisionEngine()

    def add_fighter(self, fighter: Fighter) -> None:
        fighter.world = self
        self.fighters.add(fighter)
        fs = self.fighters.sprites()
        if len(fs) == 2:
            fs[0].opponent, fs[1].opponent = fs[1], fs[0]

    def spawn_projectile(self, proj: Projectile) -> None:
        self.projectiles.add(proj)

    def spawn_effect(self, effect: GameObject) -> None:
        self.effects.add(effect)

    def spawn_particles(self, x: float, y: float, color: tuple[int, int, int], count: int = 10,
                        speed: float = 260.0) -> None:
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(0.3, 1.0) * speed
            self.effects.add(Particle(x, y, math.cos(ang) * sp, math.sin(ang) * sp - 120, color,
                                      life=random.uniform(0.3, 0.6), size=random.randint(4, 8)))

    def update(self, dt: float) -> None:
        for group in (self.fighters, self.projectiles, self.effects):
            group.update(dt)
        self.collisions.resolve(self.fighters.sprites(), self.projectiles.sprites())

    def draw(self, surface: pygame.Surface) -> None:
        for group in (self.fighters, self.projectiles, self.effects):
            for obj in group:
                obj.draw(surface)
