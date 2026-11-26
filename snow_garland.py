# -*- coding: utf-8 -*-
"""
Снегопад и гирлянда на окнах для Windows.
Запуск: python snow_garland.py   (или pythonw snow_garland.py - без консоли)
Нужен только Python 3.8+ для Windows. Сторонние библиотеки не нужны.
"""
import ctypes
import json
import math
import os
import random
import sys
import time
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk, colorchooser

# ---------------------------------------------------------------- WinAPI
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
try:
    user32.SetProcessDPIAware()
except Exception:
    pass

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
dwmapi.DwmGetWindowAttribute.argtypes = [
    wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW = 0x80000, 0x20, 0x80


def get_windows():
    """Видимые окна сверху вниз (по z-порядку): (l, t, r, b, maximized)."""
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
        result.append((r.left, r.top, r.right, r.bottom,
                       bool(user32.IsZoomed(hwnd))))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return result


def visible_top_edges(windows, skip_maximized):
    """Участки верхних границ окон, не закрытые другими окнами."""
    segs = []
    for i, (l, t, r, b, mx) in enumerate(windows):
        if mx and skip_maximized:
            continue
        spans = [(l + 8, r - 8)]
        for (l2, t2, r2, b2, _m) in windows[:i]:
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
                segs.append((a, c, t))
    return segs


# ---------------------------------------------------------------- Настройки
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                           "snow_config.json")
DEFAULTS = {
    "fps": 30,
    "snow_enabled": True,
    "snow_count": 120,
    "snow_speed": 1.0,
    "snow_size": 4,
    "snow_wind": 0.0,
    "snow_wobble": 1.0,
    "snow_shape": "Снежинка ❄",
    "snow_color": "#FFFFFF",
    "garland_enabled": True,
    "garland_arc": 220,
    "garland_sag": 28,
    "garland_gap": 36,
    "garland_width": 2,
    "garland_wire": "#2E7D32",
    "bulb_size": 5,
    "color1": "#FF3B30",
    "color2": "#FFD60A",
    "color3": "#34C759",
    "color4": "#0A84FF",
    "blink_mode": "Бегущая волна",
    "blink_speed": 2.0,
    "skip_maximized": True,
}
KEY = "#010203"  # прозрачный цвет
SNOW_LIVE = ("snow_speed", "snow_wind", "snow_wobble", "snow_enabled_dummy")


def load_cfg():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def blend(hex_color, f):
    f = max(0.0, min(1.0, f))
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


# ---------------------------------------------------------------- Приложение
class App:
    def __init__(self):
        self.cfg = load_cfg()
        self.root = tk.Tk()
        self.root.title("Снегопад и гирлянда")
        self.root.resizable(False, False)

        self.vx = user32.GetSystemMetrics(76)
        self.vy = user32.GetSystemMetrics(77)
        self.W = user32.GetSystemMetrics(78)
        self.H = user32.GetSystemMetrics(79)

        self.flakes = []
        self.bulbs = []
        self.garland_sig = None
        self.dirty_snow = True
        self.dirty_garland = True
        self.visible = True
        self.counter = 0

        self.build_overlay()
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.tick()

    # ---- оверлей
    def build_overlay(self):
        self.ov = tk.Toplevel(self.root)
        self.ov.overrideredirect(True)
        self.ov.geometry("%dx%d+%d+%d" % (self.W, self.H, self.vx, self.vy))
        self.ov.configure(bg=KEY)
        self.ov.attributes("-topmost", True)
        self.ov.attributes("-transparentcolor", KEY)
        self.canvas = tk.Canvas(self.ov, bg=KEY, highlightthickness=0,
                                width=self.W, height=self.H)
        self.canvas.pack(fill="both", expand=True)
        self.ov.update_idletasks()
        hwnd = user32.GetParent(self.ov.winfo_id()) or self.ov.winfo_id()
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                              ex | WS_EX_LAYERED | WS_EX_TRANSPARENT
                              | WS_EX_TOOLWINDOW)

    # ---- интерфейс настроек
    def set_cfg(self, key, value):
        self.cfg[key] = value
        if key.startswith("snow_") and key not in SNOW_LIVE:
            self.dirty_snow = True
        elif not key.startswith("snow_"):
            self.dirty_garland = True

    def build_ui(self):
        pad = {"padx": 8, "pady": 4}
        self.vars = {}

        def group(title):
            f = ttk.LabelFrame(self.root, text=title)
            f.pack(fill="x", padx=10, pady=6)
            return f

        def scale(parent, text, key, lo, hi, res):
            row = ttk.Frame(parent)
            row.pack(fill="x", **pad)
            ttk.Label(row, text=text, width=22).pack(side="left")
            s = tk.Scale(row, from_=lo, to=hi, resolution=res,
                         orient="horizontal", length=220,
                         command=lambda v, k=key: self.set_cfg(
                             k, float(v) if res < 1 else int(float(v))))
            s.set(self.cfg[key])
            s.pack(side="left")
            self.vars[key] = s

        def check(parent, text, key):
            v = tk.BooleanVar(value=self.cfg[key])
            ttk.Checkbutton(parent, text=text, variable=v,
                            command=lambda: self.set_cfg(key, v.get())
                            ).pack(anchor="w", **pad)
            self.vars[key] = v

        def combo(parent, text, key, values):
            row = ttk.Frame(parent)
            row.pack(fill="x", **pad)
            ttk.Label(row, text=text, width=22).pack(side="left")
            v = tk.StringVar(value=self.cfg[key])
            cb = ttk.Combobox(row, textvariable=v, values=values,
                              state="readonly", width=22)
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>",
                    lambda e: self.set_cfg(key, v.get()))
            self.vars[key] = v

        def color(parent, text, key):
            row = ttk.Frame(parent)
            row.pack(fill="x", **pad)
            ttk.Label(row, text=text, width=22).pack(side="left")
            b = tk.Button(row, width=10, bg=self.cfg[key],
                          activebackground=self.cfg[key])

            def pick():
                c = colorchooser.askcolor(self.cfg[key], parent=self.root)[1]
                if c:
                    self.set_cfg(key, c)
                    b.configure(bg=c, activebackground=c)

            b.configure(command=pick)
            b.pack(side="left")
            self.vars[key] = b

        g = group("❄ Снег")
        check(g, "Включить снег", "snow_enabled")
        scale(g, "Количество", "snow_count", 0, 600, 5)
        scale(g, "Скорость", "snow_speed", 0.1, 5.0, 0.1)
        scale(g, "Размер", "snow_size", 1, 14, 1)
        scale(g, "Ветер (← →)", "snow_wind", -3.0, 3.0, 0.1)
        scale(g, "Покачивание", "snow_wobble", 0.0, 4.0, 0.1)
        combo(g, "Форма", "snow_shape", ["Снежинка ❄", "Круг"])
        color(g, "Цвет снега", "snow_color")

        g = group("🎄 Гирлянда на окнах")
        check(g, "Включить гирлянду", "garland_enabled")
        check(g, "Не вешать на развёрнутые окна", "skip_maximized")
        scale(g, "Длина провисающей дуги", "garland_arc", 80, 600, 10)
        scale(g, "Провисание", "garland_sag", 0, 100, 1)
        scale(g, "Расстояние между лампочками", "garland_gap", 16, 120, 2)
        scale(g, "Размер лампочек", "bulb_size", 2, 14, 1)
        scale(g, "Толщина провода", "garland_width", 1, 6, 1)
        color(g, "Цвет провода", "garland_wire")
        color(g, "Цвет лампочки 1", "color1")
        color(g, "Цвет лампочки 2", "color2")
        color(g, "Цвет лампочки 3", "color3")
        color(g, "Цвет лампочки 4", "color4")
        combo(g, "Режим мигания", "blink_mode",
              ["Бегущая волна", "Мигание", "Постоянно"])
        scale(g, "Скорость мигания", "blink_speed", 0.2, 10.0, 0.2)

        g = group("⚙ Общее")
        scale(g, "Кадров в секунду", "fps", 10, 60, 5)

        row = ttk.Frame(self.root)
        row.pack(fill="x", padx=10, pady=8)
        ttk.Button(row, text="Сохранить", command=lambda: save_cfg(self.cfg)
                   ).pack(side="left", padx=3)
        ttk.Button(row, text="Сбросить", command=self.reset
                   ).pack(side="left", padx=3)
        self.toggle_btn = ttk.Button(row, text="Скрыть эффекты",
                                     command=self.toggle)
        self.toggle_btn.pack(side="left", padx=3)
        ttk.Button(row, text="Выход", command=self.quit
                   ).pack(side="right", padx=3)

    def reset(self):
        for k, v in DEFAULTS.items():
            self.set_cfg(k, v)
            w = self.vars.get(k)
            if isinstance(w, tk.Scale):
                w.set(v)
            elif isinstance(w, (tk.BooleanVar, tk.StringVar)):
                w.set(v)
            elif isinstance(w, tk.Button):
                w.configure(bg=v, activebackground=v)

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self.ov.deiconify()
            self.toggle_btn.configure(text="Скрыть эффекты")
        else:
            self.ov.withdraw()
            self.toggle_btn.configure(text="Показать эффекты")

    def quit(self):
        save_cfg(self.cfg)
        self.root.destroy()

    # ---- снег
    def make_flake(self, random_y):
        c = self.cfg
        r = max(1.0, random.uniform(0.35, 1.0) * c["snow_size"])
        x = random.uniform(0, self.W)
        y = random.uniform(0, self.H) if random_y else -10
        col = blend(c["snow_color"], random.uniform(0.75, 1.0))
        if c["snow_shape"].startswith("Круг"):
            item = self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                           fill=col, outline="")
        else:
            item = self.canvas.create_text(
                x, y, text="❄", fill=col,
                font=("Segoe UI Symbol", max(6, int(r * 2.6))))
        return {"id": item, "x": x, "y": y, "r": r,
                "vy": 0.8 + r * 0.45, "ph": random.uniform(0, 6.28),
                "k": 0.4 + r / max(1, c["snow_size"]) * 0.6,
                "circle": c["snow_shape"].startswith("Круг")}

    def rebuild_snow(self):
        for f in self.flakes:
            self.canvas.delete(f["id"])
        self.flakes = []
        if self.cfg["snow_enabled"]:
            for _ in range(int(self.cfg["snow_count"])):
                self.flakes.append(self.make_flake(True))
        self.canvas.tag_raise("garland")
        self.dirty_snow = False

    def update_snow(self):
        c = self.cfg
        sp, wind, wob = c["snow_speed"], c["snow_wind"], c["snow_wobble"]
        W, H = self.W, self.H
        for f in self.flakes:
            f["ph"] += 0.05
            f["y"] += f["vy"] * sp
            f["x"] += (wind * f["k"] + math.sin(f["ph"]) * wob * 0.6) * sp
            if f["y"] > H + 12:
                f["y"] = -12
                f["x"] = random.uniform(0, W)
            if f["x"] > W + 12:
                f["x"] = -12
            elif f["x"] < -12:
                f["x"] = W + 12
            if f["circle"]:
                r = f["r"]
                self.canvas.coords(f["id"], f["x"] - r, f["y"] - r,
                                   f["x"] + r, f["y"] + r)
            else:
                self.canvas.coords(f["id"], f["x"], f["y"])

    # ---- гирлянда
    def update_garland(self):
        c = self.cfg
        segs = []
        if c["garland_enabled"]:
            segs = visible_top_edges(get_windows(), c["skip_maximized"])
            segs = [(a - self.vx, b - self.vx, y - self.vy)
                    for a, b, y in segs]
        sig = tuple(segs)
        if sig == self.garland_sig and not self.dirty_garland:
            return
        self.garland_sig = sig
        self.dirty_garland = False
        self.canvas.delete("garland")
        self.bulbs = []
        colors = [c["color1"], c["color2"], c["color3"], c["color4"]]
        sag = c["garland_sag"]
        k = 0
        for a, b, y in segs:
            n_arcs = max(1, round((b - a) / c["garland_arc"]))
            w = (b - a) / n_arcs
            for i in range(n_arcs):
                x0 = a + i * w
                pts = []
                for s in range(17):
                    t = s / 16
                    pts += [x0 + t * w, y + 2 + sag * 4 * t * (1 - t)]
                self.canvas.create_line(*pts, fill=c["garland_wire"],
                                        width=c["garland_width"],
                                        smooth=True, tags="garland")
                cnt = max(1, int(w / c["garland_gap"]))
                for j in range(cnt):
                    t = (j + 0.5) / cnt
                    bx = x0 + t * w
                    by = y + 2 + sag * 4 * t * (1 - t)
                    r = c["bulb_size"]
                    self.canvas.create_line(bx, by, bx, by + 4,
                                            fill=c["garland_wire"],
                                            width=c["garland_width"],
                                            tags="garland")
                    glow = self.canvas.create_oval(
                        bx - r * 1.9, by + 4 - r * 1.2,
                        bx + r * 1.9, by + 4 + r * 2.6,
                        fill=KEY, outline="", tags="garland")
                    bulb = self.canvas.create_oval(
                        bx - r * 0.8, by + 4,
                        bx + r * 0.8, by + 4 + r * 2,
                        fill=colors[k % 4], outline="", tags="garland")
                    self.bulbs.append((bulb, glow, colors[k % 4], k))
                    k += 1

    def blink(self, t):
        mode, spd = self.cfg["blink_mode"], self.cfg["blink_speed"]
        for bulb, glow, col, k in self.bulbs:
            if mode == "Бегущая волна":
                f = 0.55 + 0.45 * math.sin(t * spd * 2 - k * 0.6)
            elif mode == "Мигание":
                f = 1.0 if (int(t * spd) + k) % 2 == 0 else 0.2
            else:
                f = 1.0
            self.canvas.itemconfigure(bulb, fill=blend(col, f))
            self.canvas.itemconfigure(
                glow, fill=blend(col, f * 0.28) if f > 0.45 else KEY)

    # ---- главный цикл
    def tick(self):
        if self.visible:
            if self.dirty_snow:
                self.rebuild_snow()
            self.update_snow()
            self.counter += 1
            if self.counter % 2 == 0 or self.dirty_garland:
                self.update_garland()
                self.canvas.tag_raise("garland")
            if self.counter % 2 == 0:
                self.blink(time.time())
            if self.counter % 90 == 0:
                self.ov.attributes("-topmost", True)
        self.root.after(max(10, int(1000 / self.cfg["fps"])), self.tick)


if __name__ == "__main__":
    if os.name != "nt":
        print("Программа работает только в Windows.")
        sys.exit(1)
    App().root.mainloop()
