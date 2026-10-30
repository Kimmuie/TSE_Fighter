"""character.py — ข้อมูลตัวละครทั้งหมด (Name, Title, Skills, Images, SpriteSheet)"""
from __future__ import annotations

from typing import Callable, Optional

import settings as S


class CharacterData:
    """เก็บข้อมูลตัวละครหนึ่งตัว: รูป, ชื่อ, สกิล, สไปรต์ชีท"""

    def __init__(
        self,
        name: str,
        title: str,
        color: tuple[int, int, int],
        portrait_path: str,
        sheet_path: str,
        base_stats: dict[str, int],
        playable: bool = False,
    ) -> None:
        self.name = name
        self.title = title
        self.color = color
        self.portrait_path = portrait_path
        self.sheet_path = sheet_path
        self.base_stats = base_stats
        self.playable = playable
        self.preview_image = portrait_path
        self.character_image = portrait_path
        self.sprite_sheet = sheet_path


CHARACTERS = [
    CharacterData(
        name="T. Jack",
        title="THE URBAN BRAWLER",
        color=S.P1_COLOR,
        portrait_path="imageFolder/kai_portrait.png",
        sheet_path="imageFolder/kai_sheet.png",
        base_stats={"PWR": 90, "DEF": 70, "SPD": 85, "SPC": 95},
        playable=True,
    ),
    CharacterData(
        name="T. Art",
        title="SHADOW SHINOBI",
        color=S.P2_COLOR,
        portrait_path="imageFolder/nyx_portrait.png",
        sheet_path="imageFolder/nyx_sheet.png",
        base_stats={"PWR": 75, "DEF": 60, "SPD": 98, "SPC": 90},
        playable=True,
    ),
]

LOCKED = [
    CharacterData("T. Piya", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50, "SPC": 50}),
    CharacterData("T. Pao", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50, "SPC": 50}),
    CharacterData("T. Wachira", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50, "SPC": 50}),
    CharacterData("T. May", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50, "SPC": 50}),
    CharacterData("Oat", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50, "SPC": 50}),
    CharacterData("Night", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50, "SPC": 50}),
]

ROSTER: list[CharacterData] = CHARACTERS + LOCKED
