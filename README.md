# STREET CLASH — 2-player Pygame fighter

```
pip install pygame>=2.5
python main.py
```

## Folder structure

```
imageFolder/          # portraits, sprite sheets, maps, kunai, emptyImage
main.py               # scenes + game loop
ui.py                 # HUD, cards, fonts, image loader
character.py          # character data (name, title, images, stats)
component.py          # StateMachine, Hitbox, InputController
skill.py              # skill logic
entities.py           # fighters, projectiles, particles
combat.py             # collision + BattleWorld
events.py             # EventDispatcher + HitInfo
stage.py              # background maps
settings.py           # constants
```

## Controls

| | Player 1 | Player 2 |
|---|---|---|
| Move / jump / guard | A D / W / S | Arrows |
| Attack | F | Right Shift (or Numpad 0) |
| Skills | Q  E  C | Num 1 2 3 (or 1 2 3) |

Select: move cursor with move keys, confirm with Attack. Best of 3 rounds.

4 maps rotate each round. Characters use sprite sheets (idle / attack / ko).
Skill icons use `emptyImage.png`. Kunai is an image.
