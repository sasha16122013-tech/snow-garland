# -*- coding: utf-8 -*-
"""
AuraDesk — живая атмосфера рабочего стола: снег, погода на неделю,
гирлянда, сугробы с физикой, снеговики, Дед Мороз, северное сияние,
солнце, луна, звёзды и фейерверки.

Запуск: python auradesk.py   (или pythonw auradesk.py — без консоли)
Нужен только Python 3.8+ для Windows. Сторонние библиотеки не нужны.
"""
import colorsys
import ctypes
import datetime
import json
import math
import os
import queue
import random
import sys
import threading
import time
import traceback
import tkinter as tk
import urllib.parse
import urllib.request
from ctypes import wintypes
from tkinter import ttk, colorchooser

try:
    import winreg
except ImportError:
    winreg = None

# ---------------------------------------------------------------- WinAPI
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
shell32 = ctypes.windll.shell32
gdi32 = ctypes.windll.gdi32
kernel32w = ctypes.windll.kernel32
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
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)
WINEVENTPROC = ctypes.WINFUNCTYPE(None, wintypes.HANDLE, wintypes.DWORD,
                                  wintypes.HWND, ctypes.c_long, ctypes.c_long,
                                  wintypes.DWORD, wintypes.DWORD)

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
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
user32.EnumDisplayMonitors.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                       MONITORENUMPROC, wintypes.LPARAM]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetWinEventHook.argtypes = [wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                   WINEVENTPROC, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
user32.SetWinEventHook.restype = wintypes.HANDLE
user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.CreatePopupMenu.restype = ctypes.c_void_p
user32.AppendMenuW.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
user32.TrackPopupMenu.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
user32.TrackPopupMenu.restype = ctypes.c_int
user32.DestroyMenu.argtypes = [ctypes.c_void_p]
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                   wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, wintypes.HWND, ctypes.c_void_p,
                                   ctypes.c_void_p, ctypes.c_void_p]
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateIconIndirect.argtypes = [ctypes.c_void_p]
user32.CreateIconIndirect.restype = ctypes.c_void_p
gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.UINT, ctypes.c_void_p]
gdi32.CreateBitmap.restype = ctypes.c_void_p
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL
kernel32w.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32w.GetModuleHandleW.restype = ctypes.c_void_p
kernel32w.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32w.CreateEventW.restype = ctypes.c_void_p
kernel32w.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32w.OpenEventW.restype = ctypes.c_void_p
kernel32w.SetEvent.argtypes = [ctypes.c_void_p]
kernel32w.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
dwmapi.DwmGetWindowAttribute.argtypes = [
    wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]

GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW = 0x80000, 0x20, 0x80
WS_EX_NOACTIVATE = 0x08000000
EVENT_OBJECT_LOCATIONCHANGE = 0x800B


def get_windows():
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
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        if r.right - r.left < 150 or r.bottom - r.top < 80:
            return True
        result.append((int(hwnd), r.left, r.top, r.right, r.bottom,
                       bool(user32.IsZoomed(hwnd))))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return result


def get_monitors():
    res = []

    def cb(hmon, _hdc, _lprc, _lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            m, w = mi.rcMonitor, mi.rcWork
            res.append({"mon": (m.left, m.top, m.right, m.bottom),
                        "work": (w.left, w.top, w.right, w.bottom)})
        return True

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    res.sort(key=lambda r: r["mon"][0])
    return res


def cursor_pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def foreground_hwnd():
    return int(user32.GetForegroundWindow() or 0)


def fullscreen_foreground(mon_rects):
    hwnd = user32.GetForegroundWindow()
    if not hwnd or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
        return False
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return False
    buf = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(hwnd, buf, 128)
    if buf.value in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
        return False
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    for (ml, mt, mr, mb) in mon_rects:
        if r.left <= ml + 1 and r.top <= mt + 1 and r.right >= mr - 1 and r.bottom >= mb - 1:
            return True
    return False


def visible_top_edges(windows, skip_max):
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


# ---------------------------------------------------------------- Значок в трее
class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", ctypes.c_void_p), ("hIcon", ctypes.c_void_p),
                ("hCursor", ctypes.c_void_p), ("hbrBackground", ctypes.c_void_p),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT),
                ("hIcon", ctypes.c_void_p), ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256), ("uVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", ctypes.c_ubyte * 16), ("hBalloonIcon", ctypes.c_void_p)]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD),
                ("yHotspot", wintypes.DWORD), ("hbmMask", ctypes.c_void_p),
                ("hbmColor", ctypes.c_void_p)]


def make_icon(size=32):
    px = (ctypes.c_ubyte * (size * size * 4))()
    c = (size - 1) / 2.0
    R = size / 2.0
    arms = [(math.cos(k * math.pi / 3), math.sin(k * math.pi / 3)) for k in range(6)]

    def seg(dx, dy, ox, oy, ax, ay, length, wd):
        px_, py_ = dx - ox, dy - oy
        p = px_ * ax + py_ * ay
        q = abs(-px_ * ay + py_ * ax)
        return 0 <= p <= length and q <= wd

    for y in range(size):
        for x in range(size):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            if r > R - 0.5:
                continue
            t = y / float(size)
            b, g, rr = int(0xF5 + (0xB0 - 0xF5) * t), int(0x7C + (0x4C - 0x7C) * t), int(0x38 + (0xA8 - 0x38) * t)
            white = False
            for ax, ay in arms:
                if seg(dx, dy, 0, 0, ax, ay, R * 0.82, 1.1):
                    white = True
                    break
                for pos in (0.42, 0.66):
                    bx, by = ax * R * pos, ay * R * pos
                    for sgn in (-1, 1):
                        ca, sa = math.cos(sgn * math.pi / 3), math.sin(sgn * math.pi / 3)
                        bax, bay = ax * ca - ay * sa, ax * sa + ay * ca
                        if seg(dx, dy, bx, by, bax, bay, R * 0.24, 1.0):
                            white = True
                if white:
                    break
            if white:
                b = g = rr = 255
            i = (y * size + x) * 4
            px[i], px[i + 1], px[i + 2], px[i + 3] = b, g, rr, 255
    mask = (ctypes.c_ubyte * (size * size // 8))()
    hbm_color = gdi32.CreateBitmap(size, size, 1, 32, ctypes.addressof(px))
    hbm_mask = gdi32.CreateBitmap(size, size, 1, 1, ctypes.addressof(mask))
    ii = ICONINFO(1, 0, 0, hbm_mask, hbm_color)
    hicon = user32.CreateIconIndirect(ctypes.byref(ii))
    if not hicon:
        raise OSError("icon")
    return hicon


class Tray:
    CLASS = "AuraDeskTrayWnd"
    WM_TRAY = 0x0400 + 20

    def __init__(self, tip, on_cmd, get_state):
        self.on_cmd, self.get_state = on_cmd, get_state
        self._proc_ref = WNDPROC(self._proc)
        hinst = kernel32w.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._proc_ref
        wc.hInstance = hinst
        wc.lpszClassName = self.CLASS
        user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(0, self.CLASS, "AuraDesk", 0, 0, 0, 0, 0,
                                           None, None, hinst, None)
        if not self.hwnd:
            raise OSError("tray window")
        self.hicon = make_icon()
        self.nid = NOTIFYICONDATAW()
        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.nid.hWnd = self.hwnd
        self.nid.uID = 1
        self.nid.uFlags = 1 | 2 | 4
        self.nid.uCallbackMessage = self.WM_TRAY
        self.nid.hIcon = self.hicon
        self.nid.szTip = tip[:120]
        if not shell32.Shell_NotifyIconW(0, ctypes.byref(self.nid)):
            raise OSError("tray icon")

    def _proc(self, hwnd, msg, wp, lp):
        try:
            if msg == self.WM_TRAY and (lp & 0xFFFF) in (0x202, 0x205):
                self.menu()
                return 0
        except Exception:
            log_error("tray proc")
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def menu(self):
        st = self.get_state()
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        m = user32.CreatePopupMenu()
        user32.AppendMenuW(m, 0, 1, "Открыть AuraDesk")
        user32.AppendMenuW(m, 0, 2, "Приостановить эффекты" if st["on"] else "Включить эффекты")
        user32.AppendMenuW(m, 8 if st["auto"] else 0, 3, "Запускать вместе с Windows")
        user32.AppendMenuW(m, 0x800, 0, None)
        user32.AppendMenuW(m, 0, 9, "Выход")
        user32.SetForegroundWindow(self.hwnd)
        cmd = user32.TrackPopupMenu(m, 0x1A2, pt.x, pt.y, 0, self.hwnd, None)
        user32.PostMessageW(self.hwnd, 0, 0, 0)
        user32.DestroyMenu(m)
        if cmd:
            self.on_cmd(cmd)

    def remove(self):
        try:
            shell32.Shell_NotifyIconW(2, ctypes.byref(self.nid))
        except Exception:
            pass


SHOW_EVENT = "AuraDesk_show_settings"


def start_show_listener(flag):
    h = kernel32w.CreateEventW(None, False, False, SHOW_EVENT)

    def loop():
        while True:
            if kernel32w.WaitForSingleObject(h, 1000) == 0:
                flag.set()
    threading.Thread(target=loop, daemon=True).start()


# ---------------------------------------------------------------- Настройки
APPDATA = os.environ.get("APPDATA") or os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_DIR = os.path.join(APPDATA, "AuraDesk")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
LOG_PATH = os.path.join(CONFIG_DIR, "error.log")

KINDS = [("snow", "Снежинки"), ("leaf", "Осенние листья"),
         ("spring", "Весенние листья и лепестки"), ("firefly", "Светлячки"),
         ("confetti", "Конфетти"), ("bubble", "Мыльные пузыри"),
         ("heart", "Сердечки"), ("star", "Падающие звёзды"),
         ("rain", "Дождь"), ("lantern", "Небесные фонарики")]
KIND_FACTOR = {"firefly": 0.55, "lantern": 0.2, "bubble": 0.4, "star": 0.35,
               "heart": 0.65, "confetti": 0.95, "rain": 1.35}
SEASON_KINDS = {"winter": ["snow"], "autumn": ["leaf"],
                "spring": ["spring"], "summer": ["firefly"]}

DEFAULTS = {
    # что падает
    "season": "Авто", "fall_mode": "По сезону",
    "k_snow": True, "k_leaf": False, "k_spring": False, "k_firefly": False,
    "k_confetti": False, "k_bubble": False, "k_heart": False, "k_star": False,
    "k_rain": False, "k_lantern": False,
    "snow_style": "Все вместе", "snow_color": "#FFFFFF",
    "density": 220, "speed": 1.1, "size": 5, "wobble": 1.1,
    "desktop_only": True,
    # погода и ветер
    "wind_dir": "Вправо", "wind_power": 0.5, "gust_power": 0.6, "gust_speed": 1.0,
    "blizzard_every": 0, "blizzard_len": 25, "blizzard_power": 1.6,
    "weather_city": "Днепр",
    # курсор, снеговики, сугробы
    "cursor_mode": "Физика ветра", "cursor_radius": 95, "cursor_force": 1.1,
    "cursor_blow": True, "roll_enabled": True, "roll_key": "Ctrl",
    "snowman_size": 1.0, "snowman_max": 6, "snowman_melt": 10,
    "trail_enabled": False, "trail_kind": "Искры", "trail_amount": 1.0,
    "trail_size": 1.0, "trail_life": 1.0,
    "pile_enabled": True, "pile_max": 18, "pile_rate": 1.1,
    "plow_every": 0, "plow_speed": 4,
    # гирлянда (только сверху экрана, без свечения за стеклом)
    "garland_enabled": True, "garland_winter_only": False, "skip_maximized": True,
    "garland_top": True,
    "garland_style": "Авто (по сезону)", "garland_glow": 2,
    "garland_arc": 220, "garland_sag": 28, "garland_gap": 42, "bulb_size": 5,
    "garland_width": 2, "garland_wire": "#2E7D32",
    "color1": "#FF3B30", "color2": "#FFD60A", "color3": "#34C759", "color4": "#0A84FF",
    "blink_mode": "Бегущая волна", "blink_speed": 2.0,
    # небо
    "aurora_enabled": False, "aurora_when": "Всегда", "aurora_palette": "Зелёное",
    "aurora_height": 34, "aurora_speed": 1.0, "aurora_power": 2,
    "stars_enabled": False, "stars_count": 130, "stars_height": 55, "stars_twinkle": 1.2,
    "sky_body": "Выкл", "sky_phase": "Авто", "sky_corner": "Правый верх", "sky_size": 80,
    "meteor_enabled": False, "meteor_every": 7, "meteor_len": 1.3,
    "clouds_enabled": False, "clouds_count": 8, "clouds_speed": 1.0,
    "clouds_tint": "Белые", "clouds_height": 34,
    "birds_mode": "Выкл", "birds_count": 10, "birds_size": 100, "birds_speed": 1.1,
    # праздник
    "widget_monitor": "Основной",
    "santa_enabled": False, "santa_every": 3, "santa_size": 105, "santa_speed": 7,
    "santa_height": 18, "santa_gifts": True,
    "tree_enabled": False, "tree_side": "Справа", "tree_size": 100,
    "tree_margin": 40, "tree_lift": 0,
    "fw_enabled": False, "fw_every": 6, "fw_size": 1.1,
    "count_enabled": False, "count_target": "Новый год", "count_month": 12,
    "count_day": 31, "count_corner": "Левый верх", "count_size": 100,
    "count_color": "#FFFFFF", "count_seconds": True,
    # приложение
    "ui_theme": "Ночной океан", "ui_accent": "По теме", "ui_font": "Обычный",
    "close_to_tray": True, "start_hidden": False, "pause_fullscreen": True,
    "perf_mode": "Красота", "fps": 60,
}
APP_KEYS = {"ui_theme", "ui_accent", "ui_font", "close_to_tray", "start_hidden",
            "pause_fullscreen", "perf_mode", "fps", "widget_monitor", "weather_city"}

EFFECT_NAMES = ("stars", "aurora", "clouds", "sky", "birds", "tree", "count", "santa")
EFFECT_PREFIX = (("aurora_", "aurora"), ("stars_", "stars"), ("sky_", "sky"),
                 ("clouds_", "clouds"), ("tree_", "tree"), ("santa_", "santa"),
                 ("birds_", "birds"), ("count_", "count"))
SCENE_KEYS = {"garland_enabled", "garland_winter_only", "skip_maximized",
              "garland_style", "garland_glow", "garland_arc", "garland_sag",
              "garland_gap", "bulb_size", "garland_width", "garland_wire",
              "color1", "color2", "color3", "color4", "pile_enabled", "garland_top"}
PARTICLE_KEYS = {"season", "density", "size", "snow_color", "fall_mode", "snow_style"}
DESK_TAGS = ("e_stars", "e_aurora", "e_clouds", "e_sky", "e_birds", "e_tree", "e_count",
             "e_santa", "flake", "fx")
WIN_TAGS = ("pile", "snowman", "gift", "garland", "plow", "ball", "carry")

PRESETS = [
    ("newyear", "❄", "Новый год",
     "Зима, гирлянда-лампочки сверху, ёлка, Дед Мороз, звёзды и отсчёт до праздника.",
     {"season": "Зима", "garland_style": "Лампочки", "tree_enabled": True,
      "santa_enabled": True, "count_enabled": True, "stars_enabled": True,
      "aurora_enabled": True, "density": 240, "wind_power": 0.5}),
    ("blizzard", "☃", "Снегопад Макс",
     "Густой плотный снегопад, большие сугробы на окнах, порывистый ветер и звёзды.",
     {"season": "Зима", "density": 420, "size": 6, "speed": 1.3,
      "pile_enabled": True, "pile_max": 26, "pile_rate": 1.6,
      "wind_power": 1.1, "gust_power": 1.2, "stars_enabled": True}),
    ("starry", "✦", "Звёздная сказка",
     "Яркое звёздное небо с падающими звёздами, луна, северное сияние и метеоры.",
     {"fall_mode": "Свой набор", "k_snow": True, "k_star": True, "density": 140,
      "stars_enabled": True, "stars_count": 200, "sky_body": "Луна",
      "aurora_enabled": True, "meteor_enabled": True, "meteor_every": 5,
      "garland_enabled": False}),
    ("arctic", "◈", "Арктика",
     "Холодное бирюзовое сияние, луна, сосульки сверху экрана и тихий снег.",
     {"season": "Зима", "garland_style": "Сосульки", "aurora_enabled": True,
      "aurora_palette": "Зелёное", "sky_body": "Луна", "stars_enabled": True,
      "density": 180, "wind_power": 0.8}),
    ("autumn", "❦", "Уютная осень",
     "Падают листья, плывут облака, летят птицы, ветер меняет направление.",
     {"season": "Осень", "garland_style": "Листья", "clouds_enabled": True,
      "clouds_count": 9, "birds_mode": "Птицы", "wind_power": 1.2, "wind_dir": "Меняется"}),
    ("spring", "✿", "Весна",
     "Лепестки и зелёные листья, цветочная гирлянда, птицы и лёгкие облака.",
     {"season": "Весна", "garland_style": "Цветы", "clouds_enabled": True,
      "birds_mode": "Птицы", "wind_power": 0.6}),
    ("summer", "☀", "Лето и солнце",
     "Светлячки, яркое солнце, бабочки, белые облака и флажки сверху.",
     {"season": "Лето", "garland_style": "Флажки", "sky_body": "Солнце",
      "birds_mode": "Бабочки", "clouds_enabled": True, "pile_enabled": False}),
    ("sunset", "◐", "Закат у моря",
     "Розовые закатные облака, парящие фонарики, мягкий ветер и падающие звёзды.",
     {"fall_mode": "Свой набор", "k_snow": False, "k_lantern": True, "k_star": True,
      "clouds_enabled": True, "clouds_tint": "Закат (розовые)", "clouds_count": 10,
      "stars_enabled": True, "meteor_enabled": True, "garland_enabled": False, "pile_enabled": False}),
    ("party", "✺", "Вечеринка",
     "Конфетти, сердечки, пузыри, след за курсором и праздничные фейерверки.",
     {"fall_mode": "Свой набор", "k_snow": False, "k_confetti": True, "k_heart": True,
      "k_bubble": True, "density": 220, "trail_enabled": True, "trail_kind": "Искры",
      "fw_enabled": True, "garland_style": "Шарики", "pile_enabled": False}),
    ("rain", "☂", "Пасмурный дождь",
     "Плотные серые облака, сильный дождь с брызгами на окнах и порывистый ветер.",
     {"fall_mode": "Свой набор", "k_snow": False, "k_rain": True, "density": 340,
      "clouds_enabled": True, "clouds_tint": "Серые (пасмурно)", "clouds_count": 11,
      "gust_power": 1.2, "garland_enabled": False, "pile_enabled": False}),
    ("quiet", "☕", "Тишина",
     "Немного спокойного снега без гирлянды и сугробов — чтобы не отвлекало.",
     {"density": 60, "speed": 0.7, "garland_enabled": False, "pile_enabled": False,
      "gust_power": 0.2}),
    ("eco", "⚡", "Минимум нагрузки",
     "Облегчённый режим для слабых ноутбуков и работы от батареи.",
     {"density": 40, "garland_enabled": False, "pile_enabled": False,
      "perf_mode": "Экономия", "fps": 25, "gust_power": 0.0}),
]

KEY = "#010203"
BIN = 4
FX_LIMIT = 450
SURFACE_BUCKET = 128

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
AURORA_PAL = {"Зелёное": ["#FF7CC8", "#A65ACD", "#37E79A", "#2EE6C2",
                          "#7CFFB2", "#39FF8A", "#A65ACD", "#FF7CC8"],
              "Фиолетовое": ["#B07CFF", "#7C8CFF", "#E27CFF"],
              "Розовое": ["#FF7CC8", "#FF9E7C", "#C77CFF"],
              "Бирюзовое": ["#00F5D4", "#00BBF9", "#72EFDD", "#48BFE3"]}
LEAF = [(0, -1), (0.55, -0.4), (0.5, 0.3), (0, 1), (-0.5, 0.3), (-0.55, -0.4)]
PETAL = [(0, -1), (0.65, -0.25), (0.45, 0.6), (0, 1), (-0.45, 0.6), (-0.65, -0.25)]
RECT = [(-1, -0.55), (1, -0.55), (1, 0.55), (-1, 0.55)]
GARLAND_STYLES = {"Лампочки": "bulb", "Сосульки": "icicle", "Шарики": "ball",
                  "Звёзды": "star", "Фонарики": "lantern", "Флажки": "flag",
                  "Листья": "leaf", "Цветы": "flower", "Микс": "mix"}
AUTO_STYLE = {"winter": "bulb", "autumn": "leaf", "spring": "flower", "summer": "flag"}

APP_TITLE = "AuraDesk"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "AuraDesk"


def load_cfg():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in DEFAULTS:
                if k in data and type(data[k]) == type(DEFAULTS[k]):
                    cfg[k] = data[k]
                elif k in data and isinstance(DEFAULTS[k], float) and \
                        isinstance(data[k], int) and not isinstance(data[k], bool):
                    cfg[k] = float(data[k])
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(dict(cfg), f, ensure_ascii=False, indent=2)
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


def log_exception(name, exc_info):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + name + "\n")
            f.writelines(traceback.format_exception(*exc_info))
            f.write("\n")
    except Exception:
        pass


def report_tk_exception(exc, value, tb):
    log_exception("Tk callback", (exc, value, tb))


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


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
    t = max(0.0, min(1.0, t))
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


# ---------------------------------------------------------------- Погода (Open-Meteo API)
WMO_INFO = {
    0: ("Ясно", "sun", "#FFB300"),
    1: ("Преим. ясно", "sun_cloud", "#FFD54F"),
    2: ("Переменная облачность", "sun_cloud", "#90CAF9"),
    3: ("Пасмурно", "cloud", "#90A4AE"),
    45: ("Туман", "cloud", "#B0BEC5"),
    48: ("Изморозь", "cloud", "#CFD8DC"),
    51: ("Лёгкая морось", "rain", "#64B5F6"),
    53: ("Морось", "rain", "#42A5F5"),
    55: ("Сильная морось", "rain", "#2196F3"),
    56: ("Ледяная морось", "snow_rain", "#80DEEA"),
    57: ("Сильная ледяная морось", "snow_rain", "#4DD0E1"),
    61: ("Небольшой дождь", "rain", "#42A5F5"),
    63: ("Дождь", "rain", "#1E88E5"),
    65: ("Сильный ливень", "rain", "#1565C0"),
    66: ("Ледяной дождь", "snow_rain", "#4DD0E1"),
    67: ("Сильный ледяной дождь", "snow_rain", "#00ACC1"),
    71: ("Небольшой снег", "snow", "#E1F5FE"),
    73: ("Снегопад", "snow", "#B3E5FC"),
    75: ("Сильный снегопад", "snow", "#81D4FA"),
    77: ("Снежные зёрна", "snow", "#E0F7FA"),
    80: ("Ливневый дождь", "rain", "#29B6F6"),
    81: ("Сильный ливень", "rain", "#0288D1"),
    82: ("Шквальный ливень", "storm", "#5C6BC0"),
    85: ("Снежный заряд", "snow", "#B3E5FC"),
    86: ("Сильная метель", "snow", "#81D4FA"),
    95: ("Гроза", "storm", "#7E57C2"),
    96: ("Гроза с градом", "storm", "#5E35B1"),
    99: ("Сильная гроза с градом", "storm", "#4527A0"),
}

WEEKDAYS_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def wmo_decode(code):
    return WMO_INFO.get(int(code), ("Облачно", "cloud", "#90A4AE"))


def fetch_city_forecast(city_name):
    """Загружает координаты города и прогноз на 7 дней (без внешних библиотек)."""
    q = urllib.parse.quote(city_name.strip())
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language=ru&format=json"
    req = urllib.request.Request(geo_url, headers={"User-Agent": "AuraDesk/1.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        geo = json.loads(resp.read().decode("utf-8"))
    results = geo.get("results")
    if not results:
        raise ValueError(f"Город «{city_name}» не найден")
    place = results[0]
    lat, lon = place["latitude"], place["longitude"]
    resolved_name = place.get("name", city_name)
    country = place.get("country", "")
    admin = place.get("admin1", "")

    fc_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max"
        "&timezone=auto&forecast_days=7"
    )
    req2 = urllib.request.Request(fc_url, headers={"User-Agent": "AuraDesk/1.0"})
    with urllib.request.urlopen(req2, timeout=8) as resp2:
        fc = json.loads(resp2.read().decode("utf-8"))

    cur = fc.get("current", {})
    daily = fc.get("daily", {})
    days = []
    dates = daily.get("time", [])
    codes = daily.get("weather_code", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    pop = daily.get("precipitation_probability_max", [])
    wmax = daily.get("wind_speed_10m_max", [])

    for i in range(len(dates)):
        dt = datetime.date.fromisoformat(dates[i])
        wd = "Сегодня" if i == 0 else ("Завтра" if i == 1 else WEEKDAYS_RU[dt.weekday()])
        label, kind, color = wmo_decode(codes[i] if i < len(codes) else 3)
        days.append({
            "date": dt.strftime("%d.%m"),
            "weekday": wd,
            "code": codes[i] if i < len(codes) else 3,
            "label": label,
            "kind": kind,
            "color": color,
            "tmax": round(tmax[i]) if i < len(tmax) else 0,
            "tmin": round(tmin[i]) if i < len(tmin) else 0,
            "pop": int(pop[i] or 0) if i < len(pop) else 0,
            "wind": round(wmax[i]) if i < len(wmax) else 0,
        })

    c_label, c_kind, c_color = wmo_decode(cur.get("weather_code", 3))
    return {
        "city": resolved_name,
        "region": ", ".join(x for x in (admin, country) if x and x != resolved_name),
        "temp": round(cur.get("temperature_2m", 0)),
        "feels": round(cur.get("apparent_temperature", 0)),
        "humidity": int(cur.get("relative_humidity_2m", 0)),
        "wind": round(cur.get("wind_speed_10m", 0)),
        "code": cur.get("weather_code", 3),
        "label": c_label,
        "kind": c_kind,
        "color": c_color,
        "days": days,
    }


# ---------------------------------------------------------------- Автозапуск
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


# ---------------------------------------------------------------- Движок мира
class Engine:
    strict = False

    def __init__(self, canvas, cfg, geom):
        self.cv = canvas
        self.cfg = cfg
        self.vx, self.vy, self.W, self.H = geom
        self.get_windows = get_windows
        self.get_cursor = cursor_pos
        self.get_mons = get_monitors
        self.get_key = key_down
        self.get_fg = foreground_hwnd

        self.frame = 0
        self.visible = True
        self.now = time.time()
        self.parts, self.chunks, self.fx = [], [], []
        self.piles, self.snowmen, self.gifts = {}, [], []
        self.pile_items, self.dirty_pile_keys = {}, set()
        self.pile_full_dirty = False
        self.plow, self.last_plow = None, None
        self.hold, self.cur = None, None
        self.lights, self.render, self.geo = {}, {}, {}
        self.geo_t = 0.0
        self.surfaces, self.surf_info = [], {}
        self.surface_index = {}
        self.win_rects, self.win_keys, self.wins = [], set(), []
        self.window_cache, self.last_window_scan = [], 0.0
        self.mons, self.mons_sig, self.last_work = [], None, -99.0
        self.work, self.tb_rects = [], []
        self.mask_items, self.mask_rects = [], []
        self.desk_hidden = False
        self.next_poll, self.fast_until = 0.0, 0.0
        self.season = current_season(cfg)
        self.ver = 0
        self.dirty_particles = True
        self.dirty_scene = True
        self.dirty_snowmen = True
        self.pile_dirty = False
        self.layers_dirty = True
        self.fx_dirty, self.effect_on = set(), {}
        self.bliz, self.bliz_f, self.bliz_dir, self.next_bliz = None, 0.0, 1, None
        self.next_meteor, self.next_fw = 0.0, 0.0
        self.meteors, self.rockets = [], []
        self.santa, self.next_santa, self.santa_last_t = None, None, 0.0
        self.perf_scale = 0.65 if cfg["perf_mode"] == "Экономия" else (0.95 if cfg["perf_mode"] == "Авто" else 1.0)
        self.perf_cool = 0.0
        self.ms = 0.0
        self.last_frame_perf, self.frame_scale = 0.0, 1.0
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
        if key == "widget_monitor":
            self.fx_dirty.update(("tree", "sky", "count"))
            return
        if key == "desktop_only":
            self.layers_dirty = True
            self.dirty_scene = True
            return
        for pre, name in EFFECT_PREFIX:
            if key.startswith(pre):
                self.fx_dirty.add(name)
                return
        if key in SCENE_KEYS:
            self.dirty_scene = True
            if key == "pile_enabled" and not cfg["pile_enabled"]:
                self.piles = {}
                self.mark_pile_dirty(full=True)
        elif key == "snowman_size":
            self.dirty_snowmen = True
        elif key == "perf_mode":
            self.perf_scale = 0.65 if cfg["perf_mode"] == "Экономия" else (0.95 if cfg["perf_mode"] == "Авто" else 1.0)
            self.dirty_particles = True

    def reset_world(self):
        self.season = current_season(self.cfg)
        self.piles, self.snowmen, self.gifts = {}, [], []
        self.plow, self.hold = None, None
        self.cv.delete("ball")
        self.cv.delete("carry")
        self.dirty_particles = self.dirty_scene = self.dirty_snowmen = True
        self.mark_pile_dirty(full=True)
        self.ver += 1
        self.fx_dirty.update(EFFECT_NAMES)

    def clear_snow(self):
        self.piles = {}
        self.mark_pile_dirty(full=True)

    def mark_pile_dirty(self, key=None, full=False):
        self.pile_dirty = True
        if full or key is None:
            self.pile_full_dirty = True
            self.dirty_pile_keys.clear()
        elif not self.pile_full_dirty:
            self.dirty_pile_keys.add(key)

    def clear_snowmen(self):
        self.snowmen, self.gifts = [], []
        self.dirty_snowmen = True

    def raise_all(self):
        if self.cfg["desktop_only"]:
            order = DESK_TAGS + ("mask",) + WIN_TAGS
        else:
            order = WIN_TAGS + DESK_TAGS
        for tag in order:
            self.cv.tag_raise(tag)

    def scene_tick(self, now):
        if not self.visible or now < self.next_poll:
            return
        self.now = now
        self.guard("scene", self.refresh_scene, now)
        self.next_poll = now + (0.032 if now < self.fast_until else 0.12)

    def window_location_changed(self, _hwnd):
        now = time.time()
        self.fast_until = max(self.fast_until, now + 0.4)
        self.next_poll = 0.0
        return True

    def tick(self, now):
        if not self.visible:
            return
        t0 = time.perf_counter()
        dt = t0 - self.last_frame_perf if self.last_frame_perf else 1.0 / 60.0
        self.last_frame_perf = t0
        self.frame_scale = max(0.25, min(2.5, dt * 30.0))
        cfg = self.cfg
        self.frame += 1
        self.now = now
        g = self.guard
        if self.last_plow is None:
            self.last_plow = now
        if self.frame % 60 == 0:
            s = current_season(cfg)
            if s != self.season:
                if cfg["fall_mode"] == "По сезону":
                    self.reset_world()
                else:
                    self.season = s
                    self.ver += 1
            if cfg["snowman_melt"] > 0 and self.snowmen:
                self.dirty_snowmen = True
        if self.layers_dirty:
            self.layers_dirty = False
            g("layers", self.apply_layers)
        if self.dirty_particles:
            g("rebuild", self.rebuild_particles)
        g("cursor", self.update_cursor)
        g("hold", self.update_hold)
        g("plow", self.update_plow, now)
        if self.desk_hidden:
            if self.pile_dirty and self.frame % 3 == 0:
                g("piles", self.redraw_piles)
                self.raise_all()
        else:
            g("blizzard", self.update_blizzard, now)
            g("particles", self.update_particles, now)
            g("chunks", self.update_chunks)
            g("interact", self.interact, now)
            g("trail", self.update_trail, now)
            g("schedule", self.update_schedule, now)
            g("fx", self.update_fx)
            if self.pile_dirty and self.frame % 3 == 0:
                g("piles", self.redraw_piles)
                self.raise_all()
            if self.frame % 3 == 0:
                g("blink", self.blink, now)
            g("effects", self.update_effects, now)
        self.ms = self.ms * 0.9 + (time.perf_counter() - t0) * 1000.0 * 0.1
        if self.frame % 45 == 0:
            self.adapt_perf(now)

    def refresh_scene(self, now):
        cfg = self.cfg
        vx, vy = self.vx, self.vy
        wins = self.get_windows()
        self.window_cache = list(wins)
        self.last_window_scan = now
        if now - self.last_work > 2.0 or not self.mons:
            self.last_work = now
            mons = self.get_mons() or [{"mon": (vx, vy, vx + self.W, vy + self.H),
                                        "work": (vx, vy, vx + self.W, vy + self.H)}]
            sig = tuple((m["mon"], m["work"]) for m in mons)
            if sig != self.mons_sig:
                self.mons_sig = sig
                self.mons = mons
                self.work = [m["work"] for m in mons]
                self.tb_rects = []
                for m in mons:
                    ml, mt, mr, mb = m["mon"]
                    wl, wt, wr, wb = m["work"]
                    if wb < mb:
                        self.tb_rects.append((ml - vx, wb - vy, mr - vx, mb - vy))
                    if wt > mt:
                        self.tb_rects.append((ml - vx, mt - vy, mr - vx, wt - vy))
                    if wl > ml:
                        self.tb_rects.append((ml - vx, mt - vy, wl - vx, mb - vy))
                    if wr < mr:
                        self.tb_rects.append((wr - vx, mt - vy, mr - vx, mb - vy))
                self.fx_dirty.update(("tree", "sky", "count"))
                self.dirty_scene = True

        new_geo = {w[0]: (w[1] - vx, w[2] - vy, w[3] - w[1]) for w in wins}
        for key in list(self.geo):
            if key not in new_geo:
                self.collapse(key)
        dt = max(0.004, now - self.geo_t) if self.geo_t else 0.033
        self.geo_t = now
        moved = False
        for key, g in new_geo.items():
            prev = self.geo.get(key)
            if prev:
                dx, dy = g[0] - prev[0], g[1] - prev[1]
                if dx or dy:
                    moved = True
                    if key in self.piles and (abs(dx) + abs(dy)) / dt > 400:
                        self.shed(key, g, dx / dt * 0.033, dy / dt * 0.033, dt / 0.033)
        self.geo = new_geo
        if moved:
            self.fast_until = now + 0.4

        info, deco = {}, {}
        for (hw, a, c, top, left, width) in visible_top_edges(wins, cfg["skip_maximized"]):
            ty = top - vy
            if ty < 4 or ty > self.H - 4:
                continue
            d = info.setdefault(hw, {"left": left - vx, "width": width, "top": ty, "spans": []})
            d["spans"].append((a - vx, c - vx))
        for i, m in enumerate(self.mons):
            wl, wt, wr, wb = m["work"]
            info["g%d" % i] = {"left": wl - vx, "width": wr - wl, "top": wb - vy,
                               "spans": [(wl - vx, wr - vx)]}
            if cfg["garland_top"]:
                ml, mt, mr, mb = m["mon"]
                deco["t%d" % i] = {"left": ml - vx, "width": mr - ml, "top": mt - vy,
                                   "spans": [(ml - vx, mr - vx)]}
        self.win_rects = [(l - vx, t - vy, r - vx, b - vy) for (_h, l, t, r, b, _m) in wins]
        self.win_keys = {w[0] for w in wins}
        self.wins = wins

        hidden = False
        if cfg["desktop_only"] and self.work and self.win_rects:
            hidden = True
            for (wl, wt, wr, wb) in self.work:
                L, T, R, B = wl - vx, wt - vy, wr - vx, wb - vy
                if not any(a <= L + 6 and b0 <= T + 6 and c >= R - 6 and d >= B - 6
                           for (a, b0, c, d) in self.win_rects):
                    hidden = False
                    break
        self.desk_hidden = hidden
        self.update_mask()
        if self.dirty_scene:
            self.ver += 1
            self.dirty_scene = False
        self.surf_info = info
        surfaces = [(k, a, c, d["top"], d["left"], d["width"])
                    for k, d in info.items() for (a, c) in d["spans"]]
        if surfaces != self.surfaces:
            self.surfaces = surfaces
            surface_index = {}
            for surface in surfaces:
                first = int(surface[1] // SURFACE_BUCKET)
                last = int(surface[2] // SURFACE_BUCKET)
                for bucket in range(first, last + 1):
                    surface_index.setdefault(bucket, []).append(surface)
            self.surface_index = surface_index
        gkeys = {"g%d" % i for i in range(len(self.mons))}
        for k in list(self.piles):
            if (isinstance(k, str) and k not in gkeys) or \
                    (isinstance(k, int) and k not in self.win_keys):
                del self.piles[k]
                self.mark_pile_dirty(k)
        n0 = len(self.snowmen) + len(self.gifts)

        def alive(s):
            return (isinstance(s["key"], str) and s["key"] in gkeys) or \
                   (isinstance(s["key"], int) and s["key"] in self.win_keys)

        self.snowmen = [s for s in self.snowmen if alive(s)]
        self.gifts = [s for s in self.gifts if alive(s)]
        if len(self.snowmen) + len(self.gifts) != n0:
            self.dirty_snowmen = True
        self.update_render(deco)
        if self.dirty_snowmen:
            self.redraw_snowmen()
            self.raise_all()

    def update_render(self, deco):
        """Гирлянда рисуется только по верхнему краю мониторов (t0, t1...)."""
        cv = self.cv
        rebuilt = False
        for key, d in deco.items():
            sig = (d["width"],
                   tuple((round(a - d["left"]), round(c - d["left"]))
                         for a, c in d["spans"]), self.ver)
            r = self.render.get(key)
            if r and r["sig"] == sig:
                dx, dy = d["left"] - r["left"], d["top"] - r["top"]
                if dx or dy:
                    cv.move("w%s" % key, dx, dy)
                    r["left"], r["top"] = d["left"], d["top"]
            else:
                cv.delete("w%s" % key)
                self.build_garland_top(key, d)
                self.render[key] = {"sig": sig, "left": d["left"], "top": d["top"]}
                rebuilt = True
        for key in list(self.render):
            if key not in deco:
                cv.delete("w%s" % key)
                del self.render[key]
                self.lights.pop(key, None)
        if rebuilt:
            self.raise_all()

    # ---- осыпание сугробов
    def collapse(self, key):
        g = self.geo.pop(key, None)
        p = self.piles.pop(key, None)
        if g and p:
            left, top, width = g
            h = p["h"]
            stride = max(1, len(h) // 120)
            for i in range(0, len(h), stride):
                if h[i] > 0.6:
                    mat = p["m"][i] or "snow"
                    for _ in range(max(1, int(h[i] / 5))):
                        self.spawn_chunk(left + i * BIN + random.uniform(-3, 3),
                                         top - h[i] * random.random(),
                                         random.uniform(-1.5, 1.5), random.uniform(-1, 1),
                                         mat, random.uniform(1.4, 3.2))
            self.mark_pile_dirty(key)
        if g:
            for sm in self.snowmen:
                if sm["key"] == key:
                    for _ in range(10):
                        self.spawn_chunk(g[0] + sm["off"] + random.uniform(-8, 8),
                                         g[1] - random.uniform(0, 30), random.uniform(-2, 2),
                                         random.uniform(-2, 0), "snow", 3.0)
            for gf in self.gifts:
                if gf["key"] == key:
                    self.spawn_gift(g[0] + gf["off"], g[1] - 6, gf["col"])

    def shed(self, key, g, dx, dy, k=1.0):
        p = self.piles.get(key)
        if not p:
            return
        left, top, _w = g
        frac = min(0.5, (abs(dx) + abs(dy)) / 90.0) * min(1.0, k)
        h, m = p["h"], p["m"]
        n = 0
        for i in range(len(h)):
            if h[i] > 0.8 and random.random() < frac * 0.6:
                if n < 30:
                    self.spawn_chunk(left + i * BIN, top - h[i], -dx * 0.25 + random.uniform(-1.5, 1.5),
                                     -abs(dy) * 0.15 - random.uniform(0.5, 2.5),
                                     m[i] or "snow", random.uniform(1.4, 3.0))
                    n += 1
                h[i] *= 1 - frac
        self.mark_pile_dirty(key)

    def spawn_chunk(self, x, y, vx, vy, mat, r):
        if len(self.chunks) >= 400:
            return
        i = self.cv.create_oval(x - r, y - r, x + r, y + r, fill=MAT_COLOR.get(mat, "#FFFFFF"),
                                outline="", tags="flake")
        self.below_mask(i)
        self.chunks.append({"x": x, "y": y, "py": y, "vx": vx, "vy": vy, "r": r, "mat": mat, "id": i})

    def update_chunks(self):
        if not self.chunks:
            return
        cv, cfg = self.cv, self.cfg
        pen = cfg["pile_enabled"]
        keep = []
        for c in self.chunks:
            c["py"] = c["y"]
            c["vy"] += 0.5
            c["vx"] *= 0.995
            c["x"] += c["vx"]
            c["y"] += c["vy"]
            x, y, py, r = c["x"], c["y"], c["py"], c["r"]
            landed = None
            for (key, a, e, top, left, width) in self.surface_index.get(
                    int(x // SURFACE_BUCKET), ()):
                if a <= x <= e:
                    ys = top - (self.pile_h(key, left, x) if (pen and "gift" not in c) else 0.0)
                    if py < ys <= y:
                        landed = (key, left, width)
                        break
            if landed:
                if "gift" in c:
                    self.add_gift(landed[0], landed[1], x, c["gift"])
                elif pen:
                    self.land(landed[0], landed[1], landed[2], x, c["mat"], 0.3 * r * cfg["pile_rate"])
            if landed or y > self.H + 20 or x < -60 or x > self.W + 60:
                cv.delete(c["id"])
                continue
            cv.coords(c["id"], x - r, y - r, x + r, y + r)
            keep.append(c)
        self.chunks = keep

    # ---- ветер
    def wind_now(self, now):
        cfg = self.cfg
        d = cfg["wind_dir"]
        sgn = 1.0 if d == "Вправо" else (-1.0 if d == "Влево" else math.sin(now * 0.05))
        w = cfg["wind_power"] * sgn
        gp = cfg["gust_power"]
        if gp > 0:
            t = now * cfg["gust_speed"]
            g = math.sin(t * 0.37) * 0.6 + math.sin(t * 0.91 + 1.3) * 0.3 + math.sin(t * 2.3 + 0.4) * 0.1
            w += g * gp * 1.5
        return w + self.bliz_f * cfg["blizzard_power"] * 3.0 * self.bliz_dir

    # ---- метель
    def start_blizzard(self, now=None):
        now = time.time() if now is None else now
        self.bliz = {"t0": now, "len": max(5.0, float(self.cfg["blizzard_len"]))}
        self.bliz_dir = random.choice((-1, 1))
        storm_n = int(min(180, 140 * self.cfg["blizzard_power"]) * self.perf_scale)
        for _ in range(storm_n):
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

    # ---- частицы (больше снега и высокая скорость отрисовки)
    def active_kinds(self):
        cfg = self.cfg
        if cfg["fall_mode"] == "По сезону":
            return SEASON_KINDS[self.season]
        ks = [k for k, _ in KINDS if cfg["k_" + k]]
        return ks or SEASON_KINDS[self.season]

    def rebuild_particles(self):
        self.cv.delete("flake")
        self.chunks = []
        ks = self.active_kinds()
        cap = {"Авто": 380, "Красота": 480, "Экономия": 110}.get(self.cfg["perf_mode"], 380)
        n = int(min(self.cfg["density"], cap) * self.perf_scale)
        self.parts = []
        for k in ks:
            count = int(n / len(ks) * KIND_FACTOR.get(k, 1.0))
            for _ in range(count):
                self.parts.append(self.make_particle(k, True))
        if self.bliz:
            storm_n = int(min(180, 140 * self.cfg["blizzard_power"]) * self.perf_scale)
            for _ in range(storm_n):
                self.parts.append(self.make_particle("snow", True, True))
        self.dirty_particles = False
        self.raise_all()

    def make_particle(self, kind, random_y, storm=False):
        cv, cfg = self.cv, self.cfg
        d = random.uniform(0.32, 1.0)
        r = max(1.6, cfg["size"] * d)
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
             "drag": 0.08, "sway": 0.65, "mob": 1.0, "storm": storm, "shape": None,
             "draw": "dot", "ids": [], "rise": rise, "diag": False, "col": "#FFFFFF",
             "fspin": 0.07}
        if kind == "snow":
            col = blend(cfg["snow_color"], 0.62 + 0.38 * d)
            style = cfg["snow_style"]
            p.update(tv=0.65 + 1.55 * d, col=col)
            # Дальние мелкие снежинки рисуются быстрыми точками, крупные — резными снежинками.
            if style == "Точки" or (style == "Все вместе" and d < 0.62):
                p["ids"] = [cv.create_oval(0, 0, 1, 1, fill=col, outline="", tags="flake")]
            else:
                shapes = ("Звёздочки ❄", "Хлопья ❅", "Кристаллы ❆")
                shape = random.choice(shapes) if style == "Все вместе" else style
                p.update(draw="snowflake", snow_shape=shape)
                p["ids"] = [cv.create_line(x, y, x + 1, y + 1, fill=col,
                                           width=max(1.0, r * 0.28), capstyle="round",
                                           joinstyle="round", tags="flake")]
        elif kind == "leaf":
            col = random.choice(AUTUMN)
            p.update(draw="poly", shape=LEAF, size=r * 1.5 + 3, tv=0.55 + 1.0 * d,
                     sway=1.4, drag=0.05, mat="leaf", amt=1.3, col=col)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline=blend(col, 0.6),
                                          smooth=True, tags="flake")]
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
                                          smooth=True, tags="flake")]
        elif kind == "firefly":
            col = random.choice(FLY_COL)
            p.update(draw="fly", lands=False, col=col, tv=0.0, r=max(1.5, cfg["size"] * 0.5 * d))
            p["ids"] = [cv.create_oval(0, 0, 1, 1, fill=blend(col, 0.25), outline="", tags="flake"),
                        cv.create_oval(0, 0, 1, 1, fill=col, outline="", tags="flake")]
        elif kind == "confetti":
            col = random.choice(CONFETTI_COL)
            p.update(draw="poly", shape=RECT, size=r * 0.9 + 2, tv=0.9 + 1.0 * d, sway=1.0,
                     mat="confetti", amt=0.6, col=col, spin=random.uniform(-0.25, 0.25), fspin=0.22)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline="", tags="flake")]
        elif kind == "bubble":
            rr = max(3.0, cfg["size"] * 1.6 * d + 3)
            p.update(draw="bubble", r=rr, tv=-(0.4 + 0.8 * d), sway=1.6, lands=False, drag=0.05)
            p["ids"] = [cv.create_oval(0, 0, 1, 1, fill="", outline="#BFE9FF", width=1, tags="flake"),
                        cv.create_oval(0, 0, 1, 1, fill="#FFFFFF", outline="", tags="flake")]
        elif kind == "heart":
            col = random.choice(HEART_COL)
            p.update(draw="heart", tv=0.7 + 0.9 * d, sway=1.0, mat="heart", amt=0.7, col=col)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline="", smooth=True, tags="flake")]
        elif kind == "star":
            col = random.choice(STAR_COL)
            p.update(draw="star4", tv=1.3 + 2.0 * d, sway=0.35, drag=0.1, mat=None, col=col, diag=True)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline="#FFFFFF", tags="flake")]
        elif kind == "rain":
            col = blend("#9CC4F0", 0.65 + 0.35 * d)
            p.update(draw="line", tv=10 + 9 * d, drag=0.3, mob=0.4, sway=0.0, mat=None, col=col)
            p["ids"] = [cv.create_line(0, 0, 1, 1, fill=col, width=2 if d > 0.75 else 1, tags="flake")]
        else:  # lantern
            p.update(draw="lantern", size=r * 1.2 + 6, tv=-(0.45 + 0.5 * d), sway=1.2, lands=False, drag=0.04)
            p["ids"] = [cv.create_oval(0, 0, 1, 1, fill="#FF9A3C", outline="", stipple="gray25", tags="flake"),
                        cv.create_oval(0, 0, 1, 1, fill="#FF8F3A", outline="#FFD08A", tags="flake")]
        p["vy"] = p["tv"] * cfg["speed"]
        self.place(p)
        return p

    def place(self, p):
        cv, x, y, r, dr, ids = self.cv, p["x"], p["y"], p["r"], p["draw"], p["ids"]
        if dr == "dot":
            cv.coords(ids[0], x - r, y - r, x + r, y + r)
        elif dr == "star4":
            rot = p["rot"]
            pts = []
            for q in range(8):
                a = rot + q * math.pi / 4.0
                rad = r * 1.65 if q % 2 == 0 else r * 0.42
                pts.extend((x + math.cos(a) * rad, y + math.sin(a) * rad))
            cv.coords(ids[0], *pts)
        elif dr == "heart":
            s = r * 0.95
            cv.coords(ids[0],
                      x, y + s * 1.2,
                      x - s * 1.2, y + s * 0.1,
                      x - s * 0.85, y - s * 0.85,
                      x, y - s * 0.35,
                      x + s * 0.85, y - s * 0.85,
                      x + s * 1.2, y + s * 0.1)
        elif dr == "snowflake":
            coords = [x, y]
            shape = p["snow_shape"]
            rot = p["rot"]
            for arm in range(6):
                a = rot + arm * math.tau / 6.0
                ux, uy = math.cos(a), math.sin(a)
                coords.extend((x + ux * r * 1.45, y + uy * r * 1.45))
                if shape != "Звёздочки ❄":
                    branches = ((0.46, 0.28, 0.72), (0.72, 0.2, 0.82)) if shape == "Хлопья ❅" \
                        else ((0.56, 0.32, 0.55),)
                    for along, size, angle in branches:
                        bx, by = x + ux * r * along, y + uy * r * along
                        coords.extend((bx, by))
                        for side in (-1, 1):
                            ca, sa = math.cos(a + side * angle), math.sin(a + side * angle)
                            coords.extend((bx + ca * r * size, by + sa * r * size, bx, by))
                coords.extend((x, y))
            cv.coords(ids[0], *coords)
        elif dr == "fly":
            cv.coords(ids[0], x - r * 2.4, y - r * 2.4, x + r * 2.4, y + r * 2.4)
            cv.coords(ids[1], x - r * 0.8, y - r * 0.8, x + r * 0.8, y + r * 0.8)
        elif dr == "bubble":
            cv.coords(ids[0], x - r, y - r, x + r, y + r)
            cv.coords(ids[1], x - r * 0.62, y - r * 0.62, x - r * 0.28, y - r * 0.3)
        elif dr == "lantern":
            s = p["size"]
            cv.coords(ids[0], x - s * 1.9, y - s * 1.9, x + s * 1.9, y + s * 1.9)
            cv.coords(ids[1], x - s * 0.8, y - s, x + s * 0.8, y + s)
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
        frame_scale = self.frame_scale
        spd = cfg["speed"] * frame_scale * (1 + self.bliz_f * cfg["blizzard_power"] * 0.8)
        wob = cfg["wobble"]
        wind = self.wind_now(now)
        W, H = self.W, self.H
        pile_en = cfg["pile_enabled"]
        phys = cfg["cursor_mode"].startswith("Физика") and self.cur is not None
        if phys:
            cx, cy, cvx, cvy = self.cur
            rad = float(cfg["cursor_radius"])
            rad2 = rad * rad
            force = cfg["cursor_force"]
        storm_on = self.bliz is not None
        dead = []
        for p in self.parts:
            if p["storm"] and not storm_on and random.random() < 0.04:
                dead.append(p)
                continue
            p["ph"] += 0.05 * frame_scale
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
                if self.frame % 3 == 0:
                    f = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(p["ph"] * 2.3))
                    cv.itemconfigure(p["ids"][1], fill=blend(p["col"], f))
                    cv.itemconfigure(p["ids"][0], fill=blend(p["col"], f * 0.22))
            else:
                p["py"] = p["y"]
                wx = wind * p["mob"] * (0.4 + p["d"]) + math.sin(p["ph"]) * wob * p["sway"]
                if p["diag"]:
                    wx += 1.5
                dg = p["drag"]
                vx = p["vx"] + (wx * spd - p["vx"]) * dg
                vy = p["vy"] + (p["tv"] * spd - p["vy"]) * dg
                if phys:
                    ddx, ddy = p["x"] - cx, p["y"] - cy
                    if -rad < ddx < rad and -rad < ddy < rad:
                        d2 = ddx * ddx + ddy * ddy
                        if 0.01 < d2 < rad2:
                            dist = math.sqrt(d2)
                            f = (1 - dist / rad)
                            f = f * f * force
                            vx += ddx / dist * f * 2.4 + cvx * 0.14 * f
                            vy += ddy / dist * f * 2.4 + cvy * 0.14 * f
                            if p["k"] == "bubble" and dist < rad * 0.35:
                                self.pop_bubble(p)
                                self.respawn(p)
                                self.place(p)
                                continue
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
                    if y < -p["r"] * 5 or (p["k"] == "bubble" and random.random() < 0.0006):
                        if p["k"] == "bubble" and y >= 0:
                            self.pop_bubble(p)
                        respawn = True
                else:
                    hit = None
                    if p["lands"]:
                        for (key, a, e, top, left, width) in self.surface_index.get(
                                int(x // SURFACE_BUCKET), ()):
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
                            self.burst(x, hit[3], 10, p["col"])
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
                if p["k"] == "star" and self.frame % 2 == 0:
                    self.spawn_fx(p["x"], p["y"], -p["vx"] * 0.1, -p["vy"] * 0.1, 10, p["col"], 1.5, drag=0.9)
            self.place(p)
        if dead:
            for p in dead:
                for i in p["ids"]:
                    cv.delete(i)
            ds = set(id(p) for p in dead)
            self.parts = [p for p in self.parts if id(p) not in ds]

    def pop_bubble(self, p):
        for _ in range(6):
            self.spawn_fx(p["x"], p["y"], random.uniform(-1.8, 1.8), random.uniform(-1.8, 1.0),
                          12, "#BFE9FF", 1.6, g=0.05)

    def splash(self, x, y):
        for _ in range(3):
            self.spawn_fx(x, y - 1, random.uniform(-1.4, 1.4), -random.uniform(1.0, 2.6),
                          11, "#9CC4F0", 1.4, g=0.25)

    def burst(self, x, y, n, col):
        for _ in range(n):
            a = random.uniform(0, 6.283)
            s = random.uniform(0.8, 2.8)
            self.spawn_fx(x, y, math.cos(a) * s, math.sin(a) * s - 1, 16, col, 1.6, g=0.08, drag=0.93)

    # ---- сугробы
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
        for off, k in ((0, 1.0), (-1, 0.6), (1, 0.6), (-2, 0.25), (2, 0.25)):
            j = i + off
            if 0 <= j < len(h):
                h[j] = min(cap, h[j] + amt * k)
                m[j] = mat
        self.mark_pile_dirty(key)

    def redraw_piles(self, incremental=False):
        cv = self.cv
        full = not incremental or self.pile_full_dirty
        if full:
            cv.delete("pile")
            self.pile_items.clear()
            keys = set(self.surf_info) | set(self.piles)
        else:
            keys = set(self.dirty_pile_keys)
            for key in keys:
                for item in self.pile_items.pop(key, ()):
                    cv.delete(item)
        self.pile_dirty = False
        self.pile_full_dirty = False
        self.dirty_pile_keys.clear()
        if not self.cfg["pile_enabled"]:
            return
        cap = self.cfg["pile_max"]
        for key in keys:
            p = self.piles.get(key)
            d = self.surf_info.get(key)
            if not p or not d:
                continue
            relax(p["h"], cap)
            h, m, left, top = p["h"], p["m"], d["left"], d["top"]
            tg = ("pile", "w%s" % key)
            items = self.pile_items.setdefault(key, [])
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
                            item = cv.create_polygon(*pts, fill=col, outline=blend(col, 0.85),
                                                     width=1, tags=tg)
                            items.append(item)
                    s = e + 1

    # ---- гирлянда (только сверху экрана)
    def garland_style(self):
        v = self.cfg["garland_style"]
        if v.startswith("Авто"):
            return AUTO_STYLE[self.season]
        return GARLAND_STYLES.get(v, "bulb")

    def glow(self, cx, cy, R, st1, st2, col, tg):
        cv = self.cv
        a, b = [], []
        for q in range(14):
            ang = q * 2 * math.pi / 14
            ca, sa = math.cos(ang), math.sin(ang)
            a += [cx + ca * R * 1.7, cy + sa * R * 1.7]
            b += [cx + ca * R, cy + sa * R]
        g1 = cv.create_polygon(*a, fill=col, outline="", stipple=st1, tags=tg)
        g2 = cv.create_polygon(*b, fill=col, outline="", stipple=st2, tags=tg)
        return g1, g2

    def deco(self, style, k, bx, by, r, cols, tg, wire, st1, st2):
        cv = self.cv
        if style == "bulb":
            col = cols[k % 4]
            g1, g2 = self.glow(bx, by + 5 + r * 1.1, r * 1.5, st1, st2, col, tg)
            cv.create_rectangle(bx - 2, by, bx + 2, by + 5, fill="#37474F", outline="", tags=tg)
            core = cv.create_oval(bx - r * 0.85, by + 4, bx + r * 0.85, by + 4 + r * 2.2,
                                  fill=col, outline=mix(col, "#FFFFFF", 0.5), tags=tg)
            cv.create_oval(bx - r * 0.5, by + 5 + r * 0.3, bx - r * 0.1, by + 5 + r * 0.9,
                           fill="#FFFFFF", outline="", tags=tg)
            return (core, g1, g2, col, k)
        if style == "icicle":
            L = 14 + (k * 7) % 22
            wd = r * 0.8 + 3
            col = "#8FD8FF"
            glow_shape = [bx - wd - 2, by, bx + wd + 2, by, bx, by + 2 + L]
            body_shape = [bx - wd, by + 1, bx + wd, by + 1, bx, by + 2 + L]
            g1 = cv.create_polygon(*glow_shape, fill=col, outline="", stipple=st1, tags=tg)
            g2 = cv.create_polygon(*glow_shape, fill=col, outline="", stipple=st2, tags=tg)
            body = cv.create_polygon(*body_shape, fill="#C9F0FF", outline="#8CC8FF", tags=tg)
            cv.create_line(bx - wd * 0.35, by + 4, bx - wd * 0.1, by + L * 0.7, fill="#FFFFFF", tags=tg)
            return (body, g1, g2, col, k)
        if style == "ball":
            rb = r * 1.1 + 4
            col = cols[k % 4]
            cy = by + 5 + rb
            cv.create_line(bx, by, bx, by + 5, fill=wire, tags=tg)
            cv.create_rectangle(bx - 2.5, by + 3, bx + 2.5, by + 7, fill="#E6C14B", outline="", tags=tg)
            g1, g2 = self.glow(bx, cy, rb * 0.9, st1, st2, col, tg)
            body = cv.create_oval(bx - rb, cy - rb, bx + rb, cy + rb, fill=col,
                                  outline=blend(col, 0.55), tags=tg)
            cv.create_oval(bx - rb * 0.55, cy - rb * 0.6, bx - rb * 0.15, cy - rb * 0.25,
                           fill="#FFFFFF", outline="", tags=tg)
            return (body, g1, g2, col, k)
        if style == "star":
            rs = r * 1.4 + 4
            col = "#FFD54F" if k % 3 == 0 else cols[k % 4]
            cy = by + 4 + rs
            pts = []
            for q in range(10):
                ang = -math.pi / 2 + q * math.pi / 5
                rad = rs if q % 2 == 0 else rs * 0.45
                pts += [bx + math.cos(ang) * rad, cy + math.sin(ang) * rad]
            cv.create_line(bx, by, bx, by + 4, fill=wire, tags=tg)
            g1, g2 = self.glow(bx, cy, rs * 0.9, st1, st2, col, tg)
            st = cv.create_polygon(*pts, fill=col, outline=mix(col, "#FFFFFF", 0.5), tags=tg)
            return (st, g1, g2, col, k)
        if style == "lantern":
            rl = r * 1.1 + 4
            hh = rl * 1.5
            col = cols[k % 4]
            cy = by + 6 + hh
            cv.create_line(bx, by, bx, by + 6, fill=wire, tags=tg)
            g1, g2 = self.glow(bx, cy, rl, st1, st2, col, tg)
            cv.create_rectangle(bx - rl * 0.5, cy - hh - 1, bx + rl * 0.5, cy - hh + 3,
                                fill="#5D4037", outline="", tags=tg)
            body = cv.create_oval(bx - rl, cy - hh, bx + rl, cy + hh, fill=col,
                                  outline=blend(col, 0.55), tags=tg)
            cv.create_rectangle(bx - rl * 0.5, cy + hh - 3, bx + rl * 0.5, cy + hh + 1,
                                fill="#5D4037", outline="", tags=tg)
            return (body, g1, g2, col, k)
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
            cv.create_line(bx, by, bx, by + 4, fill=wire, width=1, tags=tg)
            rot = math.pi + math.sin(k * 1.7) * 0.5
            cv.create_polygon(*shape_pts(LEAF, bx, by + 4 + sz, sz, rot, 0.85), fill=col,
                              outline=blend(col, 0.6), smooth=True, tags=tg)
            return None
        pc = PETAL_COL[(k * 3 + k // 2) % len(PETAL_COL)]
        sz = r * 0.9 + 3
        cy = by + 5 + sz
        cv.create_line(bx, by, bx, by + 5, fill=wire, width=1, tags=tg)
        for q in range(5):
            ang = q * 2 * math.pi / 5
            px, py = bx + math.cos(ang) * sz * 0.8, cy + math.sin(ang) * sz * 0.8
            cv.create_oval(px - sz * 0.55, py - sz * 0.55, px + sz * 0.55, py + sz * 0.55,
                           fill=pc, outline=blend(pc, 0.7), tags=tg)
        cv.create_oval(bx - sz * 0.4, cy - sz * 0.4, bx + sz * 0.4, cy + sz * 0.4,
                       fill="#FBC02D", outline="", tags=tg)
        return None

    def build_garland_top(self, key, d):
        cv, cfg = self.cv, self.cfg
        self.lights[key] = []
        if not cfg["garland_enabled"] or not cfg["garland_top"]:
            return
        if cfg["garland_winter_only"] and self.season != "winter":
            return
        style = self.garland_style()
        tg = ("garland", "w%s" % key)
        cols = [cfg["color1"], cfg["color2"], cfg["color3"], cfg["color4"]]
        sag, wire, ww, r = cfg["garland_sag"], cfg["garland_wire"], cfg["garland_width"], cfg["bulb_size"]
        gap = cfg["garland_gap"] * (0.6 if style == "icicle" else 1.0)
        y = d["top"]
        k = 0
        st1, st2 = {1: ("gray12", "gray25"), 2: ("gray25", "gray50"),
                    3: ("gray50", "gray75")}[int(cfg["garland_glow"])]
        for (a, b) in d["spans"]:
            n_arcs = max(1, round((b - a) / cfg["garland_arc"]))
            w = (b - a) / n_arcs
            for i in range(n_arcs):
                x0 = a + i * w
                pts = []
                for s in range(21):
                    t = s / 20
                    pts += [x0 + t * w, y + 2 + sag * 4 * t * (1 - t)]
                shadow = [v + (2 if j % 2 else 0) for j, v in enumerate(pts)]
                cv.create_line(*shadow, fill=blend(wire, 0.35), width=ww + 2, smooth=True, tags=tg)
                cv.create_line(*pts, fill=wire, width=ww, smooth=True, tags=tg)
                for px in (x0, x0 + w):
                    cv.create_oval(px - 3, y - 1, px + 3, y + 5, fill="#B0BEC5",
                                   outline="#37474F", tags=tg)
                cnt = max(1, int(w / gap))
                for j in range(cnt):
                    t = (j + 0.5) / cnt
                    bx = x0 + t * w
                    by = y + 2 + sag * 4 * t * (1 - t)
                    st = style if style != "mix" else ("bulb", "icicle", "ball", "star")[k % 4]
                    ent = self.deco(st, k, bx, by, r, cols, tg, wire, st1, st2)
                    if ent:
                        self.lights[key].append(ent)
                    k += 1

    def blink(self, t):
        cv = self.cv
        mode, spd = self.cfg["blink_mode"], self.cfg["blink_speed"]
        for lst in self.lights.values():
            for core, g1, g2, col, k in lst:
                if mode == "Бегущая волна":
                    f = 0.55 + 0.45 * math.sin(t * spd * 2 - k * 0.6)
                elif mode == "Мигание":
                    f = 1.0 if (int(t * spd) + k) % 2 == 0 else 0.15
                else:
                    f = 1.0
                cv.itemconfigure(core, fill=mix(col, "#FFFFFF", 0.1 + 0.4 * f) if f > 0.35
                                 else blend(col, 0.45))
                cv.itemconfigure(g2, state="normal" if f > 0.4 else "hidden")
                cv.itemconfigure(g1, state="normal" if f > 0.7 else "hidden")

    # ---- курсор
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

    def surface_candidates(self, left, right):
        candidates, seen = [], set()
        first, last = int(left // SURFACE_BUCKET), int(right // SURFACE_BUCKET)
        for bucket in range(first, last + 1):
            for surface in self.surface_index.get(bucket, ()):
                if surface not in seen:
                    seen.add(surface)
                    candidates.append(surface)
        return candidates

    def interact(self, now):
        cfg = self.cfg
        mode = cfg["cursor_mode"]
        if not self.visible or self.cur is None or mode == "Ничего":
            return
        cx, cy, cvx, cvy = self.cur
        rad, pm = cfg["cursor_radius"], cfg["pile_max"]
        if mode.startswith("Сметать"):
            r2 = rad * 0.5
            for (key, a, c, top, left, width) in self.surface_candidates(cx - r2, cx + r2):
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
                        self.mark_pile_dirty(key)
            keep = []
            for sm in self.snowmen:
                pos = self.snowman_pos(sm)
                if pos and abs(pos[0] - cx) <= r2 and \
                        pos[1] - 80 * cfg["snowman_size"] <= cy <= pos[1] + r2:
                    self.dirty_snowmen = True
                    continue
                keep.append(sm)
            self.snowmen = keep
        elif cfg["cursor_blow"] and math.hypot(cvx, cvy) > 9:
            spawned = 0
            for (key, a, c, top, left, width) in self.surface_candidates(cx - rad, cx + rad):
                if cx < a - rad or cx > c + rad or cy < top - pm - rad or cy > top + rad:
                    continue
                p = self.piles.get(key)
                if not p:
                    continue
                h, m = p["h"], p["m"]
                for i in range(max(0, int((cx - rad * 0.7 - left) // BIN)),
                               min(len(h) - 1, int((cx + rad * 0.7 - left) // BIN)) + 1):
                    bx = left + i * BIN
                    if h[i] > 0.5 and a <= bx <= c and spawned < 8:
                        self.spawn_chunk(bx, top - h[i], cvx * 0.35 + random.uniform(-1.5, 1.5),
                                         -random.uniform(1.0, 3.5) + cvy * 0.15, m[i] or "snow",
                                         random.uniform(1.3, 2.6))
                        h[i] *= 0.55
                        spawned += 1
                        self.mark_pile_dirty(key)

    # ---- снеговики и подарки
    def snowman_radii(self, s=None):
        s = self.cfg["snowman_size"] if s is None else s
        return (13 * s, 9.5 * s, 6.5 * s)

    def snowman_pos(self, sm):
        info = self.surf_info.get(sm["key"])
        if not info:
            return None
        x = info["left"] + sm["off"]
        for a, c in info["spans"]:
            if a <= x <= c:
                return x, info["top"]
        return None

    def redraw_snowmen(self):
        cv = self.cv
        cv.delete("snowman")
        cv.delete("gift")
        self.dirty_snowmen = False
        melt = self.cfg["snowman_melt"] * 60.0
        keep = []
        for sm in self.snowmen:
            m = 0.0
            pos = self.snowman_pos(sm)
            if melt > 0:
                m = (self.now - sm["t0"]) / melt
                if m >= 1.0:
                    if pos:
                        for _ in range(6):
                            self.spawn_fx(pos[0] + random.uniform(-10, 10), pos[1] - 2,
                                          random.uniform(-0.8, 0.8), -random.uniform(0.5, 1.5),
                                          14, "#BFE9FF", 1.5, g=0.15)
                    continue
            keep.append(sm)
            if pos:
                sc = 1.0 - 0.65 * max(0.0, (m - 0.4) / 0.6)
                self.draw_snowman(pos[0], pos[1] + 1, sm["stage"], "w%s" % sm["key"], sc)
        self.snowmen = keep
        for gf in self.gifts:
            info = self.surf_info.get(gf["key"])
            if not info:
                continue
            x = info["left"] + gf["off"]
            if any(a <= x <= c for a, c in info["spans"]):
                self.draw_gift(x, info["top"] + 1, gf["col"], "w%s" % gf["key"])

    def draw_snowman(self, x, y, stage, wt, scale=1.0):
        cv = self.cv
        s = self.cfg["snowman_size"] * scale
        t = ("carry",) if wt == "carry" else ("snowman", wt)
        r1, r2, r3 = self.snowman_radii(s)
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
        e = max(1.0, s * 0.9)
        if stage >= 2:
            for k in (-0.4, 0.15, 0.7):
                by = y2 + r2 * k
                cv.create_oval(x - e, by - e, x + e, by + e, fill="#212121", outline="", tags=t)
        if stage >= 3:
            cv.create_rectangle(x - r3 * 0.85, y3 + r3 * 0.55, x + r3 * 0.85, y3 + r3 * 0.95,
                                fill="#E53935", outline="", tags=t)
            cv.create_rectangle(x - r3 * 0.95, y3 - r3 * 0.85, x + r3 * 0.95, y3 - r3 * 0.62,
                                fill="#212121", outline="", tags=t)
            cv.create_rectangle(x - r3 * 0.6, y3 - r3 * 1.7, x + r3 * 0.6, y3 - r3 * 0.8,
                                fill="#212121", outline="", tags=t)
            for dx in (-r3 * 0.35, r3 * 0.35):
                cv.create_oval(x + dx - e, y3 - r3 * 0.15 - e, x + dx + e, y3 - r3 * 0.15 + e,
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
        width = self.surf_info[best]["width"]
        self.plow = {"key": best, "dir": d, "off": -30 if d > 0 else width + 30}

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
        info = self.surf_info.get(pl["key"])
        if not info:
            self.plow, self.last_plow = None, now
            return
        pl["off"] += pl["dir"] * cfg["plow_speed"] * 1.2 * self.frame_scale
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
        cv.create_polygon(*P(-24, -19, -20, -28, -8, -28, -5, -19), fill="#B3E5FC", outline="", tags=t)
        cv.create_line(*P(20, -12, 28, -12), fill="#5D4037", width=3, tags=t)
        cv.create_polygon(*P(26, -26, 42, -6, 42, 1, 26, 1), fill="#EF6C00", outline="#7A3300", tags=t)
        for wx, wr in ((-20, 6), (8, 6)):
            cx = x + wx * d
            cv.create_oval(cx - wr, y - 5 - wr, cx + wr, y - 5 + wr, fill="#263238", outline="", tags=t)
            cv.create_oval(cx - 2, y - 7, cx + 2, y - 3, fill="#B0BEC5", outline="", tags=t)
        bc = "#FF9800" if int(now * 6) % 2 == 0 else "#7A2E00"
        bx = x - 12 * d
        cv.create_oval(bx - 3, y - 37, bx + 3, y - 31, fill=bc, outline="", tags=t)

    # ---- эффекты-частицы
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
        self.below_mask(i)
        life = max(2, int(life))
        self.fx.append({"x": x, "y": y, "vx": vx, "vy": vy, "life": life, "max": life, "col": col,
                        "size": size, "g": g, "drag": drag, "glyph": glyph, "id": i})

    def update_fx(self):
        if not self.fx:
            return
        cv = self.cv
        keep = []
        odd = self.frame % 2 == 0
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
                s = f["size"] * (0.25 + 0.75 * k)
                cv.coords(f["id"], x - s, y - s, x + s, y + s)
            if odd and f["col"]:
                cv.itemconfigure(f["id"], fill=blend(f["col"], 0.3 + 0.7 * k))
            keep.append(f)
        self.fx = keep

    def update_trail(self, now):
        cfg = self.cfg
        if not cfg["trail_enabled"] or self.cur is None or not self.visible:
            return
        cx, cy, vx, vy = self.cur
        sp = math.hypot(vx, vy)
        if sp < 1.2:
            return
        n = cfg["trail_amount"] * min(4.0, 0.4 + sp / 7)
        count = int(n) + (1 if random.random() < n - int(n) else 0)
        kind, sz, life = cfg["trail_kind"], cfg["trail_size"], 24 * cfg["trail_life"]
        for _ in range(count):
            px, py = cx + random.uniform(-3, 3), cy + random.uniform(-3, 3)
            if kind == "Искры":
                self.spawn_fx(px, py, random.uniform(-1.5, 1.5) - vx * 0.05, random.uniform(-2, 0.5),
                              life, random.choice(SPARK_COL), 1.8 * sz, g=0.1)
            elif kind == "Звёздная пыль":
                self.spawn_fx(px, py, random.uniform(-0.5, 0.5), -random.uniform(0.1, 0.7), life * 1.5,
                              random.choice(DUST_COL), 2.6 * sz, glyph="✦")
            elif kind == "Пузырьки":
                self.spawn_fx(px, py, random.uniform(-0.4, 0.4), -random.uniform(0.4, 1.2), life * 1.5,
                              "#BFE9FF", random.uniform(3, 6) * sz, ring=True, drag=0.99)
            elif kind == "Сердечки":
                self.spawn_fx(px, py, random.uniform(-0.5, 0.5), -random.uniform(0.5, 1.2), life * 1.5,
                              random.choice(HEART_COL), 2.8 * sz, glyph="♥")
            elif kind == "Снежинки":
                self.spawn_fx(px, py, random.uniform(-0.6, 0.6), random.uniform(0.2, 0.8), life * 1.5,
                              "#FFFFFF", 2.6 * sz, glyph="❄")
            else:
                self.spawn_fx(px, py, random.uniform(-0.5, 0.5), -random.uniform(0.8, 2.0), life,
                              random.choice(FIRE_COL), 3.5 * sz, drag=0.98)

    # ---- метеоры (объёмные, с огненно-золотым ядром, плазменным хвостом и искрами) и фейерверки
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
        if cfg["fw_enabled"]:
            if self.next_fw == 0.0:
                self.next_fw = now + random.uniform(1, max(2, cfg["fw_every"]))
            elif now >= self.next_fw:
                self.spawn_rocket()
                self.next_fw = now + cfg["fw_every"] * random.uniform(0.5, 1.5)
        else:
            self.next_fw = 0.0

        cv = self.cv
        fs = self.frame_scale
        keep = []
        for m in self.meteors:
            m["x"] += m["vx"] * fs
            m["y"] += m["vy"] * fs
            m["life"] -= fs
            x, y = m["x"], m["y"]
            dx, dy = m["ux"], m["uy"]
            nx, ny = -dy, dx
            L = m["tail"] * max(0.25, m["life"] / m["max_life"])
            w = m["width"]

            # Внешний мягкий шлейф
            cv.coords(m["outer"],
                      x + dx * 6, y + dy * 6,
                      x + nx * w * 2.2 - dx * 6, y + ny * w * 2.2 - dy * 6,
                      x - dx * L, y - dy * L,
                      x - nx * w * 2.2 - dx * 6, y - ny * w * 2.2 - dy * 6)
            # Средний яркий плазменный хвост
            cv.coords(m["mid"],
                      x + dx * 5, y + dy * 5,
                      x + nx * w * 1.15 - dx * 4, y + ny * w * 1.15 - dy * 4,
                      x - dx * (L * 0.62), y - dy * (L * 0.62),
                      x - nx * w * 1.15 - dx * 4, y - ny * w * 1.15 - dy * 4)
            # Раскалённое белое ядро
            cv.coords(m["core"], x - w * 1.3, y - w * 1.3, x + w * 1.3, y + w * 1.3)
            cv.coords(m["halo"], x - w * 3.0, y - w * 3.0, x + w * 3.0, y + w * 3.0)

            # Отлетающие искры с хвоста
            if random.random() < 0.85:
                back = random.uniform(4, L * 0.45)
                sx = x - dx * back + nx * random.uniform(-w, w)
                sy = y - dy * back + ny * random.uniform(-w, w)
                self.spawn_fx(sx, sy,
                              -dx * random.uniform(0.5, 2.0) + random.uniform(-0.8, 0.8),
                              -dy * random.uniform(0.5, 2.0) + random.uniform(-0.8, 0.8),
                              random.randint(10, 20),
                              random.choice(("#FFF5CC", "#FFD166", "#90E0EF", "#FF9F1C")),
                              random.uniform(1.1, 2.2), drag=0.92)

            if m["life"] > 0 and -260 < x < self.W + 260 and y < self.H + 120:
                keep.append(m)
            else:
                for iid in (m["outer"], m["mid"], m["core"], m["halo"]):
                    cv.delete(iid)
        self.meteors = keep

        keep = []
        for rk in self.rockets:
            rk["y"] += rk["vy"] * fs
            self.spawn_fx(rk["x"], rk["y"], 0, 0, 2, "#FFFFFF", 2.4, drag=1.0)
            self.spawn_fx(rk["x"], rk["y"], random.uniform(-0.4, 0.4), 0.8, 12, "#FF9F1C", 1.5, drag=0.9)
            if rk["y"] <= rk["ty"]:
                self.firework_burst(rk["x"], rk["y"], rk["col"])
            else:
                keep.append(rk)
        self.rockets = keep

    def spawn_meteor(self):
        cv = self.cv
        dirx = random.choice((-1, 1))
        sp = random.uniform(15, 23)
        vx = dirx * sp * 0.84
        vy = sp * 0.54
        mag = math.hypot(vx, vy)
        ux, uy = vx / mag, vy / mag
        x = random.uniform(0.2, 0.92) * self.W if dirx < 0 else random.uniform(0.08, 0.8) * self.W
        y = random.uniform(0.02, 0.30) * self.H
        mlen = self.cfg["meteor_len"]
        tail = random.uniform(135, 220) * mlen
        width = random.uniform(2.8, 4.4) * (0.7 + 0.3 * mlen)
        palette = random.choice((
            ("#48CAE4", "#FFD166", "#FFF8E7"),
            ("#90E0EF", "#FF9F1C", "#FFFFFF"),
            ("#B5179E", "#F72585", "#FFF3B0"),
            ("#4CC9F0", "#FFE066", "#FFFFFF"),
        ))
        outer = cv.create_polygon(0, 0, 1, 0, 1, 1, 0, 1, fill=palette[0], outline="",
                                  stipple="gray50", tags="fx")
        mid = cv.create_polygon(0, 0, 1, 0, 1, 1, 0, 1, fill=palette[1], outline="", tags="fx")
        halo = cv.create_oval(0, 0, 1, 1, fill=palette[1], outline="", stipple="gray25", tags="fx")
        core = cv.create_oval(0, 0, 1, 1, fill=palette[2], outline="#FFFFFF", tags="fx")
        for iid in (outer, mid, halo, core):
            self.below_mask(iid)
        life = random.randint(28, 46)
        self.meteors.append({
            "x": x, "y": y, "vx": vx, "vy": vy, "ux": ux, "uy": uy,
            "tail": tail, "width": width, "life": float(life), "max_life": float(life),
            "outer": outer, "mid": mid, "halo": halo, "core": core
        })

    def spawn_rocket(self):
        self.rockets.append({"x": random.uniform(0.1, 0.9) * self.W, "y": self.H - 60.0,
                             "vy": -random.uniform(9, 13), "ty": random.uniform(0.12, 0.45) * self.H,
                             "col": random.choice(FW_COL)})

    def firework_burst(self, x, y, col):
        size = self.cfg["fw_size"]
        n = min(95, int(52 * size))
        ring = random.random() < 0.3
        col2 = random.choice(FW_COL)
        for i in range(n):
            a = (i / n) * 6.283 if ring else random.uniform(0, 6.283)
            s = (3.2 if ring else random.uniform(1.2, 5.2)) * size
            self.spawn_fx(x, y, math.cos(a) * s, math.sin(a) * s, random.randint(35, 60),
                          col if random.random() < 0.7 else col2, 2.0, g=0.06, drag=0.96)

    # ---- декоративные эффекты
    def effect_enabled(self, name):
        c = self.cfg
        if name == "sky":
            return c["sky_body"] != "Выкл"
        if name == "birds":
            return c["birds_mode"] != "Выкл"
        if name == "santa":
            return bool(c["santa_enabled"]) or self.santa is not None
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
                if self.effect_on.get(name):
                    getattr(self, "update_" + name)(now)
            except Exception:
                if self.strict:
                    raise
                log_error("effect " + name)
                self.cv.delete("e_" + name)
                self.effect_on[name] = False
                if name == "sky":
                    self.cfg["sky_body"] = "Выкл"
                elif name == "birds":
                    self.cfg["birds_mode"] = "Выкл"
                else:
                    self.cfg[name + "_enabled"] = False

    # ---- северное сияние
    def build_aurora(self):
        cv = self.cv
        rng = random.Random(481)
        count = max(14, min(28, int(self.W / 80)))
        self.aurora_strands = []
        for i in range(count):
            x = (i + rng.uniform(-0.35, 0.35)) * self.W / count
            self.aurora_strands.append({
                "ribbon": cv.create_polygon(0, 0, 0, 1, 1, 1, 1, 0,
                                             fill="#123B34", outline="", stipple="gray25",
                                             smooth=True, tags="e_aurora"),
                "core": cv.create_line(0, 0, 0, 1, fill="#73F3C1", width=2,
                                       smooth=True, capstyle="round", stipple="gray50",
                                       tags="e_aurora"),
                "x": x,
                "top": rng.uniform(0.0, 0.16),
                "length": rng.uniform(0.55, 1.1),
                "phase": rng.uniform(0.0, math.tau),
                "bend": rng.uniform(22.0, 70.0),
                "fold": rng.uniform(8.0, 26.0),
                "width": rng.uniform(10.0, 34.0),
                "color_pos": max(0.0, min(1.0, x / max(1.0, self.W))),
            })
        self.aurora_last_color = -1

    def aurora_color(self, name, pos, t, band=0):
        pal = AURORA_PAL.get(name, AURORA_PAL["Зелёное"])
        x = ((pos + 0.15 * math.sin(t * 0.2 + band)) % 1.0) * (len(pal) - 1)
        i = int(x)
        return mix(pal[i], pal[min(i + 1, len(pal) - 1)], x - i)

    def update_aurora(self, now):
        cv, cfg = self.cv, self.cfg
        t = now * cfg["aurora_speed"]
        Ht = self.H * cfg["aurora_height"] / 100.0
        power = int(cfg["aurora_power"])
        phase_t = int(now * 3)
        recolor = phase_t != self.aurora_last_color
        self.aurora_last_color = phase_t
        samples = 9
        for strand in self.aurora_strands:
            x0 = strand["x"]
            y0 = Ht * strand["top"]
            length = max(10.0, Ht * strand["length"])
            centerline, left_edge, right_edge = [], [], []
            for j in range(samples):
                p = j / (samples - 1.0)
                bend = math.sin(strand["phase"] + p * 2.8 + t * 0.16) * strand["bend"] * p
                fold = math.sin(strand["phase"] * 1.7 + p * 5.2 - t * 0.11) * strand["fold"] * p
                x = x0 + bend + fold
                y = y0 + length * p + math.sin(strand["phase"] + x0 * 0.01 + t * 0.12) * Ht * 0.018 * p
                width = strand["width"] * (0.18 + 0.82 * math.sin(math.pi * p) ** 0.7)
                centerline.extend((x, y))
                left_edge.extend((x - width * 0.5, y))
                right_edge.extend((x + width * 0.5, y))
            ribbon = left_edge + list(reversed(right_edge))
            cv.coords(strand["ribbon"], *ribbon)
            cv.coords(strand["core"], *centerline)

            if recolor:
                color = self.aurora_color(cfg["aurora_palette"], strand["color_pos"], t)
                outer = 0.15 + 0.035 * power
                core = 0.38 + 0.07 * power
                cv.itemconfigure(strand["ribbon"], fill=mix(color, "#07131D", outer))
                cv.itemconfigure(strand["core"], fill=mix(color, "#07131D", core))

    # ---- звёздное небо: красивые 4-лучевые звёзды + периодически падающие звёзды
    def build_stars(self):
        cv, cfg = self.cv, self.cfg
        rnd = random.Random(19)
        hh = self.H * cfg["stars_height"] / 100.0
        self.stars = []
        self.sky_shooting = []
        self.next_sky_shoot = self.now + random.uniform(2.5, 6.0)
        tints = ("#FFFFFF", "#CFE6FF", "#FFF3C4", "#FFD8EE", "#B8E0FF")
        for _ in range(int(cfg["stars_count"])):
            x, y = rnd.uniform(12, self.W - 12), rnd.uniform(10, hh)
            tint = rnd.choice(tints)
            kind = rnd.random()
            if kind < 0.24:
                # Яркая 4-лучевая звезда с мягким ореолом
                R = rnd.uniform(4.2, 7.6)
                r_in = R * 0.22
                halo = cv.create_oval(x - R * 1.15, y - R * 1.15, x + R * 1.15, y + R * 1.15,
                                      fill=blend(tint, 0.28), outline="", stipple="gray25", tags="e_stars")
                pts = [
                    x, y - R,
                    x + r_in, y - r_in,
                    x + R, y,
                    x + r_in, y + r_in,
                    x, y + R,
                    x - r_in, y + r_in,
                    x - R, y,
                    x - r_in, y - r_in,
                ]
                star_id = cv.create_polygon(*pts, fill=tint, outline="", tags="e_stars")
                self.stars.append({"id": star_id, "halo": halo, "ph": rnd.uniform(0, 6.3),
                                   "spd": rnd.uniform(1.4, 3.0), "tint": tint, "bright": True})
            elif kind < 0.65:
                # Средняя искорка-ромб
                R = rnd.uniform(2.1, 3.6)
                star_id = cv.create_polygon(x, y - R, x + R * 0.55, y, x, y + R, x - R * 0.55, y,
                                            fill=tint, outline="", tags="e_stars")
                self.stars.append({"id": star_id, "halo": None, "ph": rnd.uniform(0, 6.3),
                                   "spd": rnd.uniform(1.2, 2.6), "tint": tint, "bright": False})
            else:
                # Далёкая звёздная пыль
                R = rnd.uniform(1.0, 1.9)
                star_id = cv.create_oval(x - R, y - R, x + R, y + R, fill=tint, outline="", tags="e_stars")
                self.stars.append({"id": star_id, "halo": None, "ph": rnd.uniform(0, 6.3),
                                   "spd": rnd.uniform(0.8, 2.0), "tint": tint, "bright": False})

    def update_stars(self, now):
        cv = self.cv
        tw = self.cfg["stars_twinkle"]
        if self.frame % 4 == 0:
            for s in self.stars:
                f = 0.42 + 0.58 * (0.5 + 0.5 * math.sin(now * tw * s["spd"] + s["ph"]))
                cv.itemconfigure(s["id"], fill=blend(s["tint"], f))
                if s["halo"]:
                    cv.itemconfigure(s["halo"], fill=blend(s["tint"], f * 0.32))

        # Падающие звёзды прямо в звёздном небе
        if now >= self.next_sky_shoot and len(self.sky_shooting) < 3:
            self.next_sky_shoot = now + random.uniform(3.0, 8.0)
            hh = self.H * self.cfg["stars_height"] / 100.0
            dirx = random.choice((-1, 1))
            sx = random.uniform(0.1, 0.9) * self.W
            sy = random.uniform(14, max(40, hh * 0.65))
            sp = random.uniform(11, 17)
            vx, vy = dirx * sp * 0.86, sp * 0.5
            line_id = cv.create_line(sx, sy, sx, sy, fill="#FFF8DC", width=2.2,
                                     capstyle="round", tags="e_stars")
            head_id = cv.create_oval(sx - 2.5, sy - 2.5, sx + 2.5, sy + 2.5,
                                     fill="#FFFFFF", outline="#FFE082", tags="e_stars")
            self.sky_shooting.append({
                "x": sx, "y": sy, "vx": vx, "vy": vy,
                "life": 24.0, "max": 24.0, "line": line_id, "head": head_id
            })

        keep = []
        fs = self.frame_scale
        for sh in self.sky_shooting:
            sh["x"] += sh["vx"] * fs
            sh["y"] += sh["vy"] * fs
            sh["life"] -= fs
            k = max(0.0, sh["life"] / sh["max"])
            tail = 58.0 * math.sin(math.pi * k) + 12.0
            mag = math.hypot(sh["vx"], sh["vy"]) or 1.0
            tx = sh["x"] - (sh["vx"] / mag) * tail
            ty = sh["y"] - (sh["vy"] / mag) * tail
            cv.coords(sh["line"], tx, ty, sh["x"], sh["y"])
            r = 2.6 * (0.4 + 0.6 * k)
            cv.coords(sh["head"], sh["x"] - r, sh["y"] - r, sh["x"] + r, sh["y"] + r)
            cv.itemconfigure(sh["line"], fill=blend("#FFF3B0", 0.3 + 0.7 * k))
            if sh["life"] > 0:
                keep.append(sh)
            else:
                cv.delete(sh["line"])
                cv.delete(sh["head"])
        self.sky_shooting = keep

    # ---- солнце и луна (детализированные, многослойные)
    def build_sky(self):
        cv, cfg = self.cv, self.cfg
        body = cfg["sky_body"]
        if body == "Авто":
            body = "Солнце" if 6 <= time.localtime().tm_hour < 19 else "Луна"
        L, T, R, B = self.widget_mon()
        S = float(cfg["sky_size"])
        cx = R - S * 1.55 if cfg["sky_corner"].startswith("Прав") else L + S * 1.55
        cy = T + S * 1.38
        self.sky = {"body": body, "cx": cx, "cy": cy, "S": S, "rays": [], "corona": []}
        tg = "e_sky"
        if body == "Луна":
            Rr = S * 0.52
            # Мягкое многослойное лунное гало
            for k, col in ((2.15, "#233554"), (1.78, "#354F7A"), (1.46, "#5C7EB5"), (1.22, "#8FAEE0")):
                cv.create_oval(cx - Rr * k, cy - Rr * k, cx + Rr * k, cy + Rr * k,
                               fill=col, outline="", stipple="gray25", tags=tg)
            # Основной диск луны с тёплым перламутровым градиентом
            cv.create_oval(cx - Rr, cy - Rr, cx + Rr, cy + Rr,
                           fill="#EAE4CE", outline="#FFFDF5", width=2, tags=tg)
            cv.create_oval(cx - Rr * 0.92, cy - Rr * 0.92, cx + Rr * 0.84, cy + Rr * 0.84,
                           fill="#F7F3E3", outline="", tags=tg)
            # Моря (тёмные области) и кратеры с ободком
            seas = ((-0.18, -0.22, 0.34, 0.24), (0.22, -0.10, 0.26, 0.30), (-0.12, 0.25, 0.30, 0.20))
            for ox, oy, rx, ry in seas:
                cv.create_oval(cx + Rr * (ox - rx), cy + Rr * (oy - ry),
                               cx + Rr * (ox + rx), cy + Rr * (oy + ry),
                               fill="#DFD8BE", outline="", tags=tg)
            craters = ((-0.32, -0.18, 0.14), (0.26, 0.18, 0.11), (0.04, -0.44, 0.085),
                       (-0.22, 0.34, 0.095), (0.40, -0.26, 0.065), (-0.04, 0.04, 0.075),
                       (0.14, 0.44, 0.06))
            for ox, oy, rr in craters:
                cv.create_oval(cx + Rr * (ox - rr) + 1.5, cy + Rr * (oy - rr) + 1.5,
                               cx + Rr * (ox + rr) + 1.5, cy + Rr * (oy + rr) + 1.5,
                               fill="#FAF7EC", outline="", tags=tg)
                cv.create_oval(cx + Rr * (ox - rr), cy + Rr * (oy - rr),
                               cx + Rr * (ox + rr), cy + Rr * (oy + rr),
                               fill="#CFC7AA", outline="#BDB496", width=1, tags=tg)
            phase = cfg["sky_phase"]
            if phase == "Авто":
                a = self.moon_age()
                phase = "Полная" if 0.4 <= a < 0.6 else ("Растущая" if a < 0.5 else "Убывающая")
            if phase != "Полная":
                sgn = -1 if phase == "Растущая" else 1
                mx = cx + sgn * Rr * 0.58
                cv.create_oval(mx - Rr * 0.99, cy - Rr * 0.99, mx + Rr * 0.99, cy + Rr * 0.99,
                               fill=KEY, outline="", tags=tg)
            # Несколько звёздочек рядом с луной
            rnd = random.Random(3)
            for _ in range(6):
                a = rnd.uniform(0, 6.283)
                dd = Rr * rnd.uniform(1.85, 2.65)
                sx, sy = cx + math.cos(a) * dd, cy + math.sin(a) * dd
                sr = rnd.uniform(2.5, 4.5)
                cv.create_polygon(sx, sy - sr, sx + sr * 0.3, sy - sr * 0.3,
                                  sx + sr, sy, sx + sr * 0.3, sy + sr * 0.3,
                                  sx, sy + sr, sx - sr * 0.3, sy + sr * 0.3,
                                  sx - sr, sy, sx - sr * 0.3, sy - sr * 0.3,
                                  fill="#FFF8DC", outline="", tags=tg)
        else:
            Rr = S * 0.44
            # Солнечная корона и свечение
            for k, col in ((2.45, "#FF8F00"), (2.0, "#FFA000"), (1.62, "#FFB300"), (1.32, "#FFCA28")):
                o = cv.create_oval(cx - Rr * k, cy - Rr * k, cx + Rr * k, cy + Rr * k,
                                   fill=col, outline="", stipple="gray25", tags=tg)
                self.sky["corona"].append((o, Rr * k))
            # 20 мягких заострённых лучей
            for _ in range(20):
                self.sky["rays"].append(cv.create_polygon(0, 0, 1, 0, 1, 1, fill="#FFC107",
                                                          outline="", tags=tg))
            # Многослойный солнечный диск от золотисто-оранжевого края до бело-золотого центра
            for k, col in ((1.0, "#FF9800"), (0.90, "#FFB300"), (0.76, "#FFCA28"),
                           (0.58, "#FFE082"), (0.36, "#FFF8E1")):
                cv.create_oval(cx - Rr * k, cy - Rr * k, cx + Rr * k, cy + Rr * k,
                               fill=col, outline="", tags=tg)
            self.update_sky(self.now, True)

    def update_sky(self, now, force=False):
        sk = self.sky
        if not sk["rays"] or (self.frame % 3 and not force):
            return
        cv = self.cv
        cx, cy, S = sk["cx"], sk["cy"], sk["S"]
        r0 = S * 0.44 * 1.05
        n_rays = len(sk["rays"])
        for i, rid in enumerate(sk["rays"]):
            a = now * 0.18 + i * 2 * math.pi / n_rays
            is_long = (i % 2 == 0)
            pulse = 0.92 + 0.08 * math.sin(now * 2.2 + i * 0.9)
            ln = S * (1.06 if is_long else 0.78) * pulse
            wd = 0.085 if is_long else 0.065
            cv.coords(rid,
                      cx + math.cos(a - wd) * r0, cy + math.sin(a - wd) * r0,
                      cx + math.cos(a) * ln, cy + math.sin(a) * ln,
                      cx + math.cos(a + wd) * r0, cy + math.sin(a + wd) * r0)
            cv.itemconfigure(rid, fill="#FFB300" if is_long else "#FFD54F")

    # ---- большие объёмные облака
    def build_clouds(self):
        cv, cfg = self.cv, self.cfg
        body, mid_col, shade = {
            "Белые": ("#FFFFFF", "#EBF2FC", "#C9D8EE"),
            "Серые (пасмурно)": ("#C4CCD8", "#A3AEBE", "#7C8798"),
            "Закат (розовые)": ("#FFE0D4", "#FFC1B8", "#E396AB"),
        }.get(cfg["clouds_tint"], ("#FFFFFF", "#EBF2FC", "#C9D8EE"))
        rnd = random.Random(31)
        self.clouds = []
        hmax = max(self.H * 0.12, self.H * cfg["clouds_height"] / 100.0)
        count = int(cfg["clouds_count"])
        for i in range(count):
            # Большие, пушистые облака разного плана (дальние чуть меньше, передние огромные)
            depth = 0.75 + 0.55 * (i / max(1, count - 1))
            w = rnd.uniform(340, 640) * depth
            h = w * rnd.uniform(0.30, 0.36)
            x = rnd.uniform(-w * 0.6, self.W)
            y = rnd.uniform(self.H * 0.015, hmax)
            tg = ("e_clouds", "cl%d" % i)
            # Нижняя глубокая тень
            cv.create_oval(x + w * 0.05, y + h * 0.44, x + w * 0.95, y + h * 1.06,
                           fill=shade, outline="", tags=tg)
            # Средний объёмный слой
            for (bx, by, bw, bh) in ((0.02, 0.36, 0.38, 0.62), (0.22, 0.14, 0.44, 0.80),
                                     (0.50, 0.22, 0.42, 0.72), (0.66, 0.38, 0.32, 0.56)):
                cv.create_oval(x + w * bx, y + h * by, x + w * (bx + bw), y + h * (by + bh),
                               fill=mid_col, outline="", tags=tg)
            # Верхние освещённые купола облака
            for (bx, by, bw, bh) in ((0.06, 0.32, 0.34, 0.54), (0.18, 0.04, 0.36, 0.72),
                                     (0.38, 0.0, 0.38, 0.78), (0.58, 0.16, 0.32, 0.60),
                                     (0.72, 0.34, 0.24, 0.48)):
                cv.create_oval(x + w * bx, y + h * by, x + w * (bx + bw), y + h * (by + bh),
                               fill=body, outline="", tags=tg)
            # Выравнивание нижней кромки
            cv.create_oval(x + w * 0.06, y + h * 0.56, x + w * 0.94, y + h * 0.94,
                           fill=body, outline="", tags=tg)
            self.clouds.append({"tag": "cl%d" % i, "x": x, "w": w, "v": rnd.uniform(0.22, 0.55) * depth})

    def update_clouds(self, now):
        sp = self.cfg["clouds_speed"] * 1.4 * self.frame_scale
        for c in self.clouds:
            dx = c["v"] * sp
            self.cv.move(c["tag"], dx, 0)
            c["x"] += dx
            if c["x"] > self.W + 40:
                back = self.W + c["w"] + 80
                self.cv.move(c["tag"], -back, 0)
                c["x"] -= back

    # ---- птицы и бабочки
    def birds_kind(self):
        m = self.cfg["birds_mode"]
        if m == "Птицы":
            return "bird"
        if m == "Бабочки":
            return "butterfly"
        return "butterfly" if self.season == "summer" else "bird"

    def build_birds(self):
        cv, cfg = self.cv, self.cfg
        self.bkind = self.birds_kind()
        n = int(cfg["birds_count"])
        W, H = self.W, self.H
        self.birds = []
        if self.bkind == "bird":
            col = "#E8EEF8" if self.season == "winter" else "#1F2437"
            for f in range((n + 6) // 7):
                d = random.choice((1, -1))
                fl = {"d": d, "x": random.uniform(-W * 0.3, W * 1.1), "y": random.uniform(0.08, 0.5) * H,
                      "v": random.uniform(1.8, 2.8), "birds": []}
                for k in range(min(7, n - f * 7)):
                    side = 1 if k % 2 else -1
                    rank = (k + 1) // 2
                    i = cv.create_line(0, 0, 1, 1, 2, 2, 3, 3, 4, 4, fill=col, width=2, smooth=True,
                                       tags="e_birds")
                    fl["birds"].append((i, (-d * rank * 24, side * rank * 13), random.uniform(0, 6.3)))
                self.birds.append(fl)
        else:
            for k in range(n):
                col = random.choice(CONFETTI_COL)
                wl = cv.create_polygon(0, 0, 1, 1, 2, 2, fill=col, outline=blend(col, 0.6), smooth=True,
                                       tags="e_birds")
                wr = cv.create_polygon(0, 0, 1, 1, 2, 2, fill=col, outline=blend(col, 0.6), smooth=True,
                                       tags="e_birds")
                self.birds.append({"x": random.uniform(0, W), "y": random.uniform(0.1, 0.9) * H,
                                   "hd": random.uniform(0, 6.283), "ph": random.uniform(0, 6.3),
                                   "ids": (wl, wr)})

    def update_birds(self, now):
        cv, cfg = self.cv, self.cfg
        s = cfg["birds_size"] / 100.0
        sp = cfg["birds_speed"] * self.frame_scale
        W, H = self.W, self.H
        if self.bkind == "bird":
            for fl in self.birds:
                fl["x"] += fl["d"] * fl["v"] * sp * 1.6
                if (fl["d"] > 0 and fl["x"] > W + 200) or (fl["d"] < 0 and fl["x"] < -200):
                    fl["d"] = random.choice((1, -1))
                    fl["x"] = -150 if fl["d"] > 0 else W + 150
                    fl["y"] = random.uniform(0.08, 0.5) * H
                for (i, off, ph) in fl["birds"]:
                    bx = fl["x"] + off[0] * s
                    by = fl["y"] + off[1] * s + math.sin(now * 1.3 + ph) * 3
                    f = math.sin(now * 9 + ph) * 6 * s
                    cv.coords(i, bx - 10 * s, by - f, bx - 4 * s, by - f * 0.3 - 3 * s, bx, by,
                              bx + 4 * s, by - f * 0.3 - 3 * s, bx + 10 * s, by - f)
        else:
            for b in self.birds:
                b["hd"] += random.uniform(-0.25, 0.25)
                b["x"] += math.cos(b["hd"]) * sp * 1.3
                b["y"] += math.sin(b["hd"]) * sp * 0.9 + math.sin(now * 3 + b["ph"]) * 0.4
                if b["x"] > W + 20:
                    b["x"] = -20
                elif b["x"] < -20:
                    b["x"] = W + 20
                if b["y"] > H - 40:
                    b["hd"] = -abs(b["hd"])
                    b["y"] = H - 40
                elif b["y"] < 20:
                    b["y"] = 20
                    b["hd"] = abs(b["hd"])
                wf = 0.25 + 0.75 * abs(math.cos(now * 10 + b["ph"]))
                x, y = b["x"], b["y"]
                cv.coords(b["ids"][0], x, y, x - 9 * s * wf, y - 8 * s, x - 13 * s * wf, y - 1 * s,
                          x - 9 * s * wf, y + 6 * s, x, y + 2 * s)
                cv.coords(b["ids"][1], x, y, x + 9 * s * wf, y - 8 * s, x + 13 * s * wf, y - 1 * s,
                          x + 9 * s * wf, y + 6 * s, x, y + 2 * s)

    # ---- новогодняя ёлка
    def build_tree(self):
        cv, cfg = self.cv, self.cfg
        L, T, R, B = self.widget_mon()
        s = cfg["tree_size"] / 100.0
        Tw, Th = 170 * s, 250 * s
        by = B - cfg["tree_lift"]
        side, m = cfg["tree_side"], cfg["tree_margin"]
        if side == "Слева":
            cx = L + m + Tw / 2
        elif side == "Справа":
            cx = R - m - Tw / 2
        else:
            cx = (L + R) / 2
        tg = "e_tree"
        rnd = random.Random(5)
        cv.create_rectangle(cx - 9 * s, by - Th * 0.14, cx + 9 * s, by, fill="#6D4C41",
                            outline="#4E342E", tags=tg)
        tiers = ((0.50, 0.10, 0.50, "#1B8A3A"), (0.74, 0.34, 0.40, "#1F9D44"),
                 (0.97, 0.60, 0.29, "#28B04F"))
        pal = ["#FF3B30", "#FFD60A", "#34C759", "#0A84FF", "#FF6FD8", "#FF9F1C"]
        self.tree_lights = []
        for apex, base, hw, col in tiers:
            ya, yb = by - Th * apex, by - Th * base
            half = Tw * hw
            pts = [cx, ya, cx + half, yb]
            n = 6
            for q in range(n):
                pts += [cx + half - 2 * half * (q + 0.5) / n, yb - 8 * s,
                        cx + half - 2 * half * (q + 1) / n, yb]
            cv.create_polygon(*pts, fill=col, outline=blend(col, 0.55), width=2, tags=tg)
            hh = yb - ya
            cv.create_polygon(cx, ya, cx + half * 0.34, ya + hh * 0.30, cx + half * 0.12, ya + hh * 0.26,
                              cx, ya + hh * 0.36, cx - half * 0.12, ya + hh * 0.26,
                              cx - half * 0.34, ya + hh * 0.30, fill="#F4F9FF", outline="", tags=tg)
            p0 = (cx - half * 0.72, yb - hh * 0.30)
            p1 = (cx, yb - hh * 0.04)
            p2 = (cx + half * 0.72, yb - hh * 0.30)
            sw = []
            for q in range(13):
                t = q / 12.0
                sw += [(1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                       (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]]
            cv.create_line(*sw, fill="#FFD54F", width=2, smooth=True, tags=tg)
            for q in range(5):
                t = 0.12 + q * 0.19
                bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
                bby = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
                c2 = rnd.choice(pal)
                rr = 4.8 * s
                cv.create_oval(bx - rr, bby - rr + 3, bx + rr, bby + rr + 3, fill=c2,
                               outline=blend(c2, 0.55), tags=tg)
                cv.create_oval(bx - rr * 0.5, bby - rr * 0.6 + 3, bx - rr * 0.1, bby - rr * 0.1 + 3,
                               fill="#FFFFFF", outline="", tags=tg)
            for q in range(4):
                t = 0.2 + q * 0.2
                lx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
                ly = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1] - hh * 0.12
                c3 = rnd.choice(pal)
                rr = 3.2 * s
                o = cv.create_oval(lx - rr, ly - rr, lx + rr, ly + rr, fill=c3, outline="", tags=tg)
                self.tree_lights.append((o, c3, rnd.uniform(0, 6.3)))
        pts = []
        for q in range(10):
            ang = -math.pi / 2 + q * math.pi / 5
            rad = 14 * s if q % 2 == 0 else 6 * s
            pts += [cx + math.cos(ang) * rad, by - Th * 1.0 + math.sin(ang) * rad + 4 * s]
        for k in (30, 22):
            cv.create_oval(cx - k * s, by - Th + 4 * s - k * s, cx + k * s, by - Th + 4 * s + k * s,
                           fill="", outline="#FFE082", tags=tg)
        cv.create_polygon(*pts, fill="#FFD54F", outline="#FFF3B0", tags=tg)
        for gx, gw, gh, col in ((-0.95, 36, 26, "#E53935"), (0.4, 30, 22, "#1E88E5"), (0.85, 24, 18, "#FDD835")):
            x0 = cx + gx * Tw * 0.5
            cv.create_rectangle(x0, by - gh * s, x0 + gw * s, by, fill=col, outline=blend(col, 0.6), tags=tg)
            cv.create_rectangle(x0 + gw * s * 0.42, by - gh * s, x0 + gw * s * 0.58, by, fill="#FFFFFF",
                                outline="", tags=tg)
            cv.create_oval(x0 + gw * s * 0.2, by - gh * s - 7 * s, x0 + gw * s * 0.5, by - gh * s,
                           fill="#FFFFFF", outline="", tags=tg)
            cv.create_oval(x0 + gw * s * 0.5, by - gh * s - 7 * s, x0 + gw * s * 0.8, by - gh * s,
                           fill="#FFFFFF", outline="", tags=tg)

    def update_tree(self, now):
        if self.frame % 6:
            return
        for o, col, ph in self.tree_lights:
            f = 0.5 + 0.5 * math.sin(now * 3 + ph)
            self.cv.itemconfigure(o, fill=mix(col, "#FFFFFF", 0.45 * f) if f > 0.3 else blend(col, 0.45))

    # ---- слои и производительность
    def below_mask(self, item):
        if self.mask_items and self.cfg["desktop_only"]:
            self.cv.tag_lower(item, "mask")

    def apply_layers(self):
        self.update_mask()
        self.raise_all()
        self.next_poll = 0.0

    def adapt_perf(self, now):
        cfg = self.cfg
        if cfg["perf_mode"] == "Экономия" or now < self.perf_cool:
            return
        target = 0.65 if cfg["perf_mode"] == "Авто" else 0.80
        budget = 1000.0 / max(15, cfg["fps"]) * target
        if self.ms > budget and self.perf_scale > 0.45:
            self.perf_scale = max(0.45, self.perf_scale * 0.82)
            self.dirty_particles = True
            self.perf_cool = now + 1.0
        elif self.ms < budget * 0.45 and self.perf_scale < 1.0:
            self.perf_scale = min(1.0, self.perf_scale * 1.15)
            self.dirty_particles = True
            self.perf_cool = now + 1.5

    def update_mask(self):
        cv = self.cv
        if not self.cfg["desktop_only"]:
            if self.mask_items:
                cv.delete("mask")
                self.mask_items, self.mask_rects = [], []
            return
        rects = self.win_rects + self.tb_rects
        created = False
        while len(self.mask_items) < len(rects):
            self.mask_items.append(cv.create_rectangle(0, 0, 0, 0, fill=KEY, outline="", tags="mask"))
            self.mask_rects.append(None)
            created = True
        while len(self.mask_items) > len(rects):
            cv.delete(self.mask_items.pop())
            self.mask_rects.pop()
        for i, r in enumerate(rects):
            rr = (int(r[0]) - 1, int(r[1]) - 1, int(r[2]) + 1, int(r[3]) + 1)
            if self.mask_rects[i] != rr:
                cv.coords(self.mask_items[i], *rr)
                self.mask_rects[i] = rr
        if created:
            self.raise_all()

    def spawn_gift(self, x, y, col=None):
        if len(self.chunks) >= 400:
            return
        col = col or random.choice(("#E53935", "#1E88E5", "#43A047", "#FDD835", "#8E24AA"))
        i = self.cv.create_rectangle(x - 6, y - 5, x + 6, y + 5, fill=col, outline=blend(col, 0.6),
                                     tags="flake")
        self.below_mask(i)
        self.chunks.append({"x": x, "y": y, "py": y, "vx": random.uniform(-0.4, 0.4), "vy": 1.0,
                            "r": 6, "mat": "snow", "id": i, "gift": col})

    def add_gift(self, key, left, x, col):
        self.gifts.append({"key": key, "off": x - left, "col": col})
        while len(self.gifts) > 14:
            self.gifts.pop(0)
        self.dirty_snowmen = True

    def snowman_height(self, stage, s=None):
        r1, r2, r3 = self.snowman_radii(s)
        y2 = r1 + (r1 + r2) * 0.82
        y3 = y2 + (r2 + r3) * 0.82
        return (2 * r1, y2 + r2, y3 + r3 * 1.7)[stage - 1]

    def snowman_at(self, cx, cy):
        s = self.cfg["snowman_size"]
        for sm in reversed(self.snowmen):
            pos = self.snowman_pos(sm)
            if not pos:
                continue
            x, top = pos
            if abs(cx - x) <= 13 * s * 1.3 and top - self.snowman_height(sm["stage"]) - 6 <= cy <= top + 8:
                return sm
        return None

    def surface_below(self, x, y):
        best = None
        for key, d in self.surf_info.items():
            for a, c in d["spans"]:
                if a <= x <= c and d["top"] >= y - 30:
                    if best is None or d["top"] < best[1]["top"]:
                        best = (key, d)
        return best

    def update_hold(self):
        cfg, cv = self.cfg, self.cv
        if not cfg["roll_enabled"] or self.cur is None or not self.visible:
            if self.hold:
                self.drop_hold(True)
            return
        down = self.get_key(0x11 if cfg["roll_key"] == "Ctrl" else 0x10)
        cx, cy = self.cur[0], self.cur[1]
        h = self.hold
        if not down:
            if h:
                self.drop_hold(False)
            return
        R0 = 13 * cfg["snowman_size"]
        if h is None:
            sm = self.snowman_at(cx, cy)
            if sm:
                self.snowmen.remove(sm)
                self.hold = {"t": "man", "sm": sm}
                self.dirty_snowmen = True
                return
            pm = cfg["pile_max"]
            for key, d in self.surf_info.items():
                for a, c in d["spans"]:
                    if a <= cx <= c and d["top"] - pm - 25 <= cy <= d["top"] + 15 \
                            and self.pile_h(key, d["left"], cx) >= 1.5:
                        self.hold = {"t": "ball", "r": 3.0, "lx": cx, "ready": False}
                        return
            return
        cv.delete("ball")
        cv.delete("carry")
        if h["t"] == "man":
            self.draw_snowman(cx, cy + 6, h["sm"]["stage"], "carry", 1.0)
            cv.tag_raise("carry")
            return
        dist = abs(cx - h["lx"])
        h["lx"] = cx
        sb = self.surface_below(cx, cy - 8)
        rolling = False
        if sb and not h["ready"]:
            key, d = sb
            gap = d["top"] - cy
            if -15 <= gap <= cfg["pile_max"] + 25:
                rolling = True
                hh = self.pile_h(key, d["left"], cx)
                p = self.piles.get(key)
                if p and hh >= 0.8 and dist > 0 and h["r"] < R0:
                    h["r"] = min(R0, h["r"] + dist * 0.05 * min(2.0, hh / 4 + 0.5))
                    arr = p["h"]
                    for i in range(max(0, int((cx - h["r"] - 6 - d["left"]) // BIN)),
                                   min(len(arr) - 1, int((cx + h["r"] + 6 - d["left"]) // BIN)) + 1):
                        arr[i] *= 0.82
                    self.pile_dirty = True
        if h["r"] >= R0 * 0.97:
            h["ready"] = True
        r = h["r"]
        by = (sb[1]["top"] - r) if (rolling and sb) else cy
        ol = "#5CC8FF" if h["ready"] else "#9DB7D8"
        cv.create_oval(cx - r, by - r, cx + r, by + r, fill="#FFFFFF", outline=ol,
                       width=3 if h["ready"] else 1, tags="ball")
        cv.create_oval(cx - r * 0.6, by - r * 0.65, cx - r * 0.2, by - r * 0.3,
                       fill="#E6F0FF", outline="", tags="ball")
        cv.tag_raise("ball")

    def drop_hold(self, cancel=False):
        cfg, cv = self.cfg, self.cv
        h, self.hold = self.hold, None
        cv.delete("ball")
        cv.delete("carry")
        if not h:
            return
        sb = None if (cancel or self.cur is None) else self.surface_below(self.cur[0], self.cur[1])
        cx = self.cur[0] if self.cur else 0
        if h["t"] == "man":
            sm = h["sm"]
            if sb:
                sm["key"], sm["off"] = sb[0], cx - sb[1]["left"]
            self.snowmen.append(sm)
            self.dirty_snowmen = True
            return
        if not sb or not h["ready"]:
            for _ in range(5):
                self.spawn_fx(cx, (self.cur[1] if self.cur else 0), random.uniform(-1.5, 1.5),
                              random.uniform(-2, 0), 14, "#FFFFFF", 2.0, g=0.15)
            return
        key, d = sb
        near = None
        for sm in self.snowmen:
            if sm["key"] == key and sm["stage"] < 3 and abs(d["left"] + sm["off"] - cx) < 30:
                near = sm
                break
        if near:
            near["stage"] += 1
        else:
            self.snowmen.append({"key": key, "off": cx - d["left"], "stage": 1, "t0": self.now})
        while len(self.snowmen) > int(cfg["snowman_max"]):
            self.snowmen.pop(0)
        self.dirty_snowmen = True

    def draw_gift(self, x, y, col, wt):
        cv, t = self.cv, ("gift", wt)
        w, h = 14, 11
        cv.create_rectangle(x - w / 2, y - h, x + w / 2, y, fill=col, outline=blend(col, 0.6), tags=t)
        cv.create_rectangle(x - 1.5, y - h, x + 1.5, y, fill="#FFE082", outline="", tags=t)
        cv.create_rectangle(x - w / 2, y - h / 2 - 1.5, x + w / 2, y - h / 2 + 1.5,
                            fill="#FFE082", outline="", tags=t)
        cv.create_oval(x - 4.5, y - h - 4, x, y - h, fill="#FFE082", outline="", tags=t)
        cv.create_oval(x, y - h - 4, x + 4.5, y - h, fill="#FFE082", outline="", tags=t)

    def widget_mon(self):
        ms = [m["work"] for m in self.mons] or [(self.vx, self.vy, self.vx + self.W, self.vy + self.H)]
        mode = self.cfg["widget_monitor"]
        if mode == "Левый":
            w = min(ms, key=lambda r: r[0])
        elif mode == "Правый":
            w = max(ms, key=lambda r: r[0])
        else:
            w = ms[0]
            for r in ms:
                if r[0] <= 0 < r[2] and r[1] <= 0 < r[3]:
                    w = r
                    break
        return (w[0] - self.vx, w[1] - self.vy, w[2] - self.vx, w[3] - self.vy)

    def moon_age(self):
        jd = time.time() / 86400.0 + 2440587.5
        return ((jd - 2451550.1) / 29.530588853) % 1.0

    # ---- отсчёт до праздника
    def count_target(self):
        now = datetime.datetime.now()
        mode = self.cfg["count_target"]
        if mode == "Новый год":
            m, d, name = 1, 1, "Нового года"
        elif mode == "Рождество":
            m, d, name = 1, 7, "Рождества"
        else:
            m, d, name = int(self.cfg["count_month"]), int(self.cfg["count_day"]), "праздника"
        y = now.year
        try:
            t = datetime.datetime(y, m, d)
        except ValueError:
            t = datetime.datetime(y, m, 28)
        if t.date() == now.date():
            return None, name
        if t <= now:
            try:
                t = datetime.datetime(y + 1, m, d)
            except ValueError:
                t = datetime.datetime(y + 1, m, 28)
        return t - now, name

    def build_count(self):
        cv, cfg = self.cv, self.cfg
        L, T, R, B = self.widget_mon()
        s = cfg["count_size"] / 100.0
        corner = cfg["count_corner"]
        right, bottom = "Прав" in corner, "низ" in corner
        x = (R - 28) if right else (L + 28)
        y = (B - 28 - 78 * s) if bottom else (T + 28)
        anc = "ne" if right else "nw"
        f1 = ("Segoe UI", max(8, int(13 * s)))
        f2 = ("Segoe UI Semibold", max(10, int(34 * s)))
        self.cnt_ids = []
        for dx, dy, c in ((2, 2, "#000000"), (0, 0, cfg["count_color"])):
            t1 = cv.create_text(x + dx, y + dy, text="", anchor=anc, font=f1, fill=c, tags="e_count")
            t2 = cv.create_text(x + dx, y + dy + 24 * s, text="", anchor=anc, font=f2, fill=c, tags="e_count")
            self.cnt_ids.append((t1, t2))
        self.update_count(self.now, True)

    def update_count(self, now, force=False):
        if self.frame % 15 and not force:
            return
        delta, name = self.count_target()
        if delta is None:
            a, b = "Сегодня праздник!", "С праздником! ✦"
        else:
            tot = int(delta.total_seconds())
            days, rem = divmod(tot, 86400)
            hh, rem = divmod(rem, 3600)
            mm, ss = divmod(rem, 60)
            a = "До %s осталось" % name
            b = ("%d д  %02d:%02d:%02d" % (days, hh, mm, ss)) if self.cfg["count_seconds"] \
                else ("%d д  %02d:%02d" % (days, hh, mm))
        for t1, t2 in self.cnt_ids:
            self.cv.itemconfigure(t1, text=a)
            self.cv.itemconfigure(t2, text=b)

    # ---- Дед Мороз на санях с оленями (быстрый, плавный, без перестройки всего рисунка)
    def start_santa(self):
        if self.santa:
            return
        d = random.choice((1, -1))
        s = self.cfg["santa_size"] / 100.0
        x0 = -320 * s if d > 0 else self.W + 320 * s
        y0 = self.H * self.cfg["santa_height"] / 100.0 + 90 * s
        self.santa = {"d": d, "x": x0, "y": y0, "base_y": y0, "t": 0.0, "gift": 0.0,
                      "built": False, "legs": []}
        self.santa_last_t = time.perf_counter()

    def build_santa(self):
        pass

    def update_santa(self, now):
        cfg, cv = self.cv, self.cfg
        st = self.santa
        if st is None:
            if cfg["santa_enabled"]:
                if self.next_santa is None:
                    self.next_santa = now + 5
                elif now >= self.next_santa:
                    self.start_santa()
                    self.next_santa = now + cfg["santa_every"] * 60 * random.uniform(0.7, 1.3)
            return

        t_perf = time.perf_counter()
        dt = min(0.08, max(0.004, t_perf - self.santa_last_t))
        self.santa_last_t = t_perf

        s = cfg["santa_size"] / 100.0
        if not st["built"]:
            cv.delete("e_santa")
            self.draw_santa_static(st["x"], st["y"], st["d"], s, st)
            st["built"] = True
            if self.mask_items and cfg["desktop_only"]:
                cv.tag_lower("e_santa", "mask")

        # Плавная скорость (px/сек), независимая от FPS
        speed_px = (90.0 + cfg["santa_speed"] * 48.0) * dt
        dx = st["d"] * speed_px
        st["x"] += dx
        st["t"] += dt * 7.5
        new_y = (self.H * cfg["santa_height"] / 100.0 + 90 * s) + 14.0 * math.sin(st["t"] * 0.45)
        dy = new_y - st["y"]
        st["y"] = new_y

        cv.move("e_santa", dx, dy)
        self.animate_santa_legs(st["x"], st["y"], st["d"], s, st["t"], st["legs"])

        if self.frame % 2 == 0:
            self.spawn_fx(st["x"] - st["d"] * 65 * s, st["y"] - 16 * s + random.uniform(-8, 8),
                          -st["d"] * random.uniform(0.4, 1.4), random.uniform(-0.3, 0.8), 22,
                          random.choice(("#FFE066", "#FFFFFF", "#FFB347")), 2.1, g=0.03, drag=0.96)
        if cfg["santa_gifts"]:
            st["gift"] += dt
            if st["gift"] >= 0.85:
                st["gift"] = 0.0
                self.spawn_gift(st["x"] - st["d"] * 10 * s, st["y"] + 10 * s)
        if (st["d"] > 0 and st["x"] > self.W + 360 * s) or (st["d"] < 0 and st["x"] < -360 * s):
            self.santa = None
            cv.delete("e_santa")

    def draw_santa_static(self, x, y, d, s, st):
        cv = self.cv
        tg = "e_santa"

        def P(pts):
            out = []
            for (px, py) in pts:
                out += [x + px * d * s, y + py * s]
            return out

        def poly(pts, fill, outline="", smooth=False):
            cv.create_polygon(*P(pts), fill=fill, outline=outline, smooth=smooth, tags=tg)

        def line(pts, fill, w=2, smooth=False):
            cv.create_line(*P(pts), fill=fill, width=max(1, int(w * s)), smooth=smooth, tags=tg)

        def oval(cx, cy, rx, ry, fill, outline=""):
            xx, yy = x + cx * d * s, y + cy * s
            cv.create_oval(xx - rx * s, yy - ry * s, xx + rx * s, yy + ry * s, fill=fill,
                           outline=outline, tags=tg)

        line([(34, -22), (63, -22)], "#8D6E63", 1.5)
        st["legs"] = []
        for n, dx in enumerate((78, 120, 162)):
            for lx, sg in ((-8, 1), (-3, -1), (7, -1), (12, 1)):
                lid = cv.create_line(0, 0, 1, 1, fill="#6D4C41", width=max(1, int(2 * s)),
                                     capstyle="round", tags=tg)
                st["legs"].append((lid, dx, lx, sg, n))
            oval(dx, -20, 15, 8, "#8D5524", "#5D3A1A")
            oval(dx - 14, -22, 3, 3, "#8D5524")
            poly([(dx + 9, -24), (dx + 20, -38), (dx + 26, -34), (dx + 14, -18)],
                 "#8D5524", smooth=True)
            oval(dx + 25, -37, 7, 5, "#8D5524", "#5D3A1A")
            line([(dx + 22, -41), (dx + 18, -52), (dx + 22, -58)], "#D7CCC8", 2)
            line([(dx + 19, -50), (dx + 13, -54)], "#D7CCC8", 2)
            line([(dx + 26, -41), (dx + 27, -52), (dx + 31, -57)], "#D7CCC8", 2)
            if n == 2:
                oval(dx + 31, -36, 5.5, 5.5, "", "#FF9090")
            oval(dx + 31, -36, 2.6, 2.6, "#FF3030" if n == 2 else "#3E2723")
            oval(dx + 27, -39, 1, 1, "#000000")
            if n < 2:
                line([(dx + 8, -20), (dx + 27, -20)], "#8D6E63", 1.5)
        line([(-38, 8), (-32, 12), (30, 12), (42, 9), (46, 1), (42, -3)], "#C9A227", 3, True)
        line([(-20, 12), (-20, 4)], "#C9A227", 2)
        line([(10, 12), (10, 4)], "#C9A227", 2)
        poly([(-34, 4), (-38, -12), (-30, -20), (28, -20), (38, -28), (42, -22), (32, 4)],
             "#C62828", "#7F0000", True)
        line([(-34, -2), (32, -2)], "#FFD54F", 2)
        oval(-24, -28, 15, 13, "#8D6E63", "#5D4037")
        poly([(-34, -38), (-26, -38), (-26, -30), (-34, -30)], "#43A047")
        poly([(-24, -42), (-16, -42), (-16, -34), (-24, -34)], "#1E88E5")
        poly([(-30, -45), (-23, -45), (-23, -39), (-30, -39)], "#FDD835")
        poly([(-4, -20), (-7, -40), (11, -40), (14, -20)], "#D32F2F", "#8E0000", True)
        poly([(-7, -22), (14, -22), (14, -19), (-7, -19)], "#FFFFFF")
        poly([(-5, -31), (12, -31), (12, -28), (-5, -28)], "#212121")
        oval(3.5, -29.5, 2.2, 2.2, "#FFD54F")
        line([(10, -36), (28, -24)], "#D32F2F", 4)
        oval(29, -23, 2.8, 2.8, "#FFFFFF")
        oval(3, -47, 6.5, 6.5, "#FFD9C2", "#E8B89E")
        poly([(-3, -45), (9, -45), (7, -36), (3, -32), (-1, -36)], "#FFFFFF", "", True)
        oval(4, -42, 4.2, 1.6, "#FFFFFF")
        oval(5.5, -48, 0.9, 0.9, "#212121")
        oval(0.5, -48, 0.9, 0.9, "#212121")
        oval(3, -45, 1.1, 1.1, "#F4A58A")
        poly([(-5, -51), (3, -66), (12, -50)], "#D32F2F", "#8E0000", True)
        poly([(-6.5, -53), (13, -53), (13, -49), (-6.5, -49)], "#FFFFFF")
        oval(4, -67, 3.6, 3.6, "#FFFFFF")
        self.animate_santa_legs(x, y, d, s, 0.0, st["legs"])

    def animate_santa_legs(self, x, y, d, s, t, legs):
        cv = self.cv
        for lid, dx, lx, sg, n in legs:
            ph = t * 1.3 + n * 1.1
            sw = math.sin(ph + (0.0 if sg > 0 else math.pi)) * 7.5
            x0 = x + (dx + lx) * d * s
            y0 = y - 16 * s
            x1 = x + (dx + lx + sw) * d * s
            y1 = y + (-2 - abs(sw) * 0.3) * s
            cv.coords(lid, x0, y0, x1, y1)


# ---------------------------------------------------------------- Оверлей в своём потоке
class Overlay(threading.Thread):
    def __init__(self, cfg):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.q = queue.Queue()
        self.engine = None
        self.root = None
        self.user_paused = False
        self.auto_paused = False
        self.shown = True
        self.stopping = False
        self.mon_rects = []
        self.last_check = 0.0
        self.last_mons = 0.0
        self.window_hook, self.window_event_proc = None, None

    @property
    def active(self):
        return not (self.user_paused or self.auto_paused)

    def send(self, *msg):
        self.q.put(msg)

    def run(self):
        try:
            root = tk.Tk()
            root.report_callback_exception = report_tk_exception
            self.root = root
            root.withdraw()
            vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
            W, H = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
            root.overrideredirect(True)
            root.geometry("%dx%d+%d+%d" % (W, H, vx, vy))
            root.configure(bg=KEY)
            root.attributes("-topmost", True)
            root.attributes("-transparentcolor", KEY)
            cv = tk.Canvas(root, bg=KEY, highlightthickness=0, width=W, height=H)
            cv.pack(fill="both", expand=True)
            root.update_idletasks()
            hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                  ex | WS_EX_LAYERED | WS_EX_TRANSPARENT |
                                  WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
            root.deiconify()
            root.lift()
            self.engine = Engine(cv, self.cfg, (vx, vy, W, H))
            self.install_window_hook()
            self.fast()
            self.slow()
            root.mainloop()
        except Exception:
            log_error("overlay thread")
        finally:
            if self.window_hook:
                try:
                    user32.UnhookWinEvent(self.window_hook)
                except Exception:
                    pass

    def install_window_hook(self):
        def moved(_hook, event, hwnd, object_id, child_id, _thread_id, _event_time):
            if event == EVENT_OBJECT_LOCATIONCHANGE and object_id == 0 and child_id == 0:
                if self.engine:
                    self.engine.window_location_changed(hwnd)

        self.window_event_proc = WINEVENTPROC(moved)
        self.window_hook = user32.SetWinEventHook(
            EVENT_OBJECT_LOCATIONCHANGE, EVENT_OBJECT_LOCATIONCHANGE, None,
            self.window_event_proc, 0, 0, 0)

    def drain(self):
        while True:
            try:
                msg = self.q.get_nowait()
            except queue.Empty:
                return
            try:
                cmd = msg[0]
                if cmd == "notify":
                    self.engine.notify(msg[1])
                elif cmd == "call":
                    getattr(self.engine, msg[1])(*msg[2:])
                elif cmd == "visible":
                    self.user_paused = not msg[1]
                    self.apply_visibility()
                elif cmd == "stop":
                    self.stopping = True
            except Exception:
                log_error("overlay cmd %r" % (msg,))

    def apply_visibility(self):
        want = self.active
        if want != self.shown:
            self.shown = want
            self.engine.visible = want
            if want:
                self.root.deiconify()
                self.root.attributes("-topmost", True)
            else:
                self.root.withdraw()

    def check_pause(self, now):
        if now - self.last_check < 0.4:
            return
        self.last_check = now
        auto = False
        if self.cfg["pause_fullscreen"]:
            if now - self.last_mons > 3.0 or not self.mon_rects:
                self.last_mons = now
                self.mon_rects = [m["mon"] for m in get_monitors()]
            auto = fullscreen_foreground(self.mon_rects)
        if auto != self.auto_paused:
            self.auto_paused = auto
            self.apply_visibility()

    def fast(self):
        delay = 60
        try:
            self.drain()
            if self.stopping:
                self.root.quit()
                return
            now = time.time()
            self.check_pause(now)
            if self.active:
                self.engine.scene_tick(now)
                if now < self.engine.fast_until:
                    delay = 28
            else:
                delay = 150
        except Exception:
            log_error("overlay fast")
        self.root.after(delay, self.fast)

    def slow(self):
        try:
            if self.active:
                self.engine.tick(time.time())
        except Exception:
            log_error("overlay slow")
        fps = self.cfg["fps"]
        if self.cfg["perf_mode"] == "Экономия":
            fps = min(fps, 25)
        self.root.after(max(8, int(1000 / max(10, fps))) if self.active else 150, self.slow)


# ---------------------------------------------------------------- Интерфейс (тактильные кнопки + анимации)
THEMES = {
    "Ночной океан": {"bg": "#0B1320", "side": "#080E18", "card": "#111C2E", "card2": "#182740",
                     "fg": "#EDF4FF", "muted": "#879BB8", "accent": "#38BDF8", "accent2": "#0EA5E9",
                     "line": "#1E304D", "track": "#273D61", "on_acc": "#051320"},
    "Полночный фиолет": {"bg": "#110F24", "side": "#0B091A", "card": "#191636", "card2": "#24204D",
                         "fg": "#F3F1FF", "muted": "#9993C4", "accent": "#8B5CF6", "accent2": "#6D28D9",
                         "line": "#2C275C", "track": "#383270", "on_acc": "#FFFFFF"},
    "Графит": {"bg": "#14161A", "side": "#0E1013", "card": "#1C1F26", "card2": "#262A33",
               "fg": "#ECEEF2", "muted": "#8B919E", "accent": "#10B981", "accent2": "#059669",
               "line": "#2B303B", "track": "#363C4A", "on_acc": "#041710"},
    "Светлая": {"bg": "#F2F4F8", "side": "#FFFFFF", "card": "#FFFFFF", "card2": "#E9EDF5",
                "fg": "#181B24", "muted": "#666D80", "accent": "#2563EB", "accent2": "#1D4ED8",
                "line": "#DCE1EC", "track": "#C8D0E0", "on_acc": "#FFFFFF"},
}
ACCENTS = {"Небесный": "#38BDF8", "Фиолетовый": "#8B5CF6", "Изумрудный": "#10B981",
           "Янтарный": "#F59E0B", "Коралловый": "#F43F5E"}
FONT_SCALE = {"Мелкий": 0.9, "Обычный": 1.0, "Крупный": 1.15}


def make_theme(cfg):
    th = dict(THEMES.get(cfg["ui_theme"], THEMES["Ночной океан"]))
    acc = ACCENTS.get(cfg["ui_accent"])
    if acc:
        th["accent"] = acc
        th["accent2"] = blend(acc, 0.82)
    th["font_k"] = FONT_SCALE.get(cfg["ui_font"], 1.0)
    return th


class TactileButton(tk.Canvas):
    """Кнопка с физическим проседанием при нажатии и плавным возвратом."""

    def __init__(self, parent, th, k, text, command, accent=False, width=None, height=36):
        self.th, self.k, self.text, self.cmd = th, k, text, command
        self.accent = accent
        self.h = int(height * k)
        w = int(width * k) if width else max(int(120 * k), int((len(text) * 9 + 34) * k))
        self.w = w
        super().__init__(parent, width=w, height=self.h + int(4 * k),
                         bg=parent.cget("bg"), highlightthickness=0, bd=0, cursor="hand2")
        self.hover = False
        self.pressed = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._down)
        self.bind("<ButtonRelease-1>", self._up)
        self.bind("<Configure>", self._resize)
        self.draw()

    def _resize(self, e):
        if e.width > 10 and e.width != self.w:
            self.w = e.width
            self.draw()

    def _enter(self, _e):
        self.hover = True
        self.draw()

    def _leave(self, _e):
        self.hover = False
        self.pressed = False
        self.draw()

    def _down(self, _e):
        self.pressed = True
        self.draw()

    def _up(self, e):
        was = self.pressed
        self.pressed = False
        self.draw()
        if was and 0 <= e.x <= self.w and 0 <= e.y <= self.h + 4 * self.k:
            self.cmd()

    def round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1
        ]
        return self.create_polygon(*pts, smooth=True, **kw)

    def draw(self):
        self.delete("all")
        th, k = self.th, self.k
        w, h = self.w, self.h
        sink = int(2.5 * k) if self.pressed else 0
        r = int(9 * k)
        base = th["accent"] if self.accent else th["card2"]
        if self.pressed:
            fill = blend(base, 0.86)
        elif self.hover:
            fill = mix(base, "#FFFFFF", 0.10)
        else:
            fill = base
        shadow = blend(base, 0.45) if self.accent else th["line"]
        # Нижняя объёмная кромка
        if not self.pressed:
            self.round_rect(1, int(3 * k), w - 1, h + int(3 * k), r, fill=shadow, outline="")
        self.round_rect(1, 1 + sink, w - 1, h + sink, r, fill=fill,
                        outline="" if self.accent else th["line"])
        fg = th["on_acc"] if self.accent else th["fg"]
        self.create_text(w / 2, h / 2 + sink, text=self.text, fill=fg,
                         font=("Segoe UI", max(8, int(round(9.5 * th["font_k"]))), "bold"))


class Toggle(tk.Canvas):
    def __init__(self, parent, th, k, value, command):
        super().__init__(parent, width=int(48 * k), height=int(26 * k), bg=th["card"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.th, self.k, self.v, self.cmd = th, k, bool(value), command
        self.pressed = False
        self.bind("<ButtonPress-1>", self._down)
        self.bind("<ButtonRelease-1>", self._up)
        self.draw()

    def draw(self):
        k, th = self.k, self.th
        self.delete("all")
        col = th["accent"] if self.v else th["track"]
        self.create_oval(1 * k, 1 * k, 25 * k, 25 * k, fill=col, outline=col)
        self.create_oval(23 * k, 1 * k, 47 * k, 25 * k, fill=col, outline=col)
        self.create_rectangle(13 * k, 1 * k, 35 * k, 25 * k, fill=col, outline=col)
        x = 35 if self.v else 13
        stretch = 2.0 if self.pressed else 0.0
        self.create_oval((x - 10 - stretch) * k, 3 * k, (x + 10 + stretch) * k, 23 * k,
                         fill="#FFFFFF", outline="")

    def _down(self, _e):
        self.pressed = True
        self.draw()

    def _up(self, _e):
        self.pressed = False
        self.set(not self.v)
        self.cmd(self.v)

    def set(self, v):
        self.v = bool(v)
        self.draw()


class Slider(tk.Canvas):
    def __init__(self, parent, th, k, lo, hi, step, value, command, width=210):
        self.k, self.w = k, int(width * k)
        super().__init__(parent, width=self.w + int(58 * k), height=int(28 * k), bg=th["card"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.th, self.lo, self.hi, self.step, self.cmd = th, lo, hi, step, command
        self.is_int = isinstance(step, int)
        self.v = value
        self.dragging = False
        self.bind("<ButtonPress-1>", self._down)
        self.bind("<B1-Motion>", self._press)
        self.bind("<ButtonRelease-1>", self._up)
        self.draw()

    def _val(self, x):
        pad = 10 * self.k
        f = max(0.0, min(1.0, (x - pad) / float(self.w - 2 * pad)))
        v = self.lo + f * (self.hi - self.lo)
        v = round(v / self.step) * self.step
        v = max(self.lo, min(self.hi, v))
        return int(round(v)) if self.is_int else round(v, 2)

    def _down(self, e):
        self.dragging = True
        self._press(e)

    def _up(self, _e):
        self.dragging = False
        self.draw()

    def _press(self, e):
        v = self._val(e.x)
        if v != self.v:
            self.v = v
            self.draw()
            self.cmd(v)

    def set(self, v):
        self.v = v
        self.draw()

    def draw(self):
        k, th = self.k, self.th
        self.delete("all")
        pad = 10 * k
        y = 14 * k
        x0, x1 = pad, self.w - pad
        span = float(self.hi - self.lo) or 1.0
        fx = x0 + (float(self.v) - self.lo) / span * (x1 - x0)
        self.create_line(x0, y, x1, y, width=int(6 * k), fill=th["track"], capstyle="round")
        self.create_line(x0, y, max(x0, fx), y, width=int(6 * k), fill=th["accent"], capstyle="round")
        rr = (9.5 if self.dragging else 8.0) * k
        self.create_oval(fx - rr, y - rr, fx + rr, y + rr, fill="#FFFFFF", outline=th["accent"], width=2)
        self.create_text(self.w + 6 * k, y, text="%g" % round(float(self.v), 2), anchor="w",
                         fill=th["accent"], font=("Segoe UI", int(10 * th["font_k"]), "bold"))


class Drop:
    def __init__(self, parent, values, value, command, font, width=21):
        self.values = list(values)
        self.var = tk.StringVar(value=value)
        self.w = ttk.Combobox(parent, textvariable=self.var, values=values, state="readonly",
                              width=width, font=font)
        self.w.bind("<<ComboboxSelected>>", lambda e: command(self.var.get()))

    def pack(self, **kw):
        self.w.pack(**kw)

    def set(self, v):
        self.var.set(v)


class Swatch:
    def __init__(self, parent, value, command):
        self.cmd, self.v = command, value
        self.b = tk.Button(parent, width=5, relief="flat", bd=0, cursor="hand2", bg=value,
                           activebackground=value, command=self._pick)

    def _pick(self):
        c = colorchooser.askcolor(self.v)[1]
        if c:
            self.set(c)
            self.cmd(c)

    def pack(self, **kw):
        self.b.pack(**kw)

    def set(self, v):
        self.v = v
        self.b.configure(bg=v, activebackground=v)


class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
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


# ---------------------------------------------------------------- Анимированная иконка погоды для карточки дня
class WeatherAnimIcon(tk.Canvas):
    def __init__(self, parent, bg, kind, color, size=56):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
        self.kind = kind
        self.color = color
        self.S = size
        self.t = random.uniform(0, 10)
        self.drops = [(random.uniform(0.22, 0.78) * size, random.uniform(0.55, 0.92) * size) for _ in range(5)]

    def step(self):
        self.t += 0.14
        self.delete("all")
        S = self.S
        cx, cy = S * 0.5, S * 0.48
        k = self.kind

        if k in ("sun", "sun_cloud"):
            sx, sy = (cx, cy) if k == "sun" else (S * 0.36, S * 0.36)
            r = S * (0.21 if k == "sun" else 0.15)
            for i in range(10):
                a = self.t * 0.4 + i * math.tau / 10.0
                r1 = r * 1.25
                r2 = r * (1.72 + 0.18 * math.sin(self.t * 2 + i))
                self.create_line(sx + math.cos(a) * r1, sy + math.sin(a) * r1,
                                 sx + math.cos(a) * r2, sy + math.sin(a) * r2,
                                 fill="#FFB300", width=2, capstyle="round")
            self.create_oval(sx - r, sy - r, sx + r, sy + r, fill="#FFC107", outline="#FFE082", width=1)

        if k in ("sun_cloud", "cloud", "rain", "snow", "snow_rain", "storm"):
            drift = math.sin(self.t * 0.6) * 2.2
            oy = S * (0.08 if k in ("rain", "snow", "snow_rain", "storm") else 0.04)
            col = "#E2E8F0" if k in ("sun_cloud", "snow") else ("#64748B" if k == "storm" else "#94A3B8")
            self.create_oval(S * 0.18 + drift, S * 0.34 - oy, S * 0.52 + drift, S * 0.62 - oy, fill=col, outline="")
            self.create_oval(S * 0.34 + drift, S * 0.24 - oy, S * 0.70 + drift, S * 0.58 - oy, fill=col, outline="")
            self.create_oval(S * 0.52 + drift, S * 0.34 - oy, S * 0.84 + drift, S * 0.62 - oy, fill=col, outline="")
            self.create_rectangle(S * 0.28 + drift, S * 0.44 - oy, S * 0.74 + drift, S * 0.62 - oy, fill=col, outline="")

        if k in ("rain", "snow_rain", "storm"):
            for idx, (dx, dy) in enumerate(self.drops):
                ny = dy + 2.6
                if ny > S * 0.94:
                    ny = S * 0.56
                self.drops[idx] = (dx, ny)
                self.create_line(dx, ny, dx - 2.5, ny + 6, fill="#38BDF8", width=1.8, capstyle="round")

        if k in ("snow", "snow_rain"):
            for idx, (dx, dy) in enumerate(self.drops):
                ny = dy + 1.4
                nx = dx + math.sin(self.t + idx) * 0.6
                if ny > S * 0.94:
                    ny = S * 0.56
                self.drops[idx] = (nx, ny)
                self.create_oval(nx - 2, ny - 2, nx + 2, ny + 2, fill="#E0F2FE", outline="")

        if k == "storm":
            if int(self.t * 2) % 5 == 0:
                self.create_polygon(S * 0.48, S * 0.54, S * 0.40, S * 0.72, S * 0.49, S * 0.72,
                                    S * 0.43, S * 0.92, S * 0.58, S * 0.68, S * 0.49, S * 0.68,
                                    fill="#FDE047", outline="")


PAGES = [
    ("home", "⌂", "Режимы", "Готовые атмосферы в один клик"),
    ("forecast", "⛅", "Погода", "Прогноз на неделю по вашему городу и синхронизация с экраном"),
    ("fall", "❄", "Осадки", "Снег, листья, дождь, звёзды и их количество"),
    ("weather", "≋", "Ветер и метель", "Сила ветра, порывы и снежная буря"),
    ("garland", "✦", "Гирлянда", "Гирлянда вдоль верхнего края экрана"),
    ("snow", "☃", "Сугробы и снеговики", "Накопление снега на окнах и лепка снеговиков"),
    ("sky", "☾", "Небо и природа", "Сияние, звёзды, солнце, луна, облака и метеоры"),
    ("party", "★", "Праздник", "Дед Мороз, ёлка, салют и отсчёт до даты"),
    ("cursor", "☝", "Курсор", "Взаимодействие курсора со снегом и шлейф"),
    ("app", "⚙", "Приложение", "Автозапуск, производительность и тема"),
]

SEARCH_ITEMS = [
    ("Прогноз погоды на неделю", "forecast", "Прогноз на 7 дней", "погода город неделя дождь снег температура прогноз"),
    ("Режимы и сезоны", "home", "Готовые режимы", "зима осень весна лето новый год вечеринка пресет"),
    ("Снег и снежинки", "fall", "Снег", "снег снегопад снежинка хлопья кристаллы"),
    ("Количество и скорость снега", "fall", "Количество и скорость", "количество плотность скорость размер много снега"),
    ("Листья, дождь и звёзды", "fall", "Свой набор", "листья осень конфетти дождь пузыри сердечки звёзды"),
    ("Ветер", "weather", "Ветер", "ветер порывы направление"),
    ("Метель", "weather", "Метель", "метель буран снежная буря"),
    ("Гирлянда сверху экрана", "garland", "Гирлянда на верхнем крае экрана", "гирлянда лампочки верх экран монитор"),
    ("Вид гирлянды", "garland", "Вид", "гирлянда сосульки шарики звезды фонарики цветы флажки"),
    ("Сугробы и снеговики", "snow", "Сугробы", "сугроб снег снеговик уборка машина"),
    ("Северное сияние", "sky", "Северное сияние", "сияние аврора зелёное бирюзовое"),
    ("Звёзды и падающие звёзды", "sky", "Звёздное небо", "звезды звёзды небо мерцание падающие"),
    ("Солнце и луна", "sky", "Солнце и луна", "солнце луна фаза день ночь"),
    ("Облака", "sky", "Облака", "облака пасмурно закат большие"),
    ("Метеоры", "sky", "Метеоры", "метеор болид комета"),
    ("Дед Мороз", "party", "Дед Мороз", "дед мороз сани подарки"),
    ("Ёлка и фейерверки", "party", "Новогодняя ёлка", "ёлка елка салют фейерверк отсчёт"),
    ("Курсор и след", "cursor", "Курсор и снег", "курсор мышь ветер сметать след искры"),
    ("Производительность и тема", "app", "Производительность", "производительность fps кадры тема автозапуск"),
]


class App:
    def __init__(self, root, cfg, overlay, hidden=False):
        self.root, self.cfg, self.ov = root, cfg, overlay
        self.k = max(1.0, root.winfo_fpixels("1i") / 96.0)
        self.effects_on = True
        self.ctl, self.page_frames = {}, {}
        self.cur_page = "home"
        self.search_matches = []
        self.search_placeholder = True
        self.show_flag = threading.Event()
        self.tray = None
        self._dirty, self._last_change = False, 0.0
        self._flash_until = 0.0
        self.weather_data = None
        self.weather_loading = False
        self.weather_error = ""
        self.weather_icons = []
        root.title(APP_TITLE)
        try:
            self.app_icon = tk.PhotoImage(file=resource_path("AuraDesk.png"))
            root.iconphoto(True, self.app_icon)
        except Exception:
            self.app_icon = None
        root.geometry("%dx%d" % (int(1080 * self.k), int(760 * self.k)))
        root.minsize(int(940 * self.k), int(640 * self.k))
        self.build_ui_safe()
        try:
            self.tray = Tray("AuraDesk — атмосфера рабочего стола", self.tray_cmd, self.tray_state)
        except Exception:
            log_error("tray")
            self.tray = None
        try:
            start_show_listener(self.show_flag)
        except Exception:
            log_error("show listener")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        if hidden and self.tray:
            self.hide()
        elif hidden:
            root.iconify()
        if self.cfg.get("weather_city"):
            self.load_weather_async(self.cfg["weather_city"])
        self.poll()
        self.animate_widgets()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except Exception:
            pass

    def hide(self):
        self.root.withdraw()

    def on_close(self):
        if self.cfg["close_to_tray"]:
            if self.tray:
                self.hide()
            else:
                self.root.iconify()
        else:
            self.quit()

    def tray_state(self):
        return {"on": self.effects_on, "auto": is_autostart()}

    def tray_cmd(self, cmd):
        fn = {1: self.show, 2: lambda: self.set_effects(not self.effects_on, True),
              3: lambda: self.set_autostart_ui(not is_autostart(), True), 9: self.quit}.get(cmd)
        if fn:
            self.root.after(10, fn)

    def quit(self):
        save_cfg(self.cfg)
        if self.tray:
            self.tray.remove()
        self.ov.send("stop")
        time.sleep(0.15)
        os._exit(0)

    def set_effects(self, on, from_menu=False):
        self.effects_on = bool(on)
        self.ov.send("visible", self.effects_on)
        t = self.ctl.get("_effects")
        if t:
            t.set(self.effects_on)

    def set_autostart_ui(self, on, from_menu=False):
        ok = set_autostart(on)
        t = self.ctl.get("_autostart")
        if t:
            t.set(is_autostart() if not ok else on)

    # ---- поиск
    def search_focus_in(self, _event=None):
        if self.search_placeholder:
            self.search_entry.delete(0, "end")
            self.search_entry.configure(fg=self.th["fg"])
            self.search_placeholder = False

    def search_focus_out(self, _event=None):
        if not self.search_entry.get().strip():
            self.search_results_box.pack_forget()
            self.search_results_title.pack_forget()
            self.search_clear_btn.pack_forget()
            self.search_matches = []
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, "Поиск по настройкам...")
            self.search_entry.configure(fg=self.th["muted"])
            self.search_placeholder = True

    def search_update(self, event=None):
        if event and event.keysym in ("Return", "Down", "Up", "Escape"):
            return
        if self.search_placeholder:
            return
        query = self.search_entry.get().strip().casefold()
        self.search_results_box.delete(0, "end")
        if not query:
            self.search_results_box.pack_forget()
            self.search_results_title.pack_forget()
            self.search_clear_btn.pack_forget()
            self.search_matches = []
            return
        self.search_clear_btn.pack(side="right", padx=(0, 7))
        matches = [item for item in SEARCH_ITEMS
                   if query in item[0].casefold() or query in item[3].casefold()]
        matches.sort(key=lambda item: (
            0 if item[0].casefold().startswith(query) else
            1 if query in item[0].casefold() else 2,
            len(item[0])))
        self.search_matches = matches[:6]
        if not self.search_matches:
            self.search_results_box.insert("end", "Ничего не найдено")
            self.search_results_box.configure(height=1, fg=self.th["muted"])
            self.search_results_title.configure(text="НЕТ СОВПАДЕНИЙ")
        else:
            self.search_results_box.configure(height=len(self.search_matches), fg=self.th["fg"])
            for item in self.search_matches:
                self.search_results_box.insert("end", item[0])
            self.search_results_title.configure(text="РЕЗУЛЬТАТЫ · ENTER")
        self.search_results_title.pack(fill="x", padx=3, pady=(6, 2))
        self.search_results_box.pack(fill="x", pady=(3, 0))

    def search_clear(self, _event=None):
        self.search_entry.delete(0, "end")
        self.search_entry.focus_set()
        self.search_update()
        return "break"

    def search_focus_results(self, _event=None):
        if self.search_matches:
            self.search_results_box.focus_set()
            self.search_results_box.selection_clear(0, "end")
            self.search_results_box.selection_set(0)
            self.search_results_box.activate(0)
        return "break"

    def search_return_to_entry(self, _event=None):
        self.search_entry.focus_set()
        return "break"

    def search_choose_first(self, _event=None):
        if self.search_matches:
            self.search_open(self.search_matches[0])
        return "break"

    def search_choose(self, _event=None):
        selection = self.search_results_box.curselection()
        if selection and selection[0] < len(self.search_matches):
            self.search_open(self.search_matches[selection[0]])
        return "break"

    def search_open(self, item):
        _label, page_id, section, _terms = item
        self.search_matches = []
        self.search_results_box.pack_forget()
        self.search_results_title.pack_forget()
        self.search_clear_btn.pack_forget()
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, "Поиск по настройкам...")
        self.search_entry.configure(fg=self.th["muted"])
        self.search_placeholder = True
        self.show_page(page_id)
        self.root.after_idle(lambda: self.scroll_to_section(page_id, section))

    def scroll_to_section(self, page_id, section):
        sf = self.page_frames.get(page_id)
        if not sf:
            return
        sf.update_idletasks()
        for outer in sf.inner.winfo_children():
            children = outer.winfo_children()
            if not children or not isinstance(children[0], tk.Label):
                continue
            if children[0].cget("text").casefold() != section.casefold():
                continue
            region = sf.canvas.bbox("all")
            total = max(1, (region[3] - region[1]) if region else 1)
            sf.canvas.yview_moveto(max(0.0, min(1.0, outer.winfo_y() / total)))
            return

    def animate_widgets(self):
        if self.cur_page == "forecast" and self.weather_icons:
            for ic in list(self.weather_icons):
                try:
                    if ic.winfo_exists():
                        ic.step()
                except Exception:
                    pass
        self.root.after(75, self.animate_widgets)

    def poll(self):
        try:
            if self.show_flag.is_set():
                self.show_flag.clear()
                self.show()
            if self._dirty and time.time() - self._last_change > 1.5:
                save_cfg(self.cfg)
                self._dirty = False
            chip = getattr(self, "chip", None)
            if chip is not None:
                eng = self.ov.engine
                season = eng.season if eng else current_season(self.cfg)
                txt = SEASON_TITLE[season]
                if time.time() < self._flash_until:
                    txt = self._flash_text
                elif self.ov.auto_paused:
                    txt = "⏸  Пауза: полный экран"
                elif not self.effects_on:
                    txt = "⏸  Эффекты выключены"
                chip.config(text=txt)
        except Exception:
            log_error("poll")
        self.root.after(400, self.poll)

    # ---- настройки
    def set_cfg(self, key, value):
        self.cfg[key] = value
        self.ov.send("notify", key)
        self._dirty, self._last_change = True, time.time()
        if key in ("ui_theme", "ui_accent", "ui_font"):
            self.root.after(150, self.rebuild_ui)

    def apply_values(self, values):
        rebuild = False
        for k, v in values.items():
            if self.cfg.get(k) != v:
                self.cfg[k] = v
                self.ov.send("notify", k)
                c = self.ctl.get(k)
                if c:
                    c.set(v)
                if k in ("ui_theme", "ui_accent", "ui_font"):
                    rebuild = True
        self._dirty, self._last_change = True, time.time()
        if rebuild:
            self.root.after(150, self.rebuild_ui)

    def apply_preset(self, pid):
        for (i, icon, name, desc, over) in PRESETS:
            if i == pid:
                vals = {k: v for k, v in DEFAULTS.items() if k not in APP_KEYS}
                vals.update(over)
                self.apply_values(vals)
                self.flash("%s  Режим «%s» включён" % (icon, name))

    def flash(self, text):
        self._flash_text, self._flash_until = text, time.time() + 3.0

    def reset_all(self):
        from tkinter import messagebox
        if messagebox.askyesno("Сброс", "Вернуть все настройки к значениям по умолчанию?"):
            self.apply_values(dict(DEFAULTS))
            self.rebuild_ui()

    # ---- погода на неделю
    def load_weather_async(self, city):
        city = (city or "").strip()
        if not city or self.weather_loading:
            return
        self.cfg["weather_city"] = city
        self._dirty, self._last_change = True, time.time()
        self.weather_loading = True
        self.weather_error = ""
        if "forecast" in self.page_frames:
            self.refresh_forecast_page()

        def worker():
            try:
                data = fetch_city_forecast(city)
                self.root.after(0, lambda: self._on_weather_ok(data))
            except Exception as exc:
                msg = str(exc) or "Не удалось получить прогноз"
                self.root.after(0, lambda: self._on_weather_err(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_weather_ok(self, data):
        self.weather_loading = False
        self.weather_data = data
        self.weather_error = ""
        if "forecast" in self.page_frames:
            self.refresh_forecast_page()

    def _on_weather_err(self, msg):
        self.weather_loading = False
        self.weather_error = msg
        if "forecast" in self.page_frames:
            self.refresh_forecast_page()

    def refresh_forecast_page(self):
        sf = self.page_frames.get("forecast")
        if not sf:
            return
        for w in sf.inner.winfo_children():
            w.destroy()
        self.weather_icons = []
        self.page_forecast(sf.inner)
        tk.Frame(sf.inner, bg=self.th["bg"], height=24).pack()

    def sync_weather_to_desktop(self):
        if not self.weather_data:
            return
        d = self.weather_data
        kind = d["kind"]
        wind_val = min(4.5, round(d["wind"] / 8.0, 1))
        vals = {k: v for k, v in DEFAULTS.items() if k not in APP_KEYS}
        vals["wind_power"] = max(0.3, wind_val)
        if kind == "snow":
            vals.update({"season": "Зима", "fall_mode": "По сезону", "density": 320,
                         "clouds_enabled": True, "clouds_tint": "Серые (пасмурно)",
                         "clouds_count": 9, "pile_enabled": True})
        elif kind == "snow_rain":
            vals.update({"fall_mode": "Свой набор", "k_snow": True, "k_rain": True, "density": 300,
                         "clouds_enabled": True, "clouds_tint": "Серые (пасмурно)", "clouds_count": 10})
        elif kind in ("rain", "storm"):
            vals.update({"fall_mode": "Свой набор", "k_snow": False, "k_rain": True, "density": 360,
                         "clouds_enabled": True, "clouds_tint": "Серые (пасмурно)", "clouds_count": 11,
                         "gust_power": 1.3, "pile_enabled": False})
        elif kind == "sun":
            vals.update({"fall_mode": "Свой набор", "k_snow": False, "k_firefly": True, "density": 70,
                         "sky_body": "Солнце", "clouds_enabled": True, "clouds_tint": "Белые",
                         "clouds_count": 4, "pile_enabled": False})
        elif kind == "sun_cloud":
            vals.update({"fall_mode": "Свой набор", "k_snow": False, "k_spring": True, "density": 90,
                         "sky_body": "Солнце", "clouds_enabled": True, "clouds_tint": "Белые",
                         "clouds_count": 7, "pile_enabled": False})
        else:
            vals.update({"fall_mode": "Свой набор", "k_snow": False, "k_leaf": True, "density": 110,
                         "clouds_enabled": True, "clouds_tint": "Серые (пасмурно)",
                         "clouds_count": 10, "pile_enabled": False})
        self.apply_values(vals)
        self.flash(f"⛅  Погода «{d['city']}: {d['label']}» применена")

    # ---- построение интерфейса
    def F(self, size, bold=False, symbol=False):
        return ("Segoe UI Symbol" if symbol else "Segoe UI", max(7, int(round(size * self.th["font_k"]))),
                "bold" if bold else "normal")

    def build_ui_safe(self):
        try:
            self.build_ui()
        except Exception:
            log_error("build_ui")
            for w in self.root.winfo_children():
                w.destroy()
            tk.Label(self.root, text="Не удалось построить интерфейс.\nЭффекты продолжают работать.\n\n"
                                     "Журнал: " + LOG_PATH, justify="left", padx=20, pady=20).pack()
            tk.Button(self.root, text="Выход", command=self.quit).pack(pady=10)

    def rebuild_ui(self):
        keep = self.cur_page
        for w in self.root.winfo_children():
            w.destroy()
        self.ctl, self.page_frames, self.weather_icons = {}, {}, []
        self.build_ui_safe()
        try:
            self.show_page(keep)
        except Exception:
            log_error("rebuild show_page")

    def style_ttk(self):
        th = self.th
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("TCombobox", fieldbackground=th["card2"], background=th["card2"], foreground=th["fg"],
                     arrowcolor=th["fg"], bordercolor=th["line"], lightcolor=th["card2"],
                     darkcolor=th["card2"], padding=5)
        st.map("TCombobox", fieldbackground=[("readonly", th["card2"])], foreground=[("readonly", th["fg"])],
               selectbackground=[("readonly", th["card2"])], selectforeground=[("readonly", th["fg"])])
        st.configure("Vertical.TScrollbar", background=th["card2"], troughcolor=th["bg"],
                     bordercolor=th["bg"], arrowcolor=th["fg"], lightcolor=th["card2"], darkcolor=th["card2"])
        self.root.option_add("*TCombobox*Listbox.background", th["card2"])
        self.root.option_add("*TCombobox*Listbox.foreground", th["fg"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", th["accent"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", th["on_acc"])

    def build_ui(self):
        self.th = th = make_theme(self.cfg)
        k = self.k
        self.root.configure(bg=th["bg"])
        self.style_ttk()
        shell = tk.Frame(self.root, bg=th["bg"])
        shell.pack(fill="both", expand=True)
        side = tk.Frame(shell, bg=th["side"], width=int(232 * k))
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        logo = tk.Frame(side, bg=th["side"])
        logo.pack(fill="x", padx=18, pady=(20, 14))
        badge = tk.Canvas(logo, width=int(38 * k), height=int(38 * k), bg=th["side"], highlightthickness=0)
        badge.pack(side="left")
        badge.create_oval(2, 2, 36 * k, 36 * k, fill=th["accent"], outline="")
        badge.create_text(19 * k, 19 * k, text="✦", fill=th["on_acc"], font=self.F(16, True, True))
        tf = tk.Frame(logo, bg=th["side"])
        tf.pack(side="left", padx=10)
        tk.Label(tf, text="AuraDesk", bg=th["side"], fg=th["fg"], font=self.F(14, True)).pack(anchor="w")
        tk.Label(tf, text="Атмосфера экрана", bg=th["side"], fg=th["muted"], font=self.F(9)).pack(anchor="w")

        search_wrap = tk.Frame(side, bg=th["side"])
        search_wrap.pack(fill="x", padx=12, pady=(0, 8))
        search_box = tk.Frame(search_wrap, bg=th["card2"], highlightbackground=th["line"],
                              highlightthickness=1)
        search_box.pack(fill="x")
        tk.Label(search_box, text="⌕", bg=th["card2"], fg=th["muted"],
                 font=self.F(11, False, True)).pack(side="left", padx=(9, 4), pady=5)
        self.search_entry = tk.Entry(search_box, bg=th["card2"], fg=th["muted"],
                                     insertbackground=th["fg"], relief="flat", bd=0,
                                     font=self.F(9.5))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=5)
        self.search_entry.insert(0, "Поиск по настройкам...")
        self.search_placeholder = True
        self.search_clear_btn = tk.Label(search_box, text="✕", bg=th["card2"], fg=th["muted"],
                                         font=self.F(9, True), cursor="hand2")
        self.search_clear_btn.bind("<Button-1>", self.search_clear)
        self.search_entry.bind("<FocusIn>", self.search_focus_in)
        self.search_entry.bind("<FocusOut>", self.search_focus_out)
        self.search_entry.bind("<KeyRelease>", self.search_update)
        self.search_entry.bind("<Return>", self.search_choose_first)
        self.search_entry.bind("<Down>", self.search_focus_results)
        self.search_entry.bind("<Escape>", self.search_clear)
        self.search_results_title = tk.Label(search_wrap, text="", bg=th["side"], fg=th["muted"],
                                             font=self.F(7.5, True), anchor="w")
        self.search_results_box = tk.Listbox(search_wrap, bg=th["card2"], fg=th["fg"],
                                             selectbackground=th["accent"],
                                             selectforeground=th["on_acc"],
                                             activestyle="none", relief="flat", bd=0,
                                             highlightbackground=th["line"],
                                             highlightthickness=1,
                                             font=self.F(9), height=1)
        self.search_results_box.bind("<ButtonRelease-1>", self.search_choose)
        self.search_results_box.bind("<Return>", self.search_choose)
        self.search_results_box.bind("<Up>", lambda e: self.search_return_to_entry()
                                     if self.search_results_box.curselection() == (0,) else None)
        self.search_results_box.bind("<Escape>", self.search_clear)

        self.nav_btns = {}
        for pid, icon, title, _sub in PAGES:
            row = tk.Frame(side, bg=th["side"], cursor="hand2")
            row.pack(fill="x", padx=10, pady=2)
            bar = tk.Frame(row, bg=th["side"], width=int(3 * k))
            bar.pack(side="left", fill="y", pady=6)
            ic = tk.Label(row, text=icon, bg=th["side"], fg=th["muted"], font=self.F(12, False, True), width=2)
            ic.pack(side="left", padx=(6, 4), pady=7)
            lb = tk.Label(row, text=title, bg=th["side"], fg=th["muted"], font=self.F(10), anchor="w")
            lb.pack(side="left", fill="x", expand=True)
            for w in (row, ic, lb):
                w.bind("<Button-1>", lambda e, p=pid: self.show_page(p))
            self.nav_btns[pid] = (row, bar, ic, lb)

        tk.Frame(side, bg=th["line"], height=1).pack(fill="x", padx=14, pady=(10, 8))
        foot = tk.Frame(side, bg=th["side"])
        foot.pack(fill="x", padx=14, pady=(0, 14), side="bottom")
        r = tk.Frame(foot, bg=th["side"])
        r.pack(fill="x", pady=4)
        tk.Label(r, text="Эффекты", bg=th["side"], fg=th["fg"], font=self.F(10, True)).pack(side="left")
        t = Toggle(r, th, k, self.effects_on, self.set_effects)
        t.configure(bg=th["side"])
        t.pack(side="right")
        self.ctl["_effects"] = t
        b = TactileButton(foot, th, k, "Скрыть в трей" if self.tray else "Свернуть",
                          self.hide if self.tray else self.root.iconify, accent=False, width=190, height=32)
        b.pack(fill="x", pady=(8, 0))

        main = tk.Frame(shell, bg=th["bg"])
        main.pack(side="left", fill="both", expand=True)
        head = tk.Frame(main, bg=th["bg"])
        head.pack(fill="x", padx=28, pady=(20, 10))
        ht = tk.Frame(head, bg=th["bg"])
        ht.pack(side="left", fill="x", expand=True)
        self.h_title = tk.Label(ht, text="", bg=th["bg"], fg=th["fg"], font=self.F(19, True), anchor="w")
        self.h_title.pack(anchor="w")
        self.h_sub = tk.Label(ht, text="", bg=th["bg"], fg=th["muted"], font=self.F(10), anchor="w")
        self.h_sub.pack(anchor="w", pady=(2, 0))
        self.chip = tk.Label(head, text=SEASON_TITLE[current_season(self.cfg)], bg=th["card"],
                             fg=th["accent"], font=self.F(10, True, True), padx=14, pady=6)
        self.chip.pack(side="right")

        self.stack = tk.Frame(main, bg=th["bg"])
        self.stack.pack(fill="both", expand=True)
        for pid, _i, _t, _s in PAGES:
            sf = ScrollFrame(self.stack, th["bg"])
            self.page_frames[pid] = sf
            getattr(self, "page_" + pid)(sf.inner)
            tk.Frame(sf.inner, bg=th["bg"], height=24).pack()
        self.show_page("home")

    def show_page(self, pid):
        self.cur_page = pid
        th = self.th
        for k2, (row, bar, ic, lb) in self.nav_btns.items():
            act = k2 == pid
            bg = th["card2"] if act else th["side"]
            fg = th["fg"] if act else th["muted"]
            row.configure(bg=bg)
            bar.configure(bg=th["accent"] if act else bg)
            ic.configure(bg=bg, fg=th["accent"] if act else fg)
            lb.configure(bg=bg, fg=fg, font=self.F(10, act))
        for k2, sf in self.page_frames.items():
            if k2 == pid:
                sf.pack(fill="both", expand=True)
                sf.canvas.yview_moveto(0)
            else:
                sf.pack_forget()
        for p, _i, title, sub in PAGES:
            if p == pid:
                self.h_title.config(text=title)
                self.h_sub.config(text=sub)
                break

    # ---- строители строк настроек
    def section(self, parent, title):
        th = self.th
        outer = tk.Frame(parent, bg=th["bg"])
        outer.pack(fill="x", padx=28, pady=(14, 0))
        tk.Label(outer, text=title.upper(), bg=th["bg"], fg=th["muted"],
                 font=self.F(9, True), anchor="w").pack(anchor="w", pady=(0, 6))
        card = tk.Frame(outer, bg=th["card"], highlightbackground=th["line"], highlightthickness=1)
        card.pack(fill="x")
        card._n = 0
        return card

    def _row(self, card, label, desc=None):
        th = self.th
        if card._n > 0:
            tk.Frame(card, bg=th["line"], height=1).pack(fill="x", padx=16)
        card._n += 1
        row = tk.Frame(card, bg=th["card"])
        row.pack(fill="x", padx=18, pady=12)
        left = tk.Frame(row, bg=th["card"])
        left.pack(side="left", fill="x", expand=True, padx=(0, 14))
        tk.Label(left, text=label, bg=th["card"], fg=th["fg"], font=self.F(10.5, True), anchor="w").pack(anchor="w")
        if desc:
            tk.Label(left, text=desc, bg=th["card"], fg=th["muted"], font=self.F(9),
                     anchor="w", wraplength=int(480 * self.k), justify="left").pack(anchor="w", pady=(2, 0))
        return row

    def toggle(self, card, key, label, desc=None, getter=None, setter=None):
        row = self._row(card, label, desc)
        v = getter() if getter else self.cfg[key]
        cb = setter if setter else (lambda val, k2=key: self.set_cfg(k2, val))
        t = Toggle(row, self.th, self.k, v, cb)
        t.pack(side="right")
        self.ctl[key] = t

    def slider(self, card, key, label, lo, hi, step=1, desc=None):
        row = self._row(card, label, desc)
        s = Slider(row, self.th, self.k, lo, hi, step, self.cfg[key],
                   lambda val, k2=key: self.set_cfg(k2, val))
        s.pack(side="right")
        self.ctl[key] = s

    def drop(self, card, key, label, values, desc=None):
        row = self._row(card, label, desc)
        d = Drop(row, values, self.cfg[key], lambda val, k2=key: self.set_cfg(k2, val), self.F(10))
        d.pack(side="right")
        self.ctl[key] = d

    def color(self, card, key, label, desc=None):
        row = self._row(card, label, desc)
        s = Swatch(row, self.cfg[key], lambda val, k2=key: self.set_cfg(k2, val))
        s.pack(side="right", ipady=3)
        self.ctl[key] = s

    def buttons(self, card, items):
        row = tk.Frame(card, bg=self.th["card"])
        row.pack(fill="x", padx=18, pady=12)
        for text, fn, acc in items:
            b = TactileButton(row, self.th, self.k, text, fn, accent=acc, height=34)
            b.pack(side="left", padx=(0, 10))

    # ---- страницы
    def page_home(self, p):
        th, k = self.th, self.k
        c = self.section(p, "Время года")
        self.drop(c, "season", "Сезон", ["Авто", "Зима", "Весна", "Лето", "Осень"],
                  "В режиме «Авто» время года определяется по календарю само.")
        self.drop(c, "fall_mode", "Что падает", ["По сезону", "Свой набор"],
                  "Свой набор позволяет смешивать любые частицы во вкладке «Осадки».")

        wrap = tk.Frame(p, bg=th["bg"])
        wrap.pack(fill="x", padx=28, pady=(16, 0))
        tk.Label(wrap, text="ГОТОВЫЕ РЕЖИМЫ", bg=th["bg"], fg=th["muted"],
                 font=self.F(9, True), anchor="w").pack(anchor="w", pady=(0, 8))
        grid = tk.Frame(wrap, bg=th["bg"])
        grid.pack(fill="x")
        for c2 in range(3):
            grid.grid_columnconfigure(c2, weight=1, uniform="pr")
        for idx, (pid, icon, name, desc, _ov) in enumerate(PRESETS):
            r, col = divmod(idx, 3)
            card = tk.Frame(grid, bg=th["card"], highlightbackground=th["line"],
                            highlightthickness=1, cursor="hand2")
            card.grid(row=r, column=col, sticky="nsew", padx=(0 if col == 0 else 7, 0 if col == 2 else 7),
                      pady=(0 if r == 0 else 7, 7))
            top = tk.Frame(card, bg=th["card"])
            top.pack(fill="x", padx=14, pady=(12, 4))
            ic = tk.Label(top, text=icon, bg=th["card2"], fg=th["accent"], font=self.F(13, True, True),
                          width=3, pady=3)
            ic.pack(side="left")
            nm = tk.Label(top, text=name, bg=th["card"], fg=th["fg"], font=self.F(10.5, True), anchor="w")
            nm.pack(side="left", padx=9)
            ds = tk.Label(card, text=desc, bg=th["card"], fg=th["muted"], font=self.F(8.5), anchor="w",
                          justify="left", wraplength=int(215 * k))
            ds.pack(fill="x", padx=14, pady=(0, 12))
            for w in (card, top, ic, nm, ds):
                w.bind("<Button-1>", lambda e, x=pid: self.apply_preset(x))

    def page_forecast(self, p):
        th, k = self.th, self.k
        # Панель поиска города
        search_card = self.section(p, "Ваш город")
        bar = tk.Frame(search_card, bg=th["card"])
        bar.pack(fill="x", padx=18, pady=14)

        entry_box = tk.Frame(bar, bg=th["card2"], highlightbackground=th["line"], highlightthickness=1)
        entry_box.pack(side="left", fill="x", expand=True, padx=(0, 12))
        city_var = tk.StringVar(value=self.cfg.get("weather_city", "Днепр"))
        ent = tk.Entry(entry_box, textvariable=city_var, bg=th["card2"], fg=th["fg"],
                       insertbackground=th["fg"], relief="flat", bd=0, font=self.F(11))
        ent.pack(fill="x", padx=12, pady=8)
        ent.bind("<Return>", lambda _e: self.load_weather_async(city_var.get()))

        btn_find = TactileButton(bar, th, k, "Показать погоду",
                                 lambda: self.load_weather_async(city_var.get()),
                                 accent=True, width=165, height=36)
        btn_find.pack(side="right")

        # Быстрый выбор популярных городов
        quick = tk.Frame(search_card, bg=th["card"])
        quick.pack(fill="x", padx=18, pady=(0, 12))
        tk.Label(quick, text="Быстрый выбор:", bg=th["card"], fg=th["muted"], font=self.F(9)).pack(side="left", padx=(0, 8))
        for cname in ("Днепр", "Киев", "Львов", "Одесса", "Харьков"):
            qb = TactileButton(quick, th, k, cname,
                               lambda c=cname: (city_var.set(c), self.load_weather_async(c)),
                               accent=False, width=82, height=28)
            qb.pack(side="left", padx=3)

        if self.weather_loading:
            box = self.section(p, "Загрузка")
            tk.Label(box, text="Получаем прогноз погоды на неделю...", bg=th["card"], fg=th["accent"],
                     font=self.F(11, True), pady=24).pack()
            return

        if self.weather_error:
            box = self.section(p, "Ошибка")
            tk.Label(box, text=self.weather_error, bg=th["card"], fg="#F43F5E",
                     font=self.F(10.5, True), pady=20).pack()
            return

        if not self.weather_data:
            box = self.section(p, "Прогноз на неделю")
            tk.Label(box, text="Введите название вашего города сверху, чтобы увидеть погоду на 7 дней.",
                     bg=th["card"], fg=th["muted"], font=self.F(10), pady=22).pack()
            return

        d = self.weather_data
        # Текущая погода
        now_card = self.section(p, f"Сейчас · {d['city']}" + (f" ({d['region']})" if d["region"] else ""))
        top = tk.Frame(now_card, bg=th["card"])
        top.pack(fill="x", padx=20, pady=16)

        big_icon = WeatherAnimIcon(top, th["card"], d["kind"], d["color"], size=int(72 * k))
        big_icon.pack(side="left")
        self.weather_icons.append(big_icon)

        info = tk.Frame(top, bg=th["card"])
        info.pack(side="left", padx=16)
        temp_str = f"{'+' if d['temp'] > 0 else ''}{d['temp']}°C"
        tk.Label(info, text=f"{temp_str}   {d['label']}", bg=th["card"], fg=th["fg"],
                 font=self.F(18, True)).pack(anchor="w")
        feels_str = f"{'+' if d['feels'] > 0 else ''}{d['feels']}°C"
        tk.Label(info, text=f"Ощущается как {feels_str}  ·  Ветер {d['wind']} км/ч  ·  Влажность {d['humidity']}%",
                 bg=th["card"], fg=th["muted"], font=self.F(9.5)).pack(anchor="w", pady=(4, 0))

        sync_btn = TactileButton(top, th, k, "Включить эту погоду на экране",
                                 self.sync_weather_to_desktop, accent=True, width=225, height=38)
        sync_btn.pack(side="right")

        # Прогноз на 7 дней
        week_wrap = tk.Frame(p, bg=th["bg"])
        week_wrap.pack(fill="x", padx=28, pady=(16, 0))
        tk.Label(week_wrap, text="ПРОГНОЗ НА НЕДЕЛЮ (7 ДНЕЙ)", bg=th["bg"], fg=th["muted"],
                 font=self.F(9, True), anchor="w").pack(anchor="w", pady=(0, 8))

        grid = tk.Frame(week_wrap, bg=th["bg"])
        grid.pack(fill="x")
        days = d["days"]
        for i in range(len(days)):
            grid.grid_columnconfigure(i, weight=1, uniform="wday")

        for i, day in enumerate(days):
            card = tk.Frame(grid, bg=th["card"], highlightbackground=th["accent"] if i == 0 else th["line"],
                            highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0 if i == 0 else 4, 0 if i == len(days) - 1 else 4))

            tk.Label(card, text=day["weekday"], bg=th["card"],
                     fg=th["accent"] if i == 0 else th["fg"],
                     font=self.F(10, True)).pack(pady=(10, 0))
            tk.Label(card, text=day["date"], bg=th["card"], fg=th["muted"],
                     font=self.F(8.5)).pack()

            ic = WeatherAnimIcon(card, th["card"], day["kind"], day["color"], size=int(54 * k))
            ic.pack(pady=4)
            self.weather_icons.append(ic)

            tk.Label(card, text=day["label"], bg=th["card"], fg=th["fg"],
                     font=self.F(8.5), wraplength=int(95 * k), justify="center", height=2).pack(padx=4)

            tmax_s = f"{'+' if day['tmax'] > 0 else ''}{day['tmax']}°"
            tmin_s = f"{'+' if day['tmin'] > 0 else ''}{day['tmin']}°"
            tk.Label(card, text=f"{tmax_s} / {tmin_s}", bg=th["card"], fg=th["fg"],
                     font=self.F(10, True)).pack(pady=(4, 2))

            pop_col = "#38BDF8" if day["pop"] >= 40 else th["muted"]
            tk.Label(card, text=f"Осадки: {day['pop']}%", bg=th["card"], fg=pop_col,
                     font=self.F(8)).pack(pady=(0, 10))

    def page_fall(self, p):
        c = self.section(p, "Количество и скорость")
        self.slider(c, "density", "Количество частиц", 20, 480, 10,
                    "Теперь доступно до 480 снежинок для настоящего густого снегопада.")
        self.slider(c, "speed", "Скорость падения", 0.2, 3.0, 0.1)
        self.slider(c, "size", "Размер", 2, 14, 1)
        self.slider(c, "wobble", "Покачивание", 0.0, 3.0, 0.1)
        self.toggle(c, "desktop_only", "Только на рабочем столе",
                    "Скрывать падающие частицы за окнами, оставляя их на обоях. "
                    "Гирлянда сверху и сугробы на окнах всё равно видны.")
        c2 = self.section(p, "Снег")
        self.drop(c2, "snow_style", "Форма снежинок",
                  ["Все вместе", "Точки", "Звёздочки ❄", "Хлопья ❅", "Кристаллы ❆"])
        self.color(c2, "snow_color", "Цвет снега")
        c3 = self.section(p, "Свой набор")
        self.drop(c3, "fall_mode", "Режим", ["По сезону", "Свой набор"])
        for k2, label in KINDS:
            self.toggle(c3, "k_" + k2, label)

    def page_weather(self, p):
        c = self.section(p, "Ветер")
        self.drop(c, "wind_dir", "Направление", ["Вправо", "Влево", "Меняется"])
        self.slider(c, "wind_power", "Сила ветра", 0.0, 5.0, 0.1)
        self.slider(c, "gust_power", "Порывы", 0.0, 3.0, 0.1)
        self.slider(c, "gust_speed", "Частота порывов", 0.2, 3.0, 0.1)
        c2 = self.section(p, "Метель")
        self.slider(c2, "blizzard_every", "Каждые N минут (0 — выкл.)", 0, 30, 1)
        self.slider(c2, "blizzard_len", "Длительность (секунды)", 10, 90, 5)
        self.slider(c2, "blizzard_power", "Сила метели", 0.5, 3.0, 0.1)
        self.buttons(c2, [("Запустить метель", lambda: self.ov.send("call", "start_blizzard"), True)])

    def page_garland(self, p):
        c = self.section(p, "Гирлянда на верхнем крае экрана")
        self.toggle(c, "garland_enabled", "Показывать гирлянду",
                    "Гирлянда располагается аккуратно вдоль верхнего края монитора.")
        self.toggle(c, "garland_winter_only", "Только зимой")
        self.drop(c, "garland_style", "Вид",
                  ["Авто (по сезону)"] + list(GARLAND_STYLES))
        self.drop(c, "blink_mode", "Свечение", ["Бегущая волна", "Мигание", "Постоянно"])
        self.slider(c, "blink_speed", "Скорость свечения", 0.5, 8.0, 0.5)
        self.slider(c, "garland_glow", "Яркость ореола", 1, 3, 1)
        c2 = self.section(p, "Форма и цвета")
        self.slider(c2, "garland_arc", "Ширина дуги", 120, 420, 10)
        self.slider(c2, "garland_sag", "Провис", 10, 60, 2)
        self.slider(c2, "garland_gap", "Шаг украшений", 22, 90, 2)
        self.slider(c2, "bulb_size", "Размер", 3, 9, 1)
        self.slider(c2, "garland_width", "Толщина провода", 1, 5, 1)
        self.color(c2, "garland_wire", "Цвет провода")
        for i in range(1, 5):
            self.color(c2, "color%d" % i, "Цвет %d" % i)

    def page_snow(self, p):
        c = self.section(p, "Сугробы")
        self.toggle(c, "pile_enabled", "Накапливать снег на окнах и панели задач")
        self.slider(c, "pile_max", "Максимальная высота", 6, 40, 1)
        self.slider(c, "pile_rate", "Скорость накопления", 0.2, 3.0, 0.1)
        self.buttons(c, [("Убрать сугробы", lambda: self.ov.send("call", "clear_snow"), False)])
        c2 = self.section(p, "Снегоуборочная машина")
        self.slider(c2, "plow_every", "Выезжать каждые N минут (0 — выкл.)", 0, 30, 1)
        self.slider(c2, "plow_speed", "Скорость", 1, 10, 1)
        self.buttons(c2, [("Запустить сейчас", lambda: self.ov.send("call", "start_plow"), True)])
        c3 = self.section(p, "Снеговики")
        self.toggle(c3, "roll_enabled", "Лепка снеговиков",
                    "Зажмите клавишу на сугробе и проведите мышью в стороны — скатается снежный ком. "
                    "Отпустите на поверхности; три кома друг на друге дадут снеговика.")
        self.drop(c3, "roll_key", "Клавиша", ["Ctrl", "Shift"])
        self.slider(c3, "snowman_size", "Размер", 0.6, 1.8, 0.1)
        self.slider(c3, "snowman_max", "Максимум на экране", 1, 15, 1)
        self.slider(c3, "snowman_melt", "Таяние, минут (0 — не тают)", 0, 60, 1)
        self.buttons(c3, [("Убрать снеговиков", lambda: self.ov.send("call", "clear_snowmen"), False)])

    def page_sky(self, p):
        c = self.section(p, "Северное сияние")
        self.toggle(c, "aurora_enabled", "Показывать сияние")
        self.drop(c, "aurora_when", "Когда", ["Только зимой", "Всегда"])
        self.drop(c, "aurora_palette", "Цвет", list(AURORA_PAL))
        self.slider(c, "aurora_height", "Высота от экрана (%)", 15, 65, 1)
        self.slider(c, "aurora_speed", "Скорость переливов", 0.3, 3.0, 0.1)
        self.slider(c, "aurora_power", "Яркость", 1, 3, 1)

        c2 = self.section(p, "Звёздное небо")
        self.toggle(c2, "stars_enabled", "Мерцающие 4-лучевые звёзды и падающие звёзды")
        self.slider(c2, "stars_count", "Количество", 20, 260, 10)
        self.slider(c2, "stars_height", "Область сверху (%)", 20, 100, 5)
        self.slider(c2, "stars_twinkle", "Скорость мерцания", 0.3, 3.0, 0.1)

        c3 = self.section(p, "Солнце и луна")
        self.drop(c3, "sky_body", "Показывать", ["Выкл", "Авто", "Солнце", "Луна"])
        self.drop(c3, "sky_phase", "Фаза луны", ["Авто", "Полная", "Растущая", "Убывающая"])
        self.drop(c3, "sky_corner", "Угол экрана", ["Правый верх", "Левый верх"])
        self.slider(c3, "sky_size", "Размер", 40, 140, 5)

        c4 = self.section(p, "Облака")
        self.toggle(c4, "clouds_enabled", "Большие объёмные облака")
        self.slider(c4, "clouds_count", "Количество", 2, 18, 1)
        self.slider(c4, "clouds_speed", "Скорость", 0.2, 3.0, 0.1)
        self.drop(c4, "clouds_tint", "Оттенок", ["Белые", "Серые (пасмурно)", "Закат (розовые)"])
        self.slider(c4, "clouds_height", "Высота области (%)", 15, 60, 5)

        c5 = self.section(p, "Птицы и бабочки")
        self.drop(c5, "birds_mode", "Показывать", ["Выкл", "По сезону", "Птицы", "Бабочки"])
        self.slider(c5, "birds_count", "Количество", 3, 25, 1)
        self.slider(c5, "birds_size", "Размер (%)", 60, 160, 10)
        self.slider(c5, "birds_speed", "Скорость", 0.3, 3.0, 0.1)

        c6 = self.section(p, "Метеоры")
        self.toggle(c6, "meteor_enabled", "Яркие падающие метеоры с хвостом и искрами")
        self.slider(c6, "meteor_every", "Каждые N секунд", 2, 30, 1)
        self.slider(c6, "meteor_len", "Длина хвоста", 0.5, 2.5, 0.1)
        self.buttons(c6, [("Запустить метеор", lambda: self.ov.send("call", "spawn_meteor"), True)])

    def page_party(self, p):
        c = self.section(p, "Новогодняя ёлка")
        self.toggle(c, "tree_enabled", "Поставить ёлку на рабочий стол")
        self.drop(c, "tree_side", "Положение", ["Справа", "Слева", "По центру"])
        self.slider(c, "tree_size", "Размер (%)", 50, 170, 5)
        self.slider(c, "tree_margin", "Отступ от края", 10, 300, 10)
        self.slider(c, "tree_lift", "Поднять от низа", 0, 200, 5)

        c2 = self.section(p, "Дед Мороз")
        self.toggle(c2, "santa_enabled", "Плавный пролёт Деда Мороза на санях с оленями")
        self.slider(c2, "santa_every", "Каждые N минут", 1, 20, 1)
        self.slider(c2, "santa_size", "Размер (%)", 60, 160, 5)
        self.slider(c2, "santa_speed", "Скорость полёта", 1, 14, 1)
        self.slider(c2, "santa_height", "Высота полёта (%)", 5, 50, 1)
        self.toggle(c2, "santa_gifts", "Сбрасывать подарки на окна")
        self.buttons(c2, [("Запустить Деда Мороза", lambda: self.ov.send("call", "start_santa"), True)])

        c3 = self.section(p, "Фейерверки")
        self.toggle(c3, "fw_enabled", "Запускать салют")
        self.slider(c3, "fw_every", "Каждые N секунд", 2, 25, 1)
        self.slider(c3, "fw_size", "Размер залпа", 0.5, 2.0, 0.1)
        self.buttons(c3, [("Запустить залп", lambda: self.ov.send("call", "spawn_rocket"), True)])

        c4 = self.section(p, "Отсчёт до праздника")
        self.toggle(c4, "count_enabled", "Показывать счётчик на рабочем столе")
        self.drop(c4, "count_target", "Событие", ["Новый год", "Рождество", "Своя дата"])
        self.slider(c4, "count_month", "Месяц (для своей даты)", 1, 12, 1)
        self.slider(c4, "count_day", "День", 1, 31, 1)
        self.drop(c4, "count_corner", "Угол экрана", ["Левый верх", "Правый верх", "Левый низ", "Правый низ"])
        self.slider(c4, "count_size", "Размер (%)", 60, 160, 5)
        self.color(c4, "count_color", "Цвет текста")
        self.toggle(c4, "count_seconds", "Показывать секунды")

    def page_cursor(self, p):
        c = self.section(p, "Курсор и снег")
        self.drop(c, "cursor_mode", "Режим курсора",
                  ["Физика ветра", "Сметать снег и снеговиков", "Ничего"])
        self.slider(c, "cursor_radius", "Радиус действия", 40, 220, 5)
        self.slider(c, "cursor_force", "Сила потока", 0.2, 3.0, 0.1)
        self.toggle(c, "cursor_blow", "Сдувать снег с сугробов при быстром движении мыши")

        c2 = self.section(p, "След за курсором")
        self.toggle(c2, "trail_enabled", "Оставлять след")
        self.drop(c2, "trail_kind", "Вид",
                  ["Искры", "Звёздная пыль", "Пузырьки", "Сердечки", "Снежинки", "Огонь"])
        self.slider(c2, "trail_amount", "Густота", 0.3, 3.0, 0.1)
        self.slider(c2, "trail_size", "Размер", 0.5, 2.0, 0.1)
        self.slider(c2, "trail_life", "Длина хвоста", 0.4, 2.5, 0.1)

    def page_app(self, p):
        c = self.section(p, "Запуск и трей")
        self.toggle(c, "_autostart", "Запускать вместе с Windows",
                    "Приложение тихо стартует в области уведомлений при входе в систему.",
                    getter=is_autostart, setter=self.set_autostart_ui)
        self.toggle(c, "start_hidden", "Скрывать окно настроек при автозапуске")
        self.toggle(c, "close_to_tray", "При нажатии «Закрыть» сворачивать в трей")
        self.toggle(c, "pause_fullscreen", "Ставить эффекты на паузу в полноэкранных играх и видео")

        c2 = self.section(p, "Производительность и мониторы")
        self.drop(c2, "perf_mode", "Режим нагрузки", ["Авто", "Красота", "Экономия"],
                  "По умолчанию включена «Красота» — максимум частиц и плавность.")
        self.slider(c2, "fps", "Частота кадров", 20, 75, 5)
        self.drop(c2, "widget_monitor", "Монитор для ёлки, солнца, луны и счётчика",
                  ["Основной", "Левый", "Правый"])

        c3 = self.section(p, "Оформление окна")
        self.drop(c3, "ui_theme", "Тема", list(THEMES))
        self.drop(c3, "ui_accent", "Акцентный цвет", ["По теме"] + list(ACCENTS))
        self.drop(c3, "ui_font", "Размер шрифта", list(FONT_SCALE))

        c4 = self.section(p, "Управление")
        self.buttons(c4, [("Сбросить настройки", self.reset_all, False),
                          ("Выйти из приложения", self.quit, False)])


def notify_running():
    h = kernel32w.OpenEventW(0x0002, False, SHOW_EVENT)
    if h:
        kernel32w.SetEvent(h)
        return True
    return False


def main():
    if notify_running():
        return
    try:
        cfg = load_cfg()
        ov = Overlay(cfg)
        ov.start()
        for _ in range(80):
            if ov.engine is not None:
                break
            time.sleep(0.025)
        root = tk.Tk()
        root.report_callback_exception = report_tk_exception
        hidden = ("--autostart" in sys.argv and cfg["start_hidden"]) or ("--hidden" in sys.argv)
        App(root, cfg, ov, hidden=hidden)
        root.mainloop()
    except Exception:
        log_error("fatal")


if __name__ == "__main__":
    main()
