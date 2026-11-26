# -*- coding: utf-8 -*-
"""
Времена года на рабочем столе: снег, листья, конфетти, пузыри, дождь, звёзды...
Гирлянда на окнах, сугробы с физикой, снеговики, уборочная машина по всем мониторам,
северное сияние, метеоры, сани Санты, сосульки с капелью, вихрь курсора и многое другое.

Запуск: python snow_garland.py   (или pythonw snow_garland.py - без консоли)
Нужен только Python 3.8+ для Windows. Сторонние библиотеки не нужны.
"""
import colorsys
import ctypes
import json
import math
import os
import random
import sys
import threading
import time
import traceback
import tkinter as tk
import urllib.parse
import urllib.request
from ctypes import wintypes
from tkinter import colorchooser, ttk

try:
    import winreg
except ImportError:
    winreg = None

# ---------------------------------------------------------------- WinAPI
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32
try:
    user32.SetProcessDPIAware()
except Exception:
    pass


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
user32.EnumDisplayMonitors.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                       MONITORENUMPROC, wintypes.LPARAM]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetForegroundWindow.restype = wintypes.HWND
dwmapi.DwmGetWindowAttribute.argtypes = [
    wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]

GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW = 0x80000, 0x20, 0x80

NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 20
WM_LBUTTONDBLCLK = 0x0203
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
IDI_APPLICATION = 32512
IMAGE_ICON = 1
LR_DEFAULTSIZE = 0x00000040


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
    ]


def get_windows():
    """Видимые окна сверху вниз: (hwnd, l, t, r, b, maximized)."""
    result = []

    def cb(hwnd, _lp):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
        cloaked = wintypes.DWORD(0)
        dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4)
        if cloaked.value:
            return True
        if user32.GetWindowTextLengthW(hwnd) == 0:
            return True
        r = wintypes.RECT()
        if dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r),
                                        ctypes.sizeof(r)) != 0:
            user32.GetWindowRect(hwnd, ctypes.byref(r))
        if r.right - r.left < 150 or r.bottom - r.top < 80:
            return True
        result.append((int(hwnd), r.left, r.top, r.right, r.bottom,
                       bool(user32.IsZoomed(hwnd))))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return result


def get_work_areas():
    """Рабочие области мониторов (без панели задач): (l, t, r, b)."""
    res = []

    def cb(hmon, _hdc, _lprc, _lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            w = mi.rcWork
            res.append((w.left, w.top, w.right, w.bottom))
        return True

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    res.sort()
    return res


def get_monitor_rects():
    """Полные прямоугольники мониторов: (l, t, r, b)."""
    res = []

    def cb(hmon, _hdc, _lprc, _lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            m = mi.rcMonitor
            res.append((m.left, m.top, m.right, m.bottom))
        return True

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    res.sort()
    return res


def cursor_pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def foreground_hwnd():
    return int(user32.GetForegroundWindow() or 0)


def visible_top_edges(windows, skip_max):
    """Незакрытые участки верхних границ окон: (hwnd, a, c, top, left, width)."""
    segs = []
    for i, (hw, l, t, r, b, mx) in enumerate(windows):
        if mx and skip_max:
            continue
        spans = [(l + 8, r - 8)]
        for (_h, l2, t2, r2, b2, _m) in windows[:i]:
            if t2 <= t + 1 < b2:
                new = []
                for a, c in spans:
                    if r2 <= a or l2 >= c:
                        new.append((a, c))
                        continue
                    if l2 > a:
                        new.append((a, l2))
                    if r2 < c:
                        new.append((r2, c))
                spans = new
        for a, c in spans:
            if c - a >= 60:
                segs.append((hw, a, c, t, l, r - l))
    return segs


# ---------------------------------------------------------------- Настройки
APPDATA = os.environ.get("APPDATA") or os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_DIR = os.path.join(APPDATA, "SnowGarland")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
LOG_PATH = os.path.join(CONFIG_DIR, "error.log")

KINDS = [("snow", "Снежинки"), ("leaf", "Осенние листья"),
         ("spring", "Весенние листья и лепестки"), ("firefly", "Светлячки"),
         ("confetti", "Конфетти"), ("bubble", "Пузыри"),
         ("heart", "Сердечки"), ("star", "Падающие звёзды"),
         ("rain", "Дождь"), ("lantern", "Небесные фонарики")]
KIND_FACTOR = {"firefly": 0.4, "lantern": 0.12, "bubble": 0.4, "star": 0.25,
               "heart": 0.5, "confetti": 0.7, "rain": 0.9}
SEASON_KINDS = {"winter": ["snow"], "autumn": ["leaf"],
                "spring": ["spring"], "summer": ["firefly"]}

DEFAULTS = {
    "season": "Авто", "fall_mode": "По сезону",
    "city_name": "Днепр", "city_weather_status": "Не задан",
    "k_snow": True, "k_leaf": False, "k_spring": False, "k_firefly": False,
    "k_confetti": False, "k_bubble": False, "k_heart": False, "k_star": False,
    "k_rain": False, "k_lantern": False,
    "snow_style": "Все вместе", "snow_color": "#FFFFFF",
    "density": 65, "speed": 1.0, "size": 5,
    "wind": 0.0, "wind_dir": "Авто", "wind_strength": 1.0,
    "wobble": 1.0,
    "only_desktop": False,
    "pause_fullscreen": True,
    "pause_on_close": True,
    "gust_power": 0.6, "gust_speed": 1.0,
    "blizzard_every": 0, "blizzard_len": 25, "blizzard_power": 1.5,
    "cursor_mode": "Физика ветра", "cursor_radius": 90, "cursor_force": 1.0,
    "cursor_blow": True, "roll_enabled": True, "roll_key": "Ctrl",
    "snowman_size": 1.0, "snowman_max": 6, "snowman_melt_sec": 120,
    "pile_enabled": True, "pile_max": 16, "pile_rate": 1.0,
    "plow_every": 0, "plow_speed": 4,
    "garland_enabled": True, "garland_winter_only": False, "skip_maximized": True,
    "garland_style": "Авто (по сезону)", "garland_glow": 1,
    "garland_arc": 220, "garland_sag": 28, "garland_gap": 48, "bulb_size": 5,
    "garland_width": 2, "garland_wire": "#2E7D32",
    "color1": "#FF3B30", "color2": "#FFD60A", "color3": "#34C759", "color4": "#0A84FF",
    "blink_mode": "Бегущая волна", "blink_speed": 2.0,
    "trail_enabled": False, "trail_kind": "Искры", "trail_amount": 1.0,
    "trail_size": 1.0, "trail_life": 1.0,
    "aurora_enabled": False, "aurora_when": "Всегда", "aurora_palette": "Зелёное",
    "aurora_height": 28, "aurora_speed": 0.8, "aurora_power": 1, "aurora_behind": True,
    "stars_enabled": False, "stars_count": 60, "stars_height": 50, "stars_twinkle": 1.0,
    "sky_body": "Выкл", "sky_corner": "Правый верх", "sky_size": 70,
    "meteor_enabled": False, "meteor_every": 8, "meteor_len": 1.0,
    "santa_enabled": False, "santa_every": 25, "santa_size": 1.0,
    "neon_enabled": False, "neon_mode": "Радуга", "neon_width": 3, "neon_speed": 1.0,
    "edge_enabled": False, "edge_mode": "Радуга", "edge_size": 50, "edge_speed": 1.0,
    "tree_enabled": False, "tree_corner": "Правый монитор (правый низ)", "tree_size": 100,
    "fw_enabled": False, "fw_every": 6, "fw_size": 1.0,
    "halo_enabled": False, "halo_radius": 55, "halo_speed": 1.5, "halo_color": "#5CC8FF",
    "drip_enabled": False, "drip_rate": 1.0, "drip_len": 18,
    "fps": 24,
}

EFFECT_NAMES = ("stars", "aurora", "sky", "tree", "neon", "edge", "halo")
EFFECT_PREFIX = (("aurora_", "aurora"), ("stars_", "stars"), ("sky_", "sky"),
                 ("neon_", "neon"), ("edge_", "edge"), ("tree_", "tree"),
                 ("halo_", "halo"))
SCENE_KEYS = {"garland_enabled", "garland_winter_only", "skip_maximized",
              "garland_style", "garland_glow", "garland_arc", "garland_sag",
              "garland_gap", "bulb_size", "garland_width", "garland_wire",
              "color1", "color2", "color3", "color4", "pile_enabled",
              "drip_enabled", "drip_len"}
PARTICLE_KEYS = {"season", "density", "size", "snow_color", "fall_mode", "snow_style"}
RAISE_ORDER = ("e_stars", "e_aurora", "e_sky", "e_tree", "pile", "snowman",
               "garland", "e_neon", "e_edge", "e_halo", "flake", "fx", "plow", "ball")

KEY = "#010203"
BIN = 6
FX_LIMIT = 140

SEASONS = {"Зима": "winter", "Осень": "autumn", "Весна": "spring", "Лето": "summer"}
SEASON_TITLE = {"winter": "❄  Зима", "autumn": "❦  Осень",
                "spring": "✿  Весна", "summer": "☀  Лето"}
AUTUMN = ["#D84315", "#EF6C00", "#F9A825", "#8D6E63", "#BF360C", "#C0A62A"]
SPRING_LEAF = ["#66BB6A", "#81C784", "#9CCC65", "#43A047"]
PETAL_COL = ["#F8BBD0", "#F48FB1", "#FFFFFF", "#FFE0B2"]
FLY_COL = ["#E6EE9C", "#FFF59D", "#C5E1A5"]
CONFETTI_COL = ["#FF5252", "#FFD740", "#69F0AE", "#40C4FF", "#E040FB", "#FFAB40"]
HEART_COL = ["#FF4D7D", "#FF6F91", "#FF9AB5", "#E91E63"]
STAR_COL = ["#FFE066", "#FFF3B0", "#FFD23F"]
FLAG_COL = ["#FF5252", "#FFD740", "#69F0AE", "#40C4FF", "#E040FB", "#FF9100"]
SPARK_COL = ["#FFE066", "#FFB347", "#FFFFFF", "#FF8C42"]
DUST_COL = ["#FFF3B0", "#C8B6FF", "#BDE0FE", "#FFC8DD"]
FIRE_COL = ["#FFD166", "#FF9F1C", "#FF5A1F", "#E63946"]
FW_COL = ["#FF5C8A", "#FFD166", "#06D6A0", "#4CC9F0", "#C77DFF", "#FF9F1C"]
MAT_COLOR = {"snow": "#F2F7FF", "leaf": "#B4631C", "spring": "#7CB342",
             "confetti": "#FFC24B", "heart": "#FF6F91"}
AURORA_PAL = {"Зелёное": ["#39FF8A", "#2EE6C2", "#7CFFB2"],
              "Фиолетовое": ["#B07CFF", "#7C8CFF", "#E27CFF"],
              "Розовое": ["#FF7CC8", "#FF9E7C", "#C77CFF"]}
LEAF = [(0, -1), (0.55, -0.4), (0.5, 0.3), (0, 1), (-0.5, 0.3), (-0.55, -0.4)]
PETAL = [(0, -1), (0.65, -0.25), (0.45, 0.6), (0, 1), (-0.45, 0.6), (-0.65, -0.25)]
RECT = [(-1, -0.55), (1, -0.55), (1, 0.55), (-1, 0.55)]
GARLAND_STYLES = {"Лампочки": "bulb", "Сосульки": "icicle", "Шарики": "ball",
                  "Звёзды": "star", "Фонарики": "lantern", "Флажки": "flag",
                  "Листья": "leaf", "Цветы": "flower", "Микс": "mix"}
AUTO_STYLE = {"winter": "bulb", "autumn": "leaf", "spring": "flower", "summer": "flag"}
BLINK_MODES = [
    "Бегущая волна",
    "Мигание",
    "Переливание (плавное)",
    "Двойной бегущий огонь",
    "Стробоскоп",
    "Дыхание",
    "Случайное мерцание",
    "Постоянно",
]


def load_cfg():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in DEFAULTS:
            if k in data and type(data[k]) == type(DEFAULTS[k]):
                cfg[k] = data[k]
            elif k in data and isinstance(DEFAULTS[k], float) and \
                    isinstance(data[k], int) and not isinstance(data[k], bool):
                cfg[k] = float(data[k])
        if cfg.get("tree_corner") in ("Правый низ", "Левый низ"):
            cfg["tree_corner"] = "Правый монитор (правый низ)"
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def log_error(name=""):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + name + "\n")
            f.write(traceback.format_exc() + "\n")
    except Exception:
        pass


def current_season(cfg):
    v = SEASONS.get(cfg["season"])
    if v:
        return v
    m = time.localtime().tm_mon
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    return "autumn"


def blend(hex_color, f):
    f = max(0.0, min(1.0, f))
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def mix(c1, c2, t):
    a, b = c1.lstrip("#"), c2.lstrip("#")
    out = []
    for i in (0, 2, 4):
        x, y = int(a[i:i + 2], 16), int(b[i:i + 2], 16)
        out.append(int(x + (y - x) * t))
    return "#%02x%02x%02x" % tuple(out)


def hsv_hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def shape_pts(shape, x, y, size, rot, wf):
    cs, sn = math.cos(rot), math.sin(rot)
    out = []
    for px, py in shape:
        px *= wf
        out += [x + (px * cs - py * sn) * size, y + (px * sn + py * cs) * size]
    return out


def relax(h, cap):
    n = len(h)
    for i in range(n):
        if h[i] > cap:
            h[i] = cap
    for i in range(1, n - 1):
        ex = h[i] - (h[i - 1] + h[i + 1]) * 0.5 - 2.5
        if ex > 0:
            h[i] -= ex * 0.5
            h[i - 1] += ex * 0.25
            h[i + 1] += ex * 0.25


def fetch_city_weather(city_name):
    city = (city_name or "").strip()
    if not city:
        return None
    q = urllib.parse.quote(city)
    url = f"https://wttr.in/{q}?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "SnowGarland/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    cur = (data.get("current_condition") or [{}])[0]
    code = int(cur.get("weatherCode", 113))
    wind_kmh = float(cur.get("windspeedKmph", 0.0))
    wind_deg = float(cur.get("winddirDegree", 0.0))
    desc = ""
    lang_ru = cur.get("lang_ru") or cur.get("weatherDesc") or []
    if lang_ru and isinstance(lang_ru, list):
        desc = str(lang_ru[0].get("value", ""))
    snow_codes = {179, 182, 185, 227, 230, 323, 326, 329, 332, 335, 338, 350, 362, 365, 368, 371, 374, 377, 392, 395}
    rain_codes = {176, 263, 266, 293, 296, 299, 302, 305, 308, 311, 314, 353, 356, 359, 386, 389}
    if code in snow_codes:
        kinds = ["snow"]
    elif code in rain_codes:
        kinds = ["rain"]
    else:
        kinds = ["star", "bubble"] if code in (113, 116) else ["leaf", "bubble"]
    wind_x = -math.sin(math.radians(wind_deg)) * min(3.0, max(0.2, wind_kmh / 18.0))
    return {
        "kinds": kinds,
        "wind": round(wind_x, 2),
        "summary": f"{city}: {desc or code}, ветер {wind_kmh:.0f} км/ч",
    }


# ---------------------------------------------------------------- Автозапуск
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SnowGarland"


def autostart_command():
    if getattr(sys, "frozen", False):
        return '"%s" --autostart' % sys.executable
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        exe = exe[:-10] + "pythonw.exe"
    return '"%s" "%s" --autostart' % (exe, os.path.abspath(sys.argv[0]))


def is_autostart():
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_autostart(on):
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except OSError:
                    pass
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- Трей
class TrayIcon:
    def __init__(self, root, on_open, on_toggle, on_exit):
        self.root = root
        self.on_open = on_open
        self.on_toggle = on_toggle
        self.on_exit = on_exit
        self.hwnd = None
        self.uid = 1001
        self.active = False
        self._wndproc = None
        self._create_window()
        self.add()

    def _create_window(self):
        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_TRAYICON:
                if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                    self.root.after(0, self.on_open)
                elif lparam == WM_RBUTTONUP:
                    self.root.after(0, self._show_menu)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc = WNDPROC(wnd_proc)
        hinstance = kernel32.GetModuleHandleW(None)
        class_name = "SnowGarlandTrayWnd"

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HICON),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = hinstance
        wc.lpszClassName = class_name
        user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(
            0, class_name, class_name, 0, 0, 0, 0, 0, None, None, hinstance, None
        )

    def _get_icon(self):
        icon = user32.LoadImageW(None, ctypes.c_wchar_p(f"#{IDI_APPLICATION}"),
                               IMAGE_ICON, 0, 0, LR_DEFAULTSIZE)
        if not icon:
            icon = user32.LoadIconW(None, ctypes.c_wchar_p(f"#{IDI_APPLICATION}"))
        return icon

    def add(self):
        if self.active or not self.hwnd:
            return
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = self.uid
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = self._get_icon()
        nid.szTip = "Времена года и гирлянда"
        if shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
            self.active = True

    def remove(self):
        if not self.active or not self.hwnd:
            return
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = self.uid
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        self.active = False

    def _show_menu(self):
        menu = tk.Menu(self.root, tearoff=0, bg="#1D2345", fg="#E8ECFF",
                       activebackground="#5CC8FF", activeforeground="#0B1020")
        menu.add_command(label="Открыть настройки", command=self.on_open)
        menu.add_command(label="Скрыть / показать эффекты", command=self.on_toggle)
        menu.add_separator()
        menu.add_command(label="Выход", command=self.on_exit)
        x, y = cursor_pos()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()


# ---------------------------------------------------------------- Движок мира
class Engine:
    strict = False

    def __init__(self, canvas, cfg, geom, app_hwnd=0, ov_hwnd=0):
        self.cv = canvas
        self.cfg = cfg
        self.vx, self.vy, self.W, self.H = geom
        self.app_hwnd = app_hwnd
        self.ov_hwnd = ov_hwnd
        self.get_windows = get_windows
        self.get_cursor = cursor_pos
        self.get_work = get_work_areas
        self.get_monitors = get_monitor_rects
        self.get_key = key_down
        self.get_fg = foreground_hwnd

        self.frame = 0
        self.visible = True
        self.paused_fullscreen = False
        self.city_kinds = None
        self.parts, self.chunks, self.fx = [], [], []
        self.piles, self.snowmen = {}, []
        self.plow, self.last_plow = None, None
        self.roll, self.cur = None, None
        self.lights, self.render, self.geo = {}, {}, {}
        self.surfaces, self.surf_info = [], {}
        self.win_rects, self.win_keys, self.wins = [], set(), []
        self.work, self.monitors, self.last_work = [], [], -99.0
        self.last_win_scan = -99.0
        self.season = current_season(cfg)
        self.ver = 0
        self.dirty_particles = True
        self.dirty_scene = True
        self.dirty_snowmen = True
        self.pile_dirty = False
        self.fx_dirty, self.effect_on = set(), {}
        self.bliz, self.bliz_f, self.bliz_dir, self.next_bliz = None, 0.0, 1, None
        self.next_meteor, self.next_fw, self.next_santa = 0.0, 0.0, 0.0
        self.meteors, self.rockets, self.santas = [], [], []
        self.errors, self.disabled = {}, set()

    def guard(self, name, fn, *a):
        if name in self.disabled:
            return
        try:
            fn(*a)
        except Exception:
            if self.strict:
                raise
            n = self.errors.get(name, 0) + 1
            self.errors[name] = n
            if n <= 2:
                log_error(name)
            if n >= 15:
                self.disabled.add(name)

    def notify(self, key):
        cfg = self.cfg
        if key in PARTICLE_KEYS or key.startswith("k_"):
            self.dirty_particles = True
            if key == "season":
                self.reset_world()
            return
        for pre, name in EFFECT_PREFIX:
            if key.startswith(pre):
                self.fx_dirty.add(name)
                return
        if key in SCENE_KEYS:
            self.dirty_scene = True
            if key == "pile_enabled" and not cfg["pile_enabled"]:
                self.piles = {}
                self.pile_dirty = True
        elif key in ("snowman_size", "snowman_melt_sec"):
            self.dirty_snowmen = True

    def reset_world(self):
        self.season = current_season(self.cfg)
        self.piles, self.snowmen, self.plow, self.roll = {}, [], None, None
        self.cv.delete("ball")
        self.dirty_particles = self.dirty_scene = self.dirty_snowmen = True
        self.pile_dirty = True
        self.ver += 1
        self.fx_dirty.update(EFFECT_NAMES)

    def clear_snow(self):
        self.piles = {}
        self.pile_dirty = True

    def clear_snowmen(self):
        self.snowmen = []
        self.dirty_snowmen = True

    def raise_all(self):
        for tag in RAISE_ORDER:
            self.cv.tag_raise(tag)

    def covered(self, x, y):
        for (l, t, r, b) in self.win_rects:
            if l <= x <= r and t <= y <= b:
                return True
        return False

    def check_fullscreen_pause(self):
        if not self.cfg.get("pause_fullscreen", True):
            self.paused_fullscreen = False
            return False
        fg = self.get_fg()
        if not fg or fg in (self.app_hwnd, self.ov_hwnd):
            self.paused_fullscreen = False
            return False
        rect = wintypes.RECT()
        if user32.GetWindowRect(fg, ctypes.byref(rect)) == 0:
            self.paused_fullscreen = False
            return False
        w, h = rect.right - rect.left, rect.bottom - rect.top
        mons = self.monitors or [(self.vx, self.vy, self.vx + self.W, self.vy + self.H)]
        for ml, mt, mr, mb in mons:
            if abs(rect.left - ml) <= 4 and abs(rect.top - mt) <= 4 and \
                    abs(w - (mr - ml)) <= 8 and abs(h - (mb - mt)) <= 8:
                self.paused_fullscreen = True
                return True
        self.paused_fullscreen = False
        return False

    def scene_tick(self, now):
        if not self.visible:
            return
        if self.check_fullscreen_pause():
            return
        if now - self.last_win_scan >= 0.16 or self.dirty_scene:
            self.last_win_scan = now
            self.guard("scene", self.refresh_scene, now)
        if self.effect_on.get("neon"):
            self.guard("neon", self.update_neon, now)

    def tick(self, now):
        if not self.visible or self.paused_fullscreen:
            return
        self.frame += 1
        g = self.guard
        if self.last_plow is None:
            self.last_plow = now
        if self.frame % 90 == 0:
            s = current_season(self.cfg)
            if s != self.season:
                if self.cfg["fall_mode"] == "По сезону":
                    self.reset_world()
                else:
                    self.season = s
                    self.ver += 1
        if self.dirty_particles:
            g("rebuild", self.rebuild_particles)
        g("cursor", self.update_cursor)
        g("blizzard", self.update_blizzard, now)
        g("particles", self.update_particles, now)
        g("chunks", self.update_chunks)
        if self.frame % 2 == 0:
            g("interact", self.interact, now)
            g("roll", self.update_roll, now)
            g("trail", self.update_trail, now)
            g("drips", self.update_drips)
        if self.frame % 15 == 0:
            g("snowmen_melt", self.update_snowmen_melt, now)
        g("plow", self.update_plow, now)
        g("schedule", self.update_schedule, now)
        g("fx", self.update_fx)
        if self.pile_dirty and self.frame % 3 == 0:
            g("piles", self.redraw_piles)
            self.raise_all()
        if self.frame % 4 == 0:
            g("blink", self.blink, now)
        g("effects", self.update_effects, now)

    def refresh_scene(self, now):
        cfg = self.cfg
        wins = self.get_windows()
        if now - self.last_work > 3.0:
            self.work = self.get_work() or [(self.vx, self.vy, self.vx + self.W, self.vy + self.H)]
            self.monitors = self.get_monitors() or self.work
            self.last_work = now
        vx, vy = self.vx, self.vy
        info = {}
        for (hw, a, c, top, left, width) in visible_top_edges(wins, cfg["skip_maximized"]):
            ty = top - vy
            if ty < 4 or ty > self.H - 4:
                continue
            d = info.setdefault(hw, {"left": left - vx, "width": width, "top": ty, "spans": [], "bottom": ty + 100})
            d["spans"].append((a - vx, c - vx))
        for (_hw, l, t, r, b, _mx) in wins:
            if _hw in info:
                info[_hw]["bottom"] = b - vy
        for i, (l, _t, r, b) in enumerate(self.work):
            info["g%d" % i] = {"left": l - vx, "width": r - l, "top": b - vy,
                               "spans": [(l - vx, r - vx)], "bottom": b - vy}
        self.win_rects = [(l - vx, t - vy, r - vx, b - vy) for (_h, l, t, r, b, _m) in wins]
        self.win_keys = {w[0] for w in wins}
        self.wins = wins

        new_geo = {w[0]: (w[1] - vx, w[2] - vy, w[3] - w[1]) for w in wins}
        for key in list(self.geo):
            if key not in new_geo:
                self.collapse(key)
        for key, g in new_geo.items():
            prev = self.geo.get(key)
            if prev and key in self.piles:
                dx, dy = g[0] - prev[0], g[1] - prev[1]
                if abs(dx) + abs(dy) >= 12:
                    self.shed(key, g, dx, dy)
        self.geo = new_geo

        if self.dirty_scene:
            self.ver += 1
            self.dirty_scene = False
        self.surf_info = info
        self.surfaces = [(k, a, c, d["top"], d["left"], d["width"])
                         for k, d in info.items() for (a, c) in d["spans"]]
        gkeys = {"g%d" % i for i in range(len(self.work))}
        for k in list(self.piles):
            if (isinstance(k, str) and k not in gkeys) or \
                    (isinstance(k, int) and k not in self.win_keys):
                del self.piles[k]
        n0 = len(self.snowmen)
        self.snowmen = [s for s in self.snowmen
                        if (isinstance(s["key"], str) and s["key"] in gkeys)
                        or (isinstance(s["key"], int) and s["key"] in self.win_keys)]
        if len(self.snowmen) != n0:
            self.dirty_snowmen = True
        self.update_render(info)
        if self.dirty_snowmen:
            self.redraw_snowmen()
            self.raise_all()

    def update_render(self, info):
        cv = self.cv
        rebuilt = False
        for key, d in info.items():
            sig = (d["width"], tuple((round(a - d["left"]), round(c - d["left"]))
                                     for a, c in d["spans"]), self.ver)
            r = self.render.get(key)
            if r and r["sig"] == sig:
                dx, dy = d["left"] - r["left"], d["top"] - r["top"]
                if dx or dy:
                    cv.move("w%s" % key, dx, dy)
                    r["left"], r["top"] = d["left"], d["top"]
            else:
                cv.delete("w%s" % key)
                self.build_garland_key(key, d)
                self.build_window_icicles(key, d)
                self.render[key] = {"sig": sig, "left": d["left"], "top": d["top"]}
                rebuilt = True
        for key in list(self.render):
            if key not in info:
                cv.delete("w%s" % key)
                del self.render[key]
                self.lights.pop(key, None)
        if rebuilt:
            self.redraw_piles()
            self.redraw_snowmen()
            self.raise_all()

    def build_window_icicles(self, key, d):
        if isinstance(key, str) or not self.cfg.get("drip_enabled", False):
            return
        cv = self.cv
        tg = ("garland", "w%s" % key)
        max_len = float(self.cfg.get("drip_len", 18))
        y = d["top"]
        rnd = random.Random(key)
        for (a, b) in d["spans"]:
            step = 34
            x = a + 14
            while x < b - 14:
                L = rnd.uniform(max_len * 0.45, max_len)
                w = rnd.uniform(2.2, 3.6)
                cv.create_polygon(x - w, y, x + w, y, x, y + L,
                                  fill="#D6F0FF", outline="#89C9FF", tags=tg)
                x += step + rnd.randint(-4, 10)

    def update_drips(self):
        if not self.cfg.get("drip_enabled", False):
            return
        rate = float(self.cfg.get("drip_rate", 1.0))
        if random.random() > 0.12 * rate:
            return
        win_keys = [k for k in self.surf_info if isinstance(k, int)]
        if not win_keys:
            return
        d = self.surf_info[random.choice(win_keys)]
        if not d["spans"]:
            return
        a, b = random.choice(d["spans"])
        if b - a < 24:
            return
        x = random.uniform(a + 10, b - 10)
        y = d["top"] + float(self.cfg.get("drip_len", 18))
        self.spawn_fx(x, y, 0.0, 1.8, 36, "#BFE9FF", 1.7, g=0.3, drag=0.99)

    def collapse(self, key):
        g = self.geo.pop(key, None)
        p = self.piles.pop(key, None)
        if g and p:
            left, top, width = g
            h = p["h"]
            stride = max(1, len(h) // 60)
            for i in range(0, len(h), stride):
                if h[i] > 0.8:
                    mat = p["m"][i] or "snow"
                    self.spawn_chunk(left + i * BIN + random.uniform(-3, 3),
                                     top - h[i] * random.random(),
                                     random.uniform(-1.5, 1.5), random.uniform(-1, 1),
                                     mat, random.uniform(1.5, 2.8))
            self.pile_dirty = True
        self.snowmen = [sm for sm in self.snowmen if sm["key"] != key]
        self.dirty_snowmen = True
        self.cv.delete("w%s" % key)
        self.render.pop(key, None)
        self.lights.pop(key, None)

    def shed(self, key, g, dx, dy):
        p = self.piles.get(key)
        if not p:
            return
        left, top, _w = g
        sp = abs(dx) + abs(dy)
        frac = min(0.5, sp / 90.0)
        h, m = p["h"], p["m"]
        n = 0
        for i in range(len(h)):
            if h[i] > 0.8 and random.random() < frac * 0.5:
                if n < 16:
                    self.spawn_chunk(left + i * BIN, top - h[i], -dx * 0.25 + random.uniform(-1.5, 1.5),
                                     -abs(dy) * 0.15 - random.uniform(0.5, 2.5),
                                     m[i] or "snow", random.uniform(1.4, 2.6))
                    n += 1
                h[i] *= 1 - frac
        self.pile_dirty = True

    def spawn_chunk(self, x, y, vx, vy, mat, r):
        if len(self.chunks) >= 120:
            return
        i = self.cv.create_oval(x - r, y - r, x + r, y + r, fill=MAT_COLOR.get(mat, "#FFFFFF"),
                                outline="", tags="flake")
        self.chunks.append({"x": x, "y": y, "py": y, "vx": vx, "vy": vy, "r": r, "mat": mat, "id": i})

    def update_chunks(self):
        if not self.chunks:
            return
        cv, cfg = self.cv, self.cfg
        pen = cfg["pile_enabled"]
        keep = []
        for c in self.chunks:
            c["py"] = c["y"]
            c["vy"] += 0.55
            c["vx"] *= 0.995
            c["x"] += c["vx"]
            c["y"] += c["vy"]
            x, y, py, r = c["x"], c["y"], c["py"], c["r"]
            landed = False
            for (key, a, e, top, left, width) in self.surfaces:
                if a <= x <= e:
                    ys = top - (self.pile_h(key, left, x) if pen else 0.0)
                    if py < ys <= y:
                        if pen:
                            self.land(key, left, width, x, c["mat"], 0.3 * r * cfg["pile_rate"])
                        landed = True
                        break
            if landed or y > self.H + 20 or x < -60 or x > self.W + 60:
                cv.delete(c["id"])
                continue
            cv.coords(c["id"], x - r, y - r, x + r, y + r)
            keep.append(c)
        self.chunks = keep

    def wind_now(self, now):
        cfg = self.cfg
        strength = float(cfg.get("wind_strength", 1.0))
        w = float(cfg["wind"]) * strength
        wdir = cfg.get("wind_dir", "Авто")
        if wdir == "Влево":
            w = -abs(w if abs(w) > 0.2 else 1.2 * strength)
        elif wdir == "Вправо":
            w = abs(w if abs(w) > 0.2 else 1.2 * strength)
        gp = cfg["gust_power"]
        if gp > 0:
            t = now * cfg["gust_speed"]
            g = math.sin(t * 0.37) * 0.65 + math.sin(t * 0.91 + 1.3) * 0.35
            w += g * gp * 1.5
        return w + self.bliz_f * cfg["blizzard_power"] * 3.0 * self.bliz_dir

    def start_blizzard(self, now=None):
        now = time.time() if now is None else now
        self.bliz = {"t0": now, "len": max(5.0, float(self.cfg["blizzard_len"]))}
        self.bliz_dir = random.choice((-1, 1))
        for _ in range(int(70 * self.cfg["blizzard_power"])):
            self.parts.append(self.make_particle("snow", True, True))
        self.raise_all()

    def update_blizzard(self, now):
        cfg = self.cfg
        if self.bliz is None:
            self.bliz_f = 0.0
            every = cfg["blizzard_every"]
            if every > 0:
                if self.next_bliz is None:
                    self.next_bliz = now + every * 60 * random.uniform(0.6, 1.4)
                elif now >= self.next_bliz:
                    self.start_blizzard(now)
                    self.next_bliz = None
            else:
                self.next_bliz = None
            return
        t, L = now - self.bliz["t0"], self.bliz["len"]
        if t >= L:
            self.bliz, self.bliz_f = None, 0.0
            return
        ramp = L * 0.2
        self.bliz_f = max(0.0, min(1.0, t / ramp, (L - t) / ramp))

    def active_kinds(self):
        cfg = self.cfg
        mode = cfg["fall_mode"]
        if mode == "По погоде города" and self.city_kinds:
            return self.city_kinds
        if mode == "По сезону":
            return SEASON_KINDS[self.season]
        ks = [k for k, _ in KINDS if cfg["k_" + k]]
        return ks or SEASON_KINDS[self.season]

    def rebuild_particles(self):
        self.cv.delete("flake")
        self.chunks = []
        ks = self.active_kinds()
        n = int(self.cfg["density"])
        self.parts = []
        for k in ks:
            for _ in range(max(1, int(n / len(ks) * KIND_FACTOR.get(k, 1.0)))):
                self.parts.append(self.make_particle(k, True))
        if self.bliz:
            for _ in range(int(70 * self.cfg["blizzard_power"])):
                self.parts.append(self.make_particle("snow", True, True))
        self.dirty_particles = False
        self.raise_all()

    def make_particle(self, kind, random_y, storm=False):
        cv, cfg = self.cv, self.cfg
        d = random.uniform(0.35, 1.0)
        r = max(1.5, cfg["size"] * d)
        x = random.uniform(0, self.W)
        rise = kind in ("bubble", "lantern")
        if random_y:
            y = random.uniform(0, self.H)
        else:
            y = self.H + r * 4 if rise else -r * 4
        p = {"k": kind, "x": x, "y": y, "py": y, "vx": 0.0, "vy": 0.0, "r": r, "d": d,
             "size": r, "ph": random.uniform(0, 6.3), "flip": random.uniform(0, 6.3),
             "rot": random.uniform(0, 6.3), "spin": random.uniform(-0.07, 0.07),
             "hid": False, "lands": True, "mat": "snow", "amt": 1.0, "tv": 1.0,
             "drag": 0.08, "sway": 0.6, "mob": 1.0, "storm": storm, "shape": None,
             "draw": "dot", "ids": [], "rise": rise, "diag": False, "col": "#FFFFFF",
             "fspin": 0.07}
        if kind == "snow":
            col = blend(cfg["snow_color"], 0.55 + 0.45 * d)
            style = cfg["snow_style"]
            p.update(tv=0.6 + 1.5 * d, col=col)
            if style == "Точки" or (style == "Все вместе" and random.random() < 0.35):
                p["ids"] = [cv.create_oval(0, 0, 1, 1, fill=col, outline="", tags="flake")]
            else:
                ch = {"Звёздочки ❄": "❄", "Хлопья ❅": "❅", "Кристаллы ❆": "❆"}.get(style) \
                    or random.choice("❄❅❆")
                p["draw"] = "glyph"
                p["ids"] = [cv.create_text(x, y, text=ch, fill=col, tags="flake",
                                           font=("Segoe UI Symbol", max(7, int(r * 3))))]
        elif kind == "leaf":
            col = random.choice(AUTUMN)
            p.update(draw="poly", shape=LEAF, size=r * 1.5 + 3, tv=0.55 + 1.0 * d,
                     sway=1.4, drag=0.05, mat="leaf", amt=1.3, col=col)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline=blend(col, 0.6),
                                          smooth=False, tags="flake")]
        elif kind == "spring":
            if random.random() < 0.55:
                col = random.choice(SPRING_LEAF)
                p.update(shape=LEAF, size=r * 1.2 + 2.5)
            else:
                col = random.choice(PETAL_COL)
                p.update(shape=PETAL, size=r * 0.9 + 2)
            p.update(draw="poly", tv=0.45 + 0.8 * d, sway=1.2, drag=0.05, mat="spring",
                     amt=0.8, col=col)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline=blend(col, 0.7),
                                          smooth=False, tags="flake")]
        elif kind == "firefly":
            col = random.choice(FLY_COL)
            p.update(draw="fly", lands=False, col=col, tv=0.0, r=max(1.5, cfg["size"] * 0.5 * d))
            p["ids"] = [cv.create_oval(0, 0, 1, 1, fill=col, outline="", tags="flake")]
        elif kind == "confetti":
            col = random.choice(CONFETTI_COL)
            p.update(draw="poly", shape=RECT, size=r * 0.9 + 2, tv=0.9 + 1.0 * d, sway=1.0,
                     mat="confetti", amt=0.6, col=col, spin=random.uniform(-0.25, 0.25), fspin=0.22)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline="", tags="flake")]
        elif kind == "bubble":
            rr = max(4.0, cfg["size"] * 1.8 * d + 4)
            p.update(draw="bubble", r=rr, tv=-(0.4 + 0.8 * d), sway=1.6, lands=False, drag=0.05)
            p["ids"] = [cv.create_oval(0, 0, 1, 1, fill="", outline="#BFE9FF", width=1, tags="flake")]
        elif kind == "heart":
            col = random.choice(HEART_COL)
            p.update(draw="glyph", tv=0.7 + 0.9 * d, sway=1.0, mat="heart", amt=0.7, col=col)
            p["ids"] = [cv.create_text(x, y, text="♥", fill=col, tags="flake",
                                       font=("Segoe UI Symbol", max(8, int(r * 3.2) + 4)))]
        elif kind == "star":
            col = random.choice(STAR_COL)
            p.update(draw="glyph", tv=1.2 + 1.8 * d, sway=0.3, drag=0.1, mat=None, col=col, diag=True)
            p["ids"] = [cv.create_text(x, y, text=random.choice("★✦✧"), fill=col, tags="flake",
                                       font=("Segoe UI Symbol", max(8, int(r * 3.1) + 4)))]
        elif kind == "rain":
            col = blend("#9CC4F0", 0.6 + 0.4 * d)
            p.update(draw="line", tv=9 + 8 * d, drag=0.3, mob=0.4, sway=0.0, mat=None, col=col)
            p["ids"] = [cv.create_line(0, 0, 1, 1, fill=col, width=2 if d > 0.75 else 1, tags="flake")]
        else:
            p.update(draw="lantern", size=r * 1.2 + 6, tv=-(0.45 + 0.5 * d), sway=1.2, lands=False, drag=0.04)
            p["ids"] = [cv.create_oval(0, 0, 1, 1, fill="#FF8F3A", outline="#FFD08A", tags="flake")]
        p["vy"] = p["tv"] * cfg["speed"]
        self.place(p)
        return p

    def place(self, p):
        cv, x, y, r, dr, ids = self.cv, p["x"], p["y"], p["r"], p["draw"], p["ids"]
        if dr in ("dot", "fly", "bubble"):
            cv.coords(ids[0], x - r, y - r, x + r, y + r)
        elif dr == "glyph":
            cv.coords(ids[0], x, y)
        elif dr == "lantern":
            s = p["size"]
            cv.coords(ids[0], x - s * 0.8, y - s, x + s * 0.8, y + s)
        elif dr == "line":
            cv.coords(ids[0], x, y, x - p["vx"] * 1.8, y - p["vy"] * 1.8)
        else:
            wf = 0.35 + 0.65 * abs(math.cos(p["flip"]))
            cv.coords(ids[0], *shape_pts(p["shape"], x, y, p["size"], p["rot"], wf))

    def respawn(self, p):
        p["x"] = random.uniform(0, self.W)
        p["y"] = p["py"] = (self.H + p["r"] * 4) if p["rise"] else -p["r"] * 4
        p["vx"] = 0.0
        p["vy"] = p["tv"] * self.cfg["speed"]

    def update_particles(self, now):
        cfg, cv = self.cfg, self.cv
        spd = cfg["speed"] * (1 + self.bliz_f * cfg["blizzard_power"] * 0.8)
        wob = cfg["wobble"]
        wind = self.wind_now(now)
        W, H = self.W, self.H
        surfs = self.surfaces
        pile_en = cfg["pile_enabled"]
        rects = self.win_rects if cfg["only_desktop"] else None
        cur_pt = self.cur
        phys = cfg["cursor_mode"].startswith("Физика") and cur_pt is not None
        if cur_pt is not None:
            cx, cy, cvx, cvy = cur_pt
            rad = float(cfg["cursor_radius"])
            rad2 = rad * rad
            force = cfg["cursor_force"]
        storm_on = self.bliz is not None
        dead = []
        for p in self.parts:
            if p["storm"] and not storm_on and random.random() < 0.05:
                dead.append(p)
                continue
            p["ph"] += 0.06
            dr = p["draw"]
            if dr == "fly":
                p["x"] += (math.cos(p["ph"] * 0.7) * 0.8 + wind * 0.3) * spd
                p["y"] += math.sin(p["ph"] * 0.5) * 0.6 * spd
                if p["x"] > W + 30:
                    p["x"] = -30
                elif p["x"] < -30:
                    p["x"] = W + 30
                if p["y"] > H + 30:
                    p["y"] = -30
                elif p["y"] < -30:
                    p["y"] = H + 30
                if self.frame % 8 == 0:
                    f = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(p["ph"] * 2.3))
                    cv.itemconfigure(p["ids"][0], fill=blend(p["col"], f))
            else:
                p["py"] = p["y"]
                wx = wind * p["mob"] * (0.4 + p["d"]) + math.sin(p["ph"]) * wob * p["sway"]
                if p["diag"]:
                    wx += 1.5
                dg = p["drag"]
                vx = p["vx"] + (wx * spd - p["vx"]) * dg
                vy = p["vy"] + (p["tv"] * spd - p["vy"]) * dg
                if cur_pt is not None:
                    ddx, ddy = p["x"] - cx, p["y"] - cy
                    pop_r = max(rad * 0.45, p["r"] + 14.0)
                    if p["k"] == "bubble" and abs(ddx) <= pop_r and abs(ddy) <= pop_r:
                        if ddx * ddx + ddy * ddy <= pop_r * pop_r:
                            self.pop_bubble(p)
                            self.respawn(p)
                            self.place(p)
                            continue
                    if phys and -rad < ddx < rad and -rad < ddy < rad:
                        d2 = ddx * ddx + ddy * ddy
                        if 0.01 < d2 < rad2:
                            dist = math.sqrt(d2)
                            f = (1 - dist / rad)
                            f = f * f * force
                            vx += ddx / dist * f * 2.4 + cvx * 0.14 * f
                            vy += ddy / dist * f * 2.4 + cvy * 0.14 * f
                vx = max(-26.0, min(26.0, vx))
                vy = max(-26.0, min(30.0, vy))
                p["vx"], p["vy"] = vx, vy
                p["x"] += vx
                p["y"] += vy
                p["rot"] += p["spin"] * spd
                p["flip"] += p["fspin"] * spd
                x, y, py = p["x"], p["y"], p["py"]
                respawn = False
                if p["rise"]:
                    if y < -p["r"] * 5:
                        respawn = True
                else:
                    hit = None
                    if p["lands"]:
                        for (key, a, e, top, left, width) in surfs:
                            if a <= x <= e:
                                ys = top - (self.pile_h(key, left, x) if pile_en else 0.0)
                                if py < ys <= y:
                                    hit = (key, left, width, ys)
                                    break
                    if hit:
                        k = p["k"]
                        if k == "rain":
                            self.splash(x, hit[3])
                        elif k == "star":
                            self.burst(x, hit[3], 6, p["col"])
                        elif pile_en and p["mat"]:
                            self.land(hit[0], hit[1], hit[2], x, p["mat"],
                                      p["amt"] * (0.4 + p["d"]) * cfg["pile_rate"])
                        respawn = True
                    elif y > H + 14:
                        respawn = True
                if respawn:
                    if p["storm"] and not storm_on:
                        dead.append(p)
                        continue
                    self.respawn(p)
                elif p["x"] > W + 14:
                    p["x"] = -14
                elif p["x"] < -14:
                    p["x"] = W + 14
                if p["k"] == "star" and self.frame % 5 == 0:
                    self.spawn_fx(p["x"], p["y"], -p["vx"] * 0.1, -p["vy"] * 0.1, 7, p["col"], 1.3, drag=0.9)
            self.place(p)
            if rects is not None:
                x, y = p["x"], p["y"]
                inside = False
                for (l, t, r_, b) in rects:
                    if l <= x <= r_ and t <= y <= b:
                        inside = True
                        break
                if inside != p["hid"]:
                    p["hid"] = inside
                    st = "hidden" if inside else "normal"
                    for i in p["ids"]:
                        cv.itemconfigure(i, state=st)
            elif p["hid"]:
                p["hid"] = False
                for i in p["ids"]:
                    cv.itemconfigure(i, state="normal")
        if dead:
            for p in dead:
                for i in p["ids"]:
                    cv.delete(i)
            ds = set(id(p) for p in dead)
            self.parts = [p for p in self.parts if id(p) not in ds]

    def pop_bubble(self, p):
        for _ in range(4):
            self.spawn_fx(p["x"], p["y"], random.uniform(-2.0, 2.0), random.uniform(-2.0, 1.0),
                          10, "#BFE9FF", 1.6, g=0.05)

    def splash(self, x, y):
        self.spawn_fx(x, y - 1, random.uniform(-1.2, 1.2), -random.uniform(1.0, 2.2),
                      9, "#9CC4F0", 1.3, g=0.25)

    def burst(self, x, y, n, col):
        for _ in range(n):
            a = random.uniform(0, 6.283)
            s = random.uniform(0.8, 2.8)
            self.spawn_fx(x, y, math.cos(a) * s, math.sin(a) * s - 1, 12, col, 1.5, g=0.08, drag=0.93)

    def get_pile(self, key, width):
        n = int(width // BIN) + 3
        p = self.piles.get(key)
        if p is None:
            p = {"h": [0.0] * n, "m": [None] * n}
            self.piles[key] = p
        elif len(p["h"]) != n:
            p["h"] = (p["h"] + [0.0] * n)[:n]
            p["m"] = (p["m"] + [None] * n)[:n]
        return p

    def pile_h(self, key, left, x):
        p = self.piles.get(key)
        if not p:
            return 0.0
        i = int((x - left) // BIN)
        h = p["h"]
        return h[i] if 0 <= i < len(h) else 0.0

    def land(self, key, left, width, x, mat, amt):
        p = self.get_pile(key, width)
        h, m = p["h"], p["m"]
        i = int((x - left) // BIN)
        cap = self.cfg["pile_max"]
        for off, k in ((0, 1.0), (-1, 0.6), (1, 0.6)):
            j = i + off
            if 0 <= j < len(h):
                h[j] = min(cap, h[j] + amt * k)
                m[j] = mat
        self.pile_dirty = True

    def redraw_piles(self):
        cv = self.cv
        cv.delete("pile")
        self.pile_dirty = False
        if not self.cfg["pile_enabled"]:
            return
        cap = self.cfg["pile_max"]
        for p in self.piles.values():
            relax(p["h"], cap)
        for key, d in self.surf_info.items():
            p = self.piles.get(key)
            if not p:
                continue
            h, m, left, top = p["h"], p["m"], d["left"], d["top"]
            tg = ("pile", "w%s" % key)
            for (a, c) in d["spans"]:
                samples = []
                x = a
                while True:
                    i = int((x - left) // BIN)
                    hh = h[i] if 0 <= i < len(h) else 0.0
                    mt = m[i] if (0 <= i < len(m) and hh >= 0.3) else None
                    samples.append((x, hh if hh >= 0.3 else 0.0, mt))
                    if x >= c:
                        break
                    x = min(x + BIN, c)
                n = len(samples)
                s = 0
                while s < n:
                    mt = samples[s][2]
                    e = s
                    while e + 1 < n and samples[e + 1][2] == mt:
                        e += 1
                    if mt is not None:
                        lo, hi = max(0, s - 1), min(n - 1, e + 1)
                        seg = samples[lo:hi + 1]
                        if max(q[1] for q in seg) >= 0.8:
                            pts = []
                            for (qx, qh, _m) in seg:
                                pts += [qx, top - qh]
                            pts += [seg[-1][0], top, seg[0][0], top]
                            col = MAT_COLOR.get(mt, "#FFFFFF")
                            cv.create_polygon(*pts, fill=col, outline=blend(col, 0.85),
                                              width=1, tags=tg)
                    s = e + 1

    def garland_style(self):
        v = self.cfg["garland_style"]
        if v.startswith("Авто"):
            return AUTO_STYLE[self.season]
        return GARLAND_STYLES.get(v, "bulb")

    def deco(self, style, k, bx, by, r, cols, tg, wire, glow_lvl):
        cv = self.cv
        if style == "bulb":
            col = cols[k % 4]
            halo = None
            if glow_lvl >= 2:
                halo = cv.create_oval(bx - r * 1.4, by + 3, bx + r * 1.4, by + 7 + r * 2.2,
                                     fill=col, outline="", stipple="gray25", tags=tg)
            cv.create_rectangle(bx - 2, by, bx + 2, by + 5, fill="#37474F", outline="", tags=tg)
            core = cv.create_oval(bx - r * 0.85, by + 4, bx + r * 0.85, by + 4 + r * 2.2,
                                  fill=col, outline=mix(col, "#FFFFFF", 0.5), tags=tg)
            return (core, halo, col, k)
        if style == "icicle":
            L = 14 + (k * 7) % 22
            wd = r * 0.8 + 3
            cv.create_polygon(bx - wd, by + 1, bx + wd, by + 1, bx, by + 2 + L,
                              fill="#D6EEFF", outline="#8CC8FF", tags=tg)
            col = "#8FD8FF"
            tip = cv.create_oval(bx - 2.4, by + L - 1, bx + 2.4, by + L + 4, fill=col, outline="", tags=tg)
            return (tip, None, col, k)
        if style == "ball":
            rb = r * 1.1 + 4
            col = cols[k % 4]
            cy = by + 5 + rb
            cv.create_line(bx, by, bx, by + 5, fill=wire, tags=tg)
            body = cv.create_oval(bx - rb, cy - rb, bx + rb, cy + rb, fill=col,
                                  outline=blend(col, 0.55), tags=tg)
            return (body, None, col, k)
        if style == "star":
            rs = r * 1.4 + 4
            col = "#FFD54F" if k % 3 == 0 else cols[k % 4]
            cy = by + 4 + rs
            pts = []
            for q in range(10):
                ang = -math.pi / 2 + q * math.pi / 5
                rad = rs if q % 2 == 0 else rs * 0.45
                pts += [bx + math.cos(ang) * rad, cy + math.sin(ang) * rad]
            st = cv.create_polygon(*pts, fill=col, outline=mix(col, "#FFFFFF", 0.5), tags=tg)
            return (st, None, col, k)
        if style == "lantern":
            rl = r * 1.1 + 4
            hh = rl * 1.5
            col = cols[k % 4]
            cy = by + 6 + hh
            body = cv.create_oval(bx - rl, cy - hh, bx + rl, cy + hh, fill=col,
                                  outline=blend(col, 0.55), tags=tg)
            return (body, None, col, k)
        if style == "flag":
            w = r * 1.2 + 4
            h = w * 1.6
            col = FLAG_COL[k % len(FLAG_COL)]
            cv.create_polygon(bx - w, by + 1, bx + w, by + 1, bx, by + 1 + h,
                              fill=col, outline=blend(col, 0.6), tags=tg)
            return None
        if style == "leaf":
            col = AUTUMN[(k * 5 + k // 3) % len(AUTUMN)]
            sz = r * 1.5 + 3
            rot = math.pi + math.sin(k * 1.7) * 0.5
            cv.create_polygon(*shape_pts(LEAF, bx, by + 4 + sz, sz, rot, 0.85), fill=col,
                              outline=blend(col, 0.6), smooth=False, tags=tg)
            return None
        pc = PETAL_COL[(k * 3 + k // 2) % len(PETAL_COL)]
        sz = r * 0.9 + 3
        cy = by + 5 + sz
        cv.create_oval(bx - sz, cy - sz, bx + sz, cy + sz, fill=pc, outline="#FBC02D", tags=tg)
        return None

    def build_garland_key(self, key, d):
        cv, cfg = self.cv, self.cfg
        self.lights[key] = []
        if isinstance(key, str) or not cfg["garland_enabled"]:
            return
        if cfg["garland_winter_only"] and self.season != "winter":
            return
        style = self.garland_style()
        tg = ("garland", "w%s" % key)
        cols = [cfg["color1"], cfg["color2"], cfg["color3"], cfg["color4"]]
        sag, wire, ww, r = cfg["garland_sag"], cfg["garland_wire"], cfg["garland_width"], cfg["bulb_size"]
        gap = max(20, cfg["garland_gap"] * (0.7 if style == "icicle" else 1.0))
        y = d["top"]
        k = key % 7
        glow_lvl = int(cfg["garland_glow"])
        for (a, b) in d["spans"]:
            n_arcs = max(1, round((b - a) / max(100, cfg["garland_arc"])))
            w = (b - a) / n_arcs
            for i in range(n_arcs):
                x0 = a + i * w
                pts = []
                for s in range(9):
                    t = s / 8
                    pts += [x0 + t * w, y + 2 + sag * 4 * t * (1 - t)]
                cv.create_line(*pts, fill=wire, width=ww, smooth=False, tags=tg)
                cnt = max(1, int(w / gap))
                for j in range(cnt):
                    t = (j + 0.5) / cnt
                    bx = x0 + t * w
                    by = y + 2 + sag * 4 * t * (1 - t)
                    st = style if style != "mix" else ("bulb", "icicle", "ball", "star")[k % 4]
                    ent = self.deco(st, k, bx, by, r, cols, tg, wire, glow_lvl)
                    if ent:
                        self.lights[key].append(ent)
                    k += 1

    def blink(self, t):
        cv = self.cv
        mode, spd = self.cfg["blink_mode"], self.cfg["blink_speed"]
        for lst in self.lights.values():
            for core, halo, col, k in lst:
                use_col = col
                if mode == "Бегущая волна":
                    f = 0.55 + 0.45 * math.sin(t * spd * 2 - k * 0.6)
                elif mode == "Мигание":
                    f = 1.0 if (int(t * spd) + k) % 2 == 0 else 0.15
                elif mode == "Переливание (плавное)":
                    f = 0.85
                    use_col = hsv_hex(t * spd * 0.12 + k * 0.08, 0.85, 1.0)
                elif mode == "Двойной бегущий огонь":
                    idx = int(t * spd * 3) % 4
                    f = 1.0 if (k % 4) in (idx, (idx + 2) % 4) else 0.18
                elif mode == "Стробоскоп":
                    f = 1.0 if int(t * spd * 5) % 2 == 0 else 0.1
                elif mode == "Дыхание":
                    f = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(t * spd * 1.5))
                elif mode == "Случайное мерцание":
                    f = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(t * spd * 2.7 + k * 3.17))
                else:
                    f = 1.0
                cv.itemconfigure(core, fill=mix(use_col, "#FFFFFF", 0.1 + 0.4 * f) if f > 0.35
                                 else blend(use_col, 0.45))
                if halo:
                    cv.itemconfigure(halo, fill=use_col, state="normal" if f > 0.65 else "hidden")

    def update_cursor(self):
        px, py = self.get_cursor()
        x, y = px - self.vx, py - self.vy
        c = self.cur
        if c is None:
            self.cur = [x, y, 0.0, 0.0]
            return
        c[2] = c[2] * 0.6 + (x - c[0]) * 0.4
        c[3] = c[3] * 0.6 + (y - c[1]) * 0.4
        c[0], c[1] = x, y

    def scatter_snowman(self, sm, cvx=0.0, cvy=0.0):
        pos = self.snowman_pos(sm)
        if not pos:
            return
        sx, sy = pos
        for _ in range(12):
            self.spawn_chunk(
                sx + random.uniform(-14, 14),
                sy - random.uniform(4, 34 * self.cfg["snowman_size"]),
                cvx * 0.3 + random.uniform(-3.0, 3.0),
                -random.uniform(1.5, 4.5) + cvy * 0.15,
                "snow",
                random.uniform(1.8, 3.2),
            )
        self.dirty_snowmen = True

    def interact(self, now):
        cfg = self.cfg
        mode = cfg["cursor_mode"]
        if not self.visible or self.cur is None or mode == "Ничего":
            return
        cx, cy, cvx, cvy = self.cur
        rad, pm = cfg["cursor_radius"], cfg["pile_max"]
        if mode.startswith("Сметать"):
            r2 = rad * 0.5
            for (key, a, c, top, left, width) in self.surfaces:
                if cx < a - r2 or cx > c + r2 or cy < top - pm - r2 or cy > top + r2:
                    continue
                p = self.piles.get(key)
                if not p:
                    continue
                h = p["h"]
                for i in range(max(0, int((cx - r2 - left) // BIN)),
                               min(len(h) - 1, int((cx + r2 - left) // BIN)) + 1):
                    bx = left + i * BIN
                    if h[i] > 0.05 and a <= bx <= c and abs(bx - cx) < r2:
                        h[i] = 0.0 if abs(bx - cx) < r2 * 0.6 else h[i] * 0.4
                        self.pile_dirty = True
            keep = []
            for sm in self.snowmen:
                pos = self.snowman_pos(sm)
                if pos and abs(pos[0] - cx) <= r2 and \
                        pos[1] - 85 * cfg["snowman_size"] <= cy <= pos[1] + r2:
                    self.scatter_snowman(sm, cvx, cvy)
                    continue
                keep.append(sm)
            self.snowmen = keep
        elif math.hypot(cvx, cvy) > 9.0:
            keep = []
            for sm in self.snowmen:
                pos = self.snowman_pos(sm)
                if pos and abs(pos[0] - cx) <= rad * 0.55 and \
                        pos[1] - 85 * cfg["snowman_size"] <= cy <= pos[1] + 18:
                    self.scatter_snowman(sm, cvx, cvy)
                    continue
                keep.append(sm)
            self.snowmen = keep
            if cfg["cursor_blow"]:
                spawned = 0
                for (key, a, c, top, left, width) in self.surfaces:
                    if cx < a - rad or cx > c + rad or cy < top - pm - rad or cy > top + rad:
                        continue
                    p = self.piles.get(key)
                    if not p:
                        continue
                    h, m = p["h"], p["m"]
                    for i in range(max(0, int((cx - rad * 0.7 - left) // BIN)),
                                   min(len(h) - 1, int((cx + rad * 0.7 - left) // BIN)) + 1):
                        bx = left + i * BIN
                        if h[i] > 0.5 and a <= bx <= c and spawned < 4:
                            self.spawn_chunk(bx, top - h[i], cvx * 0.35 + random.uniform(-1.5, 1.5),
                                             -random.uniform(1.0, 3.5) + cvy * 0.15, m[i] or "snow",
                                             random.uniform(1.3, 2.4))
                            h[i] *= 0.55
                            spawned += 1
                            self.pile_dirty = True

    def can_make_snowball(self):
        return "snow" in self.active_kinds()

    def snowman_radii(self):
        s = self.cfg["snowman_size"]
        return (13 * s, 9.5 * s, 6.5 * s)

    def snowman_pos(self, sm):
        info = self.surf_info.get(sm["key"])
        if not info:
            return None
        x = info["left"] + sm["off"]
        y = info["top"] + sm.get("y_off", 0.0)
        for a, c in info["spans"]:
            if a - 20 <= x <= c + 20:
                return x, y
        return None

    def roll_target(self, key, x):
        info = self.surf_info.get(key)
        R = self.snowman_radii()
        if info:
            for sm in self.snowmen:
                if sm["key"] == key and sm["stage"] < 3 and abs(info["left"] + sm["off"] - x) < 34:
                    return sm, R[sm["stage"]]
        return None, R[0]

    def update_roll(self, now):
        cfg, cv = self.cfg, self.cv
        if not cfg["roll_enabled"] or self.cur is None or not self.visible or not self.can_make_snowball():
            if self.roll:
                self.roll = None
                cv.delete("ball")
            return
        down = self.get_key(0x11 if cfg["roll_key"] == "Ctrl" else 0x10)
        cx, cy = self.cur[0], self.cur[1]
        rb = self.roll
        if down:
            if rb is None:
                pm = cfg["pile_max"]
                for key, d in self.surf_info.items():
                    for a, c in d["spans"]:
                        if a <= cx <= c and d["top"] - pm - 35 <= cy <= d["top"] + 20 and \
                                self.pile_h(key, d["left"], cx) >= 1.2:
                            self.roll = {"key": key, "r": 3.0, "lx": cx, "y": cy}
                            break
                    if self.roll:
                        break
                return
            info = self.surf_info.get(rb["key"])
            if not info:
                self.roll = None
                cv.delete("ball")
                return
            dist = abs(cx - rb["lx"])
            rb["lx"] = cx
            rb["y"] = cy
            _sm, target = self.roll_target(rb["key"], cx)
            hh = self.pile_h(rb["key"], info["left"], cx)
            p = self.piles.get(rb["key"])
            if p and hh >= 0.6 and dist > 0 and rb["r"] < target:
                rb["r"] = min(target, rb["r"] + dist * 0.08 * min(2.2, hh / 3.5 + 0.6))
                h = p["h"]
                for i in range(max(0, int((cx - rb["r"] - 6 - info["left"]) // BIN)),
                               min(len(h) - 1, int((cx + rb["r"] + 6 - info["left"]) // BIN)) + 1):
                    h[i] *= 0.85
                self.pile_dirty = True
            cv.delete("ball")
            r = rb["r"]
            by = cy if r >= target * 0.98 else (info["top"] - r)
            cv.create_oval(cx - r, by - r, cx + r, by + r, fill="#FFFFFF", outline="#9DB7D8", tags="ball")
            cv.tag_raise("ball")
        elif rb:
            self.roll = None
            cv.delete("ball")
            info = self.surf_info.get(rb["key"])
            if not info:
                return
            sm, target = self.roll_target(rb["key"], rb["lx"])
            is_max = rb["r"] >= target * 0.95
            if rb["r"] >= target * 0.55 or is_max:
                y_off = min(0.0, rb["y"] - info["top"]) if is_max else 0.0
                if sm:
                    sm["stage"] = min(3, sm["stage"] + 1)
                    sm["born"] = now
                else:
                    self.snowmen.append({
                        "key": rb["key"],
                        "off": rb["lx"] - info["left"],
                        "y_off": y_off,
                        "stage": 1,
                        "born": now,
                    })
                while len(self.snowmen) > int(cfg["snowman_max"]):
                    self.snowmen.pop(0)
                self.dirty_snowmen = True

    def update_snowmen_melt(self, now):
        melt_sec = float(self.cfg.get("snowman_melt_sec", 0))
        if melt_sec <= 0 or not self.snowmen:
            return
        keep = []
        changed = False
        for sm in self.snowmen:
            born = sm.get("born", now)
            if now - born >= melt_sec:
                changed = True
                continue
            keep.append(sm)
        if changed:
            self.snowmen = keep
            self.dirty_snowmen = True

    def redraw_snowmen(self):
        self.cv.delete("snowman")
        self.dirty_snowmen = False
        for sm in self.snowmen:
            pos = self.snowman_pos(sm)
            if pos:
                self.draw_snowman(pos[0], pos[1] + 1, sm["stage"], "w%s" % sm["key"])

    def draw_snowman(self, x, y, stage, wt):
        cv, s, t = self.cv, self.cfg["snowman_size"], ("snowman", wt)
        r1, r2, r3 = self.snowman_radii()
        y1 = y - r1
        y2 = y1 - (r1 + r2) * 0.82
        y3 = y2 - (r2 + r3) * 0.82
        ol = "#9DB7D8"
        if stage >= 2:
            w = max(1, int(s * 1.5))
            cv.create_line(x - r2 * 0.9, y2, x - r2 * 2.0, y2 - r2 * 0.9, fill="#6D4C41", width=w, tags=t)
            cv.create_line(x + r2 * 0.9, y2, x + r2 * 2.0, y2 - r2 * 0.9, fill="#6D4C41", width=w, tags=t)
        balls = [(x, y1, r1)]
        if stage >= 2:
            balls.append((x, y2, r2))
        if stage >= 3:
            balls.append((x, y3, r3))
        for cx, cy, rr in balls:
            cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill="#FFFFFF", outline=ol, width=1, tags=t)
        if stage >= 3:
            cv.create_rectangle(x - r3 * 0.95, y3 - r3 * 0.85, x + r3 * 0.95, y3 - r3 * 0.62,
                                fill="#212121", outline="", tags=t)
            cv.create_rectangle(x - r3 * 0.6, y3 - r3 * 1.7, x + r3 * 0.6, y3 - r3 * 0.8,
                                fill="#212121", outline="", tags=t)
            cv.create_polygon(x, y3 + r3 * 0.05, x + r3 * 1.1, y3 + r3 * 0.2, x, y3 + r3 * 0.3,
                              fill="#FB8C00", outline="", tags=t)

    def has_snow(self):
        return any(p["h"] and max(p["h"]) >= 2.0 for p in self.piles.values())

    def start_plow(self):
        if self.plow or not self.surf_info:
            return
        best, bs = None, -1.0
        for key in self.surf_info:
            p = self.piles.get(key)
            s = sum(p["h"]) if p else 0.0
            if isinstance(key, str):
                s += 0.5
            if s > bs:
                best, bs = key, s
        d = random.choice((-1, 1))
        if isinstance(best, str):
            self.plow = {
                "multi_ground": True,
                "dir": d,
                "x": -35.0 if d > 0 else float(self.W + 35),
            }
        else:
            width = self.surf_info[best]["width"]
            self.plow = {
                "multi_ground": False,
                "key": best,
                "dir": d,
                "off": -30 if d > 0 else width + 30,
            }

    def update_plow(self, now):
        cv, cfg = self.cv, self.cfg
        cv.delete("plow")
        pl = self.plow
        if not pl:
            ev = cfg["plow_every"]
            if ev > 0 and now - self.last_plow >= ev * 60:
                if self.has_snow():
                    self.start_plow()
                else:
                    self.last_plow = now
            return

        if pl.get("multi_ground"):
            pl["x"] += pl["dir"] * cfg["plow_speed"] * 1.3
            x = pl["x"]
            if x < -60 or x > self.W + 60:
                self.plow, self.last_plow = None, now
                return
            ground_keys = sorted(
                [k for k in self.surf_info if isinstance(k, str)],
                key=lambda k: self.surf_info[k]["left"],
            )
            cur_info = None
            for gk in ground_keys:
                inf = self.surf_info[gk]
                if inf["left"] <= x <= inf["left"] + inf["width"]:
                    cur_info = (gk, inf)
                    break
            if cur_info is None and ground_keys:
                gk = min(ground_keys, key=lambda k: abs((self.surf_info[k]["left"] + self.surf_info[k]["width"] * 0.5) - x))
                cur_info = (gk, self.surf_info[gk])
            if cur_info:
                gk, info = cur_info
                p = self.piles.get(gk)
                if p:
                    h = p["h"]
                    fx = (x - info["left"]) + pl["dir"] * 26
                    for i in range(max(0, int((fx - 16) // BIN)), min(len(h) - 1, int((fx + 16) // BIN)) + 1):
                        if h[i] > 0:
                            h[i] = 0.0
                            self.pile_dirty = True
                self.draw_plow(x, info["top"], pl["dir"], now)
                cv.tag_raise("plow")
            return

        info = self.surf_info.get(pl["key"])
        if not info:
            self.plow, self.last_plow = None, now
            return
        pl["off"] += pl["dir"] * cfg["plow_speed"] * 1.2
        if pl["off"] < -40 or pl["off"] > info["width"] + 40:
            self.plow, self.last_plow = None, now
            return
        x = info["left"] + pl["off"]
        p = self.piles.get(pl["key"])
        if p:
            h = p["h"]
            fx = pl["off"] + pl["dir"] * 26
            for i in range(max(0, int((fx - 14) // BIN)), min(len(h) - 1, int((fx + 14) // BIN)) + 1):
                if h[i] > 0:
                    h[i] = 0.0
                    self.pile_dirty = True
        if any(a <= x <= c for a, c in info["spans"]):
            self.draw_plow(x, info["top"], pl["dir"], now)
            cv.tag_raise("plow")

    def draw_plow(self, x, y, d, now):
        cv, t = self.cv, "plow"

        def P(*pts):
            out = []
            for i in range(0, len(pts), 2):
                out += [x + pts[i] * d, y + pts[i + 1]]
            return out

        cv.create_polygon(*P(-34, -6, -34, -18, 20, -18, 24, -6), fill="#FBC02D", outline="#7A5B00", tags=t)
        cv.create_polygon(*P(-28, -18, -22, -31, -4, -31, 2, -18), fill="#FBC02D", outline="#7A5B00", tags=t)
        cv.create_polygon(*P(26, -26, 42, -6, 42, 1, 26, 1), fill="#EF6C00", outline="#7A3300", tags=t)
        for wx, wr in ((-20, 6), (8, 6)):
            cx = x + wx * d
            cv.create_oval(cx - wr, y - 5 - wr, cx + wr, y - 5 + wr, fill="#263238", outline="", tags=t)
        bc = "#FF9800" if int(now * 6) % 2 == 0 else "#7A2E00"
        bx = x - 12 * d
        cv.create_oval(bx - 3, y - 37, bx + 3, y - 31, fill=bc, outline="", tags=t)

    def spawn_fx(self, x, y, vx, vy, life, col, size, g=0.0, drag=0.97, glyph=None, ring=False):
        if len(self.fx) >= FX_LIMIT:
            return
        cv = self.cv
        if glyph:
            i = cv.create_text(x, y, text=glyph, fill=col, tags="fx",
                               font=("Segoe UI Symbol", max(6, int(size * 2.4))))
        elif ring:
            i = cv.create_oval(x - size, y - size, x + size, y + size, fill="", outline=col, tags="fx")
        else:
            i = cv.create_oval(x - size, y - size, x + size, y + size, fill=col, outline="", tags="fx")
        life = max(2, int(life))
        self.fx.append({"x": x, "y": y, "vx": vx, "vy": vy, "life": life, "max": life, "col": col,
                        "size": size, "g": g, "drag": drag, "glyph": glyph, "id": i})

    def update_fx(self):
        if not self.fx:
            return
        cv = self.cv
        keep = []
        odd = self.frame % 4 == 0
        for f in self.fx:
            f["life"] -= 1
            if f["life"] <= 0:
                cv.delete(f["id"])
                continue
            f["vx"] *= f["drag"]
            f["vy"] = f["vy"] * f["drag"] + f["g"]
            f["x"] += f["vx"]
            f["y"] += f["vy"]
            k = f["life"] / f["max"]
            x, y = f["x"], f["y"]
            if f["glyph"]:
                cv.coords(f["id"], x, y)
            else:
                s = f["size"] * (0.3 + 0.7 * k)
                cv.coords(f["id"], x - s, y - s, x + s, y + s)
            if odd:
                cv.itemconfigure(f["id"], fill=blend(f["col"], 0.35 + 0.65 * k))
            keep.append(f)
        self.fx = keep

    def update_trail(self, now):
        cfg = self.cfg
        if not cfg["trail_enabled"] or self.cur is None or not self.visible:
            return
        cx, cy, vx, vy = self.cur
        sp = math.hypot(vx, vy)
        if sp < 1.5:
            return
        n = cfg["trail_amount"] * min(2.5, 0.35 + sp / 9)
        count = int(n) + (1 if random.random() < n - int(n) else 0)
        kind, sz, life = cfg["trail_kind"], cfg["trail_size"], 18 * cfg["trail_life"]
        for _ in range(min(3, count)):
            px, py = cx + random.uniform(-3, 3), cy + random.uniform(-3, 3)
            if kind == "Искры":
                self.spawn_fx(px, py, random.uniform(-1.5, 1.5) - vx * 0.05, random.uniform(-2, 0.5),
                              life, random.choice(SPARK_COL), 1.7 * sz, g=0.1)
            elif kind == "Звёздная пыль":
                self.spawn_fx(px, py, random.uniform(-0.5, 0.5), -random.uniform(0.1, 0.7), life * 1.4,
                              random.choice(DUST_COL), 2.4 * sz, glyph="✦")
            elif kind == "Радуга":
                self.spawn_fx(px, py, 0, 0, life, hsv_hex(now * 0.4 + random.random() * 0.05, 0.85, 1.0),
                              3.2 * sz, drag=1.0)
            elif kind == "Пузырьки":
                self.spawn_fx(px, py, random.uniform(-0.4, 0.4), -random.uniform(0.4, 1.2), life * 1.4,
                              "#BFE9FF", random.uniform(3, 5.5) * sz, ring=True, drag=0.99)
            elif kind == "Сердечки":
                self.spawn_fx(px, py, random.uniform(-0.5, 0.5), -random.uniform(0.5, 1.2), life * 1.4,
                              random.choice(HEART_COL), 2.6 * sz, glyph="♥")
            elif kind == "Снежинки":
                self.spawn_fx(px, py, random.uniform(-0.6, 0.6), random.uniform(0.2, 0.8), life * 1.4,
                              "#FFFFFF", 2.4 * sz, glyph="❄")
            else:
                self.spawn_fx(px, py, random.uniform(-0.5, 0.5), -random.uniform(0.8, 2.0), life,
                              random.choice(FIRE_COL), 3.2 * sz, drag=0.98)

    def update_schedule(self, now):
        cfg = self.cfg
        if cfg["meteor_enabled"]:
            if self.next_meteor == 0.0:
                self.next_meteor = now + random.uniform(1, max(2, cfg["meteor_every"]))
            elif now >= self.next_meteor:
                self.spawn_meteor()
                self.next_meteor = now + cfg["meteor_every"] * random.uniform(0.5, 1.5)
        else:
            self.next_meteor = 0.0

        if cfg["santa_enabled"]:
            if self.next_santa == 0.0:
                self.next_santa = now + random.uniform(2, max(4, cfg["santa_every"]))
            elif now >= self.next_santa:
                self.spawn_santa()
                self.next_santa = now + cfg["santa_every"] * random.uniform(0.7, 1.3)
        else:
            self.next_santa = 0.0

        if cfg["fw_enabled"]:
            if self.next_fw == 0.0:
                self.next_fw = now + random.uniform(1, max(2, cfg["fw_every"]))
            elif now >= self.next_fw:
                self.spawn_rocket()
                self.next_fw = now + cfg["fw_every"] * random.uniform(0.5, 1.5)
        else:
            self.next_fw = 0.0

        keep = []
        for m in self.meteors:
            m["x"] += m["vx"]
            m["y"] += m["vy"]
            m["life"] -= 1
            self.spawn_fx(m["x"], m["y"], 0, 0, 3, "#FFFFFF", 2.4 * cfg["meteor_len"], drag=1.0)
            if m["life"] > 0 and -80 < m["x"] < self.W + 80 and m["y"] < self.H:
                keep.append(m)
        self.meteors = keep

        self.cv.delete("santa")
        keep_santa = []
        sz = float(cfg.get("santa_size", 1.0))
        for st in self.santas:
            st["x"] += st["vx"]
            st["ph"] += 0.14
            sy = st["y"] + math.sin(st["ph"]) * 7.0
            sx = st["x"]
            d = 1 if st["vx"] > 0 else -1
            self.draw_santa(sx, sy, d, sz)
            if self.frame % 3 == 0:
                self.spawn_fx(sx - 24 * d * sz, sy + random.uniform(-4, 6),
                              -st["vx"] * 0.2, random.uniform(-0.4, 0.4),
                              14, "#FFD54F", 1.7 * sz, glyph="✦")
            if -140 < sx < self.W + 140:
                keep_santa.append(st)
        self.santas = keep_santa

        keep = []
        for rk in self.rockets:
            rk["y"] += rk["vy"]
            self.spawn_fx(rk["x"], rk["y"], 0, 0, 2, "#FFFFFF", 2.2, drag=1.0)
            if rk["y"] <= rk["ty"]:
                self.firework_burst(rk["x"], rk["y"], rk["col"])
            else:
                keep.append(rk)
        self.rockets = keep

    def spawn_santa(self):
        d = random.choice((-1, 1))
        x = -90.0 if d > 0 else float(self.W + 90)
        y = random.uniform(0.08, 0.28) * self.H
        self.santas.append({"x": x, "y": y, "vx": d * 4.5, "ph": 0.0})

    def draw_santa(self, x, y, d, s):
        cv = self.cv
        rx = x + 36 * d * s
        cv.create_oval(rx - 9 * s, y - 5 * s, rx + 9 * s, y + 4 * s, fill="#8D6E63", outline="", tags="santa")
        cv.create_oval(rx + 10 * d * s - 2 * s, y - 7 * s, rx + 10 * d * s + 2 * s, y - 3 * s, fill="#FF3B30", outline="", tags="santa")
        cv.create_line(x + 12 * d * s, y, rx - 6 * d * s, y - 2 * s, fill="#FFD54F", width=1, tags="santa")
        cv.create_polygon(x - 22 * d * s, y + 6 * s, x + 16 * d * s, y + 6 * s,
                          x + 12 * d * s, y - 6 * s, x - 18 * d * s, y - 6 * s,
                          fill="#D32F2F", outline="#FFD54F", tags="santa")
        cv.create_oval(x - 8 * s, y - 15 * s, x + 4 * s, y - 4 * s, fill="#E53935", outline="", tags="santa")

    def spawn_meteor(self):
        dirx = random.choice((-1, 1))
        sp = random.uniform(14, 22)
        x = random.uniform(0.15, 0.95) * self.W if dirx < 0 else random.uniform(0.05, 0.85) * self.W
        self.meteors.append({"x": x, "y": random.uniform(0.02, 0.35) * self.H,
                             "vx": dirx * sp * 0.8, "vy": sp * 0.45, "life": random.randint(22, 38)})

    def spawn_rocket(self):
        self.rockets.append({"x": random.uniform(0.1, 0.9) * self.W, "y": self.H - 60.0,
                             "vy": -random.uniform(9, 13), "ty": random.uniform(0.12, 0.45) * self.H,
                             "col": random.choice(FW_COL)})

    def firework_burst(self, x, y, col):
        size = self.cfg["fw_size"]
        n = min(45, int(28 * size))
        ring = random.random() < 0.3
        col2 = random.choice(FW_COL)
        for i in range(n):
            a = (i / n) * 6.283 if ring else random.uniform(0, 6.283)
            s = (3.0 if ring else random.uniform(1.2, 4.8)) * size
            self.spawn_fx(x, y, math.cos(a) * s, math.sin(a) * s, random.randint(24, 38),
                          col if random.random() < 0.7 else col2, 1.8, g=0.06, drag=0.96)

    def effect_enabled(self, name):
        c = self.cfg
        if name == "sky":
            return c["sky_body"] != "Выкл"
        if name == "aurora":
            return c["aurora_enabled"] and (c["aurora_when"] == "Всегда" or self.season == "winter")
        return bool(c.get(name + "_enabled"))

    def update_effects(self, now):
        for name in EFFECT_NAMES:
            try:
                en = self.effect_enabled(name)
                on = self.effect_on.get(name, False)
                if name in self.fx_dirty or en != on:
                    self.cv.delete("e_" + name)
                    self.effect_on[name] = False
                    self.fx_dirty.discard(name)
                    if en:
                        getattr(self, "build_" + name)()
                        self.effect_on[name] = True
                        self.raise_all()
                if self.effect_on.get(name) and name != "neon":
                    getattr(self, "update_" + name)(now)
            except Exception:
                if self.strict:
                    raise
                log_error("effect " + name)
                self.cv.delete("e_" + name)
                self.effect_on[name] = False
                if name == "sky":
                    self.cfg["sky_body"] = "Выкл"
                else:
                    self.cfg[name + "_enabled"] = False

    def build_aurora(self):
        cv, _cfg = self.cv, self.cfg
        self.aur_cols = max(12, min(22, int(self.W // 95)))
        self.aur = []
        for _b in range(2):
            cols = []
            for _i in range(self.aur_cols):
                pid = cv.create_polygon(0, 0, 1, 0, 1, 1, 0, 1, fill="#39FF8A", outline="",
                                        stipple="gray12", tags="e_aurora")
                cols.append({"id": pid, "hid": False})
            self.aur.append(cols)

    def aurora_color(self, name, pos, t, band):
        if name == "Радужное":
            return hsv_hex(pos * 0.7 + t * 0.03 + band * 0.15, 0.6, 1.0)
        pal = AURORA_PAL[name]
        x = ((pos + 0.15 * math.sin(t * 0.2 + band)) % 1.0) * (len(pal) - 1)
        i = int(x)
        return mix(pal[i], pal[min(i + 1, len(pal) - 1)], x - i)

    def update_aurora(self, now):
        if self.frame % 8:
            return
        cv, cfg = self.cv, self.cfg
        W, H = self.W, self.H
        t = now * cfg["aurora_speed"]
        n = self.aur_cols
        dx = W / n
        Ht = H * cfg["aurora_height"] / 100.0
        recolor = self.frame % 24 == 0
        behind = cfg["aurora_behind"] or cfg["only_desktop"]
        for b in range(2):
            base = Ht * (0.22 + 0.18 * b)
            amp = Ht * 0.16
            ytop = [base + amp * math.sin(i * dx * 0.004 + t * 0.4 + b * 1.7) for i in range(n + 1)]
            ln = [Ht * (0.30 + 0.20 * math.sin(i * dx * 0.006 + t * 0.3 + b * 2.1)) for i in range(n + 1)]
            for i, col in enumerate(self.aur[b]):
                x0, x1 = i * dx, i * dx + dx
                y0a, y1a = ytop[i], ytop[i + 1]
                y0b, y1b = y0a + ln[i], y1a + ln[i + 1]
                cv.coords(col["id"], x0, y0a, x1, y1a, x1, y1b, x0, y0b)
                if recolor:
                    cv.itemconfigure(col["id"], fill=self.aurora_color(cfg["aurora_palette"], i / n, t, b))
                if behind:
                    hid = self.covered((x0 + x1) / 2, (y0a + y0b) / 2)
                    if hid != col["hid"]:
                        col["hid"] = hid
                        cv.itemconfigure(col["id"], state="hidden" if hid else "normal")
                elif col["hid"]:
                    col["hid"] = False
                    cv.itemconfigure(col["id"], state="normal")

    def build_stars(self):
        cv, cfg = self.cv, self.cfg
        rnd = random.Random(7)
        self.stars = []
        hh = self.H * cfg["stars_height"] / 100.0
        for idx in range(int(cfg["stars_count"])):
            x, y = rnd.uniform(0, self.W), rnd.uniform(0, hh)
            glyph = "✦" if idx % 3 == 0 else ("★" if idx % 5 == 0 else "✧")
            fsize = rnd.randint(9, 14)
            tint = rnd.choice(("#FFFFFF", "#CFE3FF", "#FFF2C8"))
            i = cv.create_text(x, y, text=glyph, fill=tint, tags="e_stars",
                               font=("Segoe UI Symbol", fsize))
            self.stars.append({"id": i, "x": x, "y": y, "ph": rnd.uniform(0, 6.3),
                               "tint": tint, "hid": False})

    def update_stars(self, now):
        if self.frame % 8:
            return
        cv, cfg = self.cv, self.cfg
        tw = cfg["stars_twinkle"]
        chk = self.frame % 24 == 0
        for s in self.stars:
            f = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(now * tw * 2 + s["ph"]))
            cv.itemconfigure(s["id"], fill=blend(s["tint"], f))
            if chk:
                hid = self.covered(s["x"], s["y"])
                if hid != s["hid"]:
                    s["hid"] = hid
                    cv.itemconfigure(s["id"], state="hidden" if hid else "normal")

    def build_sky(self):
        cv, cfg = self.cv, self.cfg
        body = cfg["sky_body"]
        if body == "Авто":
            body = "Солнце" if 6 <= time.localtime().tm_hour < 19 else "Луна"
        S = float(cfg["sky_size"])
        cx = self.W - S * 1.8 if cfg["sky_corner"].startswith("Прав") else S * 1.8
        cy = S * 1.6
        self.sky = {"body": body, "cx": cx, "cy": cy, "S": S, "hid": False, "ids": [], "rays": []}
        ids = self.sky["ids"]
        if body == "Луна":
            ids.append(cv.create_oval(cx - S * 0.5, cy - S * 0.5, cx + S * 0.5, cy + S * 0.5,
                                      fill="#F4F1DE", outline="#FFFFFF", tags="e_sky"))
        else:
            for _ in range(8):
                self.sky["rays"].append(cv.create_line(0, 0, 1, 1, fill="#FFE082", width=2, tags="e_sky"))
            ids.append(cv.create_oval(cx - S * 0.45, cy - S * 0.45, cx + S * 0.45, cy + S * 0.45,
                                      fill="#FFD54F", outline="#FFF3B0", width=2, tags="e_sky"))

    def update_sky(self, now):
        if self.frame % 8:
            return
        sk, cv = self.sky, self.cv
        if sk["rays"]:
            cx, cy, S = sk["cx"], sk["cy"], sk["S"]
            for i, rid in enumerate(sk["rays"]):
                a = now * 0.25 + i * math.pi / 4
                ln = S * (0.85 + 0.15 * math.sin(now * 2 + i))
                cv.coords(rid, cx + math.cos(a) * S * 0.55, cy + math.sin(a) * S * 0.55,
                          cx + math.cos(a) * ln, cy + math.sin(a) * ln)
        if self.frame % 24 == 0:
            hid = self.covered(sk["cx"], sk["cy"])
            if hid != sk["hid"]:
                sk["hid"] = hid
                for i in sk["ids"] + sk["rays"]:
                    cv.itemconfigure(i, state="hidden" if hid else "normal")

    def build_halo(self):
        cv = self.cv
        self.halo_dots = [
            cv.create_oval(0, 0, 1, 1, fill=self.cfg["halo_color"], outline="", tags="e_halo")
            for _ in range(8)
        ]

    def update_halo(self, now):
        if self.cur is None:
            return
        cx, cy, _, _ = self.cur
        rad = float(self.cfg.get("halo_radius", 55))
        spd = float(self.cfg.get("halo_speed", 1.5))
        col = self.cfg.get("halo_color", "#5CC8FF")
        n = len(self.halo_dots)
        for idx, did in enumerate(self.halo_dots):
            ang = now * spd + idx * (2 * math.pi / n)
            px = cx + math.cos(ang) * rad
            py = cy + math.sin(ang) * rad
            r = 2.4 if idx % 2 == 0 else 1.7
            self.cv.coords(did, px - r, py - r, px + r, py + r)
            if self.frame % 8 == 0:
                self.cv.itemconfigure(did, fill=col)

    def build_neon(self):
        cv = self.cv
        w = self.cfg["neon_width"]
        self.neon = [cv.create_rectangle(0, 0, 1, 1, outline="#FFFFFF", width=w, state="hidden", tags="e_neon")]
        self.neon_vis = False

    def neon_color(self, now):
        cfg = self.cfg
        m = cfg["neon_mode"]
        t = now * cfg["neon_speed"]
        if m == "Радуга":
            return hsv_hex(t * 0.15, 0.9, 1.0)
        if m == "Фиолетовый":
            return mix("#9B5DE5", "#F15BB5", 0.5 + 0.5 * math.sin(t))
        return mix("#00BBF9", "#00F5D4", 0.5 + 0.5 * math.sin(t))

    def update_neon(self, now):
        cv = self.cv
        fg = self.get_fg()
        rect = None
        for (hw, l, t, r, b, mx) in self.wins:
            if hw == fg and not mx:
                rect = (l - self.vx, t - self.vy, r - self.vx, b - self.vy)
                break
        if rect is None:
            if self.neon_vis:
                cv.itemconfigure(self.neon[0], state="hidden")
                self.neon_vis = False
            return
        cv.coords(self.neon[0], *rect)
        cv.itemconfigure(self.neon[0], outline=self.neon_color(now), state="normal")
        self.neon_vis = True

    def build_edge(self):
        cv, cfg = self.cv, self.cfg
        s = float(cfg["edge_size"]) * 0.5
        W = self.W
        gy = (self.work[0][3] - self.vy) if self.work else self.H
        self.edge = [
            cv.create_rectangle(0, 0, W, s, fill="#FF00FF", outline="", stipple="gray12", tags="e_edge"),
            cv.create_rectangle(0, 0, s, gy, fill="#FF00FF", outline="", stipple="gray12", tags="e_edge"),
            cv.create_rectangle(W - s, 0, W, gy, fill="#FF00FF", outline="", stipple="gray12", tags="e_edge"),
        ]

    def update_edge(self, now):
        if self.frame % 8:
            return
        cfg = self.cfg
        t = now * cfg["edge_speed"]
        m = cfg["edge_mode"]
        pulse = 0.65 + 0.35 * math.sin(t * 1.3)
        for side in range(3):
            if m == "Радуга":
                c = hsv_hex(t * 0.1 + side * 0.25, 0.85, 1.0)
            elif m == "Тёплый":
                c = mix("#FF6B35", "#F72585", 0.5 + 0.5 * math.sin(t + side))
            elif m == "Холодный":
                c = mix("#4CC9F0", "#7209B7", 0.5 + 0.5 * math.sin(t + side))
            else:
                c = {"winter": "#BFE3FF", "autumn": "#FF9F1C", "spring": "#FFB3D9",
                     "summer": "#FFE066"}[self.season]
            self.cv.itemconfigure(self.edge[side], fill=blend(c, pulse))

    def build_tree(self):
        cv, cfg = self.cv, self.cfg
        s = cfg["tree_size"] / 100.0
        corner = cfg["tree_corner"]
        mons = self.work or self.monitors or [(self.vx, self.vy, self.vx + self.W, self.vy + self.H)]
        mons_sorted = sorted(mons, key=lambda m: m[0])
        if corner.startswith("Правый монитор"):
            mon = mons_sorted[-1]
        elif corner.startswith("Левый монитор"):
            mon = mons_sorted[0]
        else:
            mon = mons_sorted[-1]
        place_right = "правый низ" in corner.lower() or corner == "Правый низ"
        l, _t, r, b = mon
        by = b - self.vy
        Tw, Th = 150 * s, 230 * s
        cx = (r - self.vx - 40 * s - Tw / 2) if place_right else (l - self.vx + 40 * s + Tw / 2)
        tg = "e_tree"
        cv.create_rectangle(cx - 9 * s, by - Th * 0.16, cx + 9 * s, by, fill="#6D4C41", outline="", tags=tg)
        layers = ((0.52, 0.12, 0.5), (0.78, 0.40, 0.4), (0.98, 0.66, 0.28))
        for apex, base, hw in layers:
            cv.create_polygon(cx, by - Th * apex, cx - Tw * hw, by - Th * base, cx + Tw * hw, by - Th * base,
                              fill="#1B8A3A", outline="#0E5A24", width=2, tags=tg)
        pts = []
        for q in range(10):
            ang = -math.pi / 2 + q * math.pi / 5
            rad = 13 * s if q % 2 == 0 else 6 * s
            pts += [cx + math.cos(ang) * rad, by - Th * 1.0 + math.sin(ang) * rad]
        cv.create_polygon(*pts, fill="#FFD54F", outline="#FFF3B0", tags=tg)
        rnd = random.Random(5)
        self.tree_lights = []
        pal = ["#FF3B30", "#FFD60A", "#34C759", "#0A84FF", "#FF6FD8"]
        for apex, base, hw in layers:
            for _ in range(4):
                v = rnd.uniform(0.15, 0.95)
                yy = by - Th * (apex - (apex - base) * v)
                half = Tw * hw * v
                xx = cx + rnd.uniform(-0.85, 0.85) * half
                col = rnd.choice(pal)
                rr = 4.2 * s
                o = cv.create_oval(xx - rr, yy - rr, xx + rr, yy + rr, fill=col, outline="", tags=tg)
                self.tree_lights.append((o, col, rnd.uniform(0, 6.3)))

    def update_tree(self, now):
        if self.frame % 8:
            return
        for o, col, ph in self.tree_lights:
            f = 0.5 + 0.5 * math.sin(now * 3 + ph)
            self.cv.itemconfigure(o, fill=mix(col, "#FFFFFF", 0.15 + 0.4 * f) if f > 0.3 else blend(col, 0.4))


# ---------------------------------------------------------------- Приложение
BG, PANEL, FG, MUTED, ACCENT = "#12162B", "#1D2345", "#E8ECFF", "#8C96C4", "#5CC8FF"


class ScrollFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=(14, 10))
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.canvas.bind("<Enter>", self._bind)
        self.canvas.bind("<Leave>", self._unbind)
        self.inner.bind("<Enter>", self._bind)

    def _bind(self, _e=None):
        self.canvas.bind_all("<MouseWheel>", self._wheel)

    def _unbind(self, _e=None):
        self.canvas.unbind_all("<MouseWheel>")

    def _wheel(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120), "units")


class App:
    def __init__(self, autostart=False):
        self.cfg = load_cfg()
        self.root = tk.Tk()
        self.root.title("Времена года и гирлянда")
        self.root.configure(bg=BG)
        self.root.geometry("650x770")
        self.root.resizable(False, True)
        self.vx = user32.GetSystemMetrics(76)
        self.vy = user32.GetSystemMetrics(77)
        self.W = user32.GetSystemMetrics(78)
        self.H = user32.GetSystemMetrics(79)
        self.visible = True
        self.paused_background = False
        self.ready = False
        self.setters = {}
        self.build_overlay()
        app_hwnd = int(self.root.winfo_id())
        ov_hwnd = int(user32.GetParent(self.ov.winfo_id()) or self.ov.winfo_id())
        self.engine = Engine(self.canvas, self.cfg, (self.vx, self.vy, self.W, self.H),
                             app_hwnd=app_hwnd, ov_hwnd=ov_hwnd)
        self.build_ui()
        self.tray = TrayIcon(self.root, self.show_window, self.toggle, self.quit)
        self.ready = True
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_background)
        if autostart:
            self.hide_to_background()
        self.slow_tick()
        self.fast_tick()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if self.paused_background:
            self.paused_background = False
            self.engine.visible = self.visible
            if self.visible:
                self.ov.deiconify()

    def hide_to_background(self):
        save_cfg(self.cfg)
        self.root.withdraw()
        if self.cfg.get("pause_on_close", True):
            self.paused_background = True
            self.engine.visible = False
            self.ov.withdraw()

    def build_overlay(self):
        self.ov = tk.Toplevel(self.root)
        self.ov.overrideredirect(True)
        self.ov.geometry("%dx%d+%d+%d" % (self.W, self.H, self.vx, self.vy))
        self.ov.configure(bg=KEY)
        self.ov.attributes("-topmost", True)
        self.ov.attributes("-transparentcolor", KEY)
        self.canvas = tk.Canvas(self.ov, bg=KEY, highlightthickness=0, width=self.W, height=self.H)
        self.canvas.pack(fill="both", expand=True)
        self.ov.update_idletasks()
        hwnd = user32.GetParent(self.ov.winfo_id()) or self.ov.winfo_id()
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)

    def set_cfg(self, key, value):
        self.cfg[key] = value
        if self.ready:
            self.engine.notify(key)

    def style(self):
        st = ttk.Style()
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, bordercolor=PANEL,
                     lightcolor=PANEL, darkcolor=PANEL, troughcolor=PANEL, font=("Segoe UI", 10))
        st.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        st.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(11, 7),
                     borderwidth=0, font=("Segoe UI", 9, "bold"))
        st.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", "#0B1020")])
        st.configure("TLabel", background=BG, foreground=FG)
        st.configure("TCheckbutton", background=BG, foreground=FG, indicatorcolor=PANEL,
                     indicatorbackground=PANEL, focuscolor=BG)
        st.map("TCheckbutton", indicatorcolor=[("selected", ACCENT)], background=[("active", BG)],
               foreground=[("active", FG)])
        st.configure("Horizontal.TScale", background=BG, troughcolor=PANEL, bordercolor=BG,
                     lightcolor=ACCENT, darkcolor=ACCENT)
        st.configure("TButton", background=PANEL, foreground=FG, padding=(10, 7), borderwidth=0,
                     focuscolor=PANEL)
        st.map("TButton", background=[("active", "#2C3566")])
        st.configure("Accent.TButton", background=ACCENT, foreground="#0B1020", font=("Segoe UI", 10, "bold"))
        st.map("Accent.TButton", background=[("active", "#8FDBFF")])
        st.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG, arrowcolor=FG,
                     bordercolor=PANEL, padding=4)
        st.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)],
               selectbackground=[("readonly", PANEL)], selectforeground=[("readonly", FG)])
        st.configure("Vertical.TScrollbar", background=PANEL, troughcolor=BG, bordercolor=BG, arrowcolor=FG)
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#0B1020")

    def tab(self, nb, title):
        sf = ScrollFrame(nb)
        nb.add(sf, text=title)
        return sf.inner

    def section(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=ACCENT, font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(12, 2))

    def hint(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=MUTED, justify="left", wraplength=570,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 4))

    def apply_city_weather(self):
        city = self.city_var.get().strip()
        self.set_cfg("city_name", city)
        self.weather_lbl.config(text="Загрузка погоды...")

        def worker():
            info = None
            try:
                info = fetch_city_weather(city)
            except Exception:
                info = None

            def done():
                if info:
                    self.engine.city_kinds = info["kinds"]
                    self.cfg["wind"] = info["wind"]
                    if "wind" in self.setters:
                        self.setters["wind"](info["wind"])
                    self.engine.dirty_particles = True
                    self.weather_lbl.config(text=info["summary"])
                else:
                    self.weather_lbl.config(text="Не удалось получить погоду (проверьте сеть/город)")

            self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def build_ui(self):
        self.style()
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(head, text="Времена года и гирлянда", bg=BG, fg=FG, font=("Segoe UI", 16, "bold")).pack(side="left")
        self.badge = tk.Label(head, text="", bg=ACCENT, fg="#0B1020", padx=10, pady=3,
                              font=("Segoe UI Symbol", 10, "bold"))
        self.badge.pack(side="right")
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=12, pady=8)

        t = self.tab(nb, "Что падает")
        self.combo(t, "Сезон", "season", ["Авто", "Зима", "Осень", "Весна", "Лето"])
        self.combo(t, "Что падает", "fall_mode", ["По сезону", "Свой набор", "По погоде города"])

        crow = ttk.Frame(t)
        crow.pack(fill="x", pady=4)
        ttk.Label(crow, text="Город для погоды", width=28, anchor="w").pack(side="left")
        self.city_var = tk.StringVar(value=self.cfg.get("city_name", "Днепр"))
        ent = ttk.Entry(crow, textvariable=self.city_var, width=20)
        ent.pack(side="left", padx=(0, 6))
        ttk.Button(crow, text="Обновить погоду", command=self.apply_city_weather).pack(side="left")
        self.weather_lbl = tk.Label(t, text=self.cfg.get("city_weather_status", "Не задан"),
                                    bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.weather_lbl.pack(anchor="w", pady=(0, 4))

        self.hint(t, "«Свой набор» — отметьте всё, что должно падать одновременно:")
        grid = ttk.Frame(t)
        grid.pack(fill="x")
        for n, (k, label) in enumerate(KINDS):
            self.check_grid(grid, label, "k_" + k, n // 2, n % 2)
        self.combo(t, "Вид снежинок", "snow_style",
                   ["Все вместе", "Звёздочки ❄", "Хлопья ❅", "Кристаллы ❆", "Точки"])
        self.color(t, "Цвет снега", "snow_color")
        self.scale(t, "Количество", "density", 0, 260, 10)
        self.scale(t, "Скорость", "speed", 0.1, 4.0, 0.1)
        self.scale(t, "Размер", "size", 2, 14, 1)
        self.combo(t, "Направление ветра", "wind_dir", ["Авто", "Влево", "Вправо"])
        self.scale(t, "Сила ветра", "wind_strength", 0.0, 3.0, 0.1)
        self.scale(t, "Смещение ветра (← →)", "wind", -3.0, 3.0, 0.1)
        self.scale(t, "Покачивание", "wobble", 0.0, 4.0, 0.1)
        self.check(t, "Только на рабочем столе (не считая гирлянды/сугробов на окнах)", "only_desktop")

        t = self.tab(nb, "Физика")
        self.section(t, "Ветер")
        self.scale(t, "Порывы ветра", "gust_power", 0.0, 3.0, 0.1)
        self.scale(t, "Скорость порывов", "gust_speed", 0.2, 3.0, 0.1)
        self.section(t, "Метель")
        self.scale(t, "Каждые N минут (0 — выкл)", "blizzard_every", 0, 60, 1)
        self.scale(t, "Длительность, сек", "blizzard_len", 5, 120, 5)
        self.scale(t, "Сила метели", "blizzard_power", 0.5, 3.0, 0.1)
        ttk.Button(t, text="Запустить метель сейчас", command=lambda: self.engine.start_blizzard()).pack(
            fill="x", pady=4)
        self.section(t, "Курсор и пузыри")
        self.combo(t, "Режим курсора", "cursor_mode", ["Физика ветра", "Сметать", "Ничего"])
        self.scale(t, "Радиус", "cursor_radius", 30, 200, 5)
        self.scale(t, "Сила отталкивания", "cursor_force", 0.1, 3.0, 0.1)
        self.check(t, "Быстрый курсор раздувает сугробы и разносит снеговиков", "cursor_blow")
        self.section(t, "Лепка снеговика")
        self.check(t, "Включить лепку (только когда идёт снег)", "roll_enabled")
        self.combo(t, "Клавиша", "roll_key", ["Ctrl", "Shift"])
        self.scale(t, "Размер снеговика", "snowman_size", 0.6, 2.0, 0.1)
        self.scale(t, "Макс. снеговиков", "snowman_max", 1, 15, 1)
        self.scale(t, "Время таяния, сек (0 — не тают)", "snowman_melt_sec", 0, 600, 15)

        t = self.tab(nb, "Гирлянда")
        self.check(t, "Включить гирлянду", "garland_enabled")
        self.check(t, "Только зимой", "garland_winter_only")
        self.check(t, "Не вешать на развёрнутые окна", "skip_maximized")
        self.combo(t, "Вид гирлянды", "garland_style",
                   ["Авто (по сезону)", "Лампочки", "Сосульки", "Шарики", "Звёзды", "Фонарики",
                    "Флажки", "Листья", "Цветы", "Микс"])
        self.scale(t, "Яркость свечения", "garland_glow", 1, 3, 1)
        self.scale(t, "Длина дуги", "garland_arc", 100, 600, 10)
        self.scale(t, "Провисание", "garland_sag", 0, 100, 1)
        self.scale(t, "Между украшениями", "garland_gap", 20, 120, 2)
        self.scale(t, "Размер украшений", "bulb_size", 2, 14, 1)
        self.scale(t, "Толщина провода", "garland_width", 1, 6, 1)
        self.color(t, "Цвет провода", "garland_wire")
        row = ttk.Frame(t)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Цвета огоньков", width=28).pack(side="left")
        for k in ("color1", "color2", "color3", "color4"):
            self.color_button(row, k).pack(side="left", padx=3)
        self.combo(t, "Режим мигания", "blink_mode", BLINK_MODES)
        self.scale(t, "Скорость мигания", "blink_speed", 0.2, 10.0, 0.2)

        t = self.tab(nb, "Сугробы")
        self.check(t, "Снег и листья оседают на окнах и панели задач", "pile_enabled")
        self.scale(t, "Высота сугроба", "pile_max", 4, 40, 1)
        self.scale(t, "Скорость накопления", "pile_rate", 0.2, 6.0, 0.2)
        self.hint(t, "Если окно закрыть или быстро двигать — сугроб осыпается вниз.")
        self.section(t, "Уборочная машина")
        self.scale(t, "Выезжает каждые N минут (0 — выкл)", "plow_every", 0, 60, 1)
        self.scale(t, "Скорость машины", "plow_speed", 1, 10, 1)
        ttk.Button(t, text="Запустить машину сейчас", style="Accent.TButton",
                   command=lambda: self.engine.start_plow()).pack(fill="x", pady=(8, 2))
        r2 = ttk.Frame(t)
        r2.pack(fill="x")
        ttk.Button(r2, text="Убрать снеговиков", command=lambda: self.engine.clear_snowmen()).pack(
            side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(r2, text="Очистить весь снег", command=lambda: self.engine.clear_snow()).pack(
            side="left", expand=True, fill="x", padx=(3, 0))

        t = self.tab(nb, "Небо")
        self.section(t, "Северное сияние")
        self.check(t, "Включить сияние", "aurora_enabled")
        self.combo(t, "Когда", "aurora_when", ["Всегда", "Только зимой"])
        self.combo(t, "Цвет", "aurora_palette", ["Зелёное", "Фиолетовое", "Розовое", "Радужное"])
        self.scale(t, "Высота, % экрана", "aurora_height", 10, 50, 1)
        self.scale(t, "Скорость", "aurora_speed", 0.2, 3.0, 0.1)
        self.scale(t, "Яркость", "aurora_power", 1, 3, 1)
        self.check(t, "Не рисовать поверх окон", "aurora_behind")
        self.section(t, "Звёздное небо")
        self.check(t, "Включить звёзды", "stars_enabled")
        self.scale(t, "Количество", "stars_count", 20, 150, 10)
        self.scale(t, "Высота, % экрана", "stars_height", 10, 100, 5)
        self.scale(t, "Мерцание", "stars_twinkle", 0.2, 4.0, 0.1)
        self.section(t, "Луна / Солнце")
        self.combo(t, "Что показывать", "sky_body", ["Выкл", "Луна", "Солнце", "Авто"])
        self.combo(t, "Угол", "sky_corner", ["Правый верх", "Левый верх"])
        self.scale(t, "Размер", "sky_size", 30, 160, 5)
        self.section(t, "Метеоры")
        self.check(t, "Падающие звёзды (метеоры)", "meteor_enabled")
        self.scale(t, "В среднем раз в N сек", "meteor_every", 2, 60, 1)
        self.scale(t, "Длина хвоста", "meteor_len", 0.4, 3.0, 0.1)
        ttk.Button(t, text="Метеор сейчас", command=lambda: self.engine.spawn_meteor()).pack(fill="x", pady=4)
        self.section(t, "Сани Деда Мороза в небе")
        self.check(t, "Включить пролёт саней с оленями", "santa_enabled")
        self.scale(t, "В среднем раз в N сек", "santa_every", 5, 120, 5)
        self.scale(t, "Размер саней", "santa_size", 0.6, 2.0, 0.1)
        ttk.Button(t, text="Запустить сани сейчас", command=lambda: self.engine.spawn_santa()).pack(fill="x", pady=4)

        t = self.tab(nb, "Эффекты")
        self.section(t, "След за курсором")
        self.check(t, "Включить след", "trail_enabled")
        self.combo(t, "Вид", "trail_kind",
                   ["Искры", "Звёздная пыль", "Радуга", "Пузырьки", "Сердечки", "Снежинки", "Огонь"])
        self.scale(t, "Густота", "trail_amount", 0.2, 3.0, 0.1)
        self.scale(t, "Размер", "trail_size", 0.4, 3.0, 0.1)
        self.scale(t, "Время жизни", "trail_life", 0.3, 3.0, 0.1)

        self.section(t, "Орбитальный вихрь вокруг курсора")
        self.check(t, "Включить орбитальное кольцо", "halo_enabled")
        self.scale(t, "Радиус кольца", "halo_radius", 25, 130, 5)
        self.scale(t, "Скорость вращения", "halo_speed", 0.3, 5.0, 0.1)
        self.color(t, "Цвет огней кольца", "halo_color")

        self.section(t, "Сосульки с капелью на окнах")
        self.check(t, "Сосульки и падающие капли", "drip_enabled")
        self.scale(t, "Частота капель", "drip_rate", 0.2, 4.0, 0.2)
        self.scale(t, "Длина сосулек, px", "drip_len", 8, 36, 2)

        self.section(t, "Фейерверки")
        self.check(t, "Включить фейерверки", "fw_enabled")
        self.scale(t, "В среднем раз в N сек", "fw_every", 2, 60, 1)
        self.scale(t, "Размер", "fw_size", 0.5, 2.0, 0.1)
        ttk.Button(t, text="Запустить салют", command=lambda: self.engine.spawn_rocket()).pack(fill="x", pady=4)
        self.section(t, "Неоновая рамка активного окна")
        self.check(t, "Включить неон", "neon_enabled")
        self.combo(t, "Цвет", "neon_mode", ["Радуга", "Фиолетовый", "Голубой"])
        self.scale(t, "Толщина", "neon_width", 1, 8, 1)
        self.scale(t, "Скорость переливания", "neon_speed", 0.2, 4.0, 0.1)
        self.section(t, "Свечение по краям экрана (сверху и по бокам)")
        self.check(t, "Включить свечение", "edge_enabled")
        self.combo(t, "Цвет", "edge_mode", ["Радуга", "Тёплый", "Холодный", "По сезону"])
        self.scale(t, "Ширина", "edge_size", 20, 160, 5)
        self.scale(t, "Скорость", "edge_speed", 0.2, 4.0, 0.1)
        self.section(t, "Новогодняя ёлка")
        self.check(t, "Ёлка с подарками", "tree_enabled")
        self.combo(t, "Монитор / сторона", "tree_corner", [
            "Правый монитор (правый низ)",
            "Правый монитор (левый низ)",
            "Левый монитор (правый низ)",
            "Левый монитор (левый низ)",
        ])
        self.scale(t, "Размер, %", "tree_size", 40, 200, 5)

        t = self.tab(nb, "Система")
        self.auto_var = tk.BooleanVar(value=is_autostart())
        ttk.Checkbutton(t, text="Запускать вместе с Windows", variable=self.auto_var,
                        command=self.toggle_autostart).pack(anchor="w", pady=4)
        self.check(t, "Автопауза при полноэкранных играх и видео", "pause_fullscreen")
        self.check(t, "Ставить эффекты на паузу при закрытии окна настроек", "pause_on_close")
        self.scale(t, "Кадров в секунду", "fps", 15, 45, 5)
        self.hint(t, "При закрытии на крестик окно уходит в трей. Нажмите на иконку в трее, "
                     "чтобы открыть настройки или выключить эффекты.")

        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=12, pady=(2, 12))
        ttk.Button(bar, text="Сохранить", style="Accent.TButton", command=lambda: save_cfg(self.cfg)).pack(
            side="left", padx=3)
        ttk.Button(bar, text="Сбросить", command=self.reset).pack(side="left", padx=3)
        self.toggle_btn = ttk.Button(bar, text="Скрыть эффекты", command=self.toggle)
        self.toggle_btn.pack(side="left", padx=3)
        ttk.Button(bar, text="Выход", command=self.quit).pack(side="right", padx=3)
        ttk.Button(bar, text="В фон", command=self.hide_to_background).pack(side="right", padx=3)

    def scale(self, parent, text, key, lo, hi, step):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=3)
        ttk.Label(f, text=text, width=32, anchor="w").pack(side="left")
        lbl = tk.Label(f, text="", width=5, anchor="e", bg=BG, fg=ACCENT, font=("Segoe UI", 10, "bold"))
        lbl.pack(side="right")
        var = tk.DoubleVar(value=self.cfg[key])
        is_int = isinstance(step, int)

        def cmd(v):
            x = round(float(v) / step) * step
            x = int(x) if is_int else round(x, 2)
            lbl.config(text="%g" % x)
            if self.ready and self.cfg.get(key) != x:
                self.set_cfg(key, x)

        ttk.Scale(f, from_=lo, to=hi, variable=var, command=cmd).pack(side="left", fill="x", expand=True, padx=6)
        cmd(self.cfg[key])

        def setter(v):
            var.set(v)
            cmd(v)
            self.cfg[key] = v
            self.engine.notify(key)
        self.setters[key] = setter

    def _check_var(self, key):
        v = tk.BooleanVar(value=self.cfg[key])

        def setter(val):
            v.set(val)
            self.set_cfg(key, val)
        self.setters[key] = setter
        return v

    def check(self, parent, text, key):
        v = self._check_var(key)
        ttk.Checkbutton(parent, text=text, variable=v,
                        command=lambda: self.set_cfg(key, v.get())).pack(anchor="w", pady=3)

    def check_grid(self, parent, text, key, row, col):
        v = self._check_var(key)
        ttk.Checkbutton(parent, text=text, variable=v,
                        command=lambda: self.set_cfg(key, v.get())).grid(row=row, column=col, sticky="w",
                                                                         padx=(0, 18), pady=2)

    def combo(self, parent, text, key, values):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=4)
        ttk.Label(f, text=text, width=32, anchor="w").pack(side="left")
        v = tk.StringVar(value=self.cfg[key])
        cb = ttk.Combobox(f, textvariable=v, values=values, state="readonly", width=26)
        cb.pack(side="left", fill="x", expand=True)
        cb.bind("<<ComboboxSelected>>", lambda e: self.set_cfg(key, v.get()))

        def setter(val):
            v.set(val)
            self.set_cfg(key, val)
        self.setters[key] = setter

    def color_button(self, parent, key):
        b = tk.Button(parent, width=4, relief="flat", bd=0, cursor="hand2",
                      bg=self.cfg[key], activebackground=self.cfg[key])

        def pick():
            c = colorchooser.askcolor(self.cfg[key], parent=self.root)[1]
            if c:
                self.set_cfg(key, c)
                b.configure(bg=c, activebackground=c)
        b.configure(command=pick)

        def setter(val):
            b.configure(bg=val, activebackground=val)
            self.set_cfg(key, val)
        self.setters[key] = setter
        return b

    def color(self, parent, text, key):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=4)
        ttk.Label(f, text=text, width=32, anchor="w").pack(side="left")
        self.color_button(f, key).pack(side="left")

    def toggle_autostart(self):
        if not set_autostart(self.auto_var.get()):
            self.auto_var.set(is_autostart())

    def reset(self):
        for k, v in DEFAULTS.items():
            if k in self.setters:
                self.setters[k](v)
            else:
                self.set_cfg(k, v)

    def toggle(self):
        self.visible = not self.visible
        self.paused_background = False
        self.engine.visible = self.visible
        if self.visible:
            self.ov.deiconify()
            self.toggle_btn.configure(text="Скрыть эффекты")
        else:
            self.ov.withdraw()
            self.toggle_btn.configure(text="Показать эффекты")

    def quit(self):
        save_cfg(self.cfg)
        if hasattr(self, "tray") and self.tray:
            self.tray.remove()
        self.root.destroy()

    def fast_tick(self):
        try:
            if self.engine.visible:
                self.engine.scene_tick(time.time())
        except Exception:
            log_error("fast_tick")
        finally:
            self.root.after(80, self.fast_tick)

    def slow_tick(self):
        try:
            if self.engine.visible:
                self.engine.tick(time.time())
                if self.engine.frame % 45 == 1:
                    self.badge.config(text=SEASON_TITLE[self.engine.season])
        except Exception:
            log_error("slow_tick")
        finally:
            self.root.after(max(20, int(1000 / max(10, self.cfg["fps"]))), self.slow_tick)


def main():
    if os.name != "nt":
        print("Программа работает только в Windows.")
        sys.exit(1)
    _mutex = kernel32.CreateMutexW(None, False, "SnowGarland_single_instance")
    if ctypes.get_last_error() == 183:
        hwnd = user32.FindWindowW(None, "Времена года и гирлянда")
        if hwnd:
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
        return
    app = App(autostart="--autostart" in sys.argv)
    app.root.mainloop()


if __name__ == "__main__":
    main()
