# Code Side
##  Prompt:
<img src="./docs/img_1.png"  title="UI"/>


```
สร้างเกมต่อสู้ 2 มิติ (2-Player Street Fighting Game) ด้วย Python และ Pygame ในธีม Neo-Brutalist / Luxury Minimalist (พื้นหลังสีดำเข้ม #121212, ผู้เล่น 1 Kai สีฟ้า #00E5FF, ผู้เล่น 2 Nyx สีแดง/ชมพู #FF1744) พร้อมระบบ UI/HUD หลอดเลือด ตัวจับเวลา และระบบจัดการภาพสำรอง (Fallback) เมื่อไม่พบไฟล์ภาพ

หลักการ OOP 8 ข้อที่ต้องปฏิบัติตาม:

- Classes, Objects และ Constructors (__init__)
- Encapsulation, Validation และ Properties (@property)
- Composition และการแบ่งความรับผิดชอบของคลาส
- Inheritance และ Game Object พื้นฐาน
- Method Overriding และความเชี่ยวชาญเฉพาะตัวของพฤติกรรม
- Polymorphism และกลุ่มวัตถุเกม (Collections)
- Abstract Base Classes (ABCs) สำหรับสกิลและตัวละคร
- Collision Detection, Events และ Observer Pattern

ตัวละครและสกิลตัวอย่าง:
- Kai (The Urban Brawler): พลังสูง สายปะทะ (สกิล Q: Plasma Hook, E: Kinetic Charge, C: Overdrive Rush)
- Nyx (Shadow Shinobi): ความเร็วสูง สายลอบเร้น (สกิล Num 1: Phantom Dash, Num 2: Nanite Kunai, Num 3: Shadow Veil)
```
##  Output:

```
assets/                                         # portraits, sprite sheets, maps, kunai, emptyImage
main.py                                         # scenes + game loop
ui.py                                           # HUD, cards, fonts, image loader
character.py (removed after refactor)           # character data (name, title, images, stats)
component.py                                    # StateMachine, Hitbox, InputController
skill.py                                        # skill logic
entities.py                                     # fighters, projectiles, particles
combat.py                                       # collision + BattleWorld
events.py                                       # EventDispatcher + HitInfo
stage.py (removed after refactor)               # background maps
settings.py                                     # constants
```
[Download TSEFighter_FirstPrompt.zip](./docs/TSEFighter_FirstPrompt.zip)


# Comparison: `main.py` Before vs After Refactoring by Hand

---

## 1. `Scene` Abstract Base Class

**Before:** `update` เป็น `@abstractmethod` ทำให้ทุก subclass ต้องบังคับ implement เมธอดนี้
```python
class Scene(ABC):
    @abstractmethod
    def update(self, dt: float) -> None: ...
```

**After:** `update` มีการทำงานเริ่มต้นเป็น `pass` ทำให้ฉากที่ไม่มีการอัปเดตอย่าง `GameOverScene` สามารถละเว้นได้
```python
class Scene(ABC):
    def update(self, dt: float) -> None:
        pass
```

---

## 2. Roster & Character Selection (`ROSTER` & `SelectScene`)

**Before:** ใช้ `RosterEntry` dataclass โดยมีตัวละครที่เล่นได้ 2 ตัว และช่องที่ล็อกไว้อีก 6 ช่อง
```python
@dataclass(frozen=True)
class RosterEntry:
    name: str
    title: str
    cls: Optional[type[Fighter]] = None

ROSTER = [
    RosterEntry("KAI", "THE URBAN BRAWLER", Kai),
    RosterEntry("NYX", "SHADOW SHINOBI", Nyx),
    RosterEntry("VIKTOR", "COMING SOON"), RosterEntry("ROXY", "COMING SOON"),
    RosterEntry("RAIDEN-X", "COMING SOON"), RosterEntry("VESPER", "COMING SOON"),
    RosterEntry("OMEGA", "COMING SOON"), RosterEntry("GHOST", "COMING SOON"),
]
```

**After:** เก็บคลาสตัวละครทั้ง 8 ตัวเป็น list โดยตรง และดึงค่า `NAME`, `PLAYABLE`, `PORTRAIT_PATH` จากแต่ละคลาสโดยตรง
```python
ROSTER = [ Jack, Art, Pao, Piya, Oat, Jin, Night, Poom ]

names = [e.NAME for e in ROSTER]
playable = [e.PLAYABLE for e in ROSTER]
paths = [e.PORTRAIT_PATH for e in ROSTER]
self.grid = RosterGrid(pygame.Rect(420, 90, 440, 560), names, playable, paths)
```

---

## 3. `MenuScene` & Controls

**Before:** ใช้แบรนด์ **STREET CLASH** ตัวอักษรขนาดใหญ่ และใช้ปุ่ม `F` / `Q E C` (P1) กับ `R-SHIFT` / `NUM 1 2 3` (P2)
```python
draw_text(surface, "STREET", 120, S.P1_COLOR, (640 - 8, 120), "midtop", display=True)
draw_text(surface, "CLASH", 120, S.P2_COLOR, (640 + 8, 235), "midtop", display=True)

for col, x, lines in (
    (S.P1_COLOR, 260, ["PLAYER 1", "A / D  move     W  jump     S  guard", "F  attack", "Q  E  C  skills"]),
    (S.P2_COLOR, 1020, ["PLAYER 2", "← / →  move   ↑  jump   ↓  guard", "R-SHIFT  attack", "NUM 1 2 3  skills (or 1 2 3)"]),
):
    pygame.draw.rect(surface, col, (x - 230, 520, 460, 130), 1)
```

**After:** เปลี่ยนเป็นแบรนด์ **TSE Fighter** ปรับดีไซน์กล่องเป็นสไตล์ Neo-Brutalist (`S.PANEL`, `S.PANEL_LIGHT`) และอัปเดตปุ่มควบคุมใหม่ (`V` / `F G H` สำหรับ P1 และ `NUM 0` / `NUM 1 2 3` สำหรับ P2)
```python
panel = pygame.Rect(0, 0, S.WIDTH, S.HEIGHT)
pygame.draw.rect(surface, S.PANEL, panel)
pygame.draw.rect(surface, S.PANEL_LIGHT, panel, 2)

draw_text(surface, "TSE", 80, S.P1_COLOR, (640 - 65, 130), "midtop", display=True)
draw_text(surface, "Fighter", 80, S.P2_COLOR, (640 + 15, 170), "midtop", display=True)

for col, x, lines in (
    (S.P1_COLOR, 340, ["PLAYER 1", "A / D  move     W  jump     S  guard", "V  attack", "F G H  skills"]),
    (S.P2_COLOR, 940, ["PLAYER 2", "← / →  move   ↑  jump   ↓  guard", "NUM 0   attack", "NUM 1 2 3  skills"]),
):
    box = pygame.Rect(x - 180, 380, 360, 120)
    pygame.draw.rect(surface, S.PANEL_LIGHT, box)
    pygame.draw.rect(surface, col, box, 1)
```

---

## 4. `Stage` & `BattleScene`

**Before:** เรียกใช้คลาส `Stage` จากไฟล์ `stage.py` และส่งค่า `self._t` เพื่อวาดฉากหลังแบบมีแอนิเมชัน
```python
# Stage is imported from stage.py
self.stage = Stage()

# Inside draw():
self.stage.draw(surface, self._t)
```

**After:** ย้าย `MAPS` และคลาส `Stage` มาไว้ใน `main.py` โดยตรง พร้อมสุ่มภาพพื้นหลังใหม่ทุกครั้งที่เริ่มยก และลบไฟล์ `stage.py` ออก
```python
MAPS = [
    ("Classroom", "assets/map1.png"),
    ("Library", "assets/map2.png"),
    ("Nightclub", "assets/map3.png"),
    ("Green Canteen", "assets/map4.png"),
]

class Stage:
    def __init__(self, map_index: int | None = None) -> None:
        self.rect = S.ARENA.copy()
        self.NAME, path = random.choice(MAPS)
        self._bg = load_image(path, self.rect.size)

# Inside BattleScene._start_round():
self.stage = Stage()  # new map each round
```

# Comparison: `entities.py` Before vs After Refactoring by Hand

## 1. Projectiles (`KunaiProjectile` vs `SpriteProjectile`)

**Before:** มี `KunaiProjectile` ที่วาดรูปทรงเรขาคณิตด้วย `pygame.draw.polygon` และมีระบบ `bleed`
```python
class KunaiProjectile(Projectile):
    def on_hit(self, target: "Fighter") -> None:
        if not target.is_blocking:
            target.apply_bleed(self._bleed_dps, self._bleed_time, self.owner)

    def draw(self, surface: pygame.Surface) -> None:
        ...
        pygame.draw.polygon(surface, self.owner.color, [...])
```

**After:** เปลี่ยนมาใช้ `SpriteProjectile` ที่โหลดรูปภาพมาแสดงผลและพลิกภาพตามทิศทาง พร้อมคลาสลูกสำหรับสกิลต่างๆ
```python
class SpriteProjectile(Projectile):
    def __init__(self, ..., sprite: str, ...) -> None:
        ...
        self._img = load_image(os.path.join(S.IMAGE_DIR, sprite), size)

    def draw(self, surface: pygame.Surface) -> None:
        img = pygame.transform.flip(self._img, True, False) if self.vel.x < 0 else self._img
        surface.blit(img, img.get_rect(center=self.rect.center))

class SoundwaveProjectile(SpriteProjectile): ...
class QuakeProjectile(SpriteProjectile): ...
class SparkProjectile(SpriteProjectile): ...
class SRSDocumentProjectile(SpriteProjectile): ...
```

---

## 2. `BaseFighter` ABC & `Fighter` Inheritance

**Before:** แยก `BaseFighter(ABC)` ออกมาเป็น Contract บังคับให้มี `create_skills`, `on_damage_taken`, และ `on_hit_landed`
```python
class BaseFighter(ABC):
    @abstractmethod
    def create_skills(self) -> list["BaseSkill"]: ...
    @abstractmethod
    def on_damage_taken(self, hit: HitInfo, damage: float) -> None: ...
    @abstractmethod
    def on_hit_landed(self, hit: HitInfo, target: "Fighter") -> None: ...

class Fighter(GameObject, BaseFighter):
    ...
```

**After:** ลบ `BaseFighter` ออก ให้ `Fighter` สืบทอดจาก `GameObject` โดยตรง และบังคับแค่ `@abstractmethod def create_skills`
```python
class Fighter(GameObject):
    ...
    @abstractmethod
    def create_skills(self) -> list["BaseSkill"]:
        pass
```

---

## 3. Rendering & Animation (Stickman vs SpriteSheet)

**Before:** วาดตัวละครแบบ Stickman ด้วยโค้ด (`_draw_stick`, `_draw_ko`, `_limb`)
```python
    def draw(self, surface: pygame.Surface) -> None:
        ...
        self._draw_stick(surface, self.rect.centerx, self.rect.bottom)
        self._draw_tag(surface)
```

**After:** เปลี่ยนมาใช้ `SpriteSheet` ตัดแบ่งเฟรมภาพ (`_slice_sheet`) เล่นแอนิเมชัน (`_tick_animation`) และวาดวงแหวนสถานะใต้เท้า (`STATUS_COLORS`)
```python
    POSES = ("idle", "walk", "attack", "jumpattack", "guard", "jump", "hit", "ko")
    STATUS_COLORS: dict[str, tuple[int, int, int]] = {
        "marked": S.PURPLE,
        "veiled": S.WHITE,
        "kinetic": S.BLUE,
        "creatine": S.RED,
    }

    def _slice_sheet(self, sheet: pygame.Surface) -> dict[str, list[pygame.Surface]]:
        ...

    def draw(self, surface: pygame.Surface) -> None:
        ...
        frame = self._current_frame()
        surface.blit(frame, frame.get_rect(midbottom=(self.rect.centerx, self.rect.bottom)))
```

---

## 4. Stats & Combat Mechanics

**Before:** มีค่าสถานะ `SPC`, ระบบเลือดไหล (`_bleeds`), และระบบกระเด็นชนกำแพง (`_bounce_window` / `WALL BOUNCE!`)
```python
    BASE_STATS: dict[str, int] = {"PWR": 50, "DEF": 50, "SPD": 50, "SPC": 50}
    ...
    self._bleeds: list[list[object]] = []
    self._bounce_window = 0.0
```

**After:** ตัด `SPC`, `_bleeds`, และ `wall_bounce` ออก เหลือ 3 ค่าสถานะหลัก และเพิ่ม Hook `on_jump` ใน `perform()` เพื่อให้สกิลดักจับจังหวะกระโดดได้
```python
    BASE_STATS: dict[str, int] = {"PWR": 50, "DEF": 50, "SPD": 50}

    def perform(self, action: str) -> None:
        if action == "jump" and any(skill.on_jump(self) for skill in self.skills):
            return
        ...
```

---

## 5. Roster (`Kai` & `Nyx` vs 8 Characters)

**Before:** มีตัวละครต้นแบบ 2 ตัวคือ `Kai` และ `Nyx`
```python
class Kai(Fighter):
    NAME = "KAI"
    ...

class Nyx(Fighter):
    NAME = "NYX"
    ...
```

**After:** เพิ่มตัวละครเป็น 8 ตัว พร้อมกำหนด `SHEET_PATH`, `PORTRAIT_PATH`, และ `PLAYABLE`
```python
class Jack(Fighter):
    NAME = "T. Jack"
    TITLE = "God of Python"
    BASE_STATS = {"PWR": 60, "DEF": 60, "SPD": 95}
    SHEET_PATH = "assets/jack_sheet.png"
    PORTRAIT_PATH = "assets/jack_portrait.png"
    ...

class Art(Fighter): ...
class Pao(Fighter): ...
class Piya(Fighter): ...
class Oat(Fighter): ...
class Jin(Fighter): ...

class Night(Fighter):
    NAME = "Night"
    TITLE = "Coming Soon!"
    PLAYABLE = False
    ...

class Poom(Fighter): ...
```
# Comparison: `skill.py` Before vs After Refactoring

## 1. ระบบจัดการ Sprite Sheet และ Timer (`BaseSkill`)

**Before:** คลาสแม่ `BaseSkill` เน้นโครงสร้างตามหลัก Template Method Pattern โดยให้ `try_cast()` เป็นตัวกลางจัดการเงื่อนไข คูลดาวน์ และพลังงาน โดยไม่มีระบบ Timer หรือ Sprite Sheet ในคลาสแม่

```python
    def try_cast(self, caster: Fighter, target: Optional[Fighter]) -> bool:
        if target is None or not caster.state_machine.can_act or not self.can_cast(caster):
            return False
        caster.energy -= self.ENERGY_COST
        self._cooldown_left = self.COOLDOWN
        caster.dispatcher.emit("on_skill_cast", caster=caster, skill=self)
        self.execute(caster, target)
        return True
```

**After:** เพิ่มระบบโหลดแอนิเมชัน Sprite Sheet (`load_sprite`, `play_pose`) และระบบจัดการ Timer ด้วย Callback (`start_timer`, `cancel_timers`, `_tick_timers`) รวมถึง Hook `on_jump` เข้ามาในคลาสแม่ `BaseSkill` เพื่อรองรับสกิลที่ทำงานหลายจังหวะ

```python
    def load_sprite(self) -> None:
        if not self.SHEET_PATH:
            return
        sheet = load_image(self.SHEET_PATH)
        ...

    def start_timer(self, delay: float, callback: Callable[[], None],
                    key: Optional[str] = None) -> None:
        self._timers.append({"left": delay, "cb": callback, "key": key})

    def on_jump(self, caster: Fighter) -> bool:
        return False
```

---

## 2. รายการสกิลของตัวละคร (Character Skills)

**Before:** โฟกัสเฉพาะสกิลของตัวละครหลัก 2 ตัว ได้แก่ **Kai** (`PlasmaHook`, `KineticCharge`, `OverdriveRush`) และ **Nyx** (`PhantomDash`, `NaniteKunai`, `ShadowVeil`)

```python
class PlasmaHook(BaseSkill):
    NAME = "PLASMA HOOK"
    DESCRIPTION = "Launches an electrified high uppercut that wall-bounces opponents on clean hit."
    COOLDOWN = 3.0
    ENERGY_COST = 15.0
    ICON = "hook"

    def execute(self, caster: Fighter, target: Fighter) -> None:
        caster.state_machine.change(State.CAST, lock=0.55)
        caster.hitbox.arm(damage=10 + 10 * caster.power, width=90, height=130, offset_x=55, offset_y=95,
                          windup=0.12, active=0.18, knockback=(700, -620), stun=0.55,
                          tags={"wall_bounce"})
        caster.play_pose("uppercut", 0.5)
        caster.burst(10, S.P1_COLOR, 220)

class KineticCharge(BaseSkill): ...
class OverdriveRush(BaseSkill): ...
class PhantomDash(BaseSkill): ...
class NaniteKunai(BaseSkill): ...
class ShadowVeil(BaseSkill): ...
```

**After:** ขยายสกิลให้รองรับตัวละครใหม่ทั้ง 6 ตัว (Jack, Art, Pao, Piya, Oat, Jin) พร้อมกำหนด `ICON`, `SHEET_PATH`, `SHEET_TIME` และลูกเล่นเฉพาะตัว

```python
class PacMan_Chomp(BaseSkill):
    NAME = "Pac-Man Chomp"
    ...

class CriticalRoast(BaseSkill): ...
class CPUSmash(BaseSkill): ...
class SRS_Barrage(BaseSkill): ...
class DoubleMuscle_Rush(BaseSkill): ...
class BottleBomb(BaseSkill): ...
```

<br/>
<br/>
<br/>
<br/>
<br/>

# Graphic Side (Before Photoshop)


##  Sprite Sheet Prompt:

```
ขนาดต่อ
SpriteSheet 1 ช่อง:
 80x180 pixel
โครงสร้าง
Sprite Sheet:
แบ่งเป็น 4 ท่าทางหลัก (แผ่นต่อตัวละคร
หรือแยกแผ่นตามความเหมาะสม) โดยแต่ละท่ามี 4 เฟรมภาพ (4
รูปต่อแถว):
1.      ท่า Idle (ยืนหายใจ/รอ): 4 เฟรม
2.      ท่า Walk (เดิน): 4 เฟรม
3.      ท่า Attack (โจมตี): 4 เฟรม
4.      ท่า Jump Attack (กระโดดโจมตี): 4 เฟรม
5.      ท่า Guard (ป้องกัน): 4 เฟรม
6.      ท่า Jump (กระโดด): 4 เฟรม
7.      ท่า Hit (โดนโจมตี): 4 เฟรม
8.      ท่า Faint (หมดแรง/แพ้): 4 เฟรม 
```
<table>
<tr>
<td align="center">
<img src="./docs/img_2.png" width="100%">
</td>

<td align="center">
<img src="./docs/img_3.png" width="100%">
</td>

<td align="center">
<img src="./docs/img_6.png" width="100%">
</td>
</tr>
</table>

## Character Portrait Prompt:

```
(Appedn Person Image)
ทำไอคอนหน้าแต่ล่ะตัวละครให้หน่อย 300x150 pixel ขอแนวเดิม ขอเป็นหนจริงๆเลยไม่ต้องปรับแก้อะไร

ขอแบบรูปเต็มๆ 300x150 ให้เห็นหน้าอยู่ชัดๆไม่ต้องตัดแค่หน้าตรงกลางแล้ว

เอาเป็น pixelart แบบนี้แต่หันหน้ามาที่กล้องไม่เอากรอบฟ้าเต็มรูปเลยแยกแต่ละคนนะไม่ต้องรวมเหมือนในรูปขนาด 300 × 150 px ทุกภาพเอาใส่ zip
```
<table>
<tr>
<td align="center">
<img src="./assets/jack_portrait.png" width="100%">
</td>

<td align="center">
<img src="./assets/art_portrait.png" width="100%">
</td>
<td align="center">
<img src="./assets/pao_portrait.png" width="100%">
</td>
<td align="center">
<img src="./assets/piya_portrait.png" width="100%">
</td>
</tr>
</table>

## Map Style Prompt:

```
ช่วยเจนภาพด่านเป็นพิกเซลจำลองจากสถานที่ในมธ ที่แรก ห้องเรียน , ศูนย์การเรียนรู้ , กํ้ากึ่ง
แมะที่สามเป็นร้ทนเหล้ามืดๆบนเพดานเป็นแปะดาวดวงเล็กๆเยอะๆ
ขอแมพ class room
ขอแมพ Learning center ต่อ
ขอแมพ KAM-KUNG ต่อ
ขอแมพโรงอาหารกรีน มหาวิทยาลัยธรรมศาตร์อีกแมพนึง
แมพกํ้ากึ้่งผิดอันต้อนอันนี้ไม่ต้องเอาป้ายสเตจมา
ขอแมพ learning center ใหม่หน่อยตัด stage ซ้ายบนออก
เอาแมพ Green center ไปใหม่หน่อยตัดซ้ายบนออก
ทุกรูปคือขนาด 1280x486 ใช่ไหมความสูงจากพื้นล่างต้อง 86 pixel นะ
```
<table>
<tr>
<td align="center">
<img src="./docs/ss_map1.png" width="100%">
</td>

<td align="center">
<img src="./docs/ss_map2.png" width="100%">
</td>

<td align="center">
<img src="./docs/ss_map3.png" width="100%">
</td>

</tr>
</table>

## Skill Icon Prompt:

```
ออกแบบไอคอนสกิลให้หน่อยขอเป็นวงกลม
1.	Jack
God of Python 
Skills
Pac-Man Chomp – พุ่งกัดศัตรูอย่างรวดเร็ว
Power Pellet – กินเม็ดพลังเพื่อเพิ่มความเร็ว
Ghost Frenzy – พุ่งทะลุศัตรูและโจมตีต่อเนื่อง
Stats: PWR 85 | DEF 65 | SPD 95

2.	Art
ฉายา: The Toxic Speaker
Skills
Critical Roast – ยิงคลื่นเสียงจากคำพูดโจมตีศัตรู
Shut Up! – ตะโกนผลักศัตรูออกไป
Emotional Damage – ปล่อยคำพูดทำลายจิตใจพร้อมคลื่นเสียงรุนแรง
Stats: PWR 90 | DEF 60 | SPD 75

3.	Pao
ฉายา: The CPU Destroyer
Skills
CPU Smash – ใช้ CPU ยักษ์ทุบศัตรู
Overclock Charge – เพิ่มพลังแล้วพุ่งชนศัตรู
Blue Screen Crash – ทุบพื้นปล่อยคลื่นกระแทกวงกว้าง
Stats: PWR 100 | DEF 95 | SPD 40

4.	Piya
ฉายา: The Missing Teacher 
Skills
Phantom Dash – หายตัวพุ่งไปด้านหลังศัตรู
Vanishing Counter – หายตัวหลบแล้วสวนกลับ
Shadow Veil – สร้างควันพรางตัวและโจมตีต่อเนื่อง
Stats: PWR 70 | DEF 55 | SPD 100

5.	Oat
ฉายา: Body Builders
Skills
Muscle Punch – ชกด้วยกล้ามแขนสุดทรงพลัง สร้างความเสียหายสูง
Protein Shake – ดื่มเวย์เพิ่มพลังโจมตีและฟื้นฟู HP
Beast Mode – เกร็งกล้ามเนื้อเพิ่มพลังและปล่อยหมัดคอมโบต่อเนื่อง
Stats: PWR 95 | DEF 100 | SPD 55

6.	Jin
ฉายา: Hole Destroyer
Skills
Bottle Bomb – ปาขวดใส่ศัตรูจากระยะไกล สร้างความเสียหายและทำให้ชะงัก
เด็กแว้นซิ่งนรก (Motorcycle Rush) – ขี่มอเตอร์ไซค์พุ่งชนศัตรูอย่างรวดเร็ว
Gangster Drift – ดริฟต์มอเตอร์ไซค์เป็นวงกว้าง สร้างความเสียหายรอบตัวและกระแทกศัตรูกระเด็น
Stats: PWR 90 | DEF 65 | SPD 100

ช่วยคอปภาพเอาแค่ไอคอนมาให้หน่อยทำเป็น zip โดยแต่ละไฟล์ใช้ชื่อตัวละครตามด้วยชื่อ skill1-skill3
```
<table>
<tr>
<td align="center">
<img src="./assets/skill/jack_iconskill_1.png" width="100%">
</td>

<td align="center">
<img src="./assets/skill/jack_iconskill_2.png" width="100%">
</td>

<td align="center">
<img src="./assets/skill/jack_iconskill_3.png" width="100%">
</td>

<td align="center">
<img src="./assets/skill/art_iconskill_1.png" width="100%">
</td>
<td align="center">
<img src="./assets/skill/art_iconskill_2.png" width="100%">
</td>
<td align="center">
<img src="./assets/skill/art_iconskill_3.png" width="100%">
</td>
<td align="center">
<img src="./assets/skill/pao_iconskill_1.png" width="100%">
</td>
<td align="center">
<img src="./assets/skill/pao_iconskill_2.png" width="100%">
</td>
<td align="center">
<img src="./assets/skill/pao_iconskill_3.png" width="100%">
</td>
</tr>
</table>


# Graphic Side (Comparing After Photoshop)

## Sprite Sheet:
[Download SpriteSheet.psd](./docs/SpriteSheet.psd)
<table>
<tr>
<td align="center">
<img src="./docs/ss_1.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/jack_sheet.png" width="100%">
<br><b>After Photoshop</b>
</td>

<td align="center">
<img src="./docs/ss_2.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/art_sheet.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
<tr>
<td align="center">
<img src="./docs/ss_3.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/pao_sheet.png" width="100%">
<br><b>After Photoshop</b>
</td>
<td align="center">
<img src="./docs/ss_4.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/piya_sheet.png" width="100%">
<br><b>After Photoshop</b>
</td>

</tr>
<tr>
<td align="center">
<img src="./docs/ss_5.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/oat_sheet.png" width="100%">
<br><b>After Photoshop</b>
</td>
<td align="center">
<img src="./docs/ss_6.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/jinn_sheet.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
</table>


## Sprite Sheet Specific Skill:
[Download SkillSprite.psd](./docs/SkillSprite.psd)
<table>
<tr>
<td align="center">
<img src="./docs/ss_skill1.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/jack_skill1.png" width="100%">
<br><b>After Photoshop</b>
</td>

<td align="center">
<img src="./docs/ss_skill2.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/jack_skill2.png" width="100%">
<br><b>After Photoshop</b>
</td>
<td align="center">
<img src="./docs/ss_skill3.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/art_skill1.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
<tr>
<td align="center">
<img src="./docs/ss_skill4.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/art_skill2.png" width="100%">
<br><b>After Photoshop</b>
</td>

<td align="center">
<img src="./docs/ss_skill5.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/art_skill3.png" width="100%">
<br><b>After Photoshop</b>
</td>
<td align="center">
<img src="./docs/ss_skill6.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/pao_skill1.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
<tr>
<td align="center">
<img src="./docs/ss_skill7.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/pao_skill2.png" width="100%">
<br><b>After Photoshop</b>
</td>

<td align="center">
<img src="./docs/ss_skill8.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/pao_skill3.png" width="100%">
<br><b>After Photoshop</b>
</td>
<td align="center">
<img src="./docs/ss_skill9.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/piya_skill1.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
<tr>
<td align="center">
<img src="./docs/ss_skill10.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/piya_skill3.png" width="100%">
<br><b>After Photoshop</b>
</td>

<td align="center">
<img src="./docs/ss_skill11.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/oat_skill1.png" width="100%">
<br><b>After Photoshop</b>
</td>
<td align="center">
<img src="./docs/ss_skill12.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/oat_skill3.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
<tr>
<td align="center">
<img src="./docs/ss_skill13.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/jinn_skill1.png" width="100%">
<br><b>After Photoshop</b>
</td>

<td align="center">
<img src="./docs/ss_skill14.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/jinn_skill2.png" width="100%">
<br><b>After Photoshop</b>
</td>
<td align="center">
<img src="./docs/ss_skill15.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/jinn_skill3.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
</table>

## Maps Style:
<table>
<tr>
<td align="center">
<img src="./docs/ss_map1.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/map1.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
<tr>

</td>
<td align="center">
<img src="./docs/ss_map2.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/map2.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
<tr>
<td align="center">
<img src="./docs/ss_map3.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/map3.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
<tr>

<td align="center">
<img src="./docs/ss_map4.png" width="100%">
<br><b>Before Photoshop</b>
</td>

<td align="center">
<img src="./assets/map4.png" width="100%">
<br><b>After Photoshop</b>
</td>
</tr>
</table>