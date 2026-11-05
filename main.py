"""main.py — จุดเริ่มต้นของเกม STREET CLASH

รัน:  python main.py
"""
from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import Optional

import pygame

import settings as S
from character import ROSTER, CharacterData
from combat import BattleWorld
from component import make_player_one_controller, make_player_two_controller
from entities import FloatingText, Fighter
from events import EventDispatcher
from stage import Stage
from ui import ComboBanner, FighterCard, HUD, RosterGrid, draw_text, load_image


class Scene(ABC):
    def __init__(self, game: "Game") -> None:
        self.game = game

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None: ...

    @abstractmethod
    def update(self, dt: float) -> None: ...

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None: ...


class MenuScene(Scene):
    def __init__(self, game: "Game") -> None:
        super().__init__(game)
        self._t = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.game.change_scene(SelectScene(self.game))
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False

    def update(self, dt: float) -> None:
        self._t += dt

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(S.BG)
        # consistent panel style
        panel = pygame.Rect(0, 0, S.WIDTH, S.HEIGHT)
        pygame.draw.rect(surface, S.PANEL, panel)
        pygame.draw.rect(surface, S.PANEL_LIGHT, panel, 2)

        draw_text(surface, "TSE", 80, S.P1_COLOR, (640 - 65, 130), "midtop", display=True)
        draw_text(surface, "Fighter", 80, S.P2_COLOR, (640 + 15, 170), "midtop", display=True)
        draw_text(surface, "2-PLAYER LOCAL FIGHTER", 14, S.GREY, (640, 280), "midtop")
        if int(self._t * 2) % 2 == 0:
            draw_text(surface, "PRESS ENTER", 20, S.WHITE, (640, 320), "midtop")

        for col, x, lines in (
            (S.P1_COLOR, 340, ["PLAYER 1", "A / D  move     W  jump     S  guard", "V  attack", "F G H  skills"]),
            (S.P2_COLOR, 940, ["PLAYER 2", "← / →  move   ↑  jump   ↓  guard", "NUM 0   attack", "NUM 1 2 3  skills"]),
        ):
            box = pygame.Rect(x - 180, 380, 360, 120)
            pygame.draw.rect(surface, S.PANEL_LIGHT, box)
            pygame.draw.rect(surface, col, box, 1)
            for i, line in enumerate(lines):
                draw_text(surface, line, 12 if i else 13, col if i == 0 else S.WHITE, (x, 396 + i * 24), "midtop")


class SelectScene(Scene):
    def __init__(self, game: "Game") -> None:
        super().__init__(game)
        self._cursor = [0, 1]
        self._ready = [False, False]
        self._countdown: Optional[float] = None
        self._previews: dict[tuple[int, str], Fighter] = {}
        names = [e.name for e in ROSTER]
        playable = [e.playable for e in ROSTER]
        paths = [e.portrait_path for e in ROSTER]
        self.grid = RosterGrid(pygame.Rect(420, 90, 440, 560), names, playable, paths)
        self.cards = (
            FighterCard(pygame.Rect(20, 90, 380, 560), S.P1_COLOR, "1", False),
            FighterCard(pygame.Rect(880, 90, 380, 560), S.P2_COLOR, "2", True),
        )


    def _preview(self, player: int) -> Optional[Fighter]:
        entry = ROSTER[self._cursor[player]]

        if not entry.playable:
            return None

        key = (player, entry.name)

        if key not in self._previews:
            color = S.P1_COLOR if player == 0 else S.P2_COLOR
            cls = entry.fighter_class

            if cls is None:
                return None

            self._previews[key] = cls(
                color,
                self.game.controllers[player],
                EventDispatcher(),
                tag=f"{player + 1}P"
            )

        return self._previews[key]


    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.game.change_scene(MenuScene(self.game))
            return
        for p, ctrl in enumerate(self.game.controllers):
            action = ctrl.action_for_event(event)
            if action == "attack":
                if ROSTER[self._cursor[p]].playable:
                    self._ready[p] = not self._ready[p]
            elif not self._ready[p]:
                step = {"left": -1, "right": 1, "jump": -2, "block": 2}.get(action or "")
                if step:
                    self._cursor[p] = (self._cursor[p] + step) % len(ROSTER)
        if all(self._ready) and self._countdown is None:
            self._countdown = 0.7

    def update(self, dt: float) -> None:
        if not all(self._ready):
            self._countdown = None
        elif self._countdown is not None:
            self._countdown -= dt
            if self._countdown <= 0:
                e1, e2 = ROSTER[self._cursor[0]], ROSTER[self._cursor[1]]
                c1 = e1.fighter_class
                c2 = e2.fighter_class

                if c1 is not None and c2 is not None:
                    self.game.change_scene(BattleScene(self.game, c1, c2))
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(S.BG)
        draw_text(surface, "SELECT YOUR FIGHTER", 36, S.WHITE, (640, 12), "midtop", display=True)
        for p, card in enumerate(self.cards):
            entry = ROSTER[self._cursor[p]]
            card.draw(surface, entry.name, entry.title, self._preview(p), self._ready[p], entry.portrait_path)
        self.grid.draw(surface, (self._cursor[0], self._cursor[1]), (self._ready[0], self._ready[1]))
        hint = "P1: A/D/W/S move • F confirm      P2: arrows move • NUM 0 confirm      ESC back"
        draw_text(surface, hint, 10, S.GREY, (640, 710), "midbottom")
        if self._countdown is not None:
            draw_text(surface, "FIGHT!", 24, S.GOLD, (640, 70), "midtop", display=True)


class BattleScene(Scene):
    INTRO_TIME = 1.5
    END_TIME = 2.4

    def __init__(self, game: "Game", cls1: type[Fighter], cls2: type[Fighter]) -> None:
        super().__init__(game)
        self.cls1, self.cls2 = cls1, cls2
        self.dispatcher = EventDispatcher()
        self.world = BattleWorld(self.dispatcher)
        self.stage = Stage()
        self.hud = HUD()
        self.combo = ComboBanner()
        c1, c2 = game.controllers
        self.fighters: list[Fighter] = [
            cls1(S.P1_COLOR, c1, self.dispatcher, tag="1P", x=S.ARENA.left + 260, facing=1),
            cls2(S.P2_COLOR, c2, self.dispatcher, tag="2P", x=S.ARENA.right - 260, facing=-1),
        ]
        for f in self.fighters:
            self.world.add_fighter(f)
        self.dispatcher.subscribe("on_hit", self._on_hit)
        self.dispatcher.subscribe("on_hit", self.combo.on_hit)
        self.dispatcher.subscribe("on_skill_cast", self._on_skill_cast)
        self.dispatcher.subscribe("on_ko", self._on_ko)
        self.wins = [0, 0]
        self.round_no = 0
        self._t = 0.0
        self._banner = ""
        self._start_round()

    def _start_round(self) -> None:
        self.round_no += 1
        self.time_left = float(S.ROUND_TIME)
        self.phase = "intro"
        self.phase_time = 0.0
        self._banner = ""
        self.world.projectiles.empty()
        self.world.effects.empty()
        # new map each round
        self.stage = Stage()
        for f, x, face in zip(self.fighters, (S.ARENA.left + 260, S.ARENA.right - 260), (1, -1)):
            f.reset(x, face)
            f.input_enabled = False

    def _end_round(self, banner: str, winner: Optional[int]) -> None:
        if self.phase != "fight":
            return
        if winner is not None:
            self.wins[winner] += 1
        self.phase, self.phase_time, self._banner = "round_end", 0.0, banner
        for f in self.fighters:
            f.input_enabled = False

    def _on_hit(self, attacker: Fighter, target: Fighter, damage: float, blocked: bool, **_: object) -> None:
        target.burst(8 if not blocked else 3, attacker.color, 240)

    def _on_skill_cast(self, caster: Fighter, skill: object, **_: object) -> None:
        self.world.spawn_effect(FloatingText(skill.NAME, caster.pos.x, caster.pos.y - 200, caster.color))  # type: ignore[attr-defined]

    def _on_ko(self, loser: Fighter, winner: Fighter, **_: object) -> None:
        idx = self.fighters.index(winner) if winner in self.fighters else 1 - self.fighters.index(loser)
        self._end_round("K.O.!", idx)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_scene(MenuScene(self.game))
            return
        if self.phase == "fight":
            for f in self.fighters:
                f.handle_event(event)

    def update(self, dt: float) -> None:
        self._t += dt
        self.phase_time += dt
        if self.phase == "intro" and self.phase_time >= self.INTRO_TIME:
            self.phase, self.phase_time = "fight", 0.0
            for f in self.fighters:
                f.input_enabled = True
        elif self.phase == "fight":
            self.time_left -= dt
            if self.time_left <= 0:
                a, b = self.fighters[0].hp, self.fighters[1].hp
                self._end_round("TIME!" if a != b else "DRAW", None if a == b else (0 if a > b else 1))
        elif self.phase == "round_end" and self.phase_time >= self.END_TIME:
            if max(self.wins) >= S.ROUNDS_TO_WIN:
                self.game.change_scene(GameOverScene(self.game, self.cls1, self.cls2, self.wins.index(max(self.wins))))
                return
            self._start_round()
        self.world.update(dt)
        self.hud.update(dt, *self.fighters)
        self.combo.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(S.BG)
        surface.set_clip(S.ARENA)
        self.stage.draw(surface, self._t)
        self.world.draw(surface)
        surface.set_clip(None)
        self.combo.draw(surface)
        self.hud.draw(surface, self.fighters[0], self.fighters[1], self.time_left, self.round_no,
                      self.wins, self.stage.NAME)
        text = ""
        if self.phase == "intro":
            text = f"ROUND {self.round_no}" if self.phase_time < 0.9 else "FIGHT!"
        elif self.phase == "round_end":
            text = self._banner
        if text:
            draw_text(surface, text, 48, S.WHITE, (S.ARENA.centerx + 3, S.ARENA.y + 140), "center", display=True)
            draw_text(surface, text, 48, S.GOLD, (S.ARENA.centerx, S.ARENA.y + 136), "center", display=True)


class GameOverScene(Scene):
    def __init__(self, game: "Game", cls1: type[Fighter], cls2: type[Fighter], winner: int) -> None:
        super().__init__(game)
        self.cls1, self.cls2, self.winner = cls1, cls2, winner

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_RETURN:
            self.game.change_scene(BattleScene(self.game, self.cls1, self.cls2))
        elif event.key == pygame.K_c:
            self.game.change_scene(SelectScene(self.game))
        elif event.key == pygame.K_ESCAPE:
            self.game.change_scene(MenuScene(self.game))

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(S.BG)
        panel = pygame.Rect(0, 0, S.WIDTH, S.HEIGHT)
        pygame.draw.rect(surface, S.PANEL, panel)
        pygame.draw.rect(surface, S.PANEL_LIGHT, panel, 2)
        cls = (self.cls1, self.cls2)[self.winner]
        col = (S.P1_COLOR, S.P2_COLOR)[self.winner]
        draw_text(surface, "GAME OVER", 28, S.GREY, (640, 160), "midtop", display=True)
        draw_text(surface, f"{cls.NAME} WINS", 56, col, (640, 220), "midtop", display=True)
        draw_text(surface, f"PLAYER {self.winner + 1} • {cls.TITLE}", 14, S.WHITE, (640, 320), "midtop")
        draw_text(surface, "ENTER  rematch      C  character select      ESC  menu", 13, S.GREY, (640, 420), "midtop")


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(S.TITLE)
        self.screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.controllers = (make_player_one_controller(), make_player_two_controller())
        self.scene: Scene = MenuScene(self)

    def change_scene(self, scene: Scene) -> None:
        self.scene = scene

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(S.FPS) / 1000.0, 1 / 30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.scene.handle_event(event)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
