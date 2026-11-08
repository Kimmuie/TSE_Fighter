"""settings.py — ค่าคงที่ส่วนกลางของเกม"""
from __future__ import annotations

import pygame

# ---------- หน้าจอ ----------
WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "TSE Fighter"

# ---------- พาเลตสี Neo-Brutalist ----------
BG = (18, 18, 18)
PANEL = (33, 33, 38)
PANEL_LIGHT = (44, 44, 52)
DARK = (12, 12, 14)
P1_COLOR = (0, 229, 255)
P2_COLOR = (255, 23, 68)
RED = (238, 75, 43)
WHITE = (255, 255, 255)
GREY = (130, 130, 140)
GOLD = (255, 214, 0)
BLUE = (137, 207, 240)

# ---------- สนามต่อสู้ ----------
ARENA = pygame.Rect(16, 118, 1248, 486)
GROUND_Y = ARENA.bottom - 20

# ---------- ฟิสิกส์ / สถานะนักสู้ ----------
GRAVITY = 2600.0
MAX_HP = 100.0
MAX_ENERGY = 100.0
MAX_STAMINA = 100.0
ENERGY_REGEN = 7.0
STAMINA_REGEN = 22.0
BLOCK_DRAIN = 12.0

# ---------- กติกา ----------
ROUND_TIME = 90
ROUNDS_TO_WIN = 2

# ---------- พาธรูป ----------
IMAGE_DIR = "imageFolder"
