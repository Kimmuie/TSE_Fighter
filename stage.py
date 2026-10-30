"""stage.py — ฉากหลังสนามต่อสู้ ใช้รูปภาพ 4 แมพ"""
from __future__ import annotations

import random

import pygame

import settings as S
from ui import load_image


MAP_PATHS = [
    "imageFolder/map1.png",
    "imageFolder/map2.png",
    "imageFolder/map3.png",
    "imageFolder/map4.png",
]

MAP_NAMES = [
    "NIGHT PURPLE",
    "OCEAN BLUE",
    "SUNSET RED",
    "FOREST GREEN",
]


class Stage:
    def __init__(self, map_index: int | None = None) -> None:
        self.rect = S.ARENA.copy()
        self.ground_y = S.GROUND_Y
        idx = map_index if map_index is not None else random.randint(0, 3)
        self.map_index = idx % 4
        self.NAME = MAP_NAMES[self.map_index]
        self._bg = load_image(MAP_PATHS[self.map_index], (self.rect.w, self.rect.h))

    def draw(self, surface: pygame.Surface, t: float = 0.0) -> None:
        surface.blit(self._bg, self.rect.topleft)
        pygame.draw.rect(surface, S.WHITE, self.rect, 1)
