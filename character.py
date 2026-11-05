"""character.py — ข้อมูลตัวละครทั้งหมด (Name, Title, Skills, Images, SpriteSheet)"""
from __future__ import annotations

from typing import Callable, Optional

import settings as S
from entities import Jack, Art, Pao, Piya, Oat, Jin


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
        fighter_class=None,
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
        self.fighter_class = fighter_class


CHARACTERS = [
    CharacterData(
        name="T. Jack",
        title="God of Python",
        color=S.GREY,
        portrait_path="imageFolder/kai_portrait.png",
        sheet_path="imageFolder/jack_sheet.png",
        base_stats=Jack.BASE_STATS.copy(),
        fighter_class=Jack,
        playable=True,
    ),
    CharacterData(
        name="T. Art",
        title="The Toxic Speaker",
        color=S.GREY,
        portrait_path="imageFolder/nyx_portrait.png",
        sheet_path="imageFolder/art_sheet.png",
        base_stats=Art.BASE_STATS.copy(),
        fighter_class=Art,
        playable=True,
    ),
    CharacterData(
        name="T. Pao",
        title="The CPU Destroyer",
        color=S.GREY,
        portrait_path="imageFolder/kai_portrait.png",
        sheet_path="imageFolder/kai_sheet.png",
        base_stats=Pao.BASE_STATS.copy(),
        fighter_class=Pao,
        playable=True,

    ),
    CharacterData(
        name="T. Piya",
        title="The Missing Teacher",
        color=S.GREY,
        portrait_path="imageFolder/kai_portrait.png",
        sheet_path="imageFolder/kai_sheet.png",
        base_stats=Piya.BASE_STATS.copy(),
        fighter_class=Piya,
        playable=True,
    ),
    CharacterData(
        name="Oat",
        title="Body Builder",
        color=S.GREY,
        portrait_path="imageFolder/nyx_portrait.png",
        sheet_path="imageFolder/nyx_sheet.png",
        base_stats=Oat.BASE_STATS.copy(),
        fighter_class=Oat,
        playable=True,
    ),
    CharacterData(
        name="Jin",
        title="Hole Destroyer",
        color=S.GREY,
        portrait_path="imageFolder/nyx_portrait.png",
        sheet_path="imageFolder/nyx_sheet.png",
        base_stats=Jin.BASE_STATS.copy(),
        fighter_class=Jin,
        playable=True,     
    ),
]

LOCKED = [
    CharacterData("T. Piya", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50}),
    CharacterData("T. Pao", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50}),
    CharacterData("T. Wachira", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50}),
    CharacterData("T. May", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50}),
    CharacterData("Oat", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50}),
    CharacterData("Night", "COMING SOON", S.GREY, "imageFolder/emptyImage.png", "imageFolder/emptyImage.png",
                  {"PWR": 50, "DEF": 50, "SPD": 50}),
]

ROSTER: list[CharacterData] = CHARACTERS + LOCKED
