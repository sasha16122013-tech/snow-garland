# -*- coding: utf-8 -*-
"""
Времена года и гирлянда: снег, листья, конфетти, пузыри, дождь, звёзды...
Гирлянда на окнах, сугробы с физикой, снеговики, Дед Мороз, северное сияние,
солнце и луна, ёлка, фейерверки, отсчёт до праздника и многое другое.

Запуск: python snow_garland.py   (или pythonw snow_garland.py - без консоли)
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
except ImportError:  # не Windows
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
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.SetParent.restype = wintypes.HWND
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
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
GWL_HWNDPARENT = -8
GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW = 0x80000, 0x20, 0x80
WS_EX_NOACTIVATE = 0x08000000
SWP_NOZORDER, SWP_NOACTIVATE, SWP_NOOWNERZORDER, SWP_SHOWWINDOW = 0x0004, 0x0010, 0x0200, 0x0040
EVENT_OBJECT_LOCATIONCHANGE = 0x800B


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
    """Мониторы: [{'mon': (l,t,r,b), 'work': (l,t,r,b)}] слева направо."""
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


def window_being_dragged(windows):
    """Find the real top-level window under the mouse while its title bar is dragged."""
    if not key_down(1):
        return 0
    p = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(p)):
        return 0
    child = user32.WindowFromPoint(p)
    hwnd = user32.GetAncestor(child, 2) or child
    hwnd = int(hwnd or 0)
    return hwnd if any(w[0] == hwnd for w in windows) else 0


def key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def foreground_hwnd():
    return int(user32.GetForegroundWindow() or 0)


def fullscreen_foreground(mon_rects):
    """True, если поверх всего окно на весь монитор (игра, видео, презентация)."""
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


def visible_window_edges(windows, skip_max, target_hw=None):
    """Visible frame segments for one tracked window, clipped by windows above it."""
    result = []
    for i, (hw, l, t, r, b, mx) in enumerate(windows):
        if target_hw and hw != target_hw:
            continue
        if mx and skip_max:
            continue
        inset = 8
        for orient, start, end, fixed in (
                ("h", l + inset, r - inset, t + inset),
                ("h", l + inset, r - inset, b - inset),
                ("v", t + inset, b - inset, l + inset),
                ("v", t + inset, b - inset, r - inset)):
            if end - start < 24:
                continue
            spans = [(start, end)]
            for (_other, l2, t2, r2, b2, _maxed) in windows[:i]:
                covers = (t2 <= fixed < b2) if orient == "h" else (l2 <= fixed < r2)
                if not covers:
                    continue
                cut_a, cut_b = (l2, r2) if orient == "h" else (t2, b2)
                updated = []
                for a, c in spans:
                    if cut_b <= a or cut_a >= c:
                        updated.append((a, c))
                    else:
                        if cut_a > a:
                            updated.append((a, cut_a))
                        if cut_b < c:
                            updated.append((cut_b, c))
                spans = updated
            for a, c in spans:
                if c - a >= 24:
                    result.append((hw, orient, a, c, fixed, l, t, r, b))
    return result


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
    """Рисуем иконку-снежинку прямо в памяти (без файлов)."""
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
            b, g, rr = int(0xE8 + (0xA0 - 0xE8) * t), int(0x5C + (0x4C - 0x5C) * t), int(0x6C + (0xF0 - 0x6C) * t)
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
    """Значок у часов. Левый или правый клик — меню: открыть настройки / пауза / выход."""
    CLASS = "SnowGarlandTrayWnd"
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
        self.hwnd = user32.CreateWindowExW(0, self.CLASS, "SnowGarland", 0, 0, 0, 0, 0,
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
        user32.AppendMenuW(m, 0, 1, "Открыть настройки")
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


SHOW_EVENT = "SnowGarland_show_settings"


def start_show_listener(flag):
    """Второй запуск exe будит первый: откроется окно настроек."""
    h = kernel32w.CreateEventW(None, False, False, SHOW_EVENT)

    def loop():
        while True:
            if kernel32w.WaitForSingleObject(h, 1000) == 0:
                flag.set()
    threading.Thread(target=loop, daemon=True).start()


def signal_existing():
    h = kernel32w.OpenEventW(0x2, False, SHOW_EVENT)
    if h:
        kernel32w.SetEvent(h)


# ---------------------------------------------------------------- Настройки
APPDATA = os.environ.get("APPDATA") or os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_DIR = os.path.join(APPDATA, "SnowGarland")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
LOG_PATH = os.path.join(CONFIG_DIR, "error.log")

KINDS = [("snow", "Снежинки"), ("leaf", "Осенние листья"),
         ("spring", "Весенние листья и лепестки"), ("firefly", "Светлячки"),
         ("confetti", "Конфетти"), ("bubble", "Мыльные пузыри"),
         ("heart", "Сердечки"), ("star", "Падающие звёзды"),
         ("rain", "Дождь"), ("lantern", "Небесные фонарики")]
KIND_FACTOR = {"firefly": 0.55, "lantern": 0.2, "bubble": 0.45, "star": 0.35,
               "heart": 0.7, "confetti": 1.0, "rain": 1.3}
SEASON_KINDS = {"winter": ["snow"], "autumn": ["leaf"],
                "spring": ["spring"], "summer": ["firefly"]}

DEFAULTS = {
    # что падает
    "season": "Авто", "fall_mode": "По сезону",
    "k_snow": True, "k_leaf": False, "k_spring": False, "k_firefly": False,
    "k_confetti": False, "k_bubble": False, "k_heart": False, "k_star": False,
    "k_rain": False, "k_lantern": False,
    "snow_style": "Все вместе", "snow_color": "#FFFFFF",
    "density": 180, "speed": 1.0, "size": 6, "wobble": 1.0,
    "desktop_only": True,
    # погода
    "wind_dir": "Вправо", "wind_power": 0.4, "gust_power": 0.6, "gust_speed": 1.0,
    "blizzard_every": 0, "blizzard_len": 25, "blizzard_power": 1.5,
    "weather_city": "",
    # курсор, снеговики, сугробы
    "cursor_mode": "Физика ветра", "cursor_radius": 90, "cursor_force": 1.0,
    "cursor_blow": True, "roll_enabled": True, "roll_key": "Ctrl",
    "snowman_size": 1.0, "snowman_max": 6, "snowman_melt": 10,
    "trail_enabled": False, "trail_kind": "Искры", "trail_amount": 1.0,
    "trail_size": 1.0, "trail_life": 1.0,
    "pile_enabled": True, "pile_max": 16, "pile_rate": 1.0,
    "plow_every": 0, "plow_speed": 4,
    # гирлянда
    "garland_enabled": True, "garland_winter_only": False, "skip_maximized": True,
    "garland_top": True, "garland_around": False,
    "garland_style": "Авто (по сезону)", "garland_glow": 2,
    "garland_arc": 220, "garland_sag": 28, "garland_gap": 42, "bulb_size": 5,
    "garland_width": 2, "garland_wire": "#2E7D32",
    "color1": "#FF3B30", "color2": "#FFD60A", "color3": "#34C759", "color4": "#0A84FF",
    "blink_mode": "Бегущая волна", "blink_speed": 2.0,
    # небо
    "aurora_enabled": False, "aurora_when": "Всегда", "aurora_palette": "Зелёное",
    "aurora_height": 32, "aurora_speed": 1.0, "aurora_power": 2,
    "stars_enabled": False, "stars_count": 90, "stars_height": 50, "stars_twinkle": 1.0,
    "sky_body": "Выкл", "sky_phase": "Авто", "sky_corner": "Правый верх", "sky_size": 70,
    "meteor_enabled": False, "meteor_every": 8, "meteor_len": 1.0,
    "clouds_enabled": False, "clouds_count": 5, "clouds_speed": 1.0,
    "clouds_tint": "Белые", "clouds_height": 30,
    "birds_mode": "Выкл", "birds_count": 8, "birds_size": 100, "birds_speed": 1.0,
    # праздник
    "widget_monitor": "Правый",
    "santa_enabled": False, "santa_every": 3, "santa_size": 100, "santa_speed": 5,
    "santa_height": 18, "santa_gifts": True,
    "tree_enabled": False, "tree_side": "Справа", "tree_size": 100,
    "tree_margin": 40, "tree_lift": 0,
    "fw_enabled": False, "fw_every": 6, "fw_size": 1.0,
    "count_enabled": False, "count_target": "Новый год", "count_month": 12,
    "count_day": 31, "count_corner": "Левый верх", "count_size": 100,
    "count_color": "#FFFFFF", "count_seconds": True,
    "strip_enabled": False, "strip_mode": "Тёплый", "strip_width": 4,
    "strip_speed": 1.0, "strip_color": "#8B5CF6",
    "neon_enabled": False, "neon_mode": "Фиолетовый", "neon_width": 3, "neon_speed": 1.0,
    # приложение
    "ui_theme": "Тёмная (фиолет)", "ui_accent": "По теме", "ui_font": "Обычный",
    "close_to_tray": True, "start_hidden": False, "pause_fullscreen": True,
    "perf_mode": "Авто", "fps": 60, "lead_ms": 0,
}
APP_KEYS = {"ui_theme", "ui_accent", "ui_font", "close_to_tray", "start_hidden",
            "pause_fullscreen", "perf_mode", "fps", "lead_ms", "widget_monitor"}

EFFECT_NAMES = ("stars", "aurora", "clouds", "sky", "birds", "tree", "count", "strip",
                "santa", "neon")
EFFECT_PREFIX = (("aurora_", "aurora"), ("stars_", "stars"), ("sky_", "sky"),
                 ("clouds_", "clouds"), ("tree_", "tree"), ("santa_", "santa"),
                 ("birds_", "birds"), ("count_", "count"), ("strip_", "strip"),
                 ("neon_", "neon"))
SCENE_KEYS = {"garland_enabled", "garland_winter_only", "skip_maximized",
              "garland_style", "garland_glow", "garland_arc", "garland_sag",
              "garland_gap", "bulb_size", "garland_width", "garland_wire",
              "color1", "color2", "color3", "color4", "pile_enabled", "garland_top",
              "garland_around"}
PARTICLE_KEYS = {"season", "density", "size", "snow_color", "fall_mode", "snow_style"}
DESK_TAGS = ("e_stars", "e_aurora", "e_clouds", "e_sky", "e_birds", "e_tree", "e_count",
             "e_strip", "e_santa", "flake", "fx")
WIN_TAGS = ("pile", "snowman", "gift", "garland", "e_neon", "plow", "ball", "carry")

PRESETS = [
    ("newyear", "❄", "Новый год",
     "Зима, гирлянда-лампочки, ёлка, Дед Мороз, звёзды и отсчёт до Нового года.",
     {"season": "Зима", "garland_style": "Лампочки", "tree_enabled": True,
      "santa_enabled": True, "count_enabled": True, "stars_enabled": True,
      "aurora_enabled": True, "wind_power": 0.5}),
    ("autumn", "❦", "Уютная осень",
     "Падают листья, плывут облака, пролетают птицы, ветер то в одну, то в другую сторону.",
     {"season": "Осень", "garland_style": "Листья", "clouds_enabled": True,
      "birds_mode": "Птицы", "wind_power": 1.2, "wind_dir": "Меняется"}),
    ("spring", "✿", "Весна",
     "Лепестки и зелёные листья, цветущая сакура, птицы и лёгкие облака.",
     {"season": "Весна", "garland_style": "Цветы", "tree_enabled": True,
      "clouds_enabled": True, "birds_mode": "Птицы", "wind_power": 0.6}),
    ("summer", "☀", "Лето",
     "Светлячки, солнце, бабочки и разноцветные флажки вместо гирлянды.",
     {"season": "Лето", "garland_style": "Флажки", "sky_body": "Солнце",
      "birds_mode": "Бабочки", "clouds_enabled": True, "pile_enabled": False}),
    ("party", "✺", "Вечеринка",
     "Конфетти, сердечки, пузыри, тёплый след за курсором и фейерверки.",
     {"fall_mode": "Свой набор", "k_snow": False, "k_confetti": True, "k_heart": True,
      "k_bubble": True, "trail_enabled": True, "trail_kind": "Звёздная пыль", "fw_enabled": True,
      "strip_enabled": False, "neon_enabled": False, "garland_style": "Шарики",
      "garland_around": False, "garland_top": True, "pile_enabled": False}),
    ("night", "☾", "Ночное небо",
     "Луна, звёзды, северное сияние, метеоры и небесные фонарики.",
     {"fall_mode": "Свой набор", "k_snow": False, "k_lantern": True, "k_star": True,
      "stars_enabled": True, "sky_body": "Луна", "aurora_enabled": True,
      "meteor_enabled": True, "garland_enabled": False, "pile_enabled": False}),
    ("rain", "☂", "Дождь",
     "Пасмурные облака, дождь с брызгами и порывистый ветер.",
     {"fall_mode": "Свой набор", "k_snow": False, "k_rain": True, "density": 240,
      "clouds_enabled": True, "clouds_tint": "Серые (пасмурно)", "gust_power": 1.0,
      "garland_enabled": False, "pile_enabled": False}),
    ("quiet", "☕", "Тишина",
     "Совсем немного снега, без гирлянды и сугробов — чтобы не отвлекало.",
     {"density": 50, "speed": 0.7, "garland_enabled": False, "pile_enabled": False,
      "gust_power": 0.3}),
    ("eco", "⚡", "Минимум нагрузки",
     "Почти ничего не рисуется — для слабых компьютеров.",
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
              "Розовое": ["#FF7CC8", "#FF9E7C", "#C77CFF"]}
LEAF = [(0, -1), (0.55, -0.4), (0.5, 0.3), (0, 1), (-0.5, 0.3), (-0.55, -0.4)]
PETAL = [(0, -1), (0.65, -0.25), (0.45, 0.6), (0, 1), (-0.45, 0.6), (-0.65, -0.25)]
RECT = [(-1, -0.55), (1, -0.55), (1, 0.55), (-1, 0.55)]
GARLAND_STYLES = {"Лампочки": "bulb", "Сосульки": "icicle", "Шарики": "ball",
                  "Звёзды": "star", "Фонарики": "lantern", "Флажки": "flag",
                  "Листья": "leaf", "Цветы": "flower", "Микс": "mix"}
AUTO_STYLE = {"winter": "bulb", "autumn": "leaf", "spring": "flower", "summer": "flag"}


def load_cfg():
    cfg = dict(DEFAULTS)
    data = {}
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
    if isinstance(data, dict) and data and data.get("_performance_revision", 0) < 13:
        revision = data.get("_performance_revision", 0)
        if revision < 3:
            if data.get("fps") == 30:
                cfg["fps"] = 60
            if data.get("lead_ms") in (8, 16, 24):
                cfg["lead_ms"] = 0
        if revision < 4:
            cfg["garland_around"] = True
        if revision < 5:
            cfg["lead_ms"] = 30
        if revision < 13:
            cfg["garland_around"] = False
            cfg["garland_top"] = True
            cfg["strip_enabled"] = False
            cfg["neon_enabled"] = False
        save_cfg(cfg)
    return cfg


def save_cfg(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            stored = dict(cfg)
            stored["_performance_revision"] = 13
            json.dump(stored, f, ensure_ascii=False, indent=2)
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
    info = (exc, value, tb)
    log_exception("Tk callback", info)
    try:
        text = ("В приложении произошла ошибка. Подробности сохранены в журнале:\n\n" +
                LOG_PATH)
        user32.MessageBoxW(None, text, "SnowGarland — ошибка", 0x10)
    except Exception:
        pass


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
    a, b = c1.lstrip("#"), c2.lstrip("#")
    out = []
    for i in (0, 2, 4):
        x, y = int(a[i:i + 2], 16), int(b[i:i + 2], 16)
        out.append(int(x + (y - x) * t))
    return "#%02x%02x%02x" % tuple(out)


def clip_polygon_rect(points, rect):
    if not rect or len(points) < 6:
        return points
    left, top, right, bottom = rect
    polygon = list(zip(points[0::2], points[1::2]))

    def hit_x(a, b, edge):
        den = b[0] - a[0]
        return (edge, a[1] if abs(den) < 1e-9 else
                a[1] + (b[1] - a[1]) * (edge - a[0]) / den)

    def hit_y(a, b, edge):
        den = b[1] - a[1]
        return (a[0] if abs(den) < 1e-9 else
                a[0] + (b[0] - a[0]) * (edge - a[1]) / den, edge)

    edges = ((lambda p: p[0] >= left, lambda a, b: hit_x(a, b, left)),
             (lambda p: p[0] <= right, lambda a, b: hit_x(a, b, right)),
             (lambda p: p[1] >= top, lambda a, b: hit_y(a, b, top)),
             (lambda p: p[1] <= bottom, lambda a, b: hit_y(a, b, bottom)))
    for inside, intersect in edges:
        if not polygon:
            break
        output, previous = [], polygon[-1]
        for current in polygon:
            prev_in, cur_in = inside(previous), inside(current)
            if cur_in:
                if not prev_in:
                    output.append(intersect(previous, current))
                output.append(current)
            elif prev_in:
                output.append(intersect(previous, current))
            previous = current
        polygon = output
    return [v for point in polygon for v in point]


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


# ---------------------------------------------------------------- Автозапуск
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SnowGarland"
APP_TITLE = "Atmosphere"


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
    """Вся «физика» и рисование."""
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
        self.lights, self.render, self.geo, self.vel = {}, {}, {}, {}
        self.around_render, self.garland_motion_items = {}, {}
        self.garland_sway, self._glow_clip = {}, None
        self.garland_target = 0
        self.garland_target_locked = False
        self.window_garland_managed = False
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
        self.santa, self.next_santa = None, None
        self.tree_lights = []
        self.perf_scale = 0.75 if cfg["perf_mode"] == "Экономия" else (0.95 if cfg["perf_mode"] == "Авто" else 1.0)
        self.perf_cool = 0.0
        self.ms = 0.0
        self.scene_ms, self.scene_rate, self.scene_cost_t = 0.0, 0.0, 0.0
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
            self.fx_dirty.update(("tree", "sky", "count", "strip"))
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
            self.perf_scale = 0.75 if cfg["perf_mode"] == "Экономия" else (0.95 if cfg["perf_mode"] == "Авто" else 1.0)
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

    def step(self, now):
        self.scene_tick(now)
        self.tick(now)

    def scene_tick(self, now):
        if not self.visible or now < self.next_poll:
            return
        self.now = now
        interval = now - self.scene_cost_t if self.scene_cost_t else 0.05
        self.scene_cost_t = now
        self.scene_rate = 1.0 / max(0.008, interval)
        started = time.perf_counter()
        self.guard("scene", self.refresh_scene, now)
        scene_cost = (time.perf_counter() - started) * 1000.0
        self.scene_ms = self.scene_ms * 0.75 + scene_cost * 0.25
        self.next_poll = now + (0.016 if now < self.fast_until else 0.080)
        if self.effect_on.get("neon"):
            self.guard("neon", self.update_neon, now)

    def window_location_changed(self, hwnd):
        hwnd = int(hwnd or 0)
        top = user32.GetAncestor(hwnd, 2) if hwnd else 0
        if top:
            hwnd = int(top)
        if self.garland_target and hwnd != self.garland_target:
            return False
        if not hwnd or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return False
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return False
        if user32.GetWindowTextLengthW(hwnd) == 0:
            return False
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False
        if self.garland_target_locked and hwnd == self.garland_target:
            frame = self.around_render.get(hwnd)
            if frame:
                width, height = rect.right - rect.left, rect.bottom - rect.top
                sig = frame.get("sig", ())
                if len(sig) >= 2 and width == sig[0] and height == sig[1]:
                    left, top = rect.left - self.vx, rect.top - self.vy
                    dx, dy = left - frame["left"], top - frame["top"]
                    if dx or dy:
                        self.cv.move("a%s" % hwnd, dx, dy)
                        self.shift_garland_motion(hwnd, "a", dx, dy)
                        frame["left"], frame["top"] = left, top
        updated = (hwnd, rect.left, rect.top, rect.right, rect.bottom,
                   bool(user32.IsZoomed(hwnd)))
        found = False
        for i, win in enumerate(self.window_cache):
            if win[0] == hwnd:
                self.window_cache[i] = updated
                found = True
                break
        if not found:
            self.window_cache.append(updated)
        if not self.garland_target:
            self.garland_target = hwnd
        now = time.time()
        self.fast_until = max(self.fast_until, now + 0.5)
        self.next_poll = 0.0
        return True

    def tick(self, now):
        if not self.visible:
            return
        t0 = time.perf_counter()
        dt = t0 - self.last_frame_perf if self.last_frame_perf else 1.0 / 30.0
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
                    self.fx_dirty.add("tree")
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
        g("garland_motion", self.update_garland_motion, now)
        self.ms = self.ms * 0.9 + (time.perf_counter() - t0) * 1000.0 * 0.1
        if self.frame % 30 == 0:
            self.adapt_perf(now)

    def refresh_scene(self, now):
        cfg = self.cfg
        vx, vy = self.vx, self.vy
        moving_scan = (self.window_cache and now - self.last_window_scan < 1.0)
        if moving_scan:
            wins = list(self.window_cache)
            foreground = self.get_fg()
            ids = {w[0] for w in wins}
            drag_target = window_being_dragged(wins)
            if foreground and foreground not in ids and user32.IsWindowVisible(foreground) and \
                    user32.GetWindowTextLengthW(foreground) > 0:
                moving_scan = False
            elif self.garland_target not in ids and not self.garland_target_locked:
                self.garland_target = drag_target or (foreground if foreground in ids else 0)
        if moving_scan:
            target = self.garland_target if self.garland_target in ids else foreground
            if target in ids:
                rect = wintypes.RECT()
                if user32.GetWindowRect(target, ctypes.byref(rect)):
                    updated = []
                    for window in wins:
                        if window[0] == target:
                            updated.append((target, rect.left, rect.top, rect.right, rect.bottom,
                                            bool(user32.IsZoomed(target))))
                        else:
                            updated.append(window)
                    wins = updated
                    self.window_cache = list(wins)
        if not moving_scan:
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
                self.fx_dirty.update(("tree", "sky", "count", "strip"))
                self.dirty_scene = True
        lead = cfg["lead_ms"] / 1000.0
        wp = []
        moved = False
        for (hw, l, t, r, b, mx) in wins:
            ox, oy = self.lead_offset(hw, l, t, now, lead)
            if ox or oy:
                moved = True
            wp.append((hw, l + ox, t + oy, r + ox, b + oy, mx))
        new_geo = {w[0]: (w[1] - vx, w[2] - vy, w[3] - w[1]) for w in wins}
        for key in list(self.vel):
            if key not in new_geo:
                del self.vel[key]
        for key in list(self.geo):
            if key not in new_geo:
                self.collapse(key)
        dt = max(0.004, now - self.geo_t) if self.geo_t else 0.033
        self.geo_t = now
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
            self.fast_until = now + 0.5
        info, deco = {}, {}
        window_heights = {hw: b - t for (hw, _l, t, _r, b, _mx) in wins}
        for (hw, a, c, top, left, width) in visible_top_edges(wp, cfg["skip_maximized"]):
            ty = top - vy
            if ty < 4 or ty > self.H - 4:
                continue
            d = info.setdefault(hw, {"left": left - vx, "width": width, "height": window_heights.get(hw, 0),
                                     "top": ty, "spans": []})
            d["spans"].append((a - vx, c - vx))
        for i, m in enumerate(self.mons):
            wl, wt, wr, wb = m["work"]
            info["g%d" % i] = {"left": wl - vx, "width": wr - wl, "top": wb - vy,
                               "spans": [(wl - vx, wr - vx)]}
            if cfg["garland_top"]:
                ml, mt, mr, mb = m["mon"]
                deco["t%d" % i] = {"left": ml - vx, "width": mr - ml, "top": mt - vy,
                                   "spans": [(ml - vx, mr - vx)]}
        self.win_rects = [(l - vx, t - vy, r - vx, b - vy) for (_h, l, t, r, b, _m) in wp]
        self.win_keys = {w[0] for w in wins}
        self.wins = wp
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
        around_edges = []
        if cfg["garland_enabled"] and cfg["garland_around"] and \
                not self.garland_target_locked and not self.window_garland_managed and \
                (not cfg["garland_winter_only"] or self.season == "winter"):
            win_ids = {w[0] for w in wins}
            foreground = self.get_fg()
            drag_target = window_being_dragged(wins)
            if self.garland_target not in win_ids and not self.garland_target_locked:
                self.garland_target = drag_target or (foreground if foreground in win_ids else 0)
            if self.garland_target:
                around_windows = wins
                if self.garland_target_locked:
                    hwnd = self.garland_target
                    rect = wintypes.RECT()
                    if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd) and \
                            user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                        exact = (hwnd, rect.left, rect.top, rect.right, rect.bottom,
                                 bool(user32.IsZoomed(hwnd)))
                        around_windows = list(wins)
                        for idx, window in enumerate(around_windows):
                            if window[0] == hwnd:
                                around_windows[idx] = exact
                                break
                        else:
                            around_windows.append(exact)
                        around_edges = visible_window_edges(
                            around_windows, cfg["skip_maximized"], hwnd)
                else:
                    around_edges = visible_window_edges(wins, cfg["skip_maximized"],
                                                        self.garland_target)
        alli = dict(info)
        alli.update(deco)
        self.update_render(alli)
        self.update_around_garland(around_edges)
        if self.dirty_snowmen:
            self.redraw_snowmen()
            self.raise_all()

    def update_render(self, info):
        cv = self.cv
        rebuilt = False
        for key, d in info.items():
            sig = (d["width"], d.get("height", 0),
                   tuple((round(a - d["left"]), round(c - d["left"]))
                         for a, c in d["spans"]), self.ver)
            r = self.render.get(key)
            if r and r["sig"] == sig:
                dx, dy = d["left"] - r["left"], d["top"] - r["top"]
                if dx or dy:
                    cv.move("w%s" % key, dx, dy)
                    self.shift_garland_motion(key, "w", dx, dy)
                    r["left"], r["top"] = d["left"], d["top"]
            else:
                cv.delete("w%s" % key)
                self.build_garland_key(key, d)
                self.render[key] = {"sig": sig, "left": d["left"], "top": d["top"]}
                if isinstance(key, int):
                    self.capture_garland_motion(key, "w")
                rebuilt = True
        for key in list(self.render):
            if key not in info:
                cv.delete("w%s" % key)
                del self.render[key]
                self.lights.pop(key, None)
                self.capture_garland_motion(key, "w")
        if rebuilt:
            self.redraw_piles()
            self.redraw_snowmen()
            self.raise_all()

    def capture_garland_motion(self, key, group):
        tag = ("w" if group == "w" else "a") + str(key)
        items = []
        for item in self.cv.find_withtag(tag):
            coords = self.cv.coords(item)
            if len(coords) >= 4:
                tags = self.cv.gettags(item)
                axis = "x" if "motion_v" in tags else "y"
                items.append({"id": item, "type": self.cv.type(item), "base": coords,
                              "axis": axis})
        self.garland_motion_items.setdefault(key, {})[group] = items

    def shift_garland_motion(self, key, group, dx, dy):
        for item in self.garland_motion_items.get(key, {}).get(group, []):
            base = item["base"]
            for i in range(0, len(base), 2):
                base[i] += dx
                base[i + 1] += dy

    def update_around_garland(self, edge_list):
        cv, cfg = self.cv, self.cfg
        grouped = {}
        for hw, orient, a, b, fixed, left, top, right, bottom in edge_list:
            entry = grouped.setdefault(hw, {
                "left": left - self.vx, "top": top - self.vy,
                "width": right - left, "height": bottom - top, "edges": []})
            if orient == "h":
                entry["edges"].append((orient, a - left, b - left, fixed - top))
            else:
                entry["edges"].append((orient, a - top, b - top, fixed - left))

        colors = tuple(cfg[k] for k in ("color1", "color2", "color3", "color4"))
        style = self.garland_style()
        gap = max(64, int(cfg["garland_gap"]))
        radius = max(2.5, min(4.5, float(cfg["bulb_size"]) * 0.7))
        wire, width = cfg["garland_wire"], max(1, int(cfg["garland_width"]))
        sag = min(9.0, max(4.0, float(cfg["garland_sag"]) * 0.22))
        for key, d in grouped.items():
            sig = (d["width"], d["height"], tuple(d["edges"]), colors,
                   gap, radius, wire, width, style, sag)
            old = self.around_render.get(key)
            tag = "a%s" % key
            if old and old["sig"] == sig:
                dx, dy = d["left"] - old["left"], d["top"] - old["top"]
                if dx or dy:
                    cv.move(tag, dx, dy)
                    self.shift_garland_motion(key, "a", dx, dy)
                    old["left"], old["top"] = d["left"], d["top"]
                continue

            cv.delete(tag)
            self.capture_garland_motion(key, "a")
            self.lights[key] = []
            clip = (d["left"] + 1, d["top"] + 1,
                    d["left"] + d["width"] - 1, d["top"] + d["height"] - 1)
            for orient, a, b, fixed in d["edges"]:
                axis_tag = "motion_h" if orient == "h" else "motion_v"
                if orient == "h":
                    x0, x1 = d["left"] + a, d["left"] + b
                    y0 = y1 = d["top"] + fixed
                    length = b - a
                    inward = 1 if fixed < d["height"] * 0.5 else -1
                    normal, tangent = (0, inward), (1, 0)
                else:
                    x0 = x1 = d["left"] + fixed
                    y0, y1 = d["top"] + a, d["top"] + b
                    length = b - a
                    inward = 1 if fixed < d["width"] * 0.5 else -1
                    normal, tangent = (inward, 0), (0, 1)
                count = max(1, int(length / gap))
                spacing = length / count
                wire_pts = []
                for s in range(max(8, int(length / 12)) + 1):
                    q = s / max(8, int(length / 12))
                    wave = abs(math.sin(math.pi * q * length / spacing))
                    bend = sag * wave
                    wire_pts.extend((x0 + (x1 - x0) * q + normal[0] * bend,
                                     y0 + (y1 - y0) * q + normal[1] * bend))
                cv.create_line(*wire_pts, fill=blend(wire, 0.35), width=width + 2,
                               smooth=True, tags=(tag, "garland", "around_garland", axis_tag))
                cv.create_line(*wire_pts, fill=wire, width=width,
                               smooth=True, tags=(tag, "garland", "around_garland", axis_tag))
                for j in range(count):
                    pos = (j + 0.5) * length / count
                    q = pos / length
                    bend = sag * abs(math.sin(math.pi * pos / spacing))
                    x = x0 + (x1 - x0) * q + normal[0] * bend
                    y = y0 + (y1 - y0) * q + normal[1] * bend
                    col = colors[(j + key) % len(colors)]
                    nx, ny = normal
                    tx, ty = tangent
                    bulb_x, bulb_y = x + nx * (radius + 2), y + ny * (radius + 2)
                    subtag = (tag, "garland", "around_garland", axis_tag)
                    cv.create_oval(x - tx * 2 - nx * 2, y - ty * 2 - ny * 2,
                                   x + tx * 2 + nx * 2, y + ty * 2 + ny * 2,
                                   fill="#26313B", outline=wire, width=1, tags=subtag)
                    if style == "icicle":
                        ice_len = 16 + (j * 5) % 12
                        half = max(2.5, radius * 0.7)
                        tip_x, tip_y = x + nx * ice_len, y + ny * ice_len
                        shape = [x - tx * (half + 2), y - ty * (half + 2),
                                 x + tx * (half + 2), y + ty * (half + 2), tip_x, tip_y]
                        outer = clip_polygon_rect(shape, clip)
                        body_shape = [x - tx * half, y - ty * half,
                                      x + tx * half, y + ty * half, tip_x, tip_y]
                        body_shape = clip_polygon_rect(body_shape, clip)
                        g1 = cv.create_polygon(*outer, fill=col, outline="", stipple="gray25",
                                               tags=subtag)
                        g2 = cv.create_polygon(*outer, fill=col, outline="", stipple="gray50",
                                               tags=subtag)
                        body = cv.create_polygon(*body_shape, fill=mix(col, "#FFFFFF", 0.48),
                                                 outline=mix(col, "#FFFFFF", 0.65), tags=subtag)
                        cv.create_line(x, y, x + nx * ice_len * 0.7,
                                       y + ny * ice_len * 0.7, fill="#FFFFFF", tags=subtag)
                        self.lights.setdefault(key, []).append((body, g1, g2, col, j))
                    else:
                        old_clip = self._glow_clip
                        self._glow_clip = clip
                        try:
                            g1, g2 = self.glow(bulb_x, bulb_y, radius * 1.35,
                                               "gray25", "gray50", col, subtag)
                        finally:
                            self._glow_clip = old_clip
                        core = cv.create_oval(bulb_x - radius, bulb_y - radius,
                                              bulb_x + radius, bulb_y + radius,
                                              fill=col, outline=mix(col, "#FFFFFF", 0.72),
                                              width=1,
                                              tags=subtag)
                        cv.create_oval(bulb_x - radius * 0.38, bulb_y - radius * 0.62,
                                       bulb_x + radius * 0.12, bulb_y - radius * 0.12,
                                       fill="#FFFFFF", outline="", tags=subtag)
                        self.lights.setdefault(key, []).append((core, g1, g2, col, j))
            self.around_render[key] = {"sig": sig, "left": d["left"], "top": d["top"],
                                       "height": d["height"]}
            self.capture_garland_motion(key, "a")

        for key in list(self.around_render):
            if key not in grouped:
                cv.delete("a%s" % key)
                del self.around_render[key]
                if cfg["garland_around"] or key not in self.render:
                    self.lights.pop(key, None)
                self.capture_garland_motion(key, "a")
                if key not in self.render:
                    self.garland_motion_items.pop(key, None)
        if grouped:
            self.raise_all()

    def update_garland_motion(self, now):
        if not self.garland_motion_items:
            return
        for key in list(self.garland_motion_items):
            velocity = self.vel.get(key)
            if velocity and now - velocity[4] <= 0.06:
                vx, vy = velocity[0], velocity[1]
                speed = math.hypot(vx, vy)
            else:
                vx = vy = speed = 0.0
            state = self.garland_sway.setdefault(key, {"amp": 0.0, "phase": 0.0, "time": now})
            dt = max(0.0, min(0.08, now - state["time"]))
            state["time"] = now
            target = min(32.0, speed * 0.026)
            relax_k = 8.0 if target > state["amp"] else 2.2
            state["amp"] += (target - state["amp"]) * (1.0 - math.exp(-relax_k * dt))
            direction = vx if abs(vx) >= abs(vy) else vy
            state["phase"] += dt * (2.7 + speed * 0.006) * (1.0 if direction >= 0 else -1.0)
            active = speed > 8.0 or state["amp"] > 0.08
            if not active and not state.get("active", False):
                continue
            state["active"] = active
            geom = self.geo.get(key)
            if not geom:
                continue
            left, top, width = geom
            width = max(1.0, float(width))
            around = self.around_render.get(key, {})
            height = max(1.0, float(around.get("height", width)))
            amp, phase = state["amp"], state["phase"]
            for group_name, groups in self.garland_motion_items.get(key, {}).items():
                if group_name == "a":
                    continue
                for item in groups:
                    base, coords = item["base"], []
                    axis = item.get("axis", "y")
                    if axis == "x":
                        center = sum(base[1::2]) / max(1, len(base) // 2)
                        p = max(0.0, min(1.0, (center - top) / height))
                    else:
                        center = sum(base[0::2]) / max(1, len(base) // 2)
                        p = max(0.0, min(1.0, (center - left) / width))
                    offset = math.sin(p * math.pi * 2.0 + phase) * amp * math.sin(math.pi * p)
                    for i in range(0, len(base), 2):
                        if axis == "x":
                            coords.extend((base[i] + offset, base[i + 1]))
                        else:
                            coords.extend((base[i], base[i + 1] + offset))
                    self.cv.coords(item["id"], *coords)

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
        self.cv.delete("w%s" % key)
        self.render.pop(key, None)
        self.lights.pop(key, None)

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
        if len(self.chunks) >= 450:
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

    # ---- метель и частицы
    def start_blizzard(self, now=None):
        now = time.time() if now is None else now
        self.bliz = {"t0": now, "len": max(5.0, float(self.cfg["blizzard_len"]))}
        self.bliz_dir = random.choice((-1, 1))
        storm_n = int(min(180, 150 * self.cfg["blizzard_power"]) * self.perf_scale)
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
        # Повышенный лимит частиц, чтобы снегопад и остальные эффекты были густыми
        cap = {"Авто": 320, "Красота": 450, "Экономия": 140}.get(self.cfg["perf_mode"], 320)
        n = int(min(self.cfg["density"], cap) * self.perf_scale)
        self.parts = []
        for k in ks:
            cnt = max(1 if self.cfg["density"] > 0 else 0,
                      int(n / max(1, len(ks)) * KIND_FACTOR.get(k, 1.0)))
            for _ in range(cnt):
                self.parts.append(self.make_particle(k, True))
        if self.bliz:
            storm_n = int(min(180, 150 * self.cfg["blizzard_power"]) * self.perf_scale)
            for _ in range(storm_n):
                self.parts.append(self.make_particle("snow", True, True))
        self.dirty_particles = False
        self.raise_all()

    def make_particle(self, kind, random_y, storm=False):
        cv, cfg = self.cv, self.cfg
        d = random.uniform(0.45, 1.15)
        r = max(2.2, cfg["size"] * 1.15 * d)
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
            col = blend(cfg["snow_color"], 0.65 + 0.35 * min(1.0, d))
            style = cfg["snow_style"]
            p.update(tv=0.85 + 1.65 * d, col=col)
            if style == "Точки":
                p["ids"] = [cv.create_oval(0, 0, 1, 1, fill=col, outline="", tags="flake")]
            else:
                shapes = ("Звёздочки ❄", "Хлопья ❅", "Кристаллы ❆")
                shape = random.choice(shapes) if style == "Все вместе" else style
                p.update(draw="snowflake", snow_shape=shape)
                p["ids"] = [cv.create_line(x, y, x + 1, y + 1, fill=col,
                                           width=max(1.2, r * 0.34), capstyle="round",
                                           joinstyle="round", tags="flake"),
                            cv.create_oval(x, y, x, y, fill=col, outline="", tags="flake")]
        elif kind == "leaf":
            col = random.choice(AUTUMN)
            p.update(draw="poly", shape=LEAF, size=r * 1.5 + 3, tv=0.65 + 1.1 * d,
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
            p.update(draw="poly", tv=0.55 + 0.9 * d, sway=1.2, drag=0.05, mat="spring",
                     amt=0.8, col=col)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline=blend(col, 0.7),
                                          smooth=True, tags="flake")]
        elif kind == "firefly":
            col = random.choice(FLY_COL)
            p.update(draw="fly", lands=False, col=col, tv=0.0, r=max(1.8, cfg["size"] * 0.55 * d))
            p["ids"] = [cv.create_oval(0, 0, 1, 1, fill=blend(col, 0.25), outline="", tags="flake"),
                        cv.create_oval(0, 0, 1, 1, fill=col, outline="", tags="flake")]
        elif kind == "confetti":
            col = random.choice(CONFETTI_COL)
            p.update(draw="poly", shape=RECT, size=r * 0.9 + 2, tv=0.9 + 1.0 * d, sway=1.0,
                     mat="confetti", amt=0.6, col=col, spin=random.uniform(-0.25, 0.25), fspin=0.22)
            p["ids"] = [cv.create_polygon(0, 0, 0, 0, 0, 0, fill=col, outline="", tags="flake")]
        elif kind == "bubble":
            rr = max(3.5, cfg["size"] * 1.6 * d + 3)
            p.update(draw="bubble", r=rr, tv=-(0.45 + 0.85 * d), sway=1.6, lands=False, drag=0.05)
            p["ids"] = [cv.create_oval(0, 0, 1, 1, fill="", outline="#BFE9FF", width=1, tags="flake"),
                        cv.create_oval(0, 0, 1, 1, fill="#FFFFFF", outline="", tags="flake")]
        elif kind == "heart":
            col = random.choice(HEART_COL)
            p.update(draw="glyph", tv=0.75 + 0.95 * d, sway=1.0, mat="heart", amt=0.7, col=col)
            p["ids"] = [cv.create_text(x, y, text="♥", fill=col, tags="flake",
                                       font=("Segoe UI Symbol", max(8, int(r * 3.2) + 4)))]
        elif kind == "star":
            col = random.choice(STAR_COL)
            p.update(draw="glyph", tv=1.2 + 1.8 * d, sway=0.3, drag=0.1, mat=None, col=col, diag=True)
            p["ids"] = [cv.create_text(x, y, text=random.choice("★✦"), fill=col, tags="flake",
                                       font=("Segoe UI Symbol", max(8, int(r * 3) + 4)))]
        elif kind == "rain":
            col = blend("#9CC4F0", 0.6 + 0.4 * min(1.0, d))
            p.update(draw="line", tv=9 + 8 * d, drag=0.3, mob=0.4, sway=0.0, mat=None, col=col)
            p["ids"] = [cv.create_line(0, 0, 1, 1, fill=col, width=2 if d > 0.75 else 1, tags="flake")]
        else:
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
        elif dr == "glyph":
            cv.coords(ids[0], x, y)
        elif dr == "snowflake":
            coords = [x, y]
            shape = p["snow_shape"]
            rot = p["rot"]
            for arm in range(6):
                a = rot + arm * math.tau / 6.0
                ux, uy = math.cos(a), math.sin(a)
                tip = (x + ux * r * 1.55, y + uy * r * 1.55)
                coords.extend(tip)
                branches = ((0.42, 0.30, 0.72), (0.67, 0.23, 0.82)) if shape == "Хлопья ❅" \
                    else (((0.54, 0.34, 0.55), (0.79, 0.18, 0.66)) if shape == "Кристаллы ❆" else ())
                for along, size, angle in branches:
                    bx, by = x + ux * r * along, y + uy * r * along
                    coords.extend((bx, by))
                    for side in (-1, 1):
                        ca, sa = math.cos(a + side * angle), math.sin(a + side * angle)
                        coords.extend((bx + ca * r * size, by + sa * r * size, bx, by))
                coords.extend((x, y))
            cv.coords(ids[0], *coords)
            dot = max(1.0, r * 0.16)
            cv.coords(ids[1], x - dot, y - dot, x + dot, y + dot)
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
                    self.spawn_fx(p["x"], p["y"], -p["vx"] * 0.1, -p["vy"] * 0.1, 10, p["col"], 1.4, drag=0.9)
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

    # ---- гирлянда
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
        clip = getattr(self, "_glow_clip", None)
        if clip:
            a, b = clip_polygon_rect(a, clip), clip_polygon_rect(b, clip)
        if len(a) < 6:
            a = [cx, cy, cx, cy, cx, cy]
        if len(b) < 6:
            b = [cx, cy, cx, cy, cx, cy]
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
            clip = getattr(self, "_glow_clip", None)
            if clip:
                glow_shape = clip_polygon_rect(glow_shape, clip)
                body_shape = clip_polygon_rect(body_shape, clip)
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

    def build_garland_key(self, key, d):
        cv, cfg = self.cv, self.cfg
        if self.window_garland_managed and isinstance(key, int):
            self.lights[key] = []
            return
        if not cfg["garland_enabled"]:
            self.lights[key] = []
            return
        if isinstance(key, str) and not key.startswith("t"):
            self.lights[key] = []
            return
        if cfg["garland_winter_only"] and self.season != "winter":
            self.lights[key] = []
            return
        if cfg["garland_around"] and isinstance(key, int):
            self.lights.setdefault(key, [])
            return
        self.lights[key] = []
        style = self.garland_style()
        tg = ("garland", "w%s" % key)
        old_clip = self._glow_clip
        self._glow_clip = None
        if isinstance(key, int):
            win = next((w for w in self.wins if w[0] == key), None)
            if win:
                _hw, wl, wt, wr, wb, _maxed = win
                self._glow_clip = (wl - self.vx + 1, wt - self.vy + 1,
                                   wr - self.vx - 1, wb - self.vy - 1)
        cols = [cfg["color1"], cfg["color2"], cfg["color3"], cfg["color4"]]
        sag, wire, ww, r = cfg["garland_sag"], cfg["garland_wire"], cfg["garland_width"], cfg["bulb_size"]
        gap = cfg["garland_gap"] * (0.6 if style == "icicle" else 1.0)
        y = d["top"]
        k = (key % 7) if isinstance(key, int) else 0
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
        self._glow_clip = old_clip

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
                s = f["size"] * (0.3 + 0.7 * k)
                cv.coords(f["id"], x - s, y - s, x + s, y + s)
            if odd:
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
            elif kind == "Радуга":
                self.spawn_fx(px, py, 0, 0, life, random.choice(FW_COL),
                              3.5 * sz, drag=1.0)
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

    # ---- метеоры и фейерверки
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
        keep = []
        for m in self.meteors:
            m["x"] += m["vx"]
            m["y"] += m["vy"]
            m["life"] -= 1
            self.spawn_fx(m["x"], m["y"], 0, 0, 3, "#FFFFFF", 2.6 * cfg["meteor_len"], drag=1.0)
            for _ in range(2):
                self.spawn_fx(m["x"] - m["vx"] * random.random(), m["y"] - m["vy"] * random.random(),
                              random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3),
                              16 * cfg["meteor_len"], "#BFD8FF", 1.6, drag=0.9)
            if m["life"] > 0 and -80 < m["x"] < self.W + 80 and m["y"] < self.H:
                keep.append(m)
        self.meteors = keep
        keep = []
        for rk in self.rockets:
            rk["y"] += rk["vy"]
            self.spawn_fx(rk["x"], rk["y"], 0, 0, 2, "#FFFFFF", 2.4, drag=1.0)
            self.spawn_fx(rk["x"], rk["y"], random.uniform(-0.4, 0.4), 0.8, 12, "#FF9F1C", 1.5, drag=0.9)
            if rk["y"] <= rk["ty"]:
                self.firework_burst(rk["x"], rk["y"], rk["col"])
            else:
                keep.append(rk)
        self.rockets = keep

    def spawn_meteor(self):
        dirx = random.choice((-1, 1))
        sp = random.uniform(14, 22)
        x = random.uniform(0.15, 0.95) * self.W if dirx < 0 else random.uniform(0.05, 0.85) * self.W
        self.meteors.append({"x": x, "y": random.uniform(0.02, 0.35) * self.H,
                             "vx": dirx * sp * 0.8, "vy": sp * 0.45, "life": random.randint(25, 45)})

    def spawn_rocket(self):
        self.rockets.append({"x": random.uniform(0.1, 0.9) * self.W, "y": self.H - 60.0,
                             "vy": -random.uniform(9, 13), "ty": random.uniform(0.12, 0.45) * self.H,
                             "col": random.choice(FW_COL)})

    def firework_burst(self, x, y, col):
        size = self.cfg["fw_size"]
        n = min(90, int(48 * size))
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
                elif name == "birds":
                    self.cfg["birds_mode"] = "Выкл"
                else:
                    self.cfg[name + "_enabled"] = False

    def build_aurora(self):
        cv = self.cv
        rng = random.Random(481)
        count = max(12, min(26, int(self.W / 85)))
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
                "top": rng.uniform(0.0, 0.18),
                "length": rng.uniform(0.52, 1.08),
                "phase": rng.uniform(0.0, math.tau),
                "bend": rng.uniform(22.0, 70.0),
                "fold": rng.uniform(8.0, 26.0),
                "width": rng.uniform(9.0, 32.0),
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

    def build_stars(self):
        cv, cfg = self.cv, self.cfg
        rnd = random.Random(7)
        hh = self.H * cfg["stars_height"] / 100.0
        self.stars = []
        for _ in range(int(cfg["stars_count"])):
            x, y = rnd.uniform(0, self.W), rnd.uniform(0, hh)
            ch = rnd.choice(("✦", "✦", "✧", "⋆", "✶", "·"))
            sz = rnd.choice((7, 8, 9, 10, 12, 14, 17))
            tint = rnd.choice(("#FFFFFF", "#CFE3FF", "#FFF2C8", "#FFD6F0"))
            i = cv.create_text(x, y, text=ch, fill=tint, font=("Segoe UI Symbol", sz), tags="e_stars")
            self.stars.append({"id": i, "ph": rnd.uniform(0, 6.3), "tint": tint})

    def update_stars(self, now):
        if self.frame % 6:
            return
        tw = self.cfg["stars_twinkle"]
        cv = self.cv
        for s in self.stars:
            f = 0.5 + 0.5 * (0.5 + 0.5 * math.sin(now * tw * 2 + s["ph"]))
            cv.itemconfigure(s["id"], fill=blend(s["tint"], f))

    def build_sky(self):
        cv, cfg = self.cv, self.cfg
        body = cfg["sky_body"]
        if body == "Авто":
            body = "Солнце" if 6 <= time.localtime().tm_hour < 19 else "Луна"
        L, T, R, B = self.widget_mon()
        S = float(cfg["sky_size"])
        cx = R - S * 1.5 if cfg["sky_corner"].startswith("Прав") else L + S * 1.5
        cy = T + S * 1.35
        self.sky = {"body": body, "cx": cx, "cy": cy, "S": S, "rays": []}
        tg = "e_sky"
        if body == "Луна":
            Rr = S * 0.5
            for k, col, w in ((1.9, "#5F78BF", 1), (1.55, "#8FA6E0", 1), (1.28, "#B9C9F2", 2)):
                cv.create_oval(cx - Rr * k, cy - Rr * k, cx + Rr * k, cy + Rr * k, fill="",
                               outline=col, width=w, tags=tg)
            cv.create_oval(cx - Rr, cy - Rr, cx + Rr, cy + Rr, fill="#F6F1D9", outline="#FFFFFF",
                           width=2, tags=tg)
            for (ox, oy, rr) in ((-0.28, -0.2, 0.17), (0.22, 0.12, 0.12), (0.05, -0.42, 0.09),
                                 (-0.2, 0.32, 0.1), (0.38, -0.25, 0.07)):
                cv.create_oval(cx + Rr * (ox - rr), cy + Rr * (oy - rr), cx + Rr * (ox + rr),
                               cy + Rr * (oy + rr), fill="#DAD4B8", outline="#C9C3A5", tags=tg)
            phase = cfg["sky_phase"]
            if phase == "Авто":
                a = self.moon_age()
                phase = "Полная" if 0.4 <= a < 0.6 else ("Растущая" if a < 0.5 else "Убывающая")
            if phase != "Полная":
                sgn = -1 if phase == "Растущая" else 1
                mx = cx + sgn * Rr * 0.55
                cv.create_oval(mx - Rr * 0.98, cy - Rr * 0.98, mx + Rr * 0.98, cy + Rr * 0.98,
                               fill=KEY, outline="", tags=tg)
            rnd = random.Random(3)
            for _ in range(5):
                a = rnd.uniform(0, 6.283)
                dd = Rr * rnd.uniform(2.1, 2.8)
                cv.create_text(cx + math.cos(a) * dd, cy + math.sin(a) * dd, text="✦",
                               fill="#FFFFFF", font=("Segoe UI Symbol", rnd.choice((8, 10, 12))), tags=tg)
        else:
            Rr = S * 0.42
            for k, col in ((2.2, "#FFE9A8"), (1.8, "#FFD97A"), (1.5, "#FFC94D")):
                cv.create_oval(cx - Rr * k, cy - Rr * k, cx + Rr * k, cy + Rr * k, fill="",
                               outline=col, width=2, tags=tg)
            for _ in range(16):
                self.sky["rays"].append(cv.create_polygon(0, 0, 1, 0, 1, 1, fill="#FFC107",
                                                          outline="", tags=tg))
            for k, col in ((1.0, "#FFB300"), (0.82, "#FFC107"), (0.62, "#FFD54F"), (0.4, "#FFE082")):
                cv.create_oval(cx - Rr * k, cy - Rr * k, cx + Rr * k, cy + Rr * k, fill=col,
                               outline="", tags=tg)
            self.update_sky(self.now, True)

    def update_sky(self, now, force=False):
        sk = self.sky
        if not sk["rays"] or (self.frame % 4 and not force):
            return
        cv = self.cv
        cx, cy, S = sk["cx"], sk["cy"], sk["S"]
        r0 = S * 0.42 * 1.12
        for i, rid in enumerate(sk["rays"]):
            a = now * 0.2 + i * 2 * math.pi / 16
            ln = S * (0.98 if i % 2 == 0 else 0.74) * (0.94 + 0.06 * math.sin(now * 2 + i))
            wd = 0.10
            cv.coords(rid, cx + math.cos(a - wd) * r0, cy + math.sin(a - wd) * r0,
                      cx + math.cos(a) * ln, cy + math.sin(a) * ln,
                      cx + math.cos(a + wd) * r0, cy + math.sin(a + wd) * r0)
            cv.itemconfigure(rid, fill="#FFC107" if i % 2 == 0 else "#FFD54F")

    def build_neon(self):
        cv, w = self.cv, self.cfg["neon_width"]
        self.neon = [cv.create_rectangle(0, 0, 1, 1, outline="#550055", width=w * 3 + 2, state="hidden", tags="e_neon"),
                     cv.create_rectangle(0, 0, 1, 1, outline="#AA00AA", width=w * 2, state="hidden", tags="e_neon"),
                     cv.create_rectangle(0, 0, 1, 1, outline="#FFFFFF", width=w, state="hidden", tags="e_neon")]
        self.neon_vis, self.neon_rect, self.neon_col = False, None, None

    def neon_color(self, now):
        cfg = self.cfg
        m = cfg["neon_mode"]
        t = now * cfg["neon_speed"]
        if m == "Фиолетовый":
            return mix("#9B5DE5", "#F15BB5", 0.5 + 0.5 * math.sin(t))
        if m == "Тёплый":
            return mix("#FF6B35", "#FFD166", 0.5 + 0.5 * math.sin(t))
        return mix("#00BBF9", "#00F5D4", 0.5 + 0.5 * math.sin(t))

    def update_neon(self, now):
        cv = self.cv
        fg = self.get_fg()
        rect = None
        for (hw, l, t, r, b, mx) in self.wins:
            if hw == fg and not mx:
                rect = (int(l - self.vx), int(t - self.vy), int(r - self.vx), int(b - self.vy))
                break
        if rect is None:
            if self.neon_vis:
                for i in self.neon:
                    cv.itemconfigure(i, state="hidden")
                self.neon_vis = False
            return
        if rect != self.neon_rect:
            for i in self.neon:
                cv.coords(i, *rect)
            self.neon_rect = rect
        col = self.neon_color(now)
        if col != self.neon_col or not self.neon_vis:
            self.neon_col = col
            for i, c in zip(self.neon, (blend(col, 0.35), blend(col, 0.7), mix(col, "#FFFFFF", 0.7))):
                cv.itemconfigure(i, outline=c, state="normal")
            self.neon_vis = True

    # ---- сезонное дерево (зима — ёлка, весна — сакура, лето — лиственное, осень — клён)
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
        self.tree_lights = []
        season = current_season(cfg)

        if season == "spring":
            # Сакура: тёмный ствол, ветви, пышная розовая крона и цветки
            cv.create_line(cx, by, cx, by - Th * 0.62, fill="#5D3A2E", width=max(4, int(13 * s)),
                           capstyle="round", tags=tg)
            for dx, dy, w in ((-0.26, -0.52, 7), (0.26, -0.55, 7), (-0.18, -0.74, 5), (0.20, -0.76, 5)):
                cv.create_line(cx, by - Th * 0.42, cx + Tw * dx, by + Th * dy,
                               fill="#5D3A2E", width=max(2, int(w * s)), capstyle="round", tags=tg)
            puffs = (
                (-0.34, -0.62, 42, "#F48FB1"),
                (0.34, -0.64, 42, "#F48FB1"),
                (0.0, -0.84, 48, "#F8BBD0"),
                (-0.22, -0.78, 38, "#FFCDD2"),
                (0.24, -0.80, 38, "#F8BBD0"),
                (0.0, -0.60, 44, "#F48FB1"),
            )
            for px, py, rad, col in puffs:
                rr = rad * s
                cy_p = by + Th * py
                cv.create_oval(cx + Tw * px - rr, cy_p - rr * 0.85,
                               cx + Tw * px + rr, cy_p + rr * 0.85,
                               fill=col, outline=blend(col, 0.78), width=1, tags=tg)
            for _ in range(18):
                bx = cx + rnd.uniform(-Tw * 0.52, Tw * 0.52)
                by_b = by - Th * rnd.uniform(0.52, 0.94)
                rr = rnd.uniform(3.5, 6.0) * s
                c_b = rnd.choice(("#FFFFFF", "#FCE4EC", "#F06292"))
                bl = cv.create_oval(bx - rr, by_b - rr, bx + rr, by_b + rr, fill=c_b, outline="", tags=tg)
                self.tree_lights.append((bl, c_b, rnd.uniform(0, 6.3)))
            return

        if season == "summer":
            # Летнее зелёное дерево с мягкой кроной и солнечными бликами
            cv.create_rectangle(cx - 10 * s, by - Th * 0.56, cx + 10 * s, by,
                                fill="#6D4C41", outline="#4E342E", tags=tg)
            for dx, dy in ((-0.28, -0.50), (0.28, -0.52), (-0.16, -0.72), (0.18, -0.74)):
                cv.create_line(cx, by - Th * 0.40, cx + Tw * dx, by + Th * dy,
                               fill="#6D4C41", width=max(2, int(6 * s)), capstyle="round", tags=tg)
            puffs = (
                (-0.35, -0.60, 44, "#2E7D32"),
                (0.35, -0.62, 44, "#2E7D32"),
                (0.0, -0.84, 50, "#43A047"),
                (-0.22, -0.76, 40, "#66BB6A"),
                (0.22, -0.78, 40, "#66BB6A"),
                (0.0, -0.58, 46, "#388E3C"),
            )
            for px, py, rad, col in puffs:
                rr = rad * s
                cy_p = by + Th * py
                cv.create_oval(cx + Tw * px - rr, cy_p - rr * 0.85,
                               cx + Tw * px + rr, cy_p + rr * 0.85,
                               fill=col, outline=blend(col, 0.7), width=1, tags=tg)
            for _ in range(12):
                bx = cx + rnd.uniform(-Tw * 0.45, Tw * 0.45)
                by_b = by - Th * rnd.uniform(0.55, 0.92)
                rr = rnd.uniform(3.0, 5.0) * s
                bl = cv.create_oval(bx - rr, by_b - rr, bx + rr, by_b + rr,
                                   fill="#AED581", outline="", tags=tg)
                self.tree_lights.append((bl, "#AED581", rnd.uniform(0, 6.3)))
            return

        if season == "autumn":
            # Осеннее дерево в золотых и багряных тонах
            cv.create_rectangle(cx - 10 * s, by - Th * 0.56, cx + 10 * s, by,
                                fill="#5D4037", outline="#3E2723", tags=tg)
            for dx, dy in ((-0.28, -0.50), (0.28, -0.52), (-0.16, -0.72), (0.18, -0.74)):
                cv.create_line(cx, by - Th * 0.40, cx + Tw * dx, by + Th * dy,
                               fill="#5D4037", width=max(2, int(6 * s)), capstyle="round", tags=tg)
            puffs = (
                (-0.35, -0.60, 44, "#D84315"),
                (0.35, -0.62, 44, "#EF6C00"),
                (0.0, -0.84, 50, "#F9A825"),
                (-0.22, -0.76, 40, "#FF8F00"),
                (0.22, -0.78, 40, "#E65100"),
                (0.0, -0.58, 46, "#BF360C"),
            )
            for px, py, rad, col in puffs:
                rr = rad * s
                cy_p = by + Th * py
                cv.create_oval(cx + Tw * px - rr, cy_p - rr * 0.85,
                               cx + Tw * px + rr, cy_p + rr * 0.85,
                               fill=col, outline=blend(col, 0.65), width=1, tags=tg)
            for _ in range(14):
                bx = cx + rnd.uniform(-Tw * 0.46, Tw * 0.46)
                by_b = by - Th * rnd.uniform(0.54, 0.92)
                rr = rnd.uniform(3.2, 5.2) * s
                c_a = rnd.choice(("#FFD54F", "#FF7043", "#FFCA28"))
                bl = cv.create_oval(bx - rr, by_b - rr, bx + rr, by_b + rr, fill=c_a, outline="", tags=tg)
                self.tree_lights.append((bl, c_a, rnd.uniform(0, 6.3)))
            return

        # Зима: новогодняя ёлка с гирляндой, звездой и подарками
        cv.create_rectangle(cx - 9 * s, by - Th * 0.14, cx + 9 * s, by, fill="#6D4C41",
                            outline="#4E342E", tags=tg)
        tiers = ((0.50, 0.10, 0.50, "#1B8A3A"), (0.74, 0.34, 0.40, "#1F9D44"),
                 (0.97, 0.60, 0.29, "#28B04F"))
        pal = ["#FF3B30", "#FFD60A", "#34C759", "#0A84FF", "#FF6FD8", "#FF9F1C"]
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
        target = 0.55 if cfg["perf_mode"] == "Авто" else 0.65
        budget = 1000.0 / max(10, cfg["fps"]) * target
        scene_per_frame = self.scene_ms * min(4.0, self.scene_rate / max(10, cfg["fps"]))
        load = self.ms + scene_per_frame
        if load > budget and self.perf_scale > 0.45:
            self.perf_scale = max(0.45, self.perf_scale * 0.8)
            self.dirty_particles = True
            self.perf_cool = now + 0.8
        elif load < budget * 0.35 and self.perf_scale < 1.0:
            self.perf_scale = min(1.0, self.perf_scale * 1.15)
            self.dirty_particles = True
            self.perf_cool = now + 1.2

    def lead_offset(self, hw, l, t, now, lead):
        s = self.vel.get(hw)
        if s is None:
            self.vel[hw] = [0.0, 0.0, l, t, now]
            return 0.0, 0.0
        if l != s[2] or t != s[3]:
            dt = now - s[4]
            if dt > 0.002:
                s[0] = s[0] * 0.4 + (l - s[2]) / dt * 0.6
                s[1] = s[1] * 0.4 + (t - s[3]) / dt * 0.6
            s[2], s[3], s[4] = l, t, now
        elif now - s[4] > 0.04:
            s[0] = s[1] = 0.0
        if lead <= 0 or abs(s[0]) + abs(s[1]) < 60:
            return 0.0, 0.0
        return (max(-40.0, min(40.0, s[0] * lead)), max(-40.0, min(40.0, s[1] * lead)))

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
        if len(self.chunks) >= 450:
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

    def build_clouds(self):
        cv, cfg = self.cv, self.cfg
        body, shade = {"Белые": ("#F7FAFF", "#D5E0F2"), "Серые (пасмурно)": ("#B9C0CC", "#8C95A5"),
                       "Закат (розовые)": ("#FFD6C9", "#E8A9B8")}.get(cfg["clouds_tint"],
                                                                   ("#F7FAFF", "#D5E0F2"))
        rnd = random.Random(21)
        self.clouds = []
        hmax = max(self.H * 0.08, self.H * cfg["clouds_height"] / 100.0)
        for i in range(int(cfg["clouds_count"])):
            w = rnd.uniform(220, 440)
            h = w * 0.3
            x = rnd.uniform(-w, self.W)
            y = rnd.uniform(self.H * 0.02, hmax)
            tg = ("e_clouds", "cl%d" % i)
            cv.create_oval(x + w * 0.04, y + h * 0.38, x + w * 0.96, y + h * 1.08, fill=shade,
                           outline="", tags=tg)
            for (bx, by, bw, bh) in ((0.0, 0.32, 0.42, 0.62), (0.18, 0.0, 0.42, 0.85),
                                     (0.42, 0.08, 0.46, 0.80), (0.62, 0.28, 0.38, 0.62)):
                cv.create_oval(x + w * bx, y + h * by, x + w * (bx + bw), y + h * (by + bh) + h * 0.1,
                               fill=body, outline="", tags=tg)
            cv.create_oval(x + w * 0.05, y + h * 0.55, x + w * 0.95, y + h * 0.98, fill=body,
                           outline="", tags=tg)
            self.clouds.append({"tag": "cl%d" % i, "x": x, "w": w, "v": rnd.uniform(0.25, 0.7)})

    def update_clouds(self, now):
        if self.frame % 2:
            return
        sp = self.cfg["clouds_speed"] * 2.0
        for c in self.clouds:
            dx = c["v"] * sp
            self.cv.move(c["tag"], dx, 0)
            c["x"] += dx
            if c["x"] > self.W + 30:
                back = self.W + c["w"] + 60
                self.cv.move(c["tag"], -back, 0)
                c["x"] -= back

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
                      "v": random.uniform(1.6, 2.6), "birds": []}
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
        sp = cfg["birds_speed"]
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

    def build_strip(self):
        cv, cfg = self.cv, self.cfg
        w = cfg["strip_width"]
        self.strip = []
        mons = self.mons or [{"work": (self.vx, self.vy, self.vx + self.W, self.vy + self.H)}]
        for m in mons:
            wl, wt, wr, wb = m["work"]
            L, T, R, B = wl - self.vx, wt - self.vy, wr - self.vx, wb - self.vy
            per = 2.0 * ((R - L) + (B - T))
            pos = 0.0
            for (x1, y1, x2, y2) in ((L, T + w / 2, R, T + w / 2), (R - w / 2, T, R - w / 2, B),
                                     (R, B - w / 2, L, B - w / 2), (L + w / 2, B, L + w / 2, T)):
                length = math.hypot(x2 - x1, y2 - y1)
                n = max(1, int(length / 40))
                for k in range(n):
                    a, b = k / float(n), (k + 1) / float(n)
                    i = cv.create_line(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a, x1 + (x2 - x1) * b,
                                       y1 + (y2 - y1) * b, width=w, fill=cfg["strip_color"], tags="e_strip")
                    self.strip.append((i, (pos + length * (a + b) / 2) / per))
                pos += length

    def update_strip(self, now):
        if self.frame % 4:
            return
        cfg, cv = self.cfg, self.cv
        t = now * cfg["strip_speed"] * 0.1
        mode = cfg["strip_mode"]
        season_col = {"winter": "#BFE3FF", "autumn": "#FF9F1C", "spring": "#FFB3D9", "summer": "#FFE066"}[self.season]
        for i, frac in self.strip:
            ph = (frac * 3 - t) % 1.0
            wave = 0.5 + 0.5 * math.sin(ph * 6.283)
            if mode == "Тёплый":
                c = mix("#FF6B35", "#F72585", wave)
            elif mode == "Холодный":
                c = mix("#4CC9F0", "#7209B7", wave)
            elif mode == "По сезону":
                c = blend(season_col, 0.45 + 0.55 * wave)
            else:
                c = blend(cfg["strip_color"], 0.45 + 0.55 * wave)
            cv.itemconfigure(i, fill=c)

    def start_santa(self):
        if self.santa:
            return
        d = random.choice((1, -1))
        s = self.cfg["santa_size"] / 100.0
        self.santa = {"d": d, "x": -300 * s if d > 0 else self.W + 300 * s, "t": 0, "gift": 0}

    def build_santa(self):
        pass

    def update_santa(self, now):
        cfg, cv = self.cfg, self.cv
        st = self.santa
        if st is None:
            if cfg["santa_enabled"]:
                if self.next_santa is None:
                    self.next_santa = now + 6
                elif now >= self.next_santa:
                    self.start_santa()
                    self.next_santa = now + cfg["santa_every"] * 60 * random.uniform(0.7, 1.3)
            return
        s = cfg["santa_size"] / 100.0
        st["x"] += st["d"] * cfg["santa_speed"] * 1.6
        st["t"] += 1
        y = self.H * cfg["santa_height"] / 100.0 + 90 * s + 16 * math.sin(st["t"] * 0.05)
        cv.delete("e_santa")
        self.draw_santa(st["x"], y, st["d"], s, st["t"])
        if self.mask_items and cfg["desktop_only"]:
            cv.tag_lower("e_santa", "mask")
        if st["t"] % 2 == 0:
            self.spawn_fx(st["x"] - st["d"] * 70 * s, y - 20 * s + random.uniform(-8, 8),
                          -st["d"] * random.uniform(0.3, 1.2), random.uniform(-0.3, 0.8), 24,
                          random.choice(("#FFE066", "#FFFFFF", "#FFB347")), 2.0, g=0.03, drag=0.96)
        if cfg["santa_gifts"]:
            st["gift"] += 1
            if st["gift"] > 50:
                st["gift"] = 0
                self.spawn_gift(st["x"] - st["d"] * 10 * s, y + 10 * s)
        if (st["d"] > 0 and st["x"] > self.W + 320 * s) or (st["d"] < 0 and st["x"] < -320 * s):
            self.santa = None
            cv.delete("e_santa")

    def draw_santa(self, x, y, d, s, t):
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

        line([(34, -22), (63, -22)], "#8D6E63", 1)
        for n, dx in enumerate((78, 120, 162)):
            ph = t * 0.35 + n * 1.3
            bob = math.sin(ph) * 2
            for lx, sg in ((-8, 1), (-3, -1), (7, -1), (12, 1)):
                sw = math.sin(ph + (0 if sg > 0 else 3.14)) * 7
                line([(dx + lx, -16 + bob), (dx + lx + sw, -2 - abs(sw) * 0.3)], "#6D4C41", 2)
            oval(dx, -20 + bob, 15, 8, "#8D5524", "#5D3A1A")
            oval(dx - 14, -22 + bob, 3, 3, "#8D5524")
            poly([(dx + 9, -24 + bob), (dx + 20, -38 + bob), (dx + 26, -34 + bob), (dx + 14, -18 + bob)],
                 "#8D5524", smooth=True)
            oval(dx + 25, -37 + bob, 7, 5, "#8D5524", "#5D3A1A")
            line([(dx + 22, -41 + bob), (dx + 18, -52 + bob), (dx + 22, -58 + bob)], "#D7CCC8", 2)
            line([(dx + 19, -50 + bob), (dx + 13, -54 + bob)], "#D7CCC8", 2)
            line([(dx + 26, -41 + bob), (dx + 27, -52 + bob), (dx + 31, -57 + bob)], "#D7CCC8", 2)
            if n == 2:
                oval(dx + 31, -36 + bob, 5.5, 5.5, "", "#FF9090")
            oval(dx + 31, -36 + bob, 2.6, 2.6, "#FF3030" if n == 2 else "#3E2723")
            oval(dx + 27, -39 + bob, 1, 1, "#000000")
            if n < 2:
                line([(dx + 8, -20), (dx + 27, -20)], "#8D6E63", 1)
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


# ---------------------------------------------------------------- Гирлянды, закреплённые за каждым окном
class WindowGarlandManager(threading.Thread):
    def __init__(self, cfg):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.root = None
        self.frames = {}
        self.visible = True
        self.stopping = threading.Event()
        self.next_enumeration = 0.0
        self.last_signature = None

    def set_visible(self, value):
        self.visible = bool(value)

    def stop(self):
        self.stopping.set()

    def signature(self):
        cfg = self.cfg
        return (self.visible, cfg["garland_enabled"], cfg["garland_around"],
                cfg["garland_winter_only"], cfg["skip_maximized"],
                current_season(cfg), cfg["garland_style"], cfg["garland_glow"],
                cfg["garland_sag"], cfg["garland_gap"], cfg["bulb_size"],
                cfg["garland_width"], cfg["garland_wire"], cfg["blink_mode"],
                cfg["blink_speed"],
                tuple(cfg[k] for k in ("color1", "color2", "color3", "color4")))

    def run(self):
        try:
            root = tk.Tk()
            root.report_callback_exception = report_tk_exception
            root.withdraw()
            self.root = root
            root.after(0, self.pulse)
            root.mainloop()
        except Exception:
            log_error("window garland manager")
        finally:
            for frame in list(self.frames.values()):
                try:
                    frame["window"].destroy()
                except Exception:
                    pass
            self.frames.clear()
            if self.root:
                try:
                    self.root.destroy()
                except Exception:
                    pass

    def create_frame(self, win):
        hwnd, left, top, right, bottom, _maxed = win
        width, height = max(1, right - left), max(1, bottom - top)
        window = tk.Toplevel(self.root)
        window.withdraw()
        window.overrideredirect(True)
        window.geometry("%dx%d+0+0" % (width, height))
        window.configure(bg=KEY)
        window.attributes("-transparentcolor", KEY)
        canvas = tk.Canvas(window, bg=KEY, highlightthickness=0,
                           width=width, height=height)
        canvas.pack(fill="both", expand=True)
        window.update_idletasks()
        overlay_hwnd = int(user32.GetAncestor(window.winfo_id(), 2) or window.winfo_id())
        ex = user32.GetWindowLongW(overlay_hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            overlay_hwnd, GWL_EXSTYLE,
            ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        style = user32.GetWindowLongW(overlay_hwnd, GWL_STYLE)
        style = (style & 0x7FFFFFFF) | WS_CHILD
        user32.SetWindowLongW(overlay_hwnd, GWL_STYLE, style)
        user32.SetParent(overlay_hwnd, hwnd)
        engine = Engine(canvas, self.cfg, (0, 0, width, height))
        engine.garland_target = hwnd
        engine.garland_target_locked = True
        state = {"window": window, "canvas": canvas, "hwnd": overlay_hwnd,
                 "engine": engine, "size": None, "shown": False,
                 "signature": None, "last_blink": 0.0}
        self.frames[hwnd] = state
        return state

    def update_frame(self, win, state, now, signature):
        cfg = self.cfg
        hwnd = win[0]
        client = wintypes.RECT()
        valid = (self.visible and cfg["garland_enabled"] and
                 user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd) and
                 user32.GetClientRect(hwnd, ctypes.byref(client)))
        if valid:
            width, height = client.right - client.left, client.bottom - client.top
            valid = width >= 150 and height >= 80
            maxed = bool(user32.IsZoomed(hwnd))
            valid = valid and not (cfg["skip_maximized"] and maxed)
            season = current_season(cfg)
            valid = valid and not (cfg["garland_winter_only"] and season != "winter")
        if not valid:
            if state["shown"]:
                state["window"].withdraw()
                state["shown"] = False
            if state["signature"] != (signature, False):
                state["engine"].update_around_garland([])
                state["signature"] = (signature, False)
            return

        size = (width, height)
        size_changed = state["size"] != size
        if size_changed:
            state["window"].geometry("%dx%d+0+0" % (width, height))
            state["canvas"].configure(width=width, height=height)
            state["engine"].W, state["engine"].H = width, height
        if not state["shown"]:
            state["window"].deiconify()
            state["shown"] = True
            size_changed = True
        if size_changed:
            user32.SetWindowPos(
                state["hwnd"], 0, 0, 0, width, height,
                SWP_NOACTIVATE | SWP_SHOWWINDOW)
            state["engine"].vx = state["engine"].vy = 0
            state["size"] = size

        draw_sig = (signature, cfg["garland_around"], size)
        if draw_sig != state["signature"] or size_changed:
            engine = state["engine"]
            engine.season = season
            edges = visible_window_edges(
                [(hwnd, 0, 0, width, height, maxed)], False, hwnd)
            if not cfg["garland_around"]:
                top_y = 8
                edges = [edge for edge in edges
                         if edge[1] == "h" and edge[4] == top_y]
            engine.update_around_garland(edges)
            state["signature"] = draw_sig
            state["last_blink"] = 0.0
        if now - state["last_blink"] >= 0.025:
            state["engine"].blink(now)
            state["last_blink"] = now

    def pulse(self):
        if self.stopping.is_set():
            self.root.quit()
            return
        try:
            now = time.time()
            if now >= self.next_enumeration:
                wins = get_windows()
                for win in wins:
                    if win[0] not in self.frames:
                        self.create_frame(win)
                visible_ids = {win[0] for win in wins}
                for hwnd, state in list(self.frames.items()):
                    if not user32.IsWindow(hwnd):
                        try:
                            state["window"].destroy()
                        except Exception:
                            pass
                        del self.frames[hwnd]
                    elif hwnd not in visible_ids:
                        if state["shown"]:
                            state["window"].withdraw()
                            state["shown"] = False
                self.next_enumeration = now + 0.20

            signature = self.signature()
            for hwnd, state in list(self.frames.items()):
                win = (hwnd, 0, 0, 0, 0, bool(user32.IsZoomed(hwnd)))
                self.update_frame(win, state, now, signature)
        except Exception:
            log_error("window garland pulse")
        self.root.after(8 if self.visible else 100, self.pulse)


# ---------------------------------------------------------------- Синхронная гирлянда на окне настроек
class PinnedGarland(threading.Thread):
    def __init__(self, target_hwnd, cfg):
        super().__init__(daemon=True)
        self.target_hwnd = int(target_hwnd)
        self.cfg = cfg
        self.root = None
        self.canvas = None
        self.engine = None
        self.overlay_hwnd = 0
        self.visible = True
        self.target_visible = False
        self.stopping = threading.Event()
        self.last_rect = None
        self.last_graphics = None
        self.last_blink = 0.0

    def set_visible(self, value):
        self.visible = bool(value)

    def stop(self):
        self.stopping.set()

    def graphics_signature(self):
        cfg = self.cfg
        season = current_season(cfg)
        style = cfg["garland_style"]
        if style.startswith("Авто"):
            style = AUTO_STYLE[season]
        return (self.visible, cfg["garland_enabled"], cfg["garland_around"],
                cfg["garland_winter_only"], season, cfg["skip_maximized"], style,
                cfg["garland_glow"], cfg["garland_sag"], cfg["garland_gap"],
                cfg["bulb_size"], cfg["garland_width"], cfg["garland_wire"],
                tuple(cfg[k] for k in ("color1", "color2", "color3", "color4")))

    def run(self):
        try:
            rect = wintypes.RECT()
            if not user32.GetWindowRect(self.target_hwnd, ctypes.byref(rect)):
                return
            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
            width, height = max(1, right - left), max(1, bottom - top)
            root = tk.Tk()
            root.report_callback_exception = report_tk_exception
            self.root = root
            root.withdraw()
            root.overrideredirect(True)
            root.geometry("%dx%d%+d%+d" % (width, height, left, top))
            root.configure(bg=KEY)
            root.attributes("-transparentcolor", KEY)
            canvas = tk.Canvas(root, bg=KEY, highlightthickness=0,
                               width=width, height=height)
            canvas.pack(fill="both", expand=True)
            root.update_idletasks()
            self.overlay_hwnd = int(user32.GetAncestor(root.winfo_id(), 2) or root.winfo_id())
            ex = user32.GetWindowLongW(self.overlay_hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                self.overlay_hwnd, GWL_EXSTYLE,
                ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
            user32.SetWindowLongW(self.overlay_hwnd, GWL_HWNDPARENT, self.target_hwnd)
            self.canvas = canvas
            self.engine = Engine(canvas, self.cfg, (left, top, width, height))
            self.engine.garland_target = self.target_hwnd
            self.engine.garland_target_locked = True
            self.last_rect = (left, top, right, bottom)
            root.deiconify()
            user32.SetWindowPos(
                self.overlay_hwnd, self.target_hwnd, left, top, width, height,
                SWP_NOACTIVATE | SWP_NOOWNERZORDER)
            self.target_visible = True
            self.apply_garland(True)
            root.after(2, self.pulse)
            root.mainloop()
        except Exception:
            log_error("pinned garland thread")
        finally:
            if self.root:
                try:
                    self.root.destroy()
                except Exception:
                    pass

    def apply_garland(self, force=False):
        cfg = self.cfg
        season = current_season(cfg)
        self.engine.season = season
        enabled = (self.visible and self.target_visible and cfg["garland_enabled"] and
                   cfg["garland_around"] and
                   (not cfg["garland_winter_only"] or season == "winter"))
        edges = []
        if enabled:
            rect = wintypes.RECT()
            if user32.GetWindowRect(self.target_hwnd, ctypes.byref(rect)):
                win = (self.target_hwnd, rect.left, rect.top, rect.right, rect.bottom,
                       bool(user32.IsZoomed(self.target_hwnd)))
                edges = visible_window_edges([win], cfg["skip_maximized"], self.target_hwnd)
        self.engine.update_around_garland(edges)
        self.last_graphics = self.graphics_signature()
        if force:
            self.last_blink = 0.0

    def pulse(self):
        if self.stopping.is_set():
            self.root.quit()
            return
        try:
            target = self.target_hwnd
            valid = (user32.IsWindowVisible(target) and not user32.IsIconic(target))
            rect = wintypes.RECT()
            valid = valid and bool(user32.GetWindowRect(target, ctypes.byref(rect)))
            valid = valid and rect.right - rect.left >= 150 and rect.bottom - rect.top >= 80
            if not valid:
                if self.root.winfo_viewable():
                    self.root.withdraw()
                if self.target_visible:
                    self.target_visible = False
                    self.apply_garland()
                self.root.after(4, self.pulse)
                return

            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
            width, height = right - left, bottom - top
            restored = False
            if not self.target_visible:
                self.target_visible = True
                self.root.deiconify()
                self.last_graphics = None
                restored = True
            old = self.last_rect
            if old != (left, top, right, bottom) or restored:
                if not self.root.winfo_viewable() and self.visible:
                    self.root.deiconify()
                old_size = (old[2] - old[0], old[3] - old[1]) if old else (0, 0)
                if old_size != (width, height):
                    self.root.geometry("%dx%d%+d%+d" % (width, height, left, top))
                    self.canvas.configure(width=width, height=height)
                    self.engine.W, self.engine.H = width, height
                if self.overlay_hwnd:
                    user32.SetWindowPos(
                        self.overlay_hwnd, self.target_hwnd, left, top, width, height,
                        SWP_NOACTIVATE | SWP_NOOWNERZORDER)
                self.engine.vx, self.engine.vy = left, top
                self.last_rect = (left, top, right, bottom)
                if old_size != (width, height):
                    self.apply_garland(True)

            signature = self.graphics_signature()
            if signature != self.last_graphics:
                self.apply_garland()
            now = time.time()
            if now - self.last_blink >= 0.025 and self.visible:
                self.engine.blink(now)
                self.last_blink = now
        except Exception:
            log_error("pinned garland update")
        self.root.after(4, self.pulse)


# ---------------------------------------------------------------- Оверлей в своём потоке
class Overlay(threading.Thread):
    def __init__(self, cfg):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.q = queue.Queue()
        self.engine = None
        self.root = None
        self.initial_target_hwnd = 0
        self.user_paused = False
        self.auto_paused = False
        self.shown = True
        self.stopping = False
        self.mon_rects = []
        self.last_check = 0.0
        self.last_mons = 0.0
        self.window_hook, self.window_event_proc = None, None
        self.fast_after_id, self.last_fast_wake = None, 0.0
        self.window_garland_manager = None

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
            self.engine.window_garland_managed = True
            self.engine.garland_target_locked = True
            self.install_window_hook()
            self.fast()
            self.slow()
            root.mainloop()
        except Exception:
            log_error("overlay thread")
        finally:
            if self.window_garland_manager:
                self.window_garland_manager.stop()
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
        if self.window_garland_manager:
            self.window_garland_manager.set_visible(want)
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
        self.fast_after_id = None
        delay = 50
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
                    delay = 16
            else:
                delay = 150
        except Exception:
            log_error("overlay fast")
        self.fast_after_id = self.root.after(delay, self.fast)

    def slow(self):
        try:
            if self.active:
                self.engine.tick(time.time())
        except Exception:
            log_error("overlay slow")
        fps = self.cfg["fps"]
        if self.cfg["perf_mode"] == "Экономия":
            fps = min(fps, 25)
        self.root.after(max(8, int(1000 / max(5, fps))) if self.active else 150, self.slow)


# ---------------------------------------------------------------- Интерфейс (без RGB, с тактильным откликом)
THEMES = {
    "Тёмная (фиолет)": {"bg": "#12102B", "side": "#0D0B22", "card": "#1B1840", "card2": "#262253",
                        "fg": "#F2F0FF", "muted": "#9A95C7", "accent": "#8B5CF6", "accent2": "#A78BFA",
                        "line": "#2D2961", "track": "#3A3570", "on_acc": "#FFFFFF"},
    "Тёмная (синяя)": {"bg": "#0B1426", "side": "#08101F", "card": "#12203A", "card2": "#1A2D4F",
                       "fg": "#EAF2FF", "muted": "#8AA0C4", "accent": "#38BDF8", "accent2": "#7DD3FC",
                       "line": "#1F3358", "track": "#2B4272", "on_acc": "#06121F"},
    "Графит": {"bg": "#16181D", "side": "#101216", "card": "#1F2229", "card2": "#2A2E37",
               "fg": "#ECEEF2", "muted": "#8D93A1", "accent": "#22D3A6", "accent2": "#5EEAD4",
               "line": "#2E323C", "track": "#3A3F4B", "on_acc": "#06140F"},
    "Светлая": {"bg": "#F3F4FA", "side": "#FFFFFF", "card": "#FFFFFF", "card2": "#ECEEF8",
                "fg": "#1B1D2A", "muted": "#6B7090", "accent": "#6C5CE7", "accent2": "#8E7FF5",
                "line": "#E1E3F0", "track": "#CFD3E8", "on_acc": "#FFFFFF"},
}
ACCENTS = {"Фиолетовый": "#8B5CF6", "Голубой": "#38BDF8", "Розовый": "#F472B6",
           "Зелёный": "#34D399", "Оранжевый": "#FB923C"}
FONT_SCALE = {"Мелкий": 0.9, "Обычный": 1.0, "Крупный": 1.15}


def make_theme(cfg):
    th = dict(THEMES.get(cfg["ui_theme"], THEMES["Тёмная (фиолет)"]))
    acc = ACCENTS.get(cfg["ui_accent"])
    if acc:
        th["accent"] = acc
        th["accent2"] = mix(acc, "#FFFFFF", 0.22)
    th["font_k"] = FONT_SCALE.get(cfg["ui_font"], 1.0)
    return th


def attach_tactile(widget, normal_bg, hover_bg, press_bg, children=()):
    targets = (widget,) + tuple(children)
    state = {"hover": False, "pressed": False}

    def sync():
        bg = press_bg if state["pressed"] else (hover_bg if state["hover"] else normal_bg)
        for w in targets:
            try:
                w.configure(bg=bg)
            except Exception:
                pass

    def on_enter(_e=None):
        state["hover"] = True
        sync()

    def on_leave(_e=None):
        state["hover"] = False
        state["pressed"] = False
        sync()

    def on_press(_e=None):
        state["pressed"] = True
        sync()

    def on_release(_e=None):
        state["pressed"] = False
        sync()

    for w in targets:
        w.bind("<Enter>", on_enter, add="+")
        w.bind("<Leave>", on_leave, add="+")
        w.bind("<ButtonPress-1>", on_press, add="+")
        w.bind("<ButtonRelease-1>", on_release, add="+")


class Toggle(tk.Canvas):
    def __init__(self, parent, th, k, value, command):
        super().__init__(parent, width=int(50 * k), height=int(28 * k), bg=th["card"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.th, self.k, self.v, self.cmd = th, k, bool(value), command
        self.hover = False
        self.pressed = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._click)
        self.draw()

    def _enter(self, _e):
        self.hover = True
        self.draw()

    def _leave(self, _e):
        self.hover = False
        self.pressed = False
        self.draw()

    def _press(self, _e):
        self.pressed = True
        self.draw()

    def _click(self, _e):
        was_pressed = self.pressed
        self.pressed = False
        if was_pressed:
            self.set(not self.v)
            self.cmd(self.v)
        else:
            self.draw()

    def draw(self):
        k, th = self.k, self.th
        self.delete("all")
        base_col = th["accent"] if self.v else th["track"]
        if self.pressed:
            col = blend(base_col, 0.82)
        elif self.hover:
            col = mix(base_col, "#FFFFFF", 0.14)
        else:
            col = base_col
        self.create_oval(1 * k, 1 * k, 27 * k, 27 * k, fill=col, outline=col)
        self.create_oval(23 * k, 1 * k, 49 * k, 27 * k, fill=col, outline=col)
        self.create_rectangle(14 * k, 1 * k, 36 * k, 27 * k, fill=col, outline=col)
        shift = 1.5 if self.pressed else 0.0
        x = (36 if self.v else 14) + (shift if self.v else -shift)
        self.create_oval((x - 10.5) * k, 3.5 * k, (x + 10.5) * k, 24.5 * k,
                         fill="#FFFFFF", outline="")

    def set(self, v):
        self.v = bool(v)
        self.draw()


class Slider(tk.Canvas):
    def __init__(self, parent, th, k, lo, hi, step, value, command, width=220):
        self.k, self.w = k, int(width * k)
        super().__init__(parent, width=self.w + int(64 * k), height=int(30 * k), bg=th["card"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.th, self.lo, self.hi, self.step, self.cmd = th, lo, hi, step, command
        self.is_int = isinstance(step, int)
        self.v = value
        self.active = False
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.draw()

    def _val(self, x):
        pad = 10 * self.k
        f = max(0.0, min(1.0, (x - pad) / float(self.w - 2 * pad)))
        v = self.lo + f * (self.hi - self.lo)
        v = round(v / self.step) * self.step
        v = max(self.lo, min(self.hi, v))
        return int(round(v)) if self.is_int else round(v, 2)

    def _press(self, e):
        self.active = True
        v = self._val(e.x)
        if v != self.v:
            self.v = v
            self.cmd(v)
        self.draw()

    def _release(self, _e):
        self.active = False
        self.draw()

    def set(self, v):
        self.v = v
        self.draw()

    def draw(self):
        k, th = self.k, self.th
        self.delete("all")
        pad = 10 * k
        y = 15 * k
        x0, x1 = pad, self.w - pad
        span = float(self.hi - self.lo) or 1.0
        fx = x0 + (float(self.v) - self.lo) / span * (x1 - x0)
        self.create_line(x0, y, x1, y, fill=th["track"], width=max(3, int(5 * k)), capstyle="round")
        if fx > x0:
            self.create_line(x0, y, fx, y, fill=th["accent"], width=max(3, int(5 * k)), capstyle="round")
        r = (8.5 if self.active else 7.5) * k
        self.create_oval(fx - r, y - r, fx + r, y + r, fill=th["accent2"] if self.active else "#FFFFFF",
                         outline=th["accent"], width=2)
        txt = str(int(round(self.v))) if self.is_int else ("%.1f" % self.v if self.step >= 0.1 else "%.2f" % self.v)
        self.create_text(self.w + 34 * k, y, text=txt, fill=th["fg"],
                         font=("Segoe UI", max(8, int(10 * k))), anchor="e")


class Drop:
    def __init__(self, parent, th, k, values, value, command):
        self.var = tk.StringVar(value=str(value))
        self.box = ttk.Combobox(parent, textvariable=self.var, values=[str(v) for v in values],
                                state="readonly", width=18, font=("Segoe UI", max(8, int(10 * k))))
        self.box.bind("<<ComboboxSelected>>", lambda _e: command(self.var.get()))

    def set(self, v):
        self.var.set(str(v))


class Swatch:
    def __init__(self, parent, th, k, value, command):
        self.v, self.cmd, self.th = value, command, th
        self.btn = tk.Button(parent, width=3, height=1, bg=value, activebackground=blend(value, 0.8),
                             bd=1, relief="solid", cursor="hand2", command=self.pick)
        attach_tactile(self.btn, value, mix(value, "#FFFFFF", 0.16), blend(value, 0.82))

    def pick(self):
        c = colorchooser.askcolor(color=self.v, title="Цвет")[1]
        if c:
            self.set(c)
            self.cmd(c)

    def set(self, v):
        self.v = v
        self.btn.configure(bg=v, activebackground=blend(v, 0.8))


class ScrollFrame(tk.Frame):
    def __init__(self, parent, th):
        super().__init__(parent, bg=th["bg"])
        self.cv = tk.Canvas(self, bg=th["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.inner = tk.Frame(self.cv, bg=th["bg"])
        self.win_id = self.cv.create_window((0, 0), window=self.inner, anchor="nw")
        self.cv.configure(yscrollcommand=sb.set)
        self.cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.cv.bind("<Configure>", self._on_canvas_configure)
        self.cv.bind("<Enter>", lambda _e: self.cv.bind_all("<MouseWheel>", self._on_wheel))
        self.cv.bind("<Leave>", lambda _e: self.cv.unbind_all("<MouseWheel>"))

    def _on_inner_configure(self, _e):
        self.cv.configure(scrollregion=self.cv.bbox("all"))

    def _on_canvas_configure(self, e):
        self.cv.itemconfigure(self.win_id, width=e.width)

    def _on_wheel(self, e):
        if self.cv.winfo_exists() and self.cv.bbox("all"):
            self.cv.yview_scroll(-1 * int(e.delta / 120), "units")


NAV = [("home", "Главная"), ("fall", "Что падает"), ("weather", "Погода"),
       ("cursor", "Курсор и снег"), ("garland", "Гирлянда"), ("sky", "Небо и птицы"),
       ("party", "Праздник"), ("app", "Приложение")]


class App:
    def __init__(self, cfg, ov, tray, show_flag):
        self.cfg, self.ov, self.tray, self.show_flag = cfg, ov, tray, show_flag
        self.win = None
        self.page = "home"
        self.nav_btns = {}
        self.controls = {}
        self.status_lbl = None
        self.pinned_garland = None
        self.root = tk.Tk()
        self.root.report_callback_exception = report_tk_exception
        self.root.withdraw()
        if not cfg["start_hidden"]:
            self.open_settings()
        self.root.after(150, self.poll)

    def poll(self):
        if self.show_flag.is_set():
            self.show_flag.clear()
            self.open_settings()
        self.root.after(150, self.poll)

    def style_ttk(self, th, k):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        f = ("Segoe UI", max(8, int(10 * k)))
        st.configure("TCombobox", fieldbackground=th["card2"], background=th["card2"],
                     foreground=th["fg"], arrowcolor=th["fg"], bordercolor=th["line"],
                     lightcolor=th["card2"], darkcolor=th["card2"], padding=4, font=f)
        st.map("TCombobox", fieldbackground=[("readonly", th["card2"]), ("hover", th["line"])],
               foreground=[("readonly", th["fg"])], selectbackground=[("readonly", th["card2"])],
               selectforeground=[("readonly", th["fg"])])
        self.root.option_add("*TCombobox*Listbox*Background", th["card2"])
        self.root.option_add("*TCombobox*Listbox*Foreground", th["fg"])
        self.root.option_add("*TCombobox*Listbox*selectBackground", th["accent"])
        self.root.option_add("*TCombobox*Listbox*selectForeground", th["on_acc"])
        st.configure("Vertical.TScrollbar", background=th["card2"], troughcolor=th["bg"],
                     bordercolor=th["bg"], arrowcolor=th["muted"], relief="flat")

    def open_settings(self):
        if self.win and self.win.winfo_exists():
            self.win.deiconify()
            self.win.lift()
            self.win.focus_force()
            if self.pinned_garland:
                self.pinned_garland.set_visible(True)
            return
        th = make_theme(self.cfg)
        k = th["font_k"]
        w = tk.Toplevel(self.root)
        w.report_callback_exception = report_tk_exception
        self.win = w
        w.title(APP_TITLE)
        w.geometry("%dx%d" % (int(940 * k), int(640 * k)))
        w.minsize(int(720 * k), int(480 * k))
        w.configure(bg=th["bg"])
        try:
            w.iconbitmap(default="")
        except Exception:
            pass
        self.style_ttk(th, k)
        w.protocol("WM_DELETE_WINDOW", self.close_win)

        side = tk.Frame(w, bg=th["side"], width=int(205 * k))
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        title_lbl = tk.Label(side, text="✦  " + APP_TITLE, bg=th["side"], fg=th["fg"],
                             font=("Segoe UI Semibold", max(10, int(14 * k))), anchor="w")
        title_lbl.pack(fill="x", padx=int(18 * k), pady=(int(22 * k), int(4 * k)))
        sub_lbl = tk.Label(side, text="Настройка эффектов", bg=th["side"], fg=th["muted"],
                           font=("Segoe UI", max(8, int(9 * k))), anchor="w")
        sub_lbl.pack(fill="x", padx=int(18 * k), pady=(0, int(18 * k)))

        self.nav_btns = {}
        for key, label in NAV:
            b = tk.Label(side, text="  " + label, bg=th["side"], fg=th["muted"],
                         font=("Segoe UI", max(8, int(10 * k))), anchor="w",
                         padx=int(12 * k), pady=int(9 * k), cursor="hand2")
            b.pack(fill="x", padx=int(8 * k), pady=int(2 * k))
            b.bind("<Button-1>", lambda _e, p=key: self.show_page(p))
            self.nav_btns[key] = b

        bottom = tk.Frame(side, bg=th["side"])
        bottom.pack(side="bottom", fill="x", padx=int(12 * k), pady=int(14 * k))
        self.status_lbl = tk.Label(bottom, text="", bg=th["side"], fg=th["muted"],
                                   font=("Segoe UI", max(8, int(9 * k))), anchor="w", justify="left")
        self.status_lbl.pack(fill="x", pady=(0, int(8 * k)))
        self.update_status()

        p_btn = tk.Label(bottom, text="Приостановить" if self.ov.active else "Включить",
                         bg=th["card2"], fg=th["fg"], font=("Segoe UI", max(8, int(9 * k))),
                         pady=int(6 * k), cursor="hand2")
        p_btn.pack(fill="x", pady=(0, int(4 * k)))
        p_btn.bind("<Button-1>", lambda _e: self.toggle_pause(p_btn))
        attach_tactile(p_btn, th["card2"], mix(th["card2"], "#FFFFFF", 0.12), blend(th["card2"], 0.85))

        q_btn = tk.Label(bottom, text="Выход из программы", bg=th["side"], fg=th["muted"],
                         font=("Segoe UI", max(8, int(9 * k))), pady=int(5 * k), cursor="hand2")
        q_btn.pack(fill="x")
        q_btn.bind("<Button-1>", lambda _e: self.quit_app())
        attach_tactile(q_btn, th["side"], th["card"], th["card2"])

        self.body = tk.Frame(w, bg=th["bg"])
        self.body.pack(side="left", fill="both", expand=True)
        self.show_page(self.page)
        w.update_idletasks()
        target_hwnd = int(user32.GetAncestor(w.winfo_id(), 2) or w.winfo_id())
        if self.pinned_garland is None:
            self.pinned_garland = PinnedGarland(target_hwnd, self.cfg)
            self.pinned_garland.start()
        else:
            self.pinned_garland.set_visible(True)

    def rebuild_win(self):
        if self.pinned_garland:
            self.pinned_garland.stop()
            self.pinned_garland = None
        if self.win and self.win.winfo_exists():
            self.win.destroy()
        self.win = None
        self.open_settings()

    def close_win(self):
        if self.pinned_garland:
            self.pinned_garland.set_visible(False)
        if self.cfg["close_to_tray"]:
            self.win.withdraw()
        else:
            self.quit_app()

    def quit_app(self):
        if self.pinned_garland:
            self.pinned_garland.stop()
        self.ov.send("stop")
        try:
            self.tray.remove()
        except Exception:
            pass
        self.root.quit()

    def toggle_pause(self, btn):
        on = not self.ov.active
        self.ov.send("visible", on)
        self.ov.user_paused = not on
        btn.configure(text="Приостановить" if on else "Включить")
        self.update_status()

    def update_status(self):
        if not self.status_lbl or not self.status_lbl.winfo_exists():
            return
        if self.ov.user_paused:
            t = "● На паузе"
        elif self.ov.auto_paused:
            t = "● Пауза (полный экран)"
        else:
            t = "● Работает"
        self.status_lbl.configure(text=t)

    def show_page(self, key):
        self.page = key
        th = make_theme(self.cfg)
        k = th["font_k"]
        for p, b in self.nav_btns.items():
            act = (p == key)
            bg = th["accent"] if act else th["side"]
            fg = th["on_acc"] if act else th["muted"]
            hover_bg = mix(th["accent"], "#FFFFFF", 0.12) if act else th["card"]
            press_bg = blend(th["accent"], 0.85) if act else th["card2"]
            b.configure(bg=bg, fg=fg,
                        font=("Segoe UI Semibold" if act else "Segoe UI", max(8, int(10 * k))))
            attach_tactile(b, bg, hover_bg, press_bg)
        for ch in self.body.winfo_children():
            ch.destroy()
        self.controls.clear()

        sf = ScrollFrame(self.body, th)
        sf.pack(fill="both", expand=True, padx=int(24 * k), pady=int(18 * k))
        p = sf.inner
        title = dict(NAV)[key]
        tk.Label(p, text=title, bg=th["bg"], fg=th["fg"],
                 font=("Segoe UI Semibold", max(12, int(17 * k))), anchor="w").pack(fill="x", pady=(0, int(14 * k)))
        getattr(self, "page_" + key)(p)

    def set(self, key, val):
        self.cfg[key] = val
        save_cfg(self.cfg)
        self.ov.send("notify", key)
        if key in APP_KEYS:
            if key in ("ui_theme", "ui_accent", "ui_font"):
                self.rebuild_win()
            elif key == "pause_fullscreen":
                self.ov.last_check = 0.0

    def card(self, parent, title=None):
        th = make_theme(self.cfg)
        k = th["font_k"]
        c = tk.Frame(parent, bg=th["card"], highlightbackground=th["line"], highlightthickness=1)
        c.pack(fill="x", pady=(0, int(12 * k)))
        inner = tk.Frame(c, bg=th["card"], padx=int(16 * k), pady=int(12 * k))
        inner.pack(fill="x")
        if title:
            tk.Label(inner, text=title, bg=th["card"], fg=th["accent2"],
                     font=("Segoe UI Semibold", max(9, int(10 * k))), anchor="w").pack(fill="x", pady=(0, int(8 * k)))
        return inner

    def row_frame(self, card, label, sub=None):
        th = make_theme(self.cfg)
        k = th["font_k"]
        r = tk.Frame(card, bg=th["card"])
        r.pack(fill="x", pady=int(5 * k))
        left = tk.Frame(r, bg=th["card"])
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=label, bg=th["card"], fg=th["fg"],
                 font=("Segoe UI", max(8, int(10 * k))), anchor="w").pack(fill="x")
        if sub:
            tk.Label(left, text=sub, bg=th["card"], fg=th["muted"],
                     font=("Segoe UI", max(7, int(8 * k))), anchor="w").pack(fill="x")
        right = tk.Frame(r, bg=th["card"])
        right.pack(side="right", padx=(int(12 * k), 0))
        return right

    def toggle(self, card, label, key, sub=None, on_change=None):
        th = make_theme(self.cfg)
        right = self.row_frame(card, label, sub)

        def cb(v):
            self.set(key, v)
            if on_change:
                on_change(v)

        t = Toggle(right, th, th["font_k"], self.cfg[key], cb)
        t.pack(side="right")
        self.controls[key] = t
        return t

    def slider(self, card, label, key, lo, hi, step, sub=None, width=210):
        th = make_theme(self.cfg)
        right = self.row_frame(card, label, sub)
        s = Slider(right, th, th["font_k"], lo, hi, step, self.cfg[key],
                   lambda v: self.set(key, v), width=width)
        s.pack(side="right")
        self.controls[key] = s
        return s

    def drop(self, card, label, key, values, sub=None, on_change=None):
        th = make_theme(self.cfg)
        right = self.row_frame(card, label, sub)

        def cb(v):
            if isinstance(self.cfg[key], int) and not isinstance(self.cfg[key], bool):
                try:
                    v = int(v)
                except ValueError:
                    pass
            self.set(key, v)
            if on_change:
                on_change(v)

        d = Drop(right, th, th["font_k"], values, self.cfg[key], cb)
        d.box.pack(side="right")
        self.controls[key] = d
        return d

    def color(self, card, label, key, sub=None):
        th = make_theme(self.cfg)
        right = self.row_frame(card, label, sub)
        sw = Swatch(right, th, th["font_k"], self.cfg[key], lambda v: self.set(key, v))
        sw.btn.pack(side="right")
        self.controls[key] = sw
        return sw

    def btn(self, card, text, cmd, accent=False):
        th = make_theme(self.cfg)
        k = th["font_k"]
        bg = th["accent"] if accent else th["card2"]
        fg = th["on_acc"] if accent else th["fg"]
        hover_bg = mix(bg, "#FFFFFF", 0.14)
        press_bg = blend(bg, 0.84)
        b = tk.Label(card, text=text, bg=bg, fg=fg,
                     font=("Segoe UI Semibold" if accent else "Segoe UI", max(8, int(9 * k))),
                     padx=int(12 * k), pady=int(6 * k), cursor="hand2")
        b.bind("<Button-1>", lambda _e: cmd())
        attach_tactile(b, bg, hover_bg, press_bg)
        return b

    # ---- страницы
    def page_home(self, p):
        th = make_theme(self.cfg)
        k = th["font_k"]
        c = self.card(p, "Время года и готовые наборы")
        self.drop(c, "Время года", "season", ["Авто", "Зима", "Весна", "Лето", "Осень"],
                  "«Авто» — по календарю", lambda _v: self.refresh_season_label())
        self.season_lbl = tk.Label(c, text="", bg=th["card"], fg=th["muted"],
                                   font=("Segoe UI", max(8, int(9 * k))), anchor="w")
        self.season_lbl.pack(fill="x", pady=(0, int(8 * k)))
        self.refresh_season_label()

        grid = tk.Frame(c, bg=th["card"])
        grid.pack(fill="x")
        for idx, (_pid, ico, name, desc, vals) in enumerate(PRESETS):
            r, col = divmod(idx, 3)
            grid.columnconfigure(col, weight=1, uniform="pr")
            tile = tk.Frame(grid, bg=th["card2"], highlightbackground=th["line"],
                            highlightthickness=1, padx=int(10 * k), pady=int(8 * k), cursor="hand2")
            tile.grid(row=r, column=col, sticky="nsew", padx=int(4 * k), pady=int(4 * k))
            t1 = tk.Label(tile, text="%s  %s" % (ico, name), bg=th["card2"], fg=th["fg"],
                          font=("Segoe UI Semibold", max(8, int(10 * k))), anchor="w", cursor="hand2")
            t1.pack(fill="x")
            t2 = tk.Label(tile, text=desc, bg=th["card2"], fg=th["muted"],
                          font=("Segoe UI", max(7, int(8 * k))), anchor="w", justify="left",
                          wraplength=int(190 * k), cursor="hand2")
            t2.pack(fill="x", pady=(int(2 * k), 0))
            attach_tactile(tile, th["card2"], mix(th["card2"], "#FFFFFF", 0.12),
                           blend(th["card2"], 0.85), children=(t1, t2))
            for w in (tile, t1, t2):
                w.bind("<Button-1>", lambda _e, v=vals: self.apply_preset(v))

        c2 = self.card(p, "Быстрые действия")
        row = tk.Frame(c2, bg=th["card"])
        row.pack(fill="x")
        self.btn(row, "Убрать сугробы", lambda: self.ov.send("call", "clear_snow")).pack(side="left", padx=(0, int(8 * k)))
        self.btn(row, "Убрать снеговиков", lambda: self.ov.send("call", "clear_snowmen")).pack(side="left", padx=(0, int(8 * k)))
        self.btn(row, "Запустить метель", lambda: self.ov.send("call", "start_blizzard")).pack(side="left", padx=(0, int(8 * k)))
        self.btn(row, "Сбросить всё", self.reset_all).pack(side="left")

    def refresh_season_label(self):
        s = current_season(self.cfg)
        self.season_lbl.configure(text="Сейчас действует: %s" % SEASON_TITLE[s])

    def apply_preset(self, vals):
        for k in ("k_snow", "k_leaf", "k_spring", "k_firefly", "k_confetti",
                  "k_bubble", "k_heart", "k_star", "k_rain", "k_lantern"):
            self.cfg[k] = False
        for k, v in vals.items():
            self.cfg[k] = v
        save_cfg(self.cfg)
        self.ov.send("call", "reset_world")
        self.show_page("home")

    def reset_all(self):
        self.cfg.clear()
        self.cfg.update(DEFAULTS)
        save_cfg(self.cfg)
        self.ov.send("call", "reset_world")
        self.rebuild_win()

    def page_fall(self, p):
        c = self.card(p, "Что падает")
        self.drop(c, "Откуда брать набор", "fall_mode", ["По сезону", "Свой набор"],
                  None, lambda _v: self.show_page("fall"))
        if self.cfg["fall_mode"] == "Свой набор":
            for key, title in KINDS:
                self.toggle(c, title, "k_" + key)
        else:
            th = make_theme(self.cfg)
            s = current_season(self.cfg)
            names = ", ".join(dict(KINDS)[k] for k in SEASON_KINDS[s])
            tk.Label(c, text="%s: %s" % (SEASON_TITLE[s], names), bg=th["card"], fg=th["muted"],
                     font=("Segoe UI", max(8, int(9 * th["font_k"]))), anchor="w").pack(fill="x", pady=(4, 0))

        c2 = self.card(p, "Снежинки и поток")
        self.drop(c2, "Вид снежинок", "snow_style",
                  ["Все вместе", "Звёздочки ❄", "Хлопья ❅", "Кристаллы ❆", "Точки"])
        self.color(c2, "Цвет снега", "snow_color")
        self.slider(c2, "Сколько частиц", "density", 0, 450, 10)
        self.slider(c2, "Скорость падения", "speed", 0.2, 3.0, 0.1)
        self.slider(c2, "Размер", "size", 2, 16, 1)
        self.slider(c2, "Покачивание из стороны в сторону", "wobble", 0.0, 3.0, 0.1)
        self.toggle(c2, "Только на рабочем столе", "desktop_only",
                      "Не рисовать поверх окон и панели задач")

    def page_weather(self, p):
        k = make_theme(self.cfg)["font_k"]
        c = self.card(p, "Ветер")
        self.drop(c, "Направление", "wind_dir", ["Вправо", "Влево", "Меняется"])
        self.slider(c, "Сила ветра", "wind_power", 0.0, 3.0, 0.1)
        self.slider(c, "Порывы", "gust_power", 0.0, 2.0, 0.1)
        self.slider(c, "Частота порывов", "gust_speed", 0.2, 3.0, 0.1)

        c2 = self.card(p, "Метель")
        self.slider(c2, "Раз в сколько минут (0 — выкл)", "blizzard_every", 0, 60, 1)
        self.slider(c2, "Сколько секунд длится", "blizzard_len", 10, 90, 5)
        self.slider(c2, "Сила метели", "blizzard_power", 0.5, 3.0, 0.1)
        self.btn(c2, "Начать метель сейчас", lambda: self.ov.send("call", "start_blizzard"),
                 accent=True).pack(anchor="w", pady=(int(6 * k), 0))

        c3 = self.card(p, "Погода за окном")
        th = make_theme(self.cfg)
        r = self.row_frame(c3, "Город", "Подставит ветер и сезон по погоде")
        ent = tk.Entry(r, bg=th["card2"], fg=th["fg"], insertbackground=th["fg"],
                       relief="flat", width=18, font=("Segoe UI", max(8, int(10 * k))))
        ent.insert(0, self.cfg["weather_city"])
        ent.pack(side="left", padx=(0, int(6 * k)), ipady=int(3 * k))
        self.w_lbl = tk.Label(c3, text="", bg=th["card"], fg=th["muted"],
                              font=("Segoe UI", max(8, int(9 * k))), anchor="w")
        self.w_lbl.pack(fill="x", pady=(int(4 * k), 0))
        self.btn(r, "Узнать", lambda: self.fetch_weather(ent.get().strip())).pack(side="left")

    def fetch_weather(self, city):
        if not city:
            return
        self.cfg["weather_city"] = city
        save_cfg(self.cfg)
        self.w_lbl.configure(text="Запрашиваю…")

        def work():
            try:
                q = urllib.parse.quote(city)
                url = "https://wttr.in/%s?format=j1" % q
                with urllib.request.urlopen(url, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                cur = data["current_condition"][0]
                temp = int(cur["temp_C"])
                wind_kmh = float(cur["windspeedKmph"])
                desc = cur["lang_ru"][0]["value"] if cur.get("lang_ru") else cur["weatherDesc"][0]["value"]
                self.root.after(0, lambda: self.apply_weather(temp, wind_kmh, desc))
            except Exception:
                self.root.after(0, lambda: self.w_lbl.configure(text="Не удалось получить погоду"))

        threading.Thread(target=work, daemon=True).start()

    def apply_weather(self, temp, wind_kmh, desc):
        self.w_lbl.configure(text="%s, %+d°C, ветер %.0f км/ч" % (desc, temp, wind_kmh))
        self.cfg["wind_power"] = round(min(3.0, wind_kmh / 18.0), 1)
        if temp <= 0 and "дожд" not in desc.lower():
            self.cfg["season"] = "Зима"
            self.cfg["fall_mode"] = "По сезону"
        elif "дожд" in desc.lower() or "лив" in desc.lower():
            self.cfg["fall_mode"] = "Свой набор"
            for k in ("k_snow", "k_leaf", "k_spring", "k_firefly", "k_confetti",
                      "k_bubble", "k_heart", "k_star", "k_rain", "k_lantern"):
                self.cfg[k] = (k == "k_rain")
        save_cfg(self.cfg)
        self.ov.send("call", "reset_world")

    def page_cursor(self, p):
        k = make_theme(self.cfg)["font_k"]
        c = self.card(p, "Курсор")
        self.drop(c, "Что делает курсор", "cursor_mode",
                  ["Физика ветра", "Сметать снег", "Ничего"])
        self.slider(c, "Радиус", "cursor_radius", 30, 220, 10)
        self.slider(c, "Сила", "cursor_force", 0.2, 3.0, 0.1)
        self.toggle(c, "Сдувать снег при быстром движении", "cursor_blow")

        c2 = self.card(p, "След за курсором")
        self.toggle(c2, "Включить след", "trail_enabled")
        self.drop(c2, "Вид следа", "trail_kind",
                  ["Искры", "Звёздная пыль", "Радуга", "Пузырьки", "Сердечки", "Снежинки", "Огонёк"])
        self.slider(c2, "Густота", "trail_amount", 0.2, 3.0, 0.1)
        self.slider(c2, "Размер следа", "trail_size", 0.5, 2.5, 0.1)
        self.slider(c2, "Как долго держится", "trail_life", 0.4, 2.5, 0.1)

        c3 = self.card(p, "Снеговики")
        self.toggle(c3, "Лепить снеговиков", "roll_enabled",
                      "Зажмите клавишу на сугробе и ведите мышью, чтобы скатать ком")
        self.drop(c3, "Клавиша", "roll_key", ["Ctrl", "Shift"])
        self.slider(c3, "Размер снеговиков", "snowman_size", 0.6, 1.6, 0.1)
        self.slider(c3, "Максимум на экране", "snowman_max", 1, 15, 1)
        self.slider(c3, "Тают через (минут, 0 — нет)", "snowman_melt", 0, 60, 1)

        c4 = self.card(p, "Сугробы и снегоуборочная машина")
        self.toggle(c4, "Копить сугробы на окнах и внизу экрана", "pile_enabled")
        self.slider(c4, "Максимальная высота", "pile_max", 4, 45, 1)
        self.slider(c4, "Скорость накопления", "pile_rate", 0.2, 3.0, 0.1)
        self.slider(c4, "Машина раз в (минут, 0 — выкл)", "plow_every", 0, 30, 1)
        self.slider(c4, "Скорость машины", "plow_speed", 1, 10, 1)
        row = tk.Frame(c4, bg=make_theme(self.cfg)["card"])
        row.pack(fill="x", pady=(int(6 * k), 0))
        self.btn(row, "Вызвать машину сейчас", lambda: self.ov.send("call", "start_plow"),
                 accent=True).pack(side="left", padx=(0, int(8 * k)))
        self.btn(row, "Очистить сугробы", lambda: self.ov.send("call", "clear_snow")).pack(side="left")

    def page_garland(self, p):
        c = self.card(p, "Гирлянда на окнах")
        self.toggle(c, "Включить гирлянду", "garland_enabled")
        self.toggle(c, "Только зимой", "garland_winter_only")
        self.toggle(c, "Не вешать на развёрнутые окна", "skip_maximized")
        self.toggle(c, "По верхнему краю экрана", "garland_top")
        self.toggle(c, "Вокруг окон (а не только сверху)", "garland_around")

        c2 = self.card(p, "Внешний вид")
        self.drop(c2, "Стиль", "garland_style",
                  ["Авто (по сезону)", "Лампочки", "Сосульки", "Шарики", "Звёзды",
                   "Фонарики", "Флажки", "Листья", "Цветы", "Микс"])
        self.slider(c2, "Яркость свечения", "garland_glow", 1, 3, 1)
        self.slider(c2, "Ширина пролёта", "garland_arc", 100, 450, 10)
        self.slider(c2, "Провисание", "garland_sag", 8, 60, 2)
        self.slider(c2, "Расстояние между лампочками", "garland_gap", 20, 80, 2)
        self.slider(c2, "Размер лампочек", "bulb_size", 3, 10, 1)
        self.slider(c2, "Толщина провода", "garland_width", 1, 5, 1)
        self.color(c2, "Цвет провода", "garland_wire")

        c3 = self.card(p, "Цвета и мигание")
        self.color(c3, "Цвет 1", "color1")
        self.color(c3, "Цвет 2", "color2")
        self.color(c3, "Цвет 3", "color3")
        self.color(c3, "Цвет 4", "color4")
        self.drop(c3, "Режим", "blink_mode", ["Бегущая волна", "Мигание", "Ровный свет"])
        self.slider(c3, "Скорость", "blink_speed", 0.2, 6.0, 0.2)

    def page_sky(self, p):
        c = self.card(p, "Северное сияние")
        self.toggle(c, "Включить сияние", "aurora_enabled")
        self.drop(c, "Когда показывать", "aurora_when", ["Всегда", "Только зимой"])
        self.drop(c, "Цвета", "aurora_palette", ["Зелёное", "Фиолетовое", "Розовое"])
        self.slider(c, "Высота полос (% экрана)", "aurora_height", 15, 65, 1)
        self.slider(c, "Скорость", "aurora_speed", 0.2, 3.0, 0.1)
        self.slider(c, "Яркость", "aurora_power", 1, 3, 1)

        c2 = self.card(p, "Звёзды и метеоры")
        self.toggle(c2, "Звёздное небо", "stars_enabled")
        self.slider(c2, "Сколько звёзд", "stars_count", 20, 220, 10)
        self.slider(c2, "Как низко спускаются (% экрана)", "stars_height", 20, 90, 5)
        self.slider(c2, "Мерцание", "stars_twinkle", 0.0, 3.0, 0.1)
        self.toggle(c2, "Падающие звёзды (метеоры)", "meteor_enabled")
        self.slider(c2, "Раз в сколько секунд", "meteor_every", 2, 30, 1)
        self.slider(c2, "Длина хвоста", "meteor_len", 0.5, 2.5, 0.1)

        c3 = self.card(p, "Солнце или луна")
        self.drop(c3, "Светило", "sky_body", ["Выкл", "Авто", "Луна", "Солнце"])
        self.drop(c3, "Фаза луны", "sky_phase", ["Авто", "Полная", "Растущая", "Убывающая"])
        self.drop(c3, "Угол", "sky_corner", ["Правый верх", "Левый верх"])
        self.slider(c3, "Размер", "sky_size", 35, 130, 5)

        c4 = self.card(p, "Облака")
        self.toggle(c4, "Плывущие облака", "clouds_enabled")
        self.slider(c4, "Сколько облаков", "clouds_count", 1, 14, 1)
        self.slider(c4, "Скорость", "clouds_speed", 0.2, 3.0, 0.1)
        self.drop(c4, "Оттенок", "clouds_tint", ["Белые", "Серые (пасмурно)", "Закат (розовые)"])
        self.slider(c4, "Полоса по высоте (% экрана)", "clouds_height", 15, 70, 5)

        c5 = self.card(p, "Птицы и бабочки")
        self.drop(c5, "Кто летает", "birds_mode", ["Выкл", "Авто", "Птицы", "Бабочки"])
        self.slider(c5, "Сколько", "birds_count", 2, 25, 1)
        self.slider(c5, "Размер (%)", "birds_size", 50, 180, 10)
        self.slider(c5, "Скорость", "birds_speed", 0.3, 3.0, 0.1)

    def page_party(self, p):
        k = make_theme(self.cfg)["font_k"]
        c0 = self.card(p, "На каком мониторе показывать виджеты")
        self.drop(c0, "Монитор", "widget_monitor", ["Правый", "Левый", "Основной"])

        c = self.card(p, "Дед Мороз на санях")
        self.toggle(c, "Пролетает время от времени", "santa_enabled")
        self.slider(c, "Раз в сколько минут", "santa_every", 1, 30, 1)
        self.slider(c, "Размер (%)", "santa_size", 50, 160, 10)
        self.slider(c, "Скорость", "santa_speed", 1, 12, 1)
        self.slider(c, "Высота (% экрана)", "santa_height", 5, 55, 1)
        self.toggle(c, "Сбрасывать подарки", "santa_gifts")
        self.btn(c, "Пролететь сейчас", lambda: self.ov.send("call", "start_santa"),
                 accent=True).pack(anchor="w", pady=(int(6 * k), 0))

        c2 = self.card(p, "Сезонное дерево")
        self.toggle(c2, "Поставить дерево на рабочий стол", "tree_enabled",
                      "Зимой — ёлка, весной — сакура, летом и осенью — крона по сезону")
        self.drop(c2, "Где поставить", "tree_side", ["Справа", "Слева", "По центру"])
        self.slider(c2, "Размер (%)", "tree_size", 50, 170, 10)
        self.slider(c2, "Отступ от края", "tree_margin", 0, 200, 10)
        self.slider(c2, "Приподнять от низа", "tree_lift", 0, 150, 5)

        c3 = self.card(p, "Фейерверки")
        self.toggle(c3, "Запускать салюты", "fw_enabled")
        self.slider(c3, "Раз в сколько секунд", "fw_every", 2, 30, 1)
        self.slider(c3, "Сила разрыва", "fw_size", 0.5, 2.0, 0.1)

        c4 = self.card(p, "Отсчёт до праздника")
        self.toggle(c4, "Показывать на экране", "count_enabled")
        self.drop(c4, "Праздник", "count_target", ["Новый год", "Рождество", "Своя дата"],
                  None, lambda _v: self.show_page("party"))
        if self.cfg["count_target"] == "Своя дата":
            self.slider(c4, "Месяц", "count_month", 1, 12, 1)
            self.slider(c4, "День", "count_day", 1, 31, 1)
        self.drop(c4, "Угол", "count_corner", ["Левый верх", "Правый верх", "Левый низ", "Правый низ"])
        self.slider(c4, "Размер (%)", "count_size", 60, 180, 10)
        self.color(c4, "Цвет текста", "count_color")
        self.toggle(c4, "Показывать секунды", "count_seconds")

        c5 = self.card(p, "Подсветка по краю экрана")
        self.toggle(c5, "Включить подсветку краёв", "strip_enabled")
        self.drop(c5, "Перелив", "strip_mode", ["Тёплый", "Холодный", "По сезону", "Свой цвет"])
        self.slider(c5, "Толщина", "strip_width", 2, 14, 1)
        self.slider(c5, "Скорость", "strip_speed", 0.2, 4.0, 0.1)
        self.color(c5, "Свой цвет", "strip_color")

        c6 = self.card(p, "Неоновая рамка активного окна")
        self.toggle(c6, "Подсвечивать активное окно", "neon_enabled")
        self.drop(c6, "Цвет", "neon_mode", ["Фиолетовый", "Тёплый", "Холодный"])
        self.slider(c6, "Толщина", "neon_width", 1, 8, 1)
        self.slider(c6, "Скорость", "neon_speed", 0.2, 4.0, 0.1)

    def page_app(self, p):
        th = make_theme(self.cfg)
        k = th["font_k"]
        c = self.card(p, "Оформление окна настроек")
        self.drop(c, "Тема", "ui_theme", list(THEMES.keys()))
        self.drop(c, "Акцент", "ui_accent", ["По теме"] + list(ACCENTS.keys()))
        self.drop(c, "Размер шрифта", "ui_font", ["Мелкий", "Обычный", "Крупный"])

        c2 = self.card(p, "Поведение")
        auto_var = tk.BooleanVar(value=is_autostart())
        right = self.row_frame(c2, "Запускать вместе с Windows")

        def toggle_auto():
            ok = set_autostart(auto_var.get())
            if not ok:
                auto_var.set(is_autostart())

        t_auto = Toggle(right, th, k, auto_var.get(),
                        lambda v: (auto_var.set(v), toggle_auto()))
        t_auto.pack(side="right")

        self.toggle(c2, "Сворачивать в трей при закрытии окна", "close_to_tray")
        self.toggle(c2, "Запускать свёрнутым в трей", "start_hidden")
        self.toggle(c2, "Пауза в играх и полноэкранных приложениях", "pause_fullscreen")

        c3 = self.card(p, "Производительность")
        self.drop(c3, "Режим", "perf_mode", ["Авто", "Красота", "Экономия"])
        self.slider(c3, "Частота кадров (FPS)", "fps", 15, 60, 5)
        self.slider(c3, "Упреждение движения окон (мс)", "lead_ms", 0, 80, 5,
                      "Если гирлянда чуть отстаёт при быстром перетаскивании окна")

        c4 = self.card(p, "О программе")
        tk.Label(c4, text="Настройки хранятся в: " + CONFIG_PATH, bg=th["card"], fg=th["muted"],
                 font=("Segoe UI", max(7, int(8 * k))), anchor="w", wraplength=int(560 * k)).pack(fill="x")
        if os.path.exists(LOG_PATH):
            tk.Label(c4, text="Журнал ошибок: " + LOG_PATH, bg=th["card"], fg=th["muted"],
                     font=("Segoe UI", max(7, int(8 * k))), anchor="w").pack(fill="x", pady=(int(2 * k), 0))


def main():
    if "--wakeup" in sys.argv:
        signal_existing()
        return
    cfg = load_cfg()
    show_flag = threading.Event()
    start_show_listener(show_flag)

    ov = Overlay(cfg)
    ov.start()

    app_holder = []

    def on_tray_cmd(cmd):
        def run_cmd():
            app = app_holder[0] if app_holder else None
            if cmd == 1 and app:
                app.open_settings()
            elif cmd == 2:
                on = not ov.active
                ov.send("visible", on)
                ov.user_paused = not on
                if app:
                    app.update_status()
            elif cmd == 3:
                set_autostart(not is_autostart())
            elif cmd == 9 and app:
                app.quit_app()

        if app_holder:
            try:
                app_holder[0].root.after(0, run_cmd)
                return
            except Exception:
                pass
        run_cmd()

    def get_tray_state():
        return {"on": ov.active, "auto": is_autostart()}

    tray = None
    try:
        tray = Tray(APP_TITLE, on_tray_cmd, get_tray_state)
    except Exception:
        log_error("tray init")

    app = App(cfg, ov, tray, show_flag)
    app_holder.append(app)
    try:
        app.root.mainloop()
    except Exception:
        log_exception("main loop", sys.exc_info())
        try:
            detail = traceback.format_exc().splitlines()[-1] if sys.exc_info()[0] else "Неизвестная ошибка"
            user32.MessageBoxW(
                None,
                "Программа завершилась с ошибкой:\n" + detail +
                "\n\nПодробности сохранены в журнале:\n" + LOG_PATH,
                "SnowGarland — ошибка", 0x10)
        except Exception:
            pass
