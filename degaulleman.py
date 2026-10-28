"""DeGaulleMan - un jeu de labyrinthe original.

Pierrot doit manger toutes les pastilles du labyrinthe en échappant aux
Paperasses. Les cocardes tricolores permettent de les renvoyer au bureau.

Easter egg : tapez GAULLE (ou le code Konami) pour que le Général prenne
la place de Pierrot.
"""
import math
import os
import random
import sys
from array import array

import pygame

# ---------------------------------------------------------------------------
# Labyrinthe
#   #  mur          .  pastille        o  cocarde (super-pastille)
#   -  porte        G  bureau des Paperasses
#   P  départ       (espace)  couloir vide
# ---------------------------------------------------------------------------
MAZE = [
    "#####################",
    "#o........#........o#",
    "#.###.###.#.###.###.#",
    "#.#...#.......#...#.#",
    "#.#.#.#.#####.#.#.#.#",
    "#...#.....#.....#...#",
    "###.###.#.#.#.###.###",
    "###.....#   #.....###",
    "###.###.##-##.###.###",
    "  ....#.#GGG#.#....  ",
    "###.#.#.#####.#.#.###",
    "###.#.....P.....#.###",
    "###.#.###.#.###.#.###",
    "#.......#.#.#.......#",
    "#.##.##.#...#.##.##.#",
    "#o.#.....###.....#.o#",
    "##.#.#.#.....#.#.#.##",
    "#....#.#.###.#.#....#",
    "#.####.#..#..#.####.#",
    "#.........#.........#",
    "#####################",
]

COLS = len(MAZE[0])
ROWS = len(MAZE)
TILE = 24
HUD_TOP = 48
HUD_BOTTOM = 40
WIDTH = COLS * TILE
HEIGHT = HUD_TOP + ROWS * TILE + HUD_BOTTOM
FPS = 60

UP, DOWN, LEFT, RIGHT, STOP = (0, -1), (0, 1), (-1, 0), (1, 0), (0, 0)
DIRS = [UP, LEFT, DOWN, RIGHT]  # ordre de préférence en cas d'égalité

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLEU = (35, 70, 215)
ROUGE = (225, 35, 50)
JAUNE = (255, 215, 60)
CREME = (255, 232, 200)

EXIT_TILE = (10, 7)    # case devant la porte du bureau
HOUSE_ROW = 9
BONUS_TILE = (10, 11)


def find_cells(ch):
    return [(c, r) for r, row in enumerate(MAZE) for c, v in enumerate(row) if v == ch]


START_TILE = find_cells("P")[0]
TUNNEL_ROW = next(r for r, row in enumerate(MAZE) if row[0] != "#" and row[-1] != "#")


def walkable(c, r):
    if r < 0 or r >= ROWS:
        return False
    if r == TUNNEL_ROW:
        c %= COLS
    if c < 0 or c >= COLS:
        return False
    return MAZE[r][c] not in "#-G"


def reverse(d):
    return (-d[0], -d[1])


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def data_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "DeGaulleMan")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


# ---------------------------------------------------------------------------
# Sons (synthétisés à la volée, aucun fichier externe)
# ---------------------------------------------------------------------------
class Sfx:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.loop_name = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.rate, _, self.channels = pygame.mixer.get_init()
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(2)
            self.loop_ch = pygame.mixer.Channel(0)
            self.eat_ch = pygame.mixer.Channel(1)
        except pygame.error:
            return
        self.ok = True
        s = {}
        s["dot_a"] = self.render([(330, 560, 0.055, "tri", 0.35)])
        s["dot_b"] = self.render([(560, 330, 0.055, "tri", 0.35)])
        s["siren"] = self.render([(420, 700, 0.22, "tri", 0.12), (700, 420, 0.22, "tri", 0.12)])
        s["fright"] = self.render([(180, 260, 0.09, "sq", 0.07), (260, 180, 0.09, "sq", 0.07)])
        s["retreat"] = self.render([(900, 1500, 0.07, "sq", 0.06), (1500, 900, 0.07, "sq", 0.06)])
        s["power"] = self.render([(200, 900, 0.15, "sq", 0.15)])
        s["eat_ghost"] = self.render([(150, 1800, 0.28, "sq", 0.18)])
        s["bonus"] = self.notes([(72, .06), (76, .06), (79, .06), (84, .12)], "sq", 0.18)
        s["life"] = self.notes([(96, .08), (0, .04)] * 5, "sin", 0.3)
        s["death"] = self.render(
            [(900 - i * 90, 300 - i * 25, 0.13, "sq", 0.16) for i in range(8)]
            + [(0, 0, 0.08, "sq", 0)]
            + [(500, 120, 0.12, "noise", 0.25), (0, 0, 0.05, "sq", 0), (500, 120, 0.12, "noise", 0.25)]
        )
        tune = [(72, .13), (76, .13), (79, .13), (76, .13), (84, .13), (79, .13), (76, .13), (79, .13),
                (74, .13), (77, .13), (81, .13), (77, .13), (83, .13), (79, .13), (74, .13), (79, .13),
                (84, .45)]
        s["start"] = self.notes(tune, "sq", 0.16)
        # La Marseillaise (Rouget de Lisle, 1792 - domaine public), premières mesures
        marseillaise = [(62, .12), (62, .24), (62, .12), (67, .32), (67, .32), (69, .32), (69, .32),
                        (74, .5), (71, .2), (67, .32), (67, .2), (71, .15), (67, .15), (64, .32),
                        (72, .6), (69, .2), (66, .2), (67, .7)]
        s["marseillaise"] = self.notes(marseillaise, "sq", 0.16)
        s["egg_off"] = self.notes([(67, .1), (60, .25)], "tri", 0.3)
        s["pause"] = self.notes([(79, .05), (0, .03), (79, .05)], "sq", 0.12)
        self.sounds = s

    def render(self, segs):
        out = array("h")
        phase = 0.0
        rate = self.rate
        fade_in = 0.004 * rate + 1
        fade_out = 0.006 * rate + 1
        for f0, f1, dur, wave, vol in segs:
            n = int(rate * dur)
            for i in range(n):
                f = f0 + (f1 - f0) * (i / n)
                phase += f / rate
                p = phase % 1.0
                if f <= 0 or vol <= 0:
                    v = 0.0
                elif wave == "sq":
                    v = 1.0 if p < 0.5 else -1.0
                elif wave == "tri":
                    v = 4.0 * abs(p - 0.5) - 1.0
                elif wave == "sin":
                    v = math.sin(2 * math.pi * p)
                else:
                    v = random.uniform(-1, 1)
                env = min(1.0, i / fade_in, (n - i) / fade_out)
                sample = int(v * vol * env * 32767)
                for _ in range(self.channels):
                    out.append(sample)
        return pygame.mixer.Sound(buffer=out.tobytes())

    def notes(self, seq, wave, vol):
        return self.render([(midi(n) if n else 0, midi(n) if n else 0, d, wave, vol) for n, d in seq])

    def play(self, name):
        if self.ok and not self.muted:
            self.sounds[name].play()

    def dot(self, flip):
        if self.ok and not self.muted:
            self.eat_ch.play(self.sounds["dot_b" if flip else "dot_a"])

    def loop(self, name):
        if not self.ok:
            return
        if self.muted:
            name = None
        if name == self.loop_name:
            return
        self.loop_name = name
        if name is None:
            self.loop_ch.stop()
        else:
            self.loop_ch.play(self.sounds[name], loops=-1)

    def stop_all(self):
        if self.ok:
            pygame.mixer.stop()
            self.loop_name = None

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop_all()


# ---------------------------------------------------------------------------
# Sprites (dessinés en code, rendus en x3 puis lissés)
# ---------------------------------------------------------------------------
_cache = {}


def _canvas(size, scale=3):
    w = size * scale
    return pygame.Surface((w, w), pygame.SRCALPHA), w


def _R(x, y, w, h):
    return pygame.Rect(int(x), int(y), int(w), int(h))


def sprite_pierrot(size, look, mouth):
    key = ("pierrot", size, look, mouth)
    if key in _cache:
        return _cache[key]
    s, W = _canvas(size)
    c = W // 2
    r = int(W * 0.40)
    fy = c + int(r * 0.12)
    ink = (70, 40, 35)
    # foulard rouge
    pygame.draw.ellipse(s, ROUGE, _R(c - r * 0.75, fy + r * 0.62, r * 1.5, r * 0.45))
    # visage
    pygame.draw.circle(s, (255, 244, 225), (c, fy), r)
    pygame.draw.circle(s, ink, (c, fy), r, 4)
    # béret bleu
    br = _R(0, 0, r * 2.05, r * 0.95)
    br.center = (c - int(r * 0.12), fy - int(r * 0.72))
    pygame.draw.ellipse(s, (28, 48, 150), br)
    pygame.draw.ellipse(s, (12, 20, 70), br, 4)
    pygame.draw.circle(s, (12, 20, 70), (br.centerx + int(r * 0.2), br.top + 4), int(r * 0.13))
    # yeux
    lx, ly = look
    ey = fy + int(r * 0.02)
    for ex in (c - int(r * 0.36), c + int(r * 0.36)):
        pygame.draw.ellipse(s, WHITE, _R(ex - r * 0.21, ey - r * 0.27, r * 0.42, r * 0.54))
        pygame.draw.ellipse(s, ink, _R(ex - r * 0.21, ey - r * 0.27, r * 0.42, r * 0.54), 2)
        pygame.draw.circle(s, BLACK, (ex + int(lx * r * 0.09), ey + int(ly * r * 0.12)), int(r * 0.12))
    # joues
    for cx in (c - int(r * 0.66), c + int(r * 0.66)):
        pygame.draw.circle(s, (255, 150, 150), (cx, fy + int(r * 0.36)), int(r * 0.13))
    # bouche
    my = fy + int(r * 0.52)
    if mouth:
        h = r * (0.18 + 0.14 * mouth)
        pygame.draw.ellipse(s, (130, 20, 35), _R(c - r * 0.2, my - h / 2, r * 0.4, h))
    else:
        pygame.draw.arc(s, ink, _R(c - r * 0.25, my - r * 0.2, r * 0.5, r * 0.3), math.pi * 1.1, math.pi * 1.9, 4)
    out = pygame.transform.smoothscale(s, (size, size))
    _cache[key] = out
    return out


def sprite_general(size, left, mouth):
    """Le Général : tête de profil avec képi à deux étoiles."""
    key = ("general", size, left, mouth)
    if key in _cache:
        return _cache[key]
    s, W = _canvas(size)
    k = W / 100.0

    def P(x, y):
        return (int(x * k), int(y * k))

    def RR(x, y, w, h):
        return _R(x * k, y * k, w * k, h * k)

    ink = (45, 28, 22)
    skin = (240, 200, 168)
    lw = max(2, int(1.6 * k))
    # col de l'uniforme
    col = [P(28, 86), P(72, 86), P(80, 100), P(20, 100)]
    pygame.draw.polygon(s, (112, 100, 64), col)
    pygame.draw.polygon(s, ink, col, lw)
    # tête allongée
    pygame.draw.ellipse(s, skin, RR(26, 28, 46, 62))
    pygame.draw.ellipse(s, ink, RR(26, 28, 46, 62), lw)
    # oreille
    pygame.draw.ellipse(s, (228, 180, 150), RR(19, 46, 13, 20))
    pygame.draw.ellipse(s, ink, RR(19, 46, 13, 20), lw)
    pygame.draw.arc(s, ink, RR(22, 50, 7, 12), -1.2, 1.2, lw)
    # le nez, illustre
    nose = [P(58, 44), P(88, 63), P(85, 69), P(63, 71)]
    pygame.draw.polygon(s, skin, nose)
    pygame.draw.lines(s, ink, False, nose, lw)
    # sourcil et oeil
    pygame.draw.line(s, (70, 60, 55), P(51, 43), P(65, 41), int(3 * k))
    pygame.draw.ellipse(s, (30, 20, 20), RR(56, 46, 6, 4))
    # moustache
    pygame.draw.rect(s, (85, 75, 70), RR(61, 72, 14, 5))
    # bouche
    if mouth:
        h = 4 + 4 * mouth
        pygame.draw.ellipse(s, (120, 30, 35), RR(61, 78, 11, h))
    else:
        pygame.draw.line(s, ink, P(62, 81), P(72, 80), lw)
    # menton
    pygame.draw.arc(s, ink, RR(48, 70, 24, 20), math.pi * 1.2, math.pi * 1.85, lw)
    # képi
    crown = [P(24, 10), P(68, 6), P(73, 35), P(23, 37)]
    pygame.draw.polygon(s, (128, 110, 72), crown)
    pygame.draw.polygon(s, ink, crown, lw)
    pygame.draw.line(s, (212, 175, 55), P(25, 10), P(68, 6), lw)
    band = [P(23, 27), P(72, 26), P(73, 35), P(23, 37)]
    pygame.draw.polygon(s, (32, 32, 38), band)
    leaves = [P(25 + i * 4, 31 + (2 if i % 2 else -2)) for i in range(12)]
    pygame.draw.lines(s, (212, 175, 55), False, leaves, lw)
    for sx in (40, 54):
        star(s, P(sx, 18), 4.5 * k, (230, 190, 60))
    visor = [P(52, 34), P(92, 38), P(90, 43), P(54, 41)]
    pygame.draw.polygon(s, (15, 15, 18), visor)
    out = pygame.transform.smoothscale(s, (size, size))
    if left:
        out = pygame.transform.flip(out, True, False)
    _cache[key] = out
    return out


def star(surf, center, r, color):
    cx, cy = center
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    pygame.draw.polygon(surf, color, pts)


def sprite_paper(size, color, look, frame, mode):
    """Une Paperasse : feuille administrative en colère."""
    key = ("paper", size, color, look, frame, mode)
    if key in _cache:
        return _cache[key]
    s, W = _canvas(size)
    m = int(W * 0.1)
    f = int(W * 0.22)
    bottom = W - m
    ink = (25, 15, 30)
    if mode == "fright":
        fill = (60, 75, 210)
    elif mode == "flash":
        fill = (235, 235, 245)
    else:
        fill = color
    teeth = 4
    tw = (W - 2 * m) / teeth
    pts = [(m, m), (W - m - f, m), (W - m, m + f), (W - m, bottom - 6)]
    for i in range(teeth * 2 + 1):
        x = W - m - i * tw / 2
        y = bottom - (6 if (i + frame) % 2 == 0 else -2)
        pts.append((x, y))
    pts.append((m, bottom - 6))
    pygame.draw.polygon(s, fill, pts)
    pygame.draw.polygon(s, ink, pts, 4)
    fold = [(W - m - f, m), (W - m - f, m + f), (W - m, m + f)]
    pygame.draw.polygon(s, tuple(min(255, v + 70) for v in fill), fold)
    pygame.draw.polygon(s, ink, fold, 3)
    cx = W // 2
    ey = int(W * 0.40)
    if mode == "normal":
        for i in range(3):
            y = int(W * (0.66 + i * 0.07))
            pygame.draw.line(s, tuple(max(0, v - 70) for v in fill), (m + 10, y), (W - m - 10 - i * 12, y), 3)
        lx, ly = look
        for ex in (cx - int(W * 0.15), cx + int(W * 0.15)):
            pygame.draw.ellipse(s, WHITE, _R(ex - W * 0.1, ey - W * 0.1, W * 0.2, W * 0.22))
            pygame.draw.circle(s, (20, 20, 90), (ex + int(lx * W * 0.05), ey + int(ly * W * 0.06)), int(W * 0.055))
        # sourcils froncés
        pygame.draw.line(s, ink, (cx - int(W * 0.27), ey - int(W * 0.15)), (cx - int(W * 0.05), ey - int(W * 0.08)), 5)
        pygame.draw.line(s, ink, (cx + int(W * 0.27), ey - int(W * 0.15)), (cx + int(W * 0.05), ey - int(W * 0.08)), 5)
    else:
        mouth_col = (230, 40, 40) if mode == "flash" else (245, 230, 200)
        for ex in (cx - int(W * 0.13), cx + int(W * 0.13)):
            pygame.draw.circle(s, mouth_col, (ex, ey), int(W * 0.045))
        my = int(W * 0.64)
        zig = [(cx - int(W * 0.25) + i * int(W * 0.0625), my + (5 if i % 2 else -5)) for i in range(9)]
        pygame.draw.lines(s, mouth_col, False, zig, 4)
    out = pygame.transform.smoothscale(s, (size, size))
    _cache[key] = out
    return out


def sprite_plane(size, color, d):
    """Paperasse capturée : repart au bureau en avion de papier."""
    key = ("plane", size, color, d)
    if key in _cache:
        return _cache[key]
    s, W = _canvas(size)
    pts = [(W * 0.92, W * 0.5), (W * 0.1, W * 0.2), (W * 0.32, W * 0.5), (W * 0.1, W * 0.8)]
    pygame.draw.polygon(s, (245, 245, 250), pts)
    pygame.draw.polygon(s, (40, 40, 60), pts, 4)
    pygame.draw.line(s, color, (W * 0.32, W * 0.5), (W * 0.92, W * 0.5), 6)
    angle = {RIGHT: 0, UP: 90, LEFT: 180, DOWN: -90}.get(d, 0)
    s = pygame.transform.rotate(s, angle)
    out = pygame.transform.smoothscale(s, (size, size))
    _cache[key] = out
    return out


def draw_cockade(surf, center, r):
    pygame.draw.circle(surf, ROUGE, center, r)
    pygame.draw.circle(surf, WHITE, center, max(1, int(r * 0.66)))
    pygame.draw.circle(surf, BLEU, center, max(1, int(r * 0.34)))


BONUSES = [
    ("baguette", 100), ("croissant", 300), ("camembert", 500), ("macaron", 700),
    ("éclair", 1000), ("tour Eiffel", 2000), ("coq", 3000), ("médaille", 5000),
]


def bonus_index(level):
    table = [0, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]
    return table[level - 1] if level <= len(table) else 7


def draw_bonus(surf, idx, center, size=22):
    cx, cy = center
    h = size / 2
    if idx == 0:  # baguette
        pts = [(cx - h, cy + h * 0.5), (cx + h * 0.6, cy - h), (cx + h, cy - h * 0.6), (cx - h * 0.6, cy + h)]
        pygame.draw.polygon(surf, (215, 160, 80), pts)
        pygame.draw.polygon(surf, (120, 70, 20), pts, 1)
        for i in range(3):
            t = -0.4 + i * 0.4
            x, y = cx + t * h, cy - t * h
            pygame.draw.line(surf, (250, 220, 160), (x - 2, y - 1), (x + 2, y + 3), 2)
    elif idx == 1:  # croissant
        pygame.draw.circle(surf, (225, 160, 60), (int(cx), int(cy)), int(h))
        pygame.draw.circle(surf, BLACK, (int(cx), int(cy + h * 0.55)), int(h * 0.7))
        for a in (-0.9, -0.3, 0.3, 0.9):
            x = cx + math.sin(a) * h * 0.8
            y = cy - math.cos(a) * h * 0.6
            pygame.draw.line(surf, (150, 90, 20), (x, y - 3), (x, y + 3), 2)
    elif idx == 2:  # camembert
        rect = _R(cx - h, cy - h * 0.6, size, h * 1.4)
        pygame.draw.ellipse(surf, (250, 245, 225), rect)
        pygame.draw.ellipse(surf, (200, 180, 120), rect, 2)
        pygame.draw.polygon(surf, (250, 215, 100), [(cx, cy), (cx + h, cy - h * 0.3), (cx + h, cy + h * 0.3)])
    elif idx == 3:  # macaron
        pygame.draw.ellipse(surf, (255, 140, 190), _R(cx - h, cy - h * 0.8, size, h * 0.8))
        pygame.draw.rect(surf, (255, 245, 230), _R(cx - h * 0.85, cy - h * 0.15, size * 0.85, h * 0.3))
        pygame.draw.ellipse(surf, (255, 140, 190), _R(cx - h, cy + h * 0.05, size, h * 0.8))
    elif idx == 4:  # éclair
        pygame.draw.rect(surf, (220, 170, 100), _R(cx - h, cy - h * 0.35, size, h * 0.8), border_radius=6)
        pygame.draw.rect(surf, (90, 50, 25), _R(cx - h, cy - h * 0.45, size, h * 0.4), border_radius=6)
    elif idx == 5:  # tour Eiffel
        col = (170, 110, 60)
        pygame.draw.polygon(surf, col, [(cx, cy - h), (cx + h * 0.8, cy + h), (cx + h * 0.4, cy + h),
                                        (cx, cy + h * 0.4), (cx - h * 0.4, cy + h), (cx - h * 0.8, cy + h)])
        pygame.draw.line(surf, col, (cx - h * 0.55, cy + h * 0.2), (cx + h * 0.55, cy + h * 0.2), 2)
        pygame.draw.line(surf, col, (cx - h * 0.3, cy - h * 0.3), (cx + h * 0.3, cy - h * 0.3), 2)
    elif idx == 6:  # coq
        pygame.draw.circle(surf, WHITE, (int(cx), int(cy + 2)), int(h * 0.75))
        pygame.draw.polygon(surf, BLEU, [(cx - h * 0.4, cy + 2), (cx - h, cy - h * 0.6), (cx - h * 0.9, cy + h * 0.4)])
        pygame.draw.circle(surf, ROUGE, (int(cx + h * 0.25), int(cy - h * 0.75)), int(h * 0.28))
        pygame.draw.polygon(surf, JAUNE, [(cx + h * 0.6, cy - h * 0.2), (cx + h, cy), (cx + h * 0.6, cy + h * 0.1)])
        pygame.draw.circle(surf, BLACK, (int(cx + h * 0.35), int(cy - h * 0.15)), 2)
    else:  # médaille
        pygame.draw.polygon(surf, ROUGE, [(cx - h * 0.5, cy - h), (cx + h * 0.5, cy - h), (cx + h * 0.2, cy), (cx - h * 0.2, cy)])
        star(surf, (cx, cy + h * 0.35), h * 0.7, WHITE)
        pygame.draw.circle(surf, JAUNE, (int(cx), int(cy + h * 0.35)), int(h * 0.25))


def render_maze(outer, inner):
    surf = pygame.Surface((WIDTH, ROWS * TILE))
    surf.fill(BLACK)
    for pass_col, rad in ((outer, 8), (inner, 5)):
        for r in range(ROWS):
            for c in range(COLS):
                if MAZE[r][c] != "#":
                    continue
                cx, cy = c * TILE + TILE // 2, r * TILE + TILE // 2
                pygame.draw.circle(surf, pass_col, (cx, cy), rad)
                for dx, dy in (RIGHT, DOWN):
                    nc, nr = c + dx, r + dy
                    if nc < COLS and nr < ROWS and MAZE[nr][nc] == "#":
                        if dx:
                            pygame.draw.rect(surf, pass_col, (cx, cy - rad, TILE, rad * 2))
                        else:
                            pygame.draw.rect(surf, pass_col, (cx - rad, cy, rad * 2, TILE))
    for c, r in find_cells("-"):
        y = r * TILE + TILE // 2
        pygame.draw.rect(surf, ROUGE, (c * TILE - 2, y - 3, TILE // 2 + 2, 6))
        pygame.draw.rect(surf, WHITE, (c * TILE + TILE // 2, y - 3, TILE // 2 + 2, 6))
    return surf


# ---------------------------------------------------------------------------
# Entités
# ---------------------------------------------------------------------------
class Mover:
    def __init__(self, col, row):
        self.x = float(col)
        self.y = float(row)
        self.dir = STOP

    @property
    def tile(self):
        return (int(math.floor(self.x + 0.5)) % COLS, int(math.floor(self.y + 0.5)))

    def at_int(self):
        return abs(self.x - round(self.x)) < 1e-6 and abs(self.y - round(self.y)) < 1e-6

    def at_center(self):
        pass

    def advance(self, dist):
        guard = 0
        while dist > 1e-9 and guard < 20:
            guard += 1
            if self.at_int():
                self.x, self.y = float(round(self.x)), float(round(self.y))
                self.at_center()
                if self.dir == STOP:
                    return
            dx, dy = self.dir
            if dx:
                pos = self.x
                target = round(pos) + dx if self.at_int() else (math.floor(pos) + 1 if dx > 0 else math.ceil(pos) - 1)
            else:
                pos = self.y
                target = round(pos) + dy if self.at_int() else (math.floor(pos) + 1 if dy > 0 else math.ceil(pos) - 1)
            seg = abs(target - pos)
            if dist >= seg:
                new = float(target)
                dist -= seg
            else:
                new = pos + (dx or dy) * dist
                dist = 0
            if dx:
                self.x = new
            else:
                self.y = new
            if self.x < -0.5:
                self.x += COLS
            elif self.x > COLS - 0.5:
                self.x -= COLS


class Player(Mover):
    def __init__(self):
        super().__init__(*START_TILE)
        self.reset()

    def reset(self):
        self.x, self.y = float(START_TILE[0]), float(START_TILE[1])
        self.dir = STOP
        self.want = LEFT
        self.facing = LEFT
        self.last_h = LEFT
        self.anim = 0.0

    def at_center(self):
        c, r = self.tile
        if self.want and walkable(c + self.want[0], r + self.want[1]):
            self.dir = self.want
        elif self.dir != STOP and not walkable(c + self.dir[0], r + self.dir[1]):
            self.dir = STOP
        if self.dir != STOP:
            self.facing = self.dir
            if self.dir[0]:
                self.last_h = self.dir

    def update(self, dt, speed):
        if self.dir != STOP and self.want == reverse(self.dir):
            self.dir = self.want
            self.facing = self.dir
            if self.dir[0]:
                self.last_h = self.dir
        moving_before = (self.x, self.y)
        self.advance(speed * dt)
        if (self.x, self.y) != moving_before:
            self.anim += dt * 12

    def mouth(self):
        return int(abs(math.sin(self.anim)) * 2.99)


GHOST_INFO = [
    # nom, surnom, couleur, coin de dispersion
    ("CERFA", "le Tenace", (225, 45, 55), (COLS - 2, -3)),
    ("TAMPON", "le Fourbe", (245, 165, 30), (1, -3)),
    ("DOSSIER", "l'Imprévisible", (45, 185, 95), (COLS - 1, ROWS + 1)),
    ("CIRCULAIRE", "la Timide", (160, 90, 225), (0, ROWS + 1)),
]
HOUSE_SLOTS = [(10, HOUSE_ROW), (10, HOUSE_ROW), (9, HOUSE_ROW), (11, HOUSE_ROW)]


class Ghost(Mover):
    def __init__(self, game, idx):
        self.game = game
        self.idx = idx
        self.name, self.nick, self.color, self.scatter = GHOST_INFO[idx]
        self.slot = HOUSE_SLOTS[idx]
        super().__init__(*self.slot)
        self.reset()

    def reset(self):
        if self.idx == 0:
            self.x, self.y = float(EXIT_TILE[0]), float(EXIT_TILE[1])
            self.state = "normal"
            self.dir = LEFT
        else:
            self.x, self.y = float(self.slot[0]), float(self.slot[1])
            self.state = "house"
            self.dir = UP if self.idx != 2 else DOWN
        self.frightened = False
        self.bob = self.idx * 1.3
        self.anim = 0.0

    def at_center(self):
        c, r = self.tile
        if self.state == "eaten" and (c, r) == EXIT_TILE:
            self.state = "entering"
            self.dir = STOP
            return
        opts = [d for d in DIRS if d != reverse(self.dir) and walkable(c + d[0], r + d[1])]
        if not opts:
            opts = [reverse(self.dir)]
        if self.frightened and self.state == "normal":
            self.dir = random.choice(opts)
            return
        tx, ty = self.game.ghost_target(self)
        best = None
        for d in opts:
            nc, nr = c + d[0], r + d[1]
            dist = (nc - tx) ** 2 + (nr - ty) ** 2
            if best is None or dist < best[0]:
                best = (dist, d)
        self.dir = best[1]

    def move_toward(self, tx, ty, step):
        if abs(self.x - tx) > 1e-6:
            d = 1 if tx > self.x else -1
            self.dir = (d, 0)
            self.x += d * min(step, abs(tx - self.x))
            return False
        if abs(self.y - ty) > 1e-6:
            d = 1 if ty > self.y else -1
            self.dir = (0, d)
            self.y += d * min(step, abs(ty - self.y))
            return False
        return True

    def update(self, dt, speed):
        self.anim += dt * 8
        if self.state == "house":
            self.bob += dt * 5
            self.y = HOUSE_ROW + 0.22 * math.sin(self.bob)
            self.dir = UP if math.cos(self.bob) > 0 else DOWN
        elif self.state == "exiting":
            step = 3.2 * dt
            if abs(self.y - HOUSE_ROW) > 1e-6 and abs(self.x - EXIT_TILE[0]) > 1e-6:
                self.move_toward(self.x, HOUSE_ROW, step)
            elif self.move_toward(EXIT_TILE[0], EXIT_TILE[1], step):
                self.x, self.y = float(EXIT_TILE[0]), float(EXIT_TILE[1])
                self.state = "normal"
                self.dir = LEFT
        elif self.state == "entering":
            if abs(self.x - EXIT_TILE[0]) > 1e-6 and abs(self.y - EXIT_TILE[1]) < 1e-6:
                self.move_toward(EXIT_TILE[0], EXIT_TILE[1], 10 * dt)
            elif self.move_toward(self.x, HOUSE_ROW, 10 * dt) and self.move_toward(self.slot[0], HOUSE_ROW, 10 * dt):
                self.state = "exiting"
                self.frightened = False
        else:
            self.advance(speed * dt)


# ---------------------------------------------------------------------------
# Jeu
# ---------------------------------------------------------------------------
KEY_DIRS = {
    pygame.K_UP: UP, pygame.K_DOWN: DOWN, pygame.K_LEFT: LEFT, pygame.K_RIGHT: RIGHT,
    pygame.K_w: UP, pygame.K_z: UP, pygame.K_s: DOWN, pygame.K_a: LEFT, pygame.K_q: LEFT, pygame.K_d: RIGHT,
}
KONAMI = [pygame.K_UP, pygame.K_UP, pygame.K_DOWN, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
          pygame.K_LEFT, pygame.K_RIGHT, pygame.K_b, pygame.K_a]
SECRET_WORD = "GAULLE"
INF = 10 ** 9


def level_params(level):
    if level == 1:
        p = dict(player=7.2, player_fr=8.0, ghost=6.8, ghost_fr=4.2, tunnel=3.6)
    elif level < 5:
        p = dict(player=8.1, player_fr=8.6, ghost=7.6, ghost_fr=4.6, tunnel=4.0)
    else:
        p = dict(player=9.0, player_fr=9.5, ghost=8.5, ghost_fr=5.0, tunnel=4.4)
    p["fright"] = max(0.0, 6.5 - 0.5 * (level - 1)) if level < 14 else 0.0
    if level == 1:
        p["modes"] = [7, 20, 7, 20, 5, 20, 5, INF]
    elif level < 5:
        p["modes"] = [7, 20, 7, 20, 5, 600, 1 / 60, INF]
    else:
        p["modes"] = [5, 20, 5, 20, 5, 600, 1 / 60, INF]
    p["elroy"] = 20 + 10 * min(level - 1, 5)
    return p


class Game:
    def __init__(self, headless=False):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        flags = 0 if headless else pygame.SCALED
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("DeGaulleMan")
        try:
            pygame.display.set_icon(sprite_general(32, False, 0))
        except pygame.error:
            pass
        self.clock = pygame.time.Clock()
        self.sfx = Sfx()
        self.font_big = pygame.font.Font(None, 64)
        self.font = pygame.font.Font(None, 30)
        self.font_small = pygame.font.Font(None, 22)
        self.maze_img = render_maze(BLEU, (6, 10, 40))
        self.maze_flash = render_maze(WHITE, (6, 10, 40))
        self.all_pellets = set(find_cells("."))
        self.all_powers = set(find_cells("o"))
        self.hs_path = os.path.join(data_dir(), "highscore.txt")
        self.highscore = self.load_highscore()
        self.egg = False
        self.key_hist = []
        self.text_hist = ""
        self.banner = None
        self.banner_t = 0.0
        self.player = Player()
        self.ghosts = [Ghost(self, i) for i in range(4)]
        self.score = 0
        self.level = 1
        self.lives = 3
        self.state = "title"
        self.t = 0.0
        self.title_t = 0.0
        self.paused = False
        self.running = True

    # -- sauvegarde ---------------------------------------------------------
    def load_highscore(self):
        try:
            with open(self.hs_path) as f:
                return int(f.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def save_highscore(self):
        try:
            with open(self.hs_path, "w") as f:
                f.write(str(self.highscore))
        except OSError:
            pass

    # -- déroulement --------------------------------------------------------
    def new_game(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.extra_given = False
        self.start_level(first=True)

    def start_level(self, first=False):
        self.params = level_params(self.level)
        self.pellets = set(self.all_pellets)
        self.powers = set(self.all_powers)
        self.eaten_count = 0
        self.died_this_level = False
        self.reset_positions()
        self.set_state("ready", 4.6 if first else 2.0)
        self.sfx.stop_all()
        if first:
            self.sfx.play("marseillaise" if self.egg else "start")

    def reset_positions(self):
        self.player.reset()
        for g in self.ghosts:
            g.reset()
        self.mode_idx = 0
        self.mode_t = 0.0
        self.fright_t = 0.0
        self.combo = 0
        self.idle_t = 0.0
        self.life_pellets = 0
        self.bonus_t = 0.0
        self.popups = []
        self.freeze = 0.0
        self.freeze_ghost = None
        self.player_pause = 0.0
        self.dot_flip = False

    def set_state(self, state, timer=0.0):
        self.state = state
        self.t = timer

    @property
    def mode(self):
        return "scatter" if self.mode_idx % 2 == 0 else "chase"

    def pellets_left(self):
        return len(self.pellets) + len(self.powers)

    def elroy(self):
        left = self.pellets_left()
        if left <= self.params["elroy"] // 2:
            return 2
        if left <= self.params["elroy"]:
            return 1
        return 0

    def ghost_target(self, g):
        if g.state == "eaten":
            return EXIT_TILE
        p = self.player
        px, py = p.tile
        dx, dy = p.facing
        mode = self.mode
        if g.idx == 0 and self.elroy():
            mode = "chase"
        if mode == "scatter":
            return g.scatter
        if g.idx == 0:
            return (px, py)
        if g.idx == 1:
            return (px + 4 * dx, py + 4 * dy)
        if g.idx == 2:
            rx, ry = self.ghosts[0].tile
            ax, ay = px + 2 * dx, py + 2 * dy
            return (2 * ax - rx, 2 * ay - ry)
        gx, gy = g.tile
        if (gx - px) ** 2 + (gy - py) ** 2 > 64:
            return (px, py)
        return g.scatter

    def add_score(self, pts):
        self.score += pts
        if not self.extra_given and self.score >= 10000:
            self.extra_given = True
            self.lives += 1
            self.sfx.play("life")
        if self.score > self.highscore:
            self.highscore = self.score

    def ghost_speed(self, g):
        p = self.params
        if g.state == "eaten":
            return 14.0
        c, r = g.tile
        if r == TUNNEL_ROW and (c <= 5 or c >= COLS - 6):
            return p["tunnel"]
        if g.frightened:
            return p["ghost_fr"]
        if g.idx == 0:
            return p["ghost"] * (1.0, 1.05, 1.1)[self.elroy()]
        return p["ghost"]

    def release_ghosts(self):
        """Libère les Paperasses une par une : quota de pastilles, ou joueur trop lent."""
        quotas = [0, 7, 17, 32] if self.died_this_level else [0, 0, 20, 45]
        for g in self.ghosts:
            if g.state != "house":
                continue
            if self.life_pellets >= quotas[g.idx] or self.idle_t >= 4.0:
                g.state = "exiting"
                self.idle_t = 0.0
            break  # un seul à la fois, dans l'ordre

    def start_fright(self):
        self.combo = 0
        dur = self.params["fright"]
        for g in self.ghosts:
            if g.state == "normal":
                g.dir = reverse(g.dir)
            if dur > 0 and g.state in ("normal", "house", "exiting"):
                g.frightened = True
        self.fright_t = dur
        self.sfx.play("power")

    def update_play(self, dt):
        if self.freeze > 0:
            self.freeze -= dt
            if self.freeze <= 0:
                self.freeze_ghost = None
            return
        self.idle_t += dt
        p = self.params

        # modes dispersion / poursuite
        if self.fright_t > 0:
            self.fright_t -= dt
            if self.fright_t <= 0:
                for g in self.ghosts:
                    g.frightened = False
        else:
            self.mode_t += dt
            if self.mode_t >= p["modes"][self.mode_idx]:
                self.mode_t = 0.0
                self.mode_idx = min(self.mode_idx + 1, len(p["modes"]) - 1)
                for g in self.ghosts:
                    if g.state == "normal":
                        g.dir = reverse(g.dir)

        # joueur
        if self.player_pause > 0:
            self.player_pause -= dt
        else:
            speed = p["player_fr"] if self.fright_t > 0 else p["player"]
            self.player.update(dt, speed)
        tile = self.player.tile
        if tile in self.pellets:
            self.pellets.discard(tile)
            self.on_eat()
            self.add_score(10)
            self.player_pause = 1 / 60
            self.dot_flip = not self.dot_flip
            self.sfx.dot(self.dot_flip)
        elif tile in self.powers:
            self.powers.discard(tile)
            self.on_eat()
            self.add_score(50)
            self.player_pause = 3 / 60
            self.start_fright()

        # bonus
        if self.bonus_t > 0:
            self.bonus_t -= dt
            if tile == BONUS_TILE:
                idx = bonus_index(self.level)
                pts = BONUSES[idx][1]
                self.add_score(pts)
                self.bonus_t = 0
                self.popups.append([str(pts), BONUS_TILE, 2.0, (255, 150, 220)])
                self.sfx.play("bonus")

        # Paperasses
        self.release_ghosts()
        for g in self.ghosts:
            g.update(dt, self.ghost_speed(g))

        self.check_collisions()

        if self.state == "play" and not self.pellets and not self.powers:
            self.sfx.stop_all()
            self.set_state("clear", 2.6)
            if self.egg:
                self.show_banner("VIVE LA FRANCE !")

        for pop in self.popups:
            pop[2] -= dt
        self.popups = [pp for pp in self.popups if pp[2] > 0]

        # musique de fond
        if self.state == "play":
            if any(g.state in ("eaten", "entering") for g in self.ghosts):
                self.sfx.loop("retreat")
            elif self.fright_t > 0:
                self.sfx.loop("fright")
            else:
                self.sfx.loop("siren")

    def on_eat(self):
        self.eaten_count += 1
        self.life_pellets += 1
        self.idle_t = 0.0
        if self.eaten_count in (70, 170):
            self.bonus_t = 9.5

    def check_collisions(self):
        px, py = self.player.x, self.player.y
        for g in self.ghosts:
            if g.state not in ("normal", "exiting"):
                continue
            dx = abs(g.x - px)
            dx = min(dx, COLS - dx)
            if dx < 0.6 and abs(g.y - py) < 0.6:
                if g.frightened:
                    g.frightened = False
                    g.state = "eaten"
                    pts = 200 * (2 ** self.combo)
                    self.combo = min(self.combo + 1, 3)
                    self.add_score(pts)
                    self.freeze = 0.6
                    self.freeze_ghost = g
                    self.popups.append([str(pts), (g.x, g.y), 0.6, (80, 230, 255)])
                    self.sfx.play("eat_ghost")
                    return
                self.sfx.stop_all()
                self.sfx.play("death")
                self.set_state("dying", 2.2)
                return

    def update(self, dt):
        if self.banner_t > 0:
            self.banner_t -= dt
        if self.state == "title":
            self.title_t += dt
            return
        if self.paused:
            return
        if self.state == "play":
            self.update_play(dt)
            return
        self.t -= dt
        if self.state == "ready":
            for g in self.ghosts:
                if g.state == "house":
                    g.update(dt, 0)
            if self.t <= 0:
                self.set_state("play")
        elif self.state == "dying":
            if self.t <= 0:
                self.lives -= 1
                if self.lives <= 0:
                    self.save_highscore()
                    self.set_state("gameover", 4.0)
                else:
                    self.died_this_level = True
                    self.reset_positions()
                    self.set_state("ready", 2.0)
        elif self.state == "clear":
            if self.t <= 0:
                self.level += 1
                if self.level - 1 in (2, 5, 9):
                    self.set_state("cutscene", 9.0)
                    self.sfx.loop("siren")
                else:
                    self.start_level()
        elif self.state == "cutscene":
            if self.t <= 0:
                self.start_level()
        elif self.state == "gameover":
            if self.t <= 0:
                self.state = "title"
                self.title_t = 0.0

    # -- entrées ------------------------------------------------------------
    def show_banner(self, text, dur=2.6):
        self.banner = text
        self.banner_t = dur

    def toggle_egg(self):
        self.egg = not self.egg
        self.key_hist.clear()
        self.text_hist = ""
        if self.egg:
            self.show_banner("JE VOUS AI COMPRIS !", 3.2)
            self.sfx.play("marseillaise")
        else:
            self.show_banner("ROMPEZ.", 1.6)
            self.sfx.play("egg_off")

    def handle_key(self, ev):
        k = ev.key
        self.key_hist = (self.key_hist + [k])[-len(KONAMI):]
        if self.key_hist == KONAMI:
            self.toggle_egg()
        ch = (ev.unicode or "").upper()
        if ch.isalpha():
            self.text_hist = (self.text_hist + ch)[-len(SECRET_WORD):]
            if self.text_hist == SECRET_WORD:
                self.toggle_egg()

        if k == pygame.K_F11:
            pygame.display.toggle_fullscreen()
            return
        if k == pygame.K_m:
            self.sfx.toggle_mute()
            return
        if self.state == "title":
            if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.new_game()
            elif k == pygame.K_ESCAPE:
                self.running = False
            return
        if k in (pygame.K_p, pygame.K_ESCAPE) and self.state in ("play", "ready"):
            self.paused = not self.paused
            self.sfx.play("pause")
            if self.paused:
                self.sfx.loop(None)
            return
        if self.paused:
            return
        if self.state == "cutscene" and k in (pygame.K_RETURN, pygame.K_SPACE):
            self.t = 0
        if k in KEY_DIRS:
            self.player.want = KEY_DIRS[k]

    # -- dessin -------------------------------------------------------------
    def to_screen(self, x, y):
        return (int(x * TILE + TILE / 2), int(HUD_TOP + y * TILE + TILE / 2))

    def player_sprite(self, size, mouth=None):
        p = self.player
        if mouth is None:
            mouth = p.mouth() if self.state == "play" else 0
        if self.egg:
            return sprite_general(size + 6, p.last_h == LEFT, mouth)
        return sprite_pierrot(size, p.facing if p.facing != STOP else LEFT, mouth)

    def text(self, txt, font, color, center, shadow=True):
        img = font.render(txt, True, color)
        rect = img.get_rect(center=center)
        if shadow:
            sh = font.render(txt, True, (0, 0, 0))
            self.screen.blit(sh, rect.move(2, 2))
        self.screen.blit(img, rect)
        return rect

    def draw_hud(self):
        self.text("SCORE", self.font_small, WHITE, (70, 12), False)
        self.text(str(self.score), self.font, WHITE, (70, 33), False)
        self.text("RECORD", self.font_small, WHITE, (WIDTH // 2, 12), False)
        self.text(str(self.highscore), self.font, WHITE, (WIDTH // 2, 33), False)
        self.text("NIVEAU", self.font_small, WHITE, (WIDTH - 70, 12), False)
        self.text(str(self.level), self.font, WHITE, (WIDTH - 70, 33), False)
        y = HEIGHT - HUD_BOTTOM // 2
        icon = sprite_general(26, False, 0) if self.egg else sprite_pierrot(22, LEFT, 0)
        for i in range(max(0, self.lives - 1)):
            self.screen.blit(icon, icon.get_rect(center=(24 + i * 28, y)))
        first = max(1, self.level - 6)
        for i, lv in enumerate(range(self.level, first - 1, -1)):
            draw_bonus(self.screen, bonus_index(lv), (WIDTH - 22 - i * 28, y), 20)

    def draw_ghost(self, g, flash_phase):
        cx, cy = self.to_screen(g.x, g.y)
        frame = int(g.anim) % 2
        if g.state in ("eaten", "entering"):
            img = sprite_plane(26, g.color, g.dir if g.dir != STOP else DOWN)
        elif g.frightened:
            mode = "flash" if (self.fright_t < 2.0 and flash_phase) else "fright"
            img = sprite_paper(28, g.color, DOWN, frame, mode)
        else:
            look = g.dir if g.dir != STOP else DOWN
            img = sprite_paper(28, g.color, look, frame, "normal")
        rect = img.get_rect(center=(cx, cy))
        self.screen.blit(img, rect)
        if rect.left < 0:
            self.screen.blit(img, rect.move(WIDTH, 0))
        elif rect.right > WIDTH:
            self.screen.blit(img, rect.move(-WIDTH, 0))

    def draw_play(self):
        flash_maze = self.state == "clear" and self.t < 2.0 and int(self.t * 4) % 2 == 0
        self.screen.blit(self.maze_flash if flash_maze else self.maze_img, (0, HUD_TOP))
        for c, r in self.pellets:
            pygame.draw.circle(self.screen, CREME, self.to_screen(c, r), 3)
        blink = int(pygame.time.get_ticks() / 220) % 2 == 0
        if blink or self.state != "play":
            for c, r in self.powers:
                draw_cockade(self.screen, self.to_screen(c, r), 8)
        if self.bonus_t > 0:
            draw_bonus(self.screen, bonus_index(self.level), self.to_screen(*BONUS_TILE), 22)

        show_ghosts = self.state in ("ready", "play") or (self.state == "dying" and self.t > 1.6)
        flash_phase = int(pygame.time.get_ticks() / 200) % 2 == 0
        if show_ghosts:
            for g in reversed(self.ghosts):
                if g is self.freeze_ghost:
                    continue
                self.draw_ghost(g, flash_phase)

        p = self.player
        center = self.to_screen(p.x, p.y)
        if self.state == "dying":
            k = 1.0 if self.t > 1.6 else max(0.0, self.t / 1.6)
            img = self.player_sprite(26, mouth=2)
            if k < 1.0:
                size = max(1, int(img.get_width() * k))
                img = pygame.transform.rotozoom(img, (1 - k) * 720, k)
                if size <= 2:
                    img = None
            if img:
                self.screen.blit(img, img.get_rect(center=center))
        elif self.state not in ("gameover",) and self.freeze_ghost is None:
            img = self.player_sprite(26)
            rect = img.get_rect(center=center)
            self.screen.blit(img, rect)
            if rect.left < 0:
                self.screen.blit(img, rect.move(WIDTH, 0))
            elif rect.right > WIDTH:
                self.screen.blit(img, rect.move(-WIDTH, 0))

        for txt, pos, _, col in self.popups:
            self.text(txt, self.font_small, col, self.to_screen(*pos))

        mid = self.to_screen(*BONUS_TILE)
        if self.state == "ready":
            self.text("PRÊT !", self.font, JAUNE, mid)
        elif self.state == "gameover":
            self.text("FIN DE PARTIE", self.font, ROUGE, mid)
        if self.paused:
            self.text("PAUSE", self.font_big, WHITE, (WIDTH // 2, HEIGHT // 2 - 40))

    def draw_title(self):
        t = self.title_t
        self.screen.fill(BLACK)
        name = "DEGAULLEMAN" if self.egg else "PIERROT"
        colors = [BLEU, WHITE, ROUGE]
        x0 = WIDTH // 2 - self.font_big.size(name)[0] // 2
        x = x0
        for i, ch in enumerate(name):
            img = self.font_big.render(ch, True, colors[i * 3 // len(name)])
            y = 70 + int(4 * math.sin(t * 3 + i * 0.5))
            self.screen.blit(img, (x, y - img.get_height() // 2))
            x += img.get_width()
        sub = "Le Général contre la paperasse" if self.egg else "Le labyrinthe tricolore"
        self.text(sub, self.font_small, CREME, (WIDTH // 2, 112))

        hero = sprite_general(110, False, int(t * 3) % 3) if self.egg else sprite_pierrot(96, (math.sin(t), 0), int(t * 3) % 3)
        self.screen.blit(hero, hero.get_rect(center=(WIDTH // 2, 195 + int(5 * math.sin(t * 2)))))

        self.text("PERSONNAGE  /  SURNOM", self.font_small, WHITE, (WIDTH // 2, 272))
        for i, (nm, nick, col, _) in enumerate(GHOST_INFO):
            if t < 0.6 + i * 0.6:
                break
            y = 305 + i * 38
            img = sprite_paper(30, col, RIGHT, int(t * 6) % 2, "normal")
            self.screen.blit(img, img.get_rect(center=(110, y)))
            lbl = self.font.render("%s  -  \"%s\"" % (nm, nick), True, col)
            self.screen.blit(lbl, (140, y - lbl.get_height() // 2))
        if t > 3.2:
            y = 465
            pygame.draw.circle(self.screen, CREME, (150, y), 3)
            self.screen.blit(self.font_small.render("10 pts", True, WHITE), (165, y - 8))
            draw_cockade(self.screen, (290, y), 8)
            self.screen.blit(self.font_small.render("50 pts", True, WHITE), (305, y - 8))
        if int(t * 2) % 2 == 0:
            self.text("ENTRÉE pour jouer", self.font, JAUNE, (WIDTH // 2, 510))
        self.text("Flèches / ZQSD : bouger    P : pause    M : son    F11 : plein écran",
                  self.font_small, (170, 170, 190), (WIDTH // 2, 548), False)
        self.text("RECORD  %d" % self.highscore, self.font_small, WHITE, (WIDTH // 2, 575), False)
        if not self.egg:
            self.text("Le Général vous observe...", self.font_small, (60, 60, 80), (WIDTH // 2, 30), False)

    def draw_cutscene(self):
        self.screen.fill(BLACK)
        self.text("ENTRACTE", self.font, JAUNE, (WIDTH // 2, 120))
        elapsed = 9.0 - self.t
        y = HEIGHT // 2
        if elapsed < 4.5:
            # Pierrot poursuivi par Cerfa vers la gauche
            k = elapsed / 4.5
            px = WIDTH + 40 - k * (WIDTH + 260)
            img = self.player_sprite(30, mouth=int(elapsed * 10) % 3)
            if not self.egg:
                img = sprite_pierrot(30, LEFT, int(elapsed * 10) % 3)
            else:
                img = sprite_general(36, True, int(elapsed * 10) % 3)
            self.screen.blit(img, img.get_rect(center=(int(px), y)))
            gimg = sprite_paper(30, GHOST_INFO[0][2], LEFT, int(elapsed * 8) % 2, "normal")
            self.screen.blit(gimg, gimg.get_rect(center=(int(px + 70), y)))
        else:
            # le héros géant chasse Cerfa effrayé
            k = (elapsed - 4.5) / 4.5
            gx = -40 + k * (WIDTH + 260)
            gimg = sprite_paper(30, GHOST_INFO[0][2], RIGHT, int(elapsed * 8) % 2, "fright")
            self.screen.blit(gimg, gimg.get_rect(center=(int(gx), y + 20)))
            m = int(elapsed * 10) % 3
            big = sprite_general(110, False, m) if self.egg else sprite_pierrot(96, RIGHT, m)
            self.screen.blit(big, big.get_rect(center=(int(gx - 120), y)))
        self.text("ENTRÉE pour passer", self.font_small, (120, 120, 140), (WIDTH // 2, HEIGHT - 40), False)

    def draw_banner(self):
        if self.banner_t <= 0 or not self.banner:
            return
        w, h = self.font.size(self.banner)
        box = pygame.Rect(0, 0, w + 40, h + 24)
        box.center = (WIDTH // 2, HUD_TOP + 7 * TILE + 12)
        stripe = box.width // 3
        pygame.draw.rect(self.screen, BLEU, (box.left, box.top, stripe, box.height))
        pygame.draw.rect(self.screen, WHITE, (box.left + stripe, box.top, stripe, box.height))
        pygame.draw.rect(self.screen, ROUGE, (box.left + 2 * stripe, box.top, box.width - 2 * stripe, box.height))
        pygame.draw.rect(self.screen, JAUNE, box, 3)
        self.text(self.banner, self.font, BLACK, box.center, False)

    def draw(self):
        self.screen.fill(BLACK)
        if self.state == "title":
            self.draw_title()
        elif self.state == "cutscene":
            self.draw_cutscene()
        else:
            self.draw_play()
            self.draw_hud()
        self.draw_banner()

    # -- boucle -------------------------------------------------------------
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 30)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type == pygame.KEYDOWN:
                    self.handle_key(ev)
            self.update(dt)
            self.draw()
            pygame.display.flip()
        self.save_highscore()
        pygame.quit()


def self_test(seconds=240):
    """Simulation sans écran : joue au hasard pour vérifier qu'il n'y a pas de crash."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    game = Game(headless=True)
    game.hs_path = os.devnull
    game.new_game()
    game.lives = 40
    dt = 1 / FPS
    states = set()
    t = 0.0
    while t < seconds:
        t += dt
        if random.random() < 0.05:
            game.player.want = random.choice(DIRS)
        if game.state == "title":
            game.new_game()
        if random.random() < 0.0005:
            game.toggle_egg()
        if game.state == "play" and random.random() < 0.004:
            game.pellets.clear()
            game.powers.clear()
        game.update(dt)
        game.draw()
        states.add(game.state)
    print("OK - états visités:", sorted(states), "niveau", game.level, "score", game.score)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        self_test()
    else:
        Game().run()
