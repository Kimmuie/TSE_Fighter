"""ui.py — องค์ประกอบ UI ทั้งหมด + โหลดรูปภาพ"""
from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING, Optional

import pygame

import settings as S

if TYPE_CHECKING:
    from entities import Fighter

_BASE = os.path.dirname(os.path.abspath(__file__))
_font_cache: dict[tuple[int, bool, bool], pygame.font.Font] = {}
_image_cache: dict[tuple, pygame.Surface] = {}


def get_font(size: int, bold: bool = True, display: bool = False) -> pygame.font.Font:
    key = (size, bold, display)
    if key not in _font_cache:
        names = (
            "expletus sans"
            if display
            else "couriernew,courier,menlo,consolas,dejavusansmono,monospace"
        )
        _font_cache[key] = pygame.font.SysFont(names, size, bold=bold)
    return _font_cache[key]

def load_image(path: str, size: tuple[int, int] | None = None, label: str = "", color: tuple[int, int, int] = S.WHITE) -> pygame.Surface:
    key = (path, size, label, color)
    if key in _image_cache:
        return _image_cache[key]
    full = path if os.path.isabs(path) else os.path.join(_BASE, path)
    surf: Optional[pygame.Surface] = None
    fallback = os.path.join(_BASE, "assets", "emptyImage.png")
    for candidate in (full, fallback):
        if candidate and os.path.isfile(candidate):
            try:
                img = pygame.image.load(candidate).convert_alpha()
                if size:
                    img = pygame.transform.smoothscale(img, size)
                surf = img
                break
            except pygame.error:
                surf = None
    if surf is None:
        w, h = size or (64, 64)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill(S.PANEL)
        pygame.draw.rect(surf, color, surf.get_rect(), 2)
        if label:
            txt = get_font(max(9, min(w, h) // 9), bold=False).render(f"[ {label} ]", True, color)
            surf.blit(txt, txt.get_rect(center=(w // 2, h - max(10, h // 8))))
    _image_cache[key] = surf
    return surf


def draw_text(surface: pygame.Surface, text: str, size: int, color: tuple[int, int, int],
              pos: tuple[int, int], anchor: str = "topleft", display: bool = False) -> pygame.Rect:
    img = get_font(size, display=display).render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    surface.blit(img, rect)
    return rect


def wrap_text(text: str, size: int, max_w: int) -> list[str]:
    font = get_font(size, bold=False)
    lines, cur = [], ""
    for word in text.split():
        test = f"{cur} {word}".strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


def draw_icon(surface: pygame.Surface, path: str, center: tuple[int, int], size: int = 26) -> None:
    icon = load_image(path, (size, size))
    surface.blit(icon, icon.get_rect(center=center))


class HealthBar:
    def __init__(self, rect: tuple[int, int, int, int], color: tuple[int, int, int], align_right: bool = False) -> None:
        self.rect = pygame.Rect(rect)
        self.color = color
        self.align_right = align_right
        self._target = 1.0
        self._shown = 1.0

    @property
    def ratio(self) -> float:
        return self._target

    @ratio.setter
    def ratio(self, value: float) -> None:
        self._target = max(0.0, min(1.0, float(value)))

    def update(self, dt: float) -> None:
        self._shown += (self._target - self._shown) * min(1.0, dt * 9)

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, S.DARK, self.rect)
        inner = self.rect.inflate(-6, -6)
        w = int(inner.w * self._shown)
        fill = pygame.Rect(inner.right - w if self.align_right else inner.x, inner.y, w, inner.h)
        pygame.draw.rect(surface, self.color, fill)
        pygame.draw.rect(surface, self.color, self.rect, 1)


class SkillBar:
    def __init__(self, rect: pygame.Rect, color: tuple[int, int, int]) -> None:
        self.rect = rect
        self.color = color

    def draw(self, surface: pygame.Surface, fighter: "Fighter") -> None:
        gap = 8
        slot_w = (self.rect.w - 2 * gap) // 3
        for i, skill in enumerate(fighter.skills):
            r = pygame.Rect(self.rect.x + i * (slot_w + gap), self.rect.y, slot_w, self.rect.h)
            ready = skill.can_cast(fighter)
            pygame.draw.rect(surface, S.PANEL, r)
            pygame.draw.rect(surface, self.color if ready else S.GREY, r, 1)
            badge = pygame.Rect(r.x + 6, r.centery - 8, 48, 16)
            pygame.draw.rect(surface, self.color, badge)
            draw_text(surface, f"[ {skill.key_label} ]", 9, S.DARK, badge.center, "center")
            icon_c = (r.x + 78, r.centery)
            pygame.draw.circle(surface, self.color, icon_c, 12, 1)
            draw_icon(surface, os.path.join(S.IMAGE_DIR, skill.ICON), icon_c, 20)
            draw_text(surface, skill.NAME, 9, S.WHITE if ready else S.GREY, (r.x + 96, r.centery - 6))
            draw_text(surface, f"EN {int(skill.ENERGY_COST)}", 8, S.GREY, (r.right - 6, r.bottom - 4), "bottomright")
            if skill.cooldown_ratio > 0:
                ov = pygame.Surface((r.w, int(r.h * skill.cooldown_ratio)), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 160))
                surface.blit(ov, r.topleft)
                draw_text(surface, f"{skill.cooldown_left:.1f}s", 11, S.WHITE, (r.right - 8, r.centery - 4), "midright")


class HUD:
    PANEL = pygame.Rect(16, 10, 1248, 100)

    def __init__(self) -> None:
        self.bar1 = HealthBar((32, 76, 500, 16), S.P1_COLOR)
        self.bar2 = HealthBar((748, 76, 500, 16), S.P2_COLOR, align_right=True)
        self.skills1 = SkillBar(pygame.Rect(16, 624, 616, 60), S.P1_COLOR)
        self.skills2 = SkillBar(pygame.Rect(648, 624, 616, 60), S.P2_COLOR)

    def update(self, dt: float, f1: "Fighter", f2: "Fighter") -> None:
        self.bar1.ratio, self.bar2.ratio = f1.hp / 100.0, f2.hp / 100.0
        self.bar1.update(dt)
        self.bar2.update(dt)

    def draw(self, surface: pygame.Surface, f1: "Fighter", f2: "Fighter", time_left: float,
             round_no: int, wins: list[int], arena_name: str) -> None:
        pygame.draw.rect(surface, S.PANEL, self.PANEL)
        pygame.draw.rect(surface, S.PANEL_LIGHT, self.PANEL, 1)
        pygame.draw.circle(surface, S.P1_COLOR, (36, 30), 5)
        draw_text(surface, "PLAYER 1", 11, S.P1_COLOR, (48, 23))
        draw_text(surface, "PLAYER 2", 11, S.P2_COLOR, (1228, 23), "topright")
        pygame.draw.circle(surface, S.P2_COLOR, (1244, 30), 5)

        badge = pygame.Rect(0, 0, 300, 22)
        badge.center = (640, 30)
        pygame.draw.rect(surface, S.DARK, badge)
        pygame.draw.rect(surface, S.GREY, badge, 1)
        draw_text(surface, f"ROUND {round_no} • {arena_name}", 10, S.WHITE, badge.center, "center")
        for i, x in enumerate((460, 478)):
            pygame.draw.circle(surface, S.P1_COLOR if wins[0] > i else S.PANEL_LIGHT, (x, 30), 5)
        for i, x in enumerate((802, 820)):
            pygame.draw.circle(surface, S.P2_COLOR if wins[1] > i else S.PANEL_LIGHT, (x, 30), 5)

        draw_text(surface, f"{f1.NAME} ({f1.TITLE})", 11, S.P1_COLOR, (32, 54))
        draw_text(surface, f"{int(round(f1.hp))}% HP", 16, S.P1_COLOR, (532, 48), "topright")
        draw_text(surface, f"{f2.NAME} ({f2.TITLE})", 11, S.P2_COLOR, (1248, 54), "topright")
        draw_text(surface, f"{int(round(f2.hp))}% HP", 16, S.P2_COLOR, (748, 48), "topleft")
        self.bar1.draw(surface)
        self.bar2.draw(surface)
        for rect, f, right in ((pygame.Rect(32, 96, 500, 4), f1, False), (pygame.Rect(748, 96, 500, 4), f2, True)):
            pygame.draw.rect(surface, S.DARK, rect)
            w = int(rect.w * f.energy / 100)
            pygame.draw.rect(surface, S.WHITE, (rect.right - w if right else rect.x, rect.y, w, rect.h))

        timer = pygame.Rect(600, 46, 80, 50)
        pygame.draw.rect(surface, S.DARK, timer)
        pygame.draw.rect(surface, S.WHITE, timer, 2)
        draw_text(surface, f"{max(0, math.ceil(time_left)):02d}", 28, S.WHITE, (640, 68), "center")
        draw_text(surface, "SECONDS", 8, S.GREY, (640, 90), "center")

        self.skills1.draw(surface, f1)
        self.skills2.draw(surface, f2)


class ComboBanner:
    def __init__(self) -> None:
        self._critical = False
        self._hits = 0
        self._dmg = 0.0
        self._ttl = 0.0
        self._last: dict[str, float] = {}
        self._clock = 0.0
        self._clash = False

    def on_hit(self, attacker: "Fighter", target: "Fighter",
            damage: float, **kwargs: object) -> None:

        if self._ttl <= 0:
            self._hits = 0
            self._dmg = 0.0
            self._critical = False

        self._hits += 1
        self._dmg += damage

        self._last[attacker.tag] = self._clock

        others = [
            t for tag, t in self._last.items()
            if tag != attacker.tag
        ]

        self._clash = any(
            self._clock - t < 0.5 for t in others
        )

        # Read critical status directly from HitInfo
        hit = kwargs.get("hit")

        self._critical = (
            hit is not None and "critical" in hit.tags
        )

        self._ttl = 1.4

    def update(self, dt: float) -> None:
        self._clock += dt
        self._ttl = max(0.0, self._ttl - dt)

        if self._ttl <= 0:
            self._critical = False

    def draw(self, surface: pygame.Surface) -> None:
        if self._ttl <= 0:
            return
        cx, y = S.ARENA.centerx, S.GROUND_Y - 78
        title = (
            "CRITICAL HIT!" if self._critical
            else "CLASH!" if self._clash
            else "COMBO!"
        )

        big = get_font(20, bold=False, display=False).render(
            title, True, S.DARK
        )
        r = big.get_rect(center=(cx, y)).inflate(20, 8)
        if self._critical:
            pygame.draw.rect(surface, S.RED, r)
        else:
            pygame.draw.rect(surface, S.WHITE, r)
        surface.blit(big, big.get_rect(center=r.center))
        sub = get_font(10).render(f"{self._hits} HITS • {int(self._dmg * 10):,} DMG", True, S.DARK)
        sr = sub.get_rect(center=(cx, r.bottom + 10)).inflate(14, 5)
        pygame.draw.rect(surface, S.GOLD, sr)
        surface.blit(sub, sub.get_rect(center=sr.center))


class FighterCard:
    def __init__(self, rect: pygame.Rect, color: tuple[int, int, int], label: str, mirrored: bool) -> None:
        self.rect = rect
        self.color = color
        self.label = label
        self.mirrored = mirrored

    def draw(self, surface: pygame.Surface, name: str, title: str, preview: Optional["Fighter"], ready: bool,
             portrait_path: str = "") -> None:
        r, col = self.rect, self.color
        pygame.draw.rect(surface, S.PANEL, r)
        pygame.draw.rect(surface, col, r, 2)
        left = not self.mirrored
        draw_text(surface, f"PLAYER {self.label}", 11, col, (r.x + 16, r.y + 14) if left else (r.right - 16, r.y + 14),
                  "topleft" if left else "topright")
        badge = pygame.Rect(0, 0, 78, 20)
        badge.topright = (r.right - 12, r.y + 12) if left else (r.x + 90, r.y + 12)
        pygame.draw.rect(surface, col if ready else S.PANEL_LIGHT, badge)
        draw_text(surface, f"P{self.label} READY" if ready else "CHOOSING", 10, S.DARK if ready else S.GREY,
                  badge.center, "center")

        port = pygame.Rect(r.x + 16, r.y + 44, r.w - 32, 140)
        img = load_image(portrait_path or "assets/emptyImage.png", port.size, f"PORTRAIT {name}", col)
        surface.blit(img, port)
        pygame.draw.rect(surface, col, port, 1)

        ax, anchor = (r.x + 16, "topleft") if left else (r.right - 16, "topright")
        draw_text(surface, name, 28, S.WHITE, (ax, r.y + 194), anchor, display=True)
        draw_text(surface, title, 11, S.GREY, (ax, r.y + 230), anchor)
        if preview is None:
            draw_text(surface, "LOCKED", 18, S.GREY, (r.centerx, r.y + 380), "center")
            return
        draw_text(surface, "COMBAT SKILLS", 11, col, (ax, r.y + 256), anchor)
        for i, sk in enumerate(preview.skills):
            sr = pygame.Rect(r.x + 16, r.y + 278 + i * 68, r.w - 32, 62)
            pygame.draw.rect(surface, S.PANEL_LIGHT, sr)
            ic = (sr.x + 28, sr.centery) if left else (sr.right - 28, sr.centery)
            pygame.draw.circle(surface, col, ic, 16, 2)
            draw_icon(surface, os.path.join(S.IMAGE_DIR, sk.ICON), ic, 24)
            kb = pygame.Rect(0, 0, 52, 14)
            if left:
                kb.topright = (sr.right - 6, sr.y + 5)
                name_x, desc_x, desc_w = sr.x + 56, sr.x + 56, sr.w - 68
            else:
                kb.topleft = (sr.x + 6, sr.y + 5)
                name_x, desc_x, desc_w = sr.x + 66, sr.x + 10, sr.w - 70
            pygame.draw.rect(surface, col, kb)
            draw_text(surface, f"[ {sk.key_label} ]", 8, S.DARK, kb.center, "center")
            draw_text(surface, sk.NAME, 10, S.WHITE, (name_x, sr.y + 5))
            for j, line in enumerate(wrap_text(sk.DESCRIPTION, 9, desc_w)[:3]):
                draw_text(surface, line, 9, S.GREY, (desc_x, sr.y + 22 + j * 12))
        stats = preview.stats_percent
        stat_labels = (("Power", "PWR"), ("Defense", "DEF"), ("Speed", "SPD"))
        for i, (label, key) in enumerate(stat_labels):
            bx = r.x + 16 + (i % 2) * ((r.w - 32) // 2 + 6)
            by = r.y + 490 + (i // 2) * 26
            bw = (r.w - 32) // 2 - 12
            value = stats[key]
            draw_text(surface, label, 9, S.WHITE, (bx, by))
            draw_text(surface, f"{value}%", 9, S.WHITE, (bx + bw, by), "topright")
            pygame.draw.rect(surface, S.DARK, (bx, by + 12, bw, 4))
            pygame.draw.rect(surface, col, (bx, by + 12, int(bw * value / 100), 4))


class RosterGrid:
    def __init__(self, rect: pygame.Rect, names: list[str], playable: list[bool], portrait_paths: list[str]) -> None:
        self.rect = rect
        self.names = names
        self.playable = playable
        self.portrait_paths = portrait_paths

    def cell(self, i: int) -> pygame.Rect:
        w = (self.rect.w - 40 - 12) // 2
        return pygame.Rect(self.rect.x + 20 + (i % 2) * (w + 12), self.rect.y + 50 + (i // 2) * 120, w, 108)

    def draw(self, surface: pygame.Surface, cursors: tuple[int, int], ready: tuple[bool, bool]) -> None:
        pygame.draw.rect(surface, S.PANEL, self.rect)
        pygame.draw.rect(surface, S.PANEL_LIGHT, self.rect, 1)
        draw_text(surface, f"ROSTER - {len(self.names)} AVAILABLE", 12, S.WHITE, (self.rect.centerx, self.rect.y + 22), "center")
        for i, name in enumerate(self.names):
            c = self.cell(i)
            pygame.draw.rect(surface, S.PANEL_LIGHT, c)
            pygame.draw.rect(surface, (60, 60, 70), c, 1)
            img = load_image(self.portrait_paths[i], (c.w - 25, 65), name, S.WHITE if self.playable[i] else S.GREY)
            surface.blit(img, img.get_rect(center=(c.centerx, c.centery - 12)))
            col = S.WHITE if self.playable[i] else S.GREY
            draw_text(surface, name, 11, col, (c.centerx, c.centery + 28), "center")
            draw_text(surface, "[ READY ]" if self.playable[i] else "[ LOCKED ]", 8, S.GREY, (c.centerx, c.centery + 42), "center")
        for p, (col, tag) in enumerate(((S.P1_COLOR, "1P"), (S.P2_COLOR, "2P"))):
            c = self.cell(cursors[p])
            inset = c.inflate(-4 * p, -4 * p)
            pygame.draw.rect(surface, col, inset, 2 if not ready[p] else 4)
            b = pygame.Rect(0, 0, 24, 14)
            b.topleft = (c.x, c.y) if p == 0 else (c.right - 24, c.y)
            pygame.draw.rect(surface, col, b)
            draw_text(surface, tag, 9, S.DARK, b.center, "center")
