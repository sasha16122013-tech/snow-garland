# -*- coding: utf-8 -*-
import ctypes
from ctypes import wintypes
import json
import math
import os
import random
import sys
import time
import traceback
import tkinter as tk
from tkinter import ttk, colorchooser

try:
    import winreg
except ImportError:
    winreg = None

# Правильное определение типов WinAPI для избежания ошибок
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
try:
    user32.SetProcessDPIAware()
except Exception:
    pass

# Теперь используем явные типы, чтобы Python их точно видел
DWORD = wintypes.DWORD
RECT = wintypes.RECT
HWND = wintypes.HWND
BOOL = wintypes.BOOL
LPARAM = wintypes.LPARAM
POINT = wintypes.POINT

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", DWORD), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", DWORD)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsZoomed.argtypes = [wintypes.HWND]
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
user32.EnumDisplayMonitors.argtypes = [ctypes.c_void_p, ctypes.c_void_p, MONITORENUMPROC, wintypes.LPARAM]
dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, ctypes.DWORD, ctypes.c_void_p, ctypes.DWORD]

GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW = 0x80000, 0x20, 0x80

def get_windows():
    result = []
    def cb(hwnd, _lp):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd): return True
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW: return True
        cloaked = wintypes.DWORD(0)
        dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4)
        if cloaked.value: return True
        if user32.GetWindowTextLengthW(hwnd) == 0: return True
        r = wintypes.RECT()
        if dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
            user32.GetWindowRect(hwnd, ctypes.byref(r))
        if r.right - r.left < 150 or r.bottom - r.top < 80: return True
        result.append((int(hwnd), r.left, r.top, r.right, r.bottom, bool(user32.IsZoomed(hwnd))))
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return result

def get_work_areas():
    res = []
    def cb(hmon, _hdc, _lprc, _lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            w = mi.rcWork; res.append((w.left, w.top, w.right, w.bottom))
        return True
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    res.sort()
    return res

def cursor_pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y

def visible_top_edges(windows, skip_max):
    segs = []
    for i, (hw, l, t, r, b, mx) in enumerate(windows):
        if mx and skip_max: continue
        spans = [(l + 8, r - 8)]
        for (_h, l2, t2, r2, b2, _m) in windows[:i]:
            if t2 <= t + 1 < b2:
                new = []
                for a, c in spans:
                    if r2 <= a or l2 >= c: new.append((a, c)); continue
                    if l2 > a: new.append((a, l2))
                    if r2 < c: new.append((r2, c))
                spans = new
        for a, c in spans:
            if c - a >= 60: segs.append((hw, a, c, t, l, r - l))
    return segs

APPDATA = os.environ.get("APPDATA") or os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_DIR = os.path.join(APPDATA, "SnowGarland")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
LOG_PATH = os.path.join(CONFIG_DIR, "error.log")

DEFAULTS = {
    "season": "Авто", "custom_season_enabled": True, "density": 100, "speed": 1.0,
    "size": 5, "wind": 0.0, "wobble": 1.0, "snow_color": "#FFFFFF", "only_desktop": False,
    "pile_enabled": True, "pile_max": 16, "pile_rate": 1.0, "garland_enabled": True,
    "garland_winter_only": False, "skip_maximized": True, "garland_arc": 220,
    "garland_sag": 28, "garland_gap": 40, "bulb_size": 5, "garland_width": 2,
    "garland_wire": "#2E7D32", "color1": "#FF3B30", "color2": "#FFD60A",
    "color3": "#34C759", "color4": "#0A84FF", "blink_mode": "Бегущая волна",
    "blink_speed": 2.0, "cursor_mode": "Сметать курсором", "cursor_radius": 45,
    "snowman_size": 1.0, "snowman_max": 6, "snowman_dwell": 1.2, "plow_auto": False,
    "plow_speed": 4, "fps": 30,
}
PARTICLE_KEYS = {"season", "custom_season_enabled", "density", "size", "snow_color"}
LIVE_KEYS = {"speed", "wind", "wobble", "cursor_mode", "cursor_radius", "snowman_size",
             "snowman_max", "snowman_dwell", "plow_auto", "plow_speed", "pile_max",
             "pile_rate", "blink_mode", "blink_speed", "fps", "only_desktop"}

KEY = "#010203"
BIN = 4
SEASONS = {"Зима": "winter", "Осень": "autumn", "Весна": "spring", "Лето": "summer"}
SEASON_TITLE = {"winter": "❄ Зима", "autumn": "❦ Осень", "spring": "✿ Весна", "summer": "☀ Лето"}
AUTUMN = ["#D84315", "#EF6C00", "#F9A825", "#8D6E63", "#BF360C", "#C0A62A"]
SPRING_LEAF = ["#66BB6A", "#81C784", "#9CCC65", "#43A047"]
PETAL_COL = ["#F8BBD0", "#F48FB1", "#FFFFFF", "#FFE0B2"]
FLY_COL = ["#E6EE9C", "#FFF59D", "#C5E1A5"]
MAGIC_COL = ["#00FFFF", "#FF00FF", "#FFFF00", "#00FF00"]
PILE_COLOR = {"winter": "#F2F7FF", "autumn": "#B4631C", "spring": "#8FBF4D", "summer": "#000000"}
LEAF = [(0, -1), (0.55, -0.4), (0.5, 0.3), (0, 1), (-0.5, 0.3), (-0.55, -0.4)]
PETAL = [(0, -1), (0.65, -0.25), (0.45, 0.6), (0, 1), (-0.45, 0.6), (-0.65, -0.25)]

def load_cfg():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in DEFAULTS:
            if k in data and type(data[k]) == type(DEFAULTS[k]): cfg[k] = data[k]
    except Exception: pass
    return cfg

def save_cfg(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f: json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception: pass

def log_error():
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f: f.write(time.strftime("%Y-%m-%d %H:%M:%S\n") + traceback.format_exc() + "\n")
    except Exception: pass

def current_season(cfg):
    if not cfg.get("custom_season_enabled", True):
        m = time.localtime().tm_mon
        if m in (12, 1, 2): return "winter"
        if m in (3, 4, 5): return "spring"
        if m in (6, 7, 8): return "summer"
        return "autumn"
    return SEASONS.get(cfg["season"], "winter")

def blend(hex_color, f):
    f = max(0.0, min(1.0, f)); h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))

def mix(c1, c2, t):
    a, b = c1.lstrip("#"), c2.lstrip("#"); out = []
    for i in (0, 2, 4):
        x, y = int(a[i:i+2], 16), int(b[i:i+2], 16)
        out.append(int(x + (y - x) * t))
    return "#%02x%02x%02x" % tuple(out)

def shape_pts(shape, x, y, size, rot, wf):
    cs, sn = math.cos(rot), math.sin(rot); out = []
    for px, py in shape:
        px *= wf; out += [x + (px * cs - py * sn) * size, y + (px * sn + py * cs) * size]
    return out

def relax(h, cap):
    n = len(h)
    for i in range(n):
        if h[i] > cap: h[i] = cap
    for i in range(1, n - 1):
        ex = h[i] - (h[i - 1] + h[i + 1]) * 0.5 - 2.5
        if ex > 0: h[i] -= ex * 0.5; h[i - 1] += ex * 0.25; h[i + 1] += ex * 0.25

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SnowGarland"

def autostart_command():
    if getattr(sys, "frozen", False): return '"%s" --autostart' % sys.executable
    exe = sys.executable
    if exe.lower().endswith("python.exe"): exe = exe[:-10] + "pythonw.exe"
    return '"%s" "%s" --autostart' % (exe, os.path.abspath(sys.argv[0]))

def is_autostart():
    if not winreg: return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME); return True
    except OSError: return False

def set_autostart(on):
    if not winreg: return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on: winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, autostart_command())
            else:
                try: winreg.DeleteValue(k, APP_NAME)
                except OSError: pass
        return True
    except OSError: return False

class Engine:
    def __init__(self, canvas, cfg, geom):
        self.cv = canvas; self.cfg = cfg
        self.vx, self.vy, self.W, self.H = geom
        self.get_windows = get_windows; self.get_cursor = cursor_pos; self.get_work = get_work_areas
        self.frame = 0; self.visible = True; self.parts = []; self.piles = {}
        self.snowmen = []; self.plow = None; self.bulbs = []; self.surfaces = []
        self.surf_info = {}; self.win_rects = []; self.win_keys = set(); self.work = []
        self.last_work = -99.0; self.scene_sig = None; self.season = current_season(cfg)
        self.dirty_particles = True; self.dirty_scene = True; self.dirty_snowmen = True; self.pile_dirty = False

    def notify(self, key):
        if key in PARTICLE_KEYS: self.dirty_particles = True
        elif key not in LIVE_KEYS: self.dirty_scene = True
        if key == "pile_enabled" and not self.cfg["pile_enabled"]: self.piles = {}; self.pile_dirty = True
        if key in ("season", "custom_season_enabled"): self.reset_world()

    def reset_world(self):
        self.season = current_season(self.cfg)
        self.piles = {}; self.snowmen = []; self.plow = None
        self.dirty_particles = True; self.dirty_scene = True; self.dirty_snowmen = True; self.pile_dirty = True

    def clear_snow(self): self.piles = {}; self.pile_dirty = True
    def clear_snowmen(self): self.snowmen = []; self.dirty_snowmen = True

    def tick(self, now):
        self.frame += 1
        if self.frame % 30 == 0:
            self.refresh_scene(now)
            if not self.cfg.get("custom_season_enabled", True) and current_season(self.cfg) != self.season:
                self.reset_world()
        if self.dirty_particles: self.rebuild_particles()
        self.update_particles(); self.interact(now); self.update_plow(now)
        if self.pile_dirty and self.frame % 3 == 0: self.redraw_piles(); self.raise_all()
        if self.frame % 2 == 0: self.blink(now)

    def raise_all(self):
        for tag in ("pile", "snowman", "garland", "flake", "plow", "dwell"): self.cv.tag_raise(tag)

    def make_particle(self, random_y):
        cv, cfg, s = self.cv, self.cfg, self.season
        d = random.uniform(0.35, 1.0); r = max(1.5, cfg["size"] * d)
        x = random.uniform(0, self.W); y = random.uniform(0, self.H) if random_y else -r * 4
        p = {"x": x, "y": y, "py": y, "r": r, "d": d, "ph": random.uniform(0, 6.3),
             "flip": random.uniform(0, 6.3), "rot": random.uniform(0, 6.3),
             "spin": random.uniform(-0.07, 0.07), "hid": False, "lands": True, "shape": None, "size": r}
        if s == "winter":
            col = blend(cfg["snow_color"], 0.55 + 0.45 * d); p["vy"] = 0.6 + 1.5 * d
            if random.random() < 0.3:
                p["kind"] = "dot"; p["ids"] = [cv.create_oval(0, 0, 1, 1, fill=col, outline="", tags="flake")]
            else:
                p["kind"] = "glyph"; p["ids"] = [cv.create_text(x, y, text=random.choice("❄❅❆"), fill=col, font=("Segoe UI Symbol", max(7, int(r * 3))), tags="flake")]
        elif s == "autumn":
            col = random.choice(AUTUMN); p.update(kind="leaf", shape=LEAF, size=r * 1.5 + 3, vy=0.55 + 1.0 * d)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline=blend(col, 0.6), smooth=True, tags="flake")]
        elif s == "spring":
            if random.random() < 0.55: col = random.choice(SPRING_LEAF); p.update(kind="leaf", shape=LEAF, size=r * 1.2 + 2.5)
            else: col = random.choice(PETAL_COL); p.update(kind="petal", shape=PETAL, size=r * 0.9 + 2)
            p["vy"] = 0.45 + 0.8 * d
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline=blend(col, 0.7), smooth=True, tags="flake")]
        else:
            col = random.choice(MAGIC_COL)
            p.update(kind="magic", shape=[(0,-1), (0.3,-0.3), (1,0), (0.3,0.3), (0,1), (-0.3,0.3), (-1,0), (-0.3,-0.3)], size=r * 1.2, vy=0.5 + 1.2 * d)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline="", tags="flake")]
        self.place(p); return p

    def rebuild_particles(self):
        self.cv.delete("flake"); n = int(self.cfg["density"])
        self.parts = [self.make_particle(True) for _ in range(n)]
        self.dirty_particles = False; self.raise_all()

    def place(self, p):
        cv, x, y, r, k = self.cv, p["x"], p["y"], p["r"], p["kind"]
        if k == "dot": cv.coords(p["ids"][0], x - r, y - r, x + r, y + r)
        elif k == "glyph": cv.coords(p["ids"][0], x, y)
        elif k == "fly": cv.coords(p["ids"][0], x - r * 2.4, y - r * 2.4, x + r * 2.4, y + r * 2.4)
        else:
            wf = 0.35 + 0.65 * abs(math.cos(p["flip"]))
            cv.coords(p["ids"][0], *shape_pts(p["shape"], x, y, p["size"], p["rot"], wf))

    def respawn(self, p): p["x"] = random.uniform(0, self.W); p["y"] = p["py"] = -p["r"] * 4

    def update_particles(self):
        cfg, cv = self.cfg, self.cv
        sp, wind, wob = cfg["speed"], cfg["wind"], cfg["wobble"]
        W, H = self.W, self.H; surfs = self.surfaces; pile_en = cfg["pile_enabled"]
        rects = self.win_rects if cfg["only_desktop"] else None
        sway = 0.6 if self.season == "winter" else 1.1
        for p in self.parts:
            p["ph"] += 0.05; p["py"] = p["y"]; p["y"] += p["vy"] * sp
            p["x"] += (wind * (0.4 + p["d"]) + math.sin(p["ph"]) * wob * sway) * sp
            p["rot"] += p["spin"] * sp; p["flip"] += 0.07 * sp
            x, y, py = p["x"], p["y"], p["py"]; landed = False
            for (key, a, c, top, left, width) in surfs:
                if a <= x <= c:
                    hh = self.pile_h(key, left, x) if pile_en else 0.0
                    ys = top - hh
                    if py < ys <= y:
                        if pile_en: self.land(key, left, width, x, p)
                        landed = True; break
            if landed or y > H + 14: self.respawn(p)
            elif p["x"] > W + 14: p["x"] = -14
            elif p["x"] < -14: p["x"] = W + 14
            self.place(p)
            if rects is not None:
                inside = any(l <= x <= r_ and t <= y <= b for (l, t, r_, b) in rects)
                if inside != p["hid"]:
                    p["hid"] = inside; st = "hidden" if inside else "normal"
                    for i in p["ids"]: cv.itemconfigure(i, state=st)

    def get_pile(self, key, width):
        n = int(width // BIN) + 3; p = self.piles.get(key)
        if p is None: p = {"h": [0.0] * n}; self.piles[key] = p
        elif len(p["h"]) != n: p["h"] = (p["h"] + [0.0] * n)[:n]
        return p

    def pile_h(self, key, left, x):
        p = self.piles.get(key)
        if not p: return 0.0
        i = int((x - left) // BIN); h = p["h"]
        return h[i] if 0 <= i < len(h) else 0.0

    def land(self, key, left, width, x, particle):
        cfg = self.cfg; h = self.get_pile(key, width)["h"]
        base = {"winter": 1.0, "autumn": 1.3, "spring": 0.8}.get(self.season, 0.8)
        amt = base * (0.4 + particle["d"]) * cfg["pile_rate"]
        i = int((x - left) // BIN); cap = cfg["pile_max"]
        for off, k in ((0, 1.0), (-1, 0.6), (1, 0.6), (-2, 0.25), (2, 0.25)):
            j = i + off
            if 0 <= j < len(h): h[j] = min(cap, h[j] + amt * k)
        self.pile_dirty = True

    def redraw_piles(self):
        cv = self.cv; cv.delete("pile"); self.pile_dirty = False
        if not self.cfg["pile_enabled"]: return
        cap = self.cfg["pile_max"]; col = PILE_COLOR[self.season]
        for p in self.piles.values(): relax(p["h"], cap)
        for (key, a, c, top, left, width) in self.surfaces:
            p = self.piles.get(key)
            if not p: continue
            h = p["h"]; pts, mx, x = [], 0.0, a
            while True:
                i = int((x - left) // BIN)
                hh = h[i] if 0 <= i < len(h) else 0.0
                mx = max(mx, hh); pts += [x, top - hh]
                if x >= c: break
                x = min(x + BIN, c)
            if mx < 0.8: continue
            pts += [c, top, a, top]
            cv.create_polygon(*pts, fill=col, outline=blend(col, 0.85), width=1, tags="pile")

    def refresh_scene(self, now):
        cfg = self.cfg; wins = self.get_windows()
        if now - self.last_work > 2.0: self.work = self.get_work(); self.last_work = now
        surfs = []
        for (hw, a, c, top, left, width) in visible_top_edges(wins, cfg["skip_maximized"]):
            ty = top - self.vy
            if ty < 4 or ty > self.H - 4: continue
            surfs.append((hw, a - self.vx, c - self.vx, ty, left - self.vx, width))
        for i, (l, _t, r, b) in enumerate(self.work):
            surfs.append(("g%d" % i, l - self.vx, r - self.vx, b - self.vy, l - self.vx, r - l))
        self.win_rects = [(l - self.vx, t - self.vy, r - self.vx, b - self.vy) for (_h, l, t, r, b, _m) in wins]
        self.win_keys = {w[0] for w in wins}; sig = tuple(surfs)
        if sig != self.scene_sig or self.dirty_scene:
            self.scene_sig = sig; self.dirty_scene = False; self.surfaces = surfs
            info = {}
            for (key, a, c, top, left, width) in surfs:
                d = info.setdefault(key, {"left": left, "width": width, "top": top, "spans": []})
                d["spans"].append((a, c))
            self.surf_info = info
            gkeys = {"g%d" % i for i in range(len(self.work))}
            for k in list(self.piles):
                if (isinstance(k, str) and k not in gkeys) or (isinstance(k, int) and k not in self.win_keys): del self.piles[k]
            self.snowmen = [s for s in self.snowmen if (isinstance(s["key"], str) and s["key"] in gkeys) or (isinstance(s["key"], int) and s["key"] in self.win_keys)]
            self.build_garland(); self.redraw_piles(); self.redraw_snowmen(); self.raise_all()
        elif self.dirty_snowmen: self.redraw_snowmen(); self.raise_all()

    def build_garland(self):
        cv, cfg = self.cv, self.cfg; cv.delete("garland"); self.bulbs = []
        if not cfg["garland_enabled"]: return
        if cfg["garland_winter_only"] and self.season != "winter": return
        kind = {"winter": "bulb", "summer": "bulb", "autumn": "leaf", "spring": "flower"}[self.season]
        cols = [cfg["color1"], cfg["color2"], cfg["color3"], cfg["color4"]]
        sag, wire, ww = cfg["garland_sag"], cfg["garland_wire"], cfg["garland_width"]
        r = cfg["bulb_size"]; k = 0
        for (key, a, b, y, left, width) in self.surfaces:
            if isinstance(key, str): continue
            n_arcs = max(1, round((b - a) / cfg["garland_arc"])); w = (b - a) / n_arcs
            for i in range(n_arcs):
                x0 = a + i * w; pts = []
                for s in range(21):
                    t = s / 20; pts += [x0 + t * w, y + 2 + sag * 4 * t * (1 - t)]
                shadow = [v + (2 if j % 2 else 0) for j, v in enumerate(pts)]
                cv.create_line(*shadow, fill=blend(wire, 0.35), width=ww + 2, smooth=True, tags="garland")
                cv.create_line(*pts, fill=wire, width=ww, smooth=True, tags="garland")
                for px in (x0, x0 + w):
                    cv.create_oval(px - 3, y - 1, px + 3, y + 5, fill="#B0BEC5", outline="#37474F", tags="garland")
                cnt = max(1, int(w / cfg["garland_gap"]))
                for j in range(cnt):
                    t = (j + 0.5) / cnt; bx = x0 + t * w; by = y + 2 + sag * 4 * t * (1 - t)
                    if kind == "bulb":
                        col = cols[k % 4]
                        g1 = cv.create_oval(bx - r * 2.3, by + 5 - r * 0.9, bx + r * 2.3, by + 5 + r * 3.0, fill=KEY, outline="", tags="garland")
                        g2 = cv.create_oval(bx - r * 1.5, by + 5 - r * 0.3, bx + r * 1.5, by + 5 + r * 2.4, fill=KEY, outline="", tags="garland")
                        cv.create_rectangle(bx - 2, by, bx + 2, by + 5, fill="#37474F", outline="", tags="garland")
                        bulb = cv.create_oval(bx - r * 0.85, by + 4, bx + r * 0.85, by + 4 + r * 2.2, fill=col, outline="", tags="garland")
                        cv.create_oval(bx - r * 0.5, by + 5 + r * 0.3, bx - r * 0.1, by + 5 + r * 0.9, fill=mix(col, "#FFFFFF", 0.75), outline="", tags="garland")
                        self.bulbs.append((bulb, g1, g2, col, k))
                    elif kind == "leaf":
                        col = AUTUMN[(k * 5 + k // 3) % len(AUTUMN)]; sz = r * 1.5 + 3
                        cv.create_line(bx, by, bx, by + 4, fill=wire, width=1, tags="garland")
                        rot = math.pi + math.sin(k * 1.7) * 0.5
                        cv.create_polygon(*shape_pts(LEAF, bx, by + 4 + sz, sz, rot, 0.85), fill=col, outline=blend(col, 0.6), smooth=True, tags="garland")
                    else:
                        pc = PETAL_COL[(k * 3 + k // 2) % len(PETAL_COL)]; sz = r * 0.9 + 3; cy = by + 5 + sz
                        cv.create_line(bx, by, bx, by + 5, fill=wire, width=1, tags="garland")
                        for q in range(5):
                            ang = q * 2 * math.pi / 5; px, py = bx + math.cos(ang) * sz * 0.8, cy + math.sin(ang) * sz * 0.8
                            cv.create_oval(px - sz * 0.55, py - sz * 0.55, px + sz * 0.55, py + sz * 0.55, fill=pc, outline=blend(pc, 0.7), tags="garland")
                        cv.create_oval(bx - sz * 0.4, cy - sz * 0.4, bx + sz * 0.4, cy + sz * 0.4, fill="#FBC02D", outline="", tags="garland")
                    k += 1

    def blink(self, t):
        cv = self.cv; mode, spd = self.cfg["blink_mode"], self.cfg["blink_speed"]
        for bulb, g1, g2, col, k in self.bulbs:
            if mode == "Бегущая волна": f = 0.55 + 0.45 * math.sin(t * spd * 2 - k * 0.6)
            elif mode == "Мигание": f = 1.0 if (int(t * spd) + k) % 2 == 0 else 0.2
            else: f = 1.0
            cv.itemconfigure(bulb, fill=blend(col, 0.35 + 0.65 * f))
            cv.itemconfigure(g2, fill=blend(col, f * 0.30) if f > 0.5 else KEY)
            cv.itemconfigure(g1, fill=blend(col, f * 0.15) if f > 0.65 else KEY)

    def snowman_pos(self, sm):
        info = self.surf_info.get(sm["key"])
        if not info: return None
        x = info["left"] + sm["off"]
        for a, c in info["spans"]:
            if a <= x <= c: return x, info["top"]
        return None

    def redraw_snowmen(self):
        self.cv.delete("snowman"); self.dirty_snowmen = False
        for sm in self.snowmen:
            pos = self.snowman_pos(sm)
            if pos: self.draw_snowman(pos[0], pos[1] + 1)

    def draw_snowman(self, x, y):
        cv, s, t = self.cv, self.cfg["snowman_size"], "snowman"
        r1, r2, r3 = 13 * s, 9.5 * s, 6.5 * s
        y1 = y - r1; y2 = y1 - (r1 + r2) * 0.82; y3 = y2 - (r2 + r3) * 0.82
        w = max(1, int(s * 1.5))
        cv.create_line(x - r2 * 0.9, y2, x - r2 * 2.0, y2 - r2 * 0.9, fill="#6D4C41", width=w, tags=t)
        cv.create_line(x + r2 * 0.9, y2, x + r2 * 2.0, y2 - r2 * 0.9, fill="#6D4C41", width=w, tags=t)
        for cx, cy, rr in ((x, y1, r1), (x, y2, r2), (x, y3, r3)):
            cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill="#FFFFFF", outline="#9DB7D8", width=1, tags=t)
        cv.create_rectangle(x - r3 * 0.85, y3 + r3 * 0.55, x + r3 * 0.85, y3 + r3 * 0.95, fill="#E53935", outline="", tags=t)
        cv.create_rectangle(x - r3 * 0.95, y3 - r3 * 0.85, x + r3 * 0.95, y3 - r3 * 0.62, fill="#212121", outline="", tags=t)
        cv.create_rectangle(x - r3 * 0.6, y3 - r3 * 1.7, x + r3 * 0.6, y3 - r3 * 0.8, fill="#212121", outline="", tags=t)
        e = max(1.0, s * 0.9)
        for dx in (-r3 * 0.35, r3 * 0.35):
            cv.create_oval(x + dx - e, y3 - r3 * 0.15 - e, x + dx + e, y3 - r3 * 0.15 + e, fill="#212121", outline="", tags=t)
        cv.create_polygon(x, y3 + r3 * 0.05, x + r3 * 1.1, y3 + r3 * 0.2, x, y3 + r3 * 0.3, fill="#FB8C00", outline="", tags=t)
        for k in (-0.4, 0.15, 0.7):
            by = y2 + r2 * k
            cv.create_oval(x - e, by - e, x + e, by + e, fill="#212121", outline="", tags=t)

    def interact(self, now):
        cv, cfg = self.cv, self.cfg; cv.delete("dwell")
        mode = cfg["cursor_mode"]
        if mode == "Ничего" or not self.visible: self.dwell = None; return
        px, py = self.get_cursor(); cx, cy = px - self.vx, py - self.vy
        rad, pm = cfg["cursor_radius"], cfg["pile_max"]
        if mode.startswith("Сметать"):
            for (key, a, c, top, left, width) in self.surfaces:
                if cx < a - rad or cx > c + rad or cy < top - pm - rad or cy > top + rad: continue
                p = self.piles.get(key)
                if not p: continue
                h = p["h"]; i0 = max(0, int((cx - rad - left) // BIN)); i1 = min(len(h) - 1, int((cx + rad - left) // BIN))
                for i in range(i0, i1 + 1):
                    bx = left + i * BIN
                    if h[i] > 0.05 and a <= bx <= c:
                        d = abs(bx - cx)
                        if d < rad: h[i] = 0.0 if d < rad * 0.6 else h[i] * 0.4; self.pile_dirty = True
            keep = []
            for sm in self.snowmen:
                pos = self.snowman_pos(sm)
                if pos and abs(pos[0] - cx) <= rad * 0.8 and pos[1] - 80 * cfg["snowman_size"] <= cy <= pos[1] + rad:
                    self.dirty_snowmen = True; continue
                keep.append(sm)
            self.snowmen = keep
        else: self.update_dwell(now, cx, cy, pm)

    def update_dwell(self, now, cx, cy, pm):
        cfg, cv = self.cv, self.cfg
        if now < self.dwell_cool: self.dwell = None; return
        target = None
        for (key, a, c, top, left, width) in self.surfaces:
            if a <= cx <= c and top - pm - 12 <= cy <= top + 10 and self.pile_h(key, left, cx) >= 4:
                target = (key, cx - left, left); break
        if not target: self.dwell = None; return
        d = self.dwell
        if not d or d["key"] != target[0] or abs(d["off"] - target[1]) > 25:
            d = self.dwell = {"key": target[0], "off": target[1], "t0": now}
        prog = (now - d["t0"]) / max(0.3, cfg["snowman_dwell"])
        rr = 4 + 10 * min(1.0, prog)
        cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill="#FFFFFF", outline="#9DB7D8", tags="dwell")
        cv.tag_raise("dwell")
        if prog >= 1: self.build_snowman(target[0], target[1]); self.dwell = None; self.dwell_cool = now + 1.5

    def build_snowman(self, key, off):
        self.snowmen.append({"key": key, "off": off})
        while len(self.snowmen) > int(self.cfg["snowman_max"]): self.snowmen.pop(0)
        p = self.piles.get(key)
        if p:
            h = p["h"]
            for i in range(max(0, int((off - 30) // BIN)), min(len(h) - 1, int((off + 30) // BIN)) + 1): h[i] *= 0.25
            self.pile_dirty = True
        self.dirty_snowmen = True

    def piles_full(self):
        lim = self.cfg["pile_max"] * 0.7
        return any(p["h"] and max(p["h"]) >= lim for p in self.piles.values())

    def start_plow(self):
        if self.plow or not self.surf_info: return
        best, bs = None, -1.0
        for key in self.surf_info:
            p = self.piles.get(key); s = sum(p["h"]) if p else 0.0
            if isinstance(key, str): s += 0.5
            if s > bs: best, bs = key, s
        d = random.choice((-1, 1)); width = self.surf_info[best]["width"]
        self.plow = {"key": best, "dir": d, "off": -30 if d > 0 else width + 30}

    def update_plow(self, now):
        cv = self.cv; cv.delete("plow"); pl = self.plow
        if not pl:
            if self.cfg["plow_auto"] and now - self.last_plow > 20 and self.piles_full(): self.start_plow()
            return
        info = self.surf_info.get(pl["key"])
        if not info: self.plow, self.last_plow = None, now; return
        pl["off"] += pl["dir"] * self.cfg["plow_speed"] * 1.2
        if pl["off"] < -40 or pl["off"] > info["width"] + 40: self.plow, self.last_plow = None, now; return
        x = info["left"] + pl["off"]; p = self.piles.get(pl["key"])
        if p:
            h = p["h"]; fx = pl["off"] + pl["dir"] * 26
            for i in range(max(0, int((fx - 14) // BIN)), min(len(h) - 1, int((fx + 14) // BIN)) + 1):
                if h[i] > 0: h[i] = 0.0; self.pile_dirty = True
        if any(a <= x <= c for a, c in info["spans"]): self.draw_plow(x, info["top"], pl["dir"], now); cv.tag_raise("plow")

    def draw_plow(self, x, y, d, now):
        cv, t = self.cv, "plow"
        def P(*pts):
            out = []
            for i in range(0, len(pts), 2): out += [x + pts[i] * d, y + pts[i + 1]]
            return out
        cv.create_polygon(*P(-34, -6, -34, -18, 20, -18, 24, -6), fill="#FBC02D", outline="#7A5B00", tags=t)
        cv.create_polygon(*P(-28, -18, -22, -31, -4, -31, 2, -18), fill="#FBC02D", outline="#7A5B00", tags=t)
        cv.create_polygon(*P(-24, -19, -20, -28, -8, -28, -5, -19), fill="#B3E5FC", outline="", tags=t)
        cv.create_line(*P(20, -12, 28, -12), fill="#5D4037", width=3, tags=t)
        cv.create_polygon(*P(26, -26, 42, -6, 42, 1, 26, 1), fill="#EF6C00", outline="#7A3300", tags=t)
        for wx, wr in ((-20, 6), (8, 6)):
            cx = x + wx * d
            cv.create_oval(cx - wr, y - 5 - wr, cx + wr, y - 5 + wr, fill="#263238", outline="", tags=t)
            cv.create_oval(cx - 2, y - 7, cx + 2, y - 3, fill="#B0BEC5", outline="", tags=t)
        bc = "#FF9800" if int(now * 6) % 2 == 0 else "#7A2E00"; bx = x - 12 * d
        cv.create_oval(bx - 3, y - 37, bx + 3, y - 31, fill=bc, outline="", tags=t)
        BG, PANEL, FG, MUTED, ACCENT = "#12162B", "#1D2345", "#E8ECFF", "#8C96C4", "#5CC8FF"

class App:
    def __init__(self, autostart=False):
        self.cfg = load_cfg(); self.root = tk.Tk()
        self.root.title("Времена года и гирлянда"); self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.vx = user32.GetSystemMetrics(76); self.vy = user32.GetSystemMetrics(77)
        self.W = user32.GetSystemMetrics(78); self.H = user32.GetSystemMetrics(79)
        self.visible = True; self.ready = False; self.setters = {}
        self.build_overlay()
        self.engine = Engine(self.canvas, self.cfg, (self.vx, self.vy, self.W, self.H))
        self.build_ui()
        self.ready = True
        
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        
        if autostart: self.hide_to_tray()
        self.tick()

    def build_overlay(self):
        self.ov = tk.Toplevel(self.root); self.ov.overrideredirect(True)
        self.ov.geometry("%dx%d+%d+%d" % (self.W, self.H, self.vx, self.vy))
        self.ov.configure(bg=KEY); self.ov.attributes("-topmost", True)
        self.ov.attributes("-transparentcolor", KEY)
        self.canvas = tk.Canvas(self.ov, bg=KEY, highlightthickness=0, width=self.W, height=self.H)
        self.canvas.pack(fill="both", expand=True); self.ov.update_idletasks()
        hwnd = user32.GetParent(self.ov.winfo_id()) or self.ov.winfo_id()
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)

    def set_cfg(self, key, value):
        self.cfg[key] = value
        if self.ready: self.engine.notify(key)

    def style(self):
        st = ttk.Style(); st.theme_use("clam")
        st.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL, troughcolor=PANEL, font=("Segoe UI", 10))
        st.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        st.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(14, 8), borderwidth=0, font=("Segoe UI", 10, "bold"))
        st.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", "#0B1020")])
        st.configure("TLabel", background=BG, foreground=FG)
        st.configure("TCheckbutton", background=BG, foreground=FG, indicatorcolor=PANEL, indicatorbackground=PANEL, focuscolor=BG)
        st.map("TCheckbutton", indicatorcolor=[("selected", ACCENT)], background=[("active", BG)], foreground=[("active", FG)])
        st.configure("Horizontal.TScale", background=BG, troughcolor=PANEL, bordercolor=BG, lightcolor=ACCENT, darkcolor=ACCENT)
        st.configure("TButton", background=PANEL, foreground=FG, padding=(10, 7), borderwidth=0, focuscolor=PANEL)
        st.map("TButton", background=[("active", "#2C3566")])
        st.configure("Accent.TButton", background=ACCENT, foreground="#0B1020", font=("Segoe UI", 10, "bold"))
        st.map("Accent.TButton", background=[("active", "#8FDBFF")])
        st.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG, arrowcolor=FG, bordercolor=PANEL, padding=4)
        st.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)], selectbackground=[("readonly", PANEL)], selectforeground=[("readonly", FG)])
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#0B1020")

    def build_ui(self):
        self.style()
        head = tk.Frame(self.root, bg=BG); head.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(head, text="Времена года и гирлянда", bg=BG, fg=FG, font=("Segoe UI", 16, "bold")).pack(side="left")
        self.badge = tk.Label(head, text="", bg=ACCENT, fg="#0B1020", padx=10, pady=3, font=("Segoe UI Symbol", 10, "bold"))
        self.badge.pack(side="right")

        nb = ttk.Notebook(self.root); nb.pack(fill="both", expand=True, padx=12, pady=8)
        t1, t2, t3, t4 = [ttk.Frame(nb, padding=14) for _ in range(4)]
        nb.add(t1, text="Сезон"); nb.add(t2, text="Гирлянда"); nb.add(t3, text="Сугробы и уборка"); nb.add(t4, text="Система")

        # --- Сезон
        self.check(t1, "Включить ручной выбор сезона (выкл = авто по месяцам)", "custom_season_enabled")
        self.combo(t1, "Сезон", "season", ["Авто", "Зима", "Осень", "Весна", "Лето"])
        self.scale(t1, "Количество", "density", 0, 600, 10)
        self.scale(t1, "Скорость", "speed", 0.1, 4.0, 0.1)
        self.scale(t1, "Размер", "size", 2, 14, 1)
        self.scale(t1, "Ветер (← →)", "wind", -3.0, 3.0, 0.1)
        self.scale(t1, "Покачивание", "wobble", 0.0, 4.0, 0.1)
        self.color(t1, "Цвет снега", "snow_color")
        self.check(t1, "Падает только на рабочем столе", "only_desktop")

        # --- Гирлянда
        self.check(t2, "Включить гирлянду", "garland_enabled")
        self.check(t2, "Только зимой", "garland_winter_only")
        self.check(t2, "Не вешать на развёрнутые окна", "skip_maximized")
        self.scale(t2, "Длина дуги", "garland_arc", 80, 600, 10)
        self.scale(t2, "Провисание", "garland_sag", 0, 100, 1)
        self.scale(t2, "Между лампочками", "garland_gap", 16, 120, 2)
        self.scale(t2, "Размер лампочек", "bulb_size", 2, 14, 1)
        self.scale(t2, "Толщина провода", "garland_width", 1, 6, 1)
        self.color(t2, "Цвет провода", "garland_wire")
        row = ttk.Frame(t2); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Цвета лампочек", width=22).pack(side="left")
        for k in ("color1", "color2", "color3", "color4"): self.color_button(row, k).pack(side="left", padx=3)
        self.combo(t2, "Режим мигания", "blink_mode", ["Бегущая волна", "Мигание", "Постоянно"])
        self.scale(t2, "Скорость мигания", "blink_speed", 0.2, 10.0, 0.2)

        # --- Сугробы и уборка
        self.check(t3, "Оседает на окнах и панели задач", "pile_enabled")
        self.scale(t3, "Высота сугроба", "pile_max", 4, 40, 1)
        self.scale(t3, "Скорость накопления", "pile_rate", 0.2, 6.0, 0.2)
        self.combo(t3, "Курсор", "cursor_mode", ["Ничего", "Сметать курсором", "Лепить снеговика"])
        self.scale(t3, "Радиус курсора", "cursor_radius", 15, 120, 5)
        self.scale(t3, "Размер снеговика", "snowman_size", 0.6, 2.0, 0.1)
        self.scale(t3, "Макс. снеговиков", "snowman_max", 1, 15, 1)
        self.scale(t3, "Время лепки, сек", "snowman_dwell", 0.5, 4.0, 0.1)
        self.check(t3, "Уборочная машина выезжает сама", "plow_auto")
        self.scale(t3, "Скорость машины", "plow_speed", 1, 10, 1)
        br = ttk.Frame(t3); br.pack(fill="x", pady=(8, 0))
        ttk.Button(br, text="Запустить уборочную машину", style="Accent.TButton", command=lambda: self.engine.start_plow()).pack(fill="x", pady=2)
        r2 = ttk.Frame(br); r2.pack(fill="x")
        ttk.Button(r2, text="Убрать снеговиков", command=lambda: self.engine.clear_snowmen()).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(r2, text="Очистить весь снег", command=lambda: self.engine.clear_snow()).pack(side="left", expand=True, fill="x", padx=(3, 0))

        # --- Система
        self.auto_var = tk.BooleanVar(value=is_autostart())
        ttk.Checkbutton(t4, text="Запускать вместе с Windows", variable=self.auto_var, command=self.toggle_autostart).pack(anchor="w", pady=4)
        self.scale(t4, "Кадров в секунду", "fps", 10, 60, 5)
        tk.Label(t4, bg=BG, fg=MUTED, justify="left", wraplength=400, font=("Segoe UI", 9),
                 text="Закройте это окно на крестик — анимация останется работать в фоновом режиме!").pack(anchor="w", pady=(14, 0))

        bar = ttk.Frame(self.root); bar.pack(fill="x", padx=12, pady=(2, 12))
        ttk.Button(bar, text="Сохранить", style="Accent.TButton", command=lambda: save_cfg(self.cfg)).pack(side="left", padx=3)
        ttk.Button(bar, text="Сбросить", command=self.reset).pack(side="left", padx=3)
        self.toggle_btn = ttk.Button(bar, text="Скрыть эффекты", command=self.toggle)
        self.toggle_btn.pack(side="left", padx=3)
        ttk.Button(bar, text="Выход", command=self.quit).pack(side="right", padx=3)
        ttk.Button(bar, text="В фоновый режим", command=self.hide_to_tray).pack(side="right", padx=3)

    def scale(self, parent, text, key, lo, hi, step):
        f = ttk.Frame(parent); f.pack(fill="x", pady=3)
        ttk.Label(f, text=text, width=22, anchor="w").pack(side="left")
        lbl = tk.Label(f, text="", width=5, anchor="e", bg=BG, fg=ACCENT, font=("Segoe UI", 10, "bold"))
        lbl.pack(side="right")
        var = tk.DoubleVar(value=self.cfg[key]); is_int = isinstance(step, int)
        def cmd(v):
            x = round(float(v) / step) * step; x = int(x) if is_int else round(x, 2)
            lbl.config(text="%g" % x)
            if self.ready and self.cfg.get(key) != x: self.set_cfg(key, x)
        ttk.Scale(f, from_=lo, to=hi, variable=var, command=cmd).pack(side="left", fill="x", expand=True, padx=6)
        cmd(self.cfg[key])
        def setter(v):
            var.set(v); cmd(v); self.cfg[key] = v; self.engine.notify(key)
        self.setters[key] = setter

    def check(self, parent, text, key):
        v = tk.BooleanVar(value=self.cfg[key])
        cb = ttk.Checkbutton(parent, text=text, variable=v, command=lambda: self.set_cfg(key, v.get()))
        cb.pack(anchor="w", pady=3)
        def setter(val): v.set(val); self.set_cfg(key, val)
        self.setters[key] = setter

    def combo(self, parent, text, key, values):
        f = ttk.Frame(parent); f.pack(fill="x", pady=4)
        ttk.Label(f, text=text, width=22, anchor="w").pack(side="left")
        v = tk.StringVar(value=self.cfg[key])
        cb = ttk.Combobox(f, textvariable=v, values=values, state="readonly", width=24)
        cb.pack(side="left", fill="x", expand=True)
        cb.bind("<<ComboboxSelected>>", lambda e: self.set_cfg(key, v.get()))
        def setter(val): v.set(val); self.set_cfg(key, val)
        self.setters[key] = setter

    def color_button(self, parent, key):
        b = tk.Button(parent, width=4, relief="flat", bd=0, cursor="hand2", bg=self.cfg[key], activebackground=self.cfg[key])
        def pick():
            c = colorchooser.askcolor(self.cfg[key], parent=self.root)[1]
            if c: self.set_cfg(key, c); b.configure(bg=c, activebackground=c)
        b.configure(command=pick)
        def setter(val): b.configure(bg=val, activebackground=val); self.set_cfg(key, val)
        self.setters[key] = setter
        return b

    def color(self, parent, text, key):
        f = ttk.Frame(parent); f.pack(fill="x", pady=4)
        ttk.Label(f, text=text, width=22, anchor="w").pack(side="left")
        self.color_button(f, key).pack(side="left")

    def toggle_autostart(self):
        ok = set_autostart(self.auto_var.get())
        if not ok: self.auto_var.set(is_autostart())

    def reset(self):
        for k, v in DEFAULTS.items():
            if k in self.setters: self.setters[k](v)
            else: self.set_cfg(k, v)

    def toggle(self):
        self.visible = not self.visible; self.engine.visible = self.visible
        if self.visible: self.ov.deiconify(); self.toggle_btn.configure(text="Скрыть эффекты")
        else: self.ov.withdraw(); self.toggle_btn.configure(text="Показать эффекты")

    def hide_to_tray(self):
        self.root.withdraw()

    def quit(self):
        save_cfg(self.cfg); self.root.destroy()

    def tick(self):
        try:
            if self.visible:
                self.engine.tick(time.time())
                if self.engine.frame % 30 == 1: self.badge.config(text=SEASON_TITLE[self.engine.season])
                if self.engine.frame % 90 == 0: self.ov.attributes("-topmost", True)
        except Exception: log_error()
        finally: self.root.after(max(10, int(1000 / self.cfg["fps"])), self.tick)

def main():
    if os.name != "nt": sys.exit(1)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _mutex = kernel32.CreateMutexW(None, False, "SnowGarland_single_instance")
    if ctypes.get_last_error() == 183:
        user32.MessageBoxW(0, "Программа уже запущена. Её окно — в фоновом режиме.", "Времена года и гирлянда", 0x40)
        return
    app = App(autostart="--autostart" in sys.argv)
    app.root.mainloop()

if __name__ == "__main__":
    main()
