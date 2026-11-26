import ctypes
from ctypes import wintypes
import datetime
import math
import random
import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
LWA_COLORKEY = 0x00000001

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2

TRANSPARENT_KEY = "#010203"


def get_current_season() -> str:
    m = datetime.date.today().month
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    return "autumn"


def get_window_bounds(hwnd):
    rect = wintypes.RECT()
    hr = dwmapi.DwmGetWindowAttribute(
        hwnd,
        DWMWA_EXTENDED_FRAME_BOUNDS,
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    if hr != 0 and not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return (rect.left, rect.top, rect.right, rect.bottom)


def get_taskbar_top(screen_h: int) -> int:
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    if hwnd:
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            if 0 < rect.top < screen_h:
                return rect.top
    return screen_h - 48


class SmoothSlider(tk.Canvas):
    """Надёжный кастомный ползунок на Canvas — не конфликтует с перетаскиванием окна."""

    def __init__(self, parent, variable, lo, hi, step=1, accent="#38bdf8", bg="#141926", is_float=False):
        super().__init__(parent, width=178, height=24, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.var = variable
        self.lo = float(lo)
        self.hi = float(hi)
        self.step = float(step)
        self.accent = accent
        self.is_float = is_float
        self._dragging = False

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_move)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.var.trace_add("write", lambda *_: self._draw())
        self._draw()

    def _val_from_x(self, x: float) -> float:
        pad = 9.0
        usable = max(1.0, float(self.winfo_reqwidth()) - 2 * pad)
        ratio = max(0.0, min(1.0, (x - pad) / usable))
        raw = self.lo + ratio * (self.hi - self.lo)
        snapped = round(raw / self.step) * self.step
        clamped = max(self.lo, min(self.hi, snapped))
        if self.is_float:
            return round(clamped, 3)
        return int(round(clamped))

    def _on_press(self, e):
        self._dragging = True
        self.var.set(self._val_from_x(e.x))

    def _on_move(self, e):
        if self._dragging:
            self.var.set(self._val_from_x(e.x))

    def _on_release(self, _e):
        self._dragging = False

    def _draw(self):
        self.delete("all")
        w = float(self.winfo_reqwidth())
        pad = 9.0
        cy = 12.0
        cur = float(self.var.get())
        span = max(1e-9, self.hi - self.lo)
        ratio = max(0.0, min(1.0, (cur - self.lo) / span))
        kx = pad + ratio * (w - 2 * pad)

        self.create_line(pad, cy, w - pad, cy, fill="#242c42", width=4, capstyle="round")
        if kx > pad:
            self.create_line(pad, cy, kx, cy, fill=self.accent, width=4, capstyle="round")
        self.create_oval(kx - 7, cy - 7, kx + 7, cy + 7, fill="#ffffff", outline=self.accent, width=2)


class SwitchPill(tk.Canvas):
    def __init__(self, parent, var: tk.BooleanVar, command=None, accent="#38bdf8", bg="#141926"):
        super().__init__(parent, width=40, height=20, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.var = var
        self.command = command
        self.accent = accent
        self.bind("<Button-1>", self._toggle)
        self.var.trace_add("write", lambda *_: self._draw())
        self._draw()

    def _toggle(self, _e=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        on = self.var.get()
        col = self.accent if on else "#252c40"
        self.create_oval(1, 1, 19, 19, fill=col, outline="")
        self.create_oval(21, 1, 39, 19, fill=col, outline="")
        self.create_rectangle(10, 1, 30, 19, fill=col, outline="")
        kx = 30 if on else 10
        self.create_oval(kx - 6.5, 3.5, kx + 6.5, 16.5, fill="#ffffff", outline="")


class FeatureWindow(tk.Toplevel):
    """Отдельное окно для конкретной фичи с плавным перетаскиванием без лагов."""

    def __init__(self, master, title: str, accent: str, geometry: str, on_close_hide=None):
        super().__init__(master)
        self.title(title)
        self.geometry(geometry)
        self.resizable(False, False)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#0b0e17")
        self.on_close_hide = on_close_hide
        self._drag_start_root = (0, 0)
        self._drag_start_win = (0, 0)

        try:
            self.update_idletasks()
            hwnd = user32.GetParent(self.winfo_id()) or self.winfo_id()
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
                ctypes.sizeof(ctypes.c_int),
            )
        except Exception:
            pass

        self.shell = tk.Frame(
            self,
            bg="#0b0e17",
            highlightbackground="#222a40",
            highlightthickness=1,
        )
        self.shell.pack(fill="both", expand=True)

        bar = tk.Frame(self.shell, bg="#111625", height=40)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=accent, height=2).pack(fill="x", side="top")

        lbl = tk.Label(bar, text=title, bg="#111625", fg="#f8fafc", font=("Segoe UI", 10, "bold"))
        lbl.pack(side="left", padx=12)

        btn_hide = tk.Button(
            bar,
            text="✕",
            bg="#192036",
            fg="#94a3b8",
            activebackground="#ef4444",
            activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            width=3,
            cursor="hand2",
            command=self.hide_window,
        )
        btn_hide.pack(side="right", padx=8)

        for w in (bar, lbl):
            w.bind("<ButtonPress-1>", self._start_move)
            w.bind("<B1-Motion>", self._do_move)

        self.body = tk.Frame(self.shell, bg="#0b0e17")
        self.body.pack(fill="both", expand=True, padx=12, pady=8)

    def _start_move(self, e):
        self._drag_start_root = (e.x_root, e.y_root)
        self._drag_start_win = (self.winfo_x(), self.winfo_y())

    def _do_move(self, e):
        dx = e.x_root - self._drag_start_root[0]
        dy = e.y_root - self._drag_start_root[1]
        nx = self._drag_start_win[0] + dx
        ny = self._drag_start_win[1] + dy
        self.geometry(f"+{nx}+{ny}")

    def hide_window(self):
        self.withdraw()
        if self.on_close_hide:
            self.on_close_hide()

    def show_window(self):
        self.deiconify()
        self.lift()


class AtmosphereMultiWindowApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Центр окон атмосферы")
        self.root.geometry("330x255+60+60")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0b0e17")
        self._hub_drag_root = (0, 0)
        self._hub_drag_win = (0, 0)

        try:
            self.root.update_idletasks()
            hwnd_root = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            dwmapi.DwmSetWindowAttribute(
                hwnd_root,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
                ctypes.sizeof(ctypes.c_int),
            )
        except Exception:
            pass

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # --- Параметры погоды и сугробов ---
        self.weather_enabled = tk.BooleanVar(value=True)
        self.auto_season = tk.BooleanVar(value=False)
        self.season = tk.StringVar(value="winter")
        self.pile_enabled = tk.BooleanVar(value=True)
        self.pile_max_cap = tk.IntVar(value=22)       # Максимальная высота сугроба до осыпания (px)
        self.flake_shape = tk.StringVar(value="crystal")
        self.count_var = tk.IntVar(value=70)
        self.speed_var = tk.DoubleVar(value=2.0)
        self.wind_var = tk.DoubleVar(value=0.25)

        # --- Снегоуборочная машина (снег и листья) ---
        self.plow_enabled = tk.BooleanVar(value=True)
        self.plow_mode = tk.StringVar(value="both")     # time, threshold, both
        self.plow_interval = tk.IntVar(value=20)
        self.plow_threshold = tk.IntVar(value=12)
        self.plow_x = -120.0
        self.plow_active = False
        self.plow_ticks = 0

        # --- Гирлянда ---
        self.top_garland = tk.BooleanVar(value=True)
        self.win_garland = tk.BooleanVar(value=True)
        self.win_scope = tk.StringVar(value="all")
        self.garland_style = tk.StringVar(value="bulb")
        self.garland_scale = tk.DoubleVar(value=1.0)
        self.garland_mode = tk.StringVar(value="rainbow")
        self.garland_palette = tk.StringVar(value="classic")
        self.garland_spacing = tk.IntVar(value=38)

        # --- Фейерверки ---
        self.fireworks_enabled = tk.BooleanVar(value=True)
        self.firework_interval = tk.IntVar(value=6)
        self.fw_ticks = 45

        # --- Северное сияние и шлейф ---
        self.aurora_enabled = tk.BooleanVar(value=True)
        self.cursor_trail = tk.BooleanVar(value=True)
        self.storm_timer = 0

        # --- Состояние симуляции ---
        self.particles = []
        self.falling_chunks = []
        self.sparks = []
        self.fireworks = []
        self.last_mouse = (-1, -1)
        self.blink_phase = 0
        self.anim_phase = 0.0
        self.window_bounds = {}
        self.active_hwnd = None

        self.pile_step = 5
        self.pile_cols = (self.screen_w // self.pile_step) + 2
        self.pile = [0.0] * self.pile_cols
        self.pile_owner = [0] * self.pile_cols

        self.particle_pool = []
        self.chunk_pool = []
        self.spark_pool = []
        self.pile_pool = []
        self.bulb_pool = []
        self.aurora_photo = None
        self.aurora_img_id = None
        self.plow_pool = ()

        self.my_hwnds = set()
        self._build_hub_ui()
        self._init_overlay()
        self._init_feature_windows()
        self._init_pools()
        self._collect_my_hwnds()
        self._scan_windows(initial=True)
        self._rebuild_particles()

        self._anim_loop()
        self._blink_loop()
        self._windows_loop()

    def _collect_my_hwnds(self):
        self.my_hwnds.clear()
        for w in [self.root, self.overlay] + list(self.feature_windows.values()):
            try:
                hwnd = user32.GetParent(w.winfo_id()) or w.winfo_id()
                self.my_hwnds.add(hwnd)
            except Exception:
                pass

    def _is_own_window(self, hwnd) -> bool:
        if hwnd in self.my_hwnds:
            return True
        parent = user32.GetParent(hwnd)
        return parent in self.my_hwnds

    # =========================================================================
    # ЦЕНТР УПРАВЛЕНИЯ ОКНАМИ
    # =========================================================================
    def _hub_drag_start(self, e):
        self._hub_drag_root = (e.x_root, e.y_root)
        self._hub_drag_win = (self.root.winfo_x(), self.root.winfo_y())

    def _hub_drag_move(self, e):
        nx = self._hub_drag_win[0] + (e.x_root - self._hub_drag_root[0])
        ny = self._hub_drag_win[1] + (e.y_root - self._hub_drag_root[1])
        self.root.geometry(f"+{nx}+{ny}")

    def _build_hub_ui(self):
        shell = tk.Frame(self.root, bg="#0b0e17", highlightbackground="#232b42", highlightthickness=1)
        shell.pack(fill="both", expand=True)

        bar = tk.Frame(shell, bg="#111625", height=44)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Frame(bar, bg="#38bdf8", height=2).pack(fill="x", side="top")

        lbl = tk.Label(bar, text="✦ ОКНА ПРИКОЛЮХ", bg="#111625", fg="#f8fafc", font=("Segoe UI", 10, "bold"))
        lbl.pack(side="left", padx=12)

        btn_exit = tk.Button(
            bar,
            text="✕",
            bg="#192036",
            fg="#f87171",
            activebackground="#ef4444",
            activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            width=3,
            cursor="hand2",
            command=self.root.destroy,
        )
        btn_exit.pack(side="right", padx=8)

        for w in (bar, lbl):
            w.bind("<ButtonPress-1>", self._hub_drag_start)
            w.bind("<B1-Motion>", self._hub_drag_move)

        body = tk.Frame(shell, bg="#0b0e17")
        body.pack(fill="both", expand=True, padx=12, pady=10)

        win_defs = [
            ("weather", "❄️ Окно: Погода, Сугробы и Уборка", "#38bdf8"),
            ("garland", "💡 Окно: Гирлянда и Размер", "#fbbf24"),
            ("fireworks", "🎆 Окно: Фейерверки", "#f43f5e"),
            ("aurora", "🌌 Окно: Северное сияние и Шлейф", "#2dd4bf"),
        ]
        for key, text, col in win_defs:
            tk.Button(
                body,
                text=text,
                bg="#141a29",
                fg="#f1f5f9",
                activebackground="#1e273d",
                activeforeground=col,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                anchor="w",
                padx=12,
                pady=7,
                cursor="hand2",
                command=lambda k=key: self.feature_windows[k].show_window(),
            ).pack(fill="x", pady=3)

    # =========================================================================
    # ОТДЕЛЬНЫЕ ОКНА ДЛЯ КАЖДОЙ ФИЧИ
    # =========================================================================
    def _init_feature_windows(self):
        self.feature_windows = {
            "weather": FeatureWindow(self.root, "❄️ Погода, Сугробы и Машина", "#38bdf8", "410x585+410+60"),
            "garland": FeatureWindow(self.root, "💡 Гирлянда", "#fbbf24", "410x450+835+60"),
            "fireworks": FeatureWindow(self.root, "🎆 Фейерверки", "#f43f5e", "390x235+410+660"),
            "aurora": FeatureWindow(self.root, "🌌 Северное сияние и Фишки", "#2dd4bf", "390x235+815+660"),
        }
        self._populate_weather_win(self.feature_windows["weather"].body)
        self._populate_garland_win(self.feature_windows["garland"].body)
        self._populate_fireworks_win(self.feature_windows["fireworks"].body)
        self._populate_aurora_win(self.feature_windows["aurora"].body)

    def _section(self, parent, title: str, accent="#38bdf8"):
        box = tk.Frame(parent, bg="#141926", highlightbackground="#1f273d", highlightthickness=1)
        box.pack(fill="x", pady=4)
        tk.Label(box, text=title, bg="#141926", fg=accent, font=("Segoe UI", 8, "bold")).pack(
            anchor="w", padx=10, pady=(5, 2)
        )
        inner = tk.Frame(box, bg="#141926")
        inner.pack(fill="x", padx=10, pady=(0, 7))
        return inner

    def _row_switch(self, parent, label: str, var: tk.BooleanVar, cmd=None, accent="#38bdf8"):
        r = tk.Frame(parent, bg="#141926")
        r.pack(fill="x", pady=2)
        tk.Label(r, text=label, bg="#141926", fg="#f1f5f9", font=("Segoe UI", 9)).pack(side="left")
        SwitchPill(r, var, command=cmd, accent=accent, bg="#141926").pack(side="right")

    def _row_slider(self, parent, label: str, var, lo, hi, step=1, accent="#38bdf8", is_float=False, cmd=None):
        r = tk.Frame(parent, bg="#141926")
        r.pack(fill="x", pady=2)
        tk.Label(r, text=label, bg="#141926", fg="#cbd5e1", font=("Segoe UI", 9)).pack(side="left")
        val_lbl = tk.Label(r, text="", bg="#141926", fg=accent, font=("Segoe UI", 9, "bold"), width=5, anchor="e")
        val_lbl.pack(side="right", padx=(4, 0))

        def sync_val(*_args):
            v = var.get()
            val_lbl.config(text=f"{v:.2f}" if is_float else f"{v}")
            if cmd:
                cmd()

        var.trace_add("write", sync_val)
        sync_val()

        sl = SmoothSlider(r, var, lo, hi, step=step, accent=accent, bg="#141926", is_float=is_float)
        sl.pack(side="right")

    def _row_pills(self, parent, items, getter, setter, accent="#2563eb"):
        r = tk.Frame(parent, bg="#0f1320", padx=2, pady=2)
        r.pack(fill="x", pady=3)
        btns = {}
        for k, txt in items:
            b = tk.Button(
                r,
                text=txt,
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                bd=0,
                pady=4,
                cursor="hand2",
                command=lambda v=k: setter(v),
            )
            b.pack(side="left", expand=True, fill="x", padx=2)
            btns[k] = b

        def refresh():
            cur = getter()
            for k, b in btns.items():
                on = k == cur
                b.configure(bg=accent if on else "#0f1320", fg="#ffffff" if on else "#64748b")

        refresh()
        return refresh

    def _populate_weather_win(self, parent):
        s1 = self._section(parent, "СЕЗОН И ПОТОК", "#38bdf8")
        self._row_switch(s1, "Включить осадки / листья", self.weather_enabled)
        self._row_switch(s1, "Авто-сезон по календарю", self.auto_season, cmd=self._on_auto_season, accent="#10b981")
        self._ref_season = self._row_pills(
            s1,
            [("winter", "❄️ Зима"), ("spring", "🌿 Весна"), ("summer", "✨ Лето"), ("autumn", "🍁 Осень")],
            self._active_season,
            self._set_season,
        )
        self._ref_shape = self._row_pills(
            s1,
            [("circle", "• Хлопья"), ("crystal", "❄ Кристаллы"), ("star", "✦ Звёзды"), ("mix", "🎲 Микс")],
            self.flake_shape.get,
            self._set_shape,
            accent="#6366f1",
        )
        self._row_slider(s1, "Плотность:", self.count_var, 15, 130, 1, accent="#38bdf8", cmd=self._rebuild_particles)
        self._row_slider(s1, "Скорость:", self.speed_var, 0.6, 6.0, 0.2, accent="#38bdf8", is_float=True)
        self._row_slider(s1, "Ветер:", self.wind_var, -2.5, 2.5, 0.1, accent="#38bdf8", is_float=True)

        s2 = self._section(parent, "СУГРОБЫ И ОКНА", "#60a5fa")
        self._row_switch(s2, "Накапливать на окнах и панели", self.pile_enabled, cmd=self._on_pile_toggle)
        self._row_slider(s2, "Высота осыпания (px):", self.pile_max_cap, 8, 45, 1, accent="#60a5fa")
        tk.Button(
            s2,
            text="🧹 Очистить сугробы и листья",
            bg="#1e263b",
            fg="#e2e8f0",
            activebackground="#2b3654",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            pady=4,
            cursor="hand2",
            command=self._clear_pile,
        ).pack(fill="x", pady=(3, 0))

        s3 = self._section(parent, "СНЕГОУБОРОЧНАЯ МАШИНА", "#f59e0b")
        self._row_switch(s3, "Убирать снег и листья машиной", self.plow_enabled, accent="#f59e0b")
        self._ref_plow = self._row_pills(
            s3,
            [("both", "⏱️+📏 Оба"), ("time", "⏱️ Время"), ("threshold", "📏 Порог")],
            self.plow_mode.get,
            self._set_plow_mode,
            accent="#d97706",
        )
        self._row_slider(s3, "Интервал (сек):", self.plow_interval, 5, 120, 5, accent="#f59e0b")
        self._row_slider(s3, "Порог сугроба (px):", self.plow_threshold, 4, 30, 1, accent="#f59e0b")

    def _populate_garland_win(self, parent):
        s1 = self._section(parent, "ГДЕ И ФОРМА", "#fbbf24")
        self._row_switch(s1, "Гирлянда вверху экрана", self.top_garland, accent="#f59e0b")
        self._row_switch(s1, "Гирлянда на окнах", self.win_garland, accent="#f59e0b")
        self._ref_scope = self._row_pills(
            s1,
            [("all", "На всех окнах"), ("active", "Только активное")],
            self.win_scope.get,
            self._set_scope,
            accent="#d97706",
        )
        self._ref_style = self._row_pills(
            s1,
            [("bulb", "💡 Лампочки"), ("icicle", "🧊 Сосульки"), ("star", "✦ Звёзды")],
            self.garland_style.get,
            self._set_style,
            accent="#ea580c",
        )

        s2 = self._section(parent, "РАЗМЕР И АНИМАЦИЯ", "#f472b6")
        self._row_slider(s2, "Размер гирлянды:", self.garland_scale, 0.6, 1.8, 0.05, accent="#f472b6", is_float=True)
        self._row_slider(s2, "Шаг (px):", self.garland_spacing, 24, 72, 2, accent="#f472b6")
        self._ref_mode = self._row_pills(
            s2,
            [("rainbow", "🌈 Перелив"), ("wave", "🌊 Волна"), ("twinkle", "✨ Мерцание"), ("steady", "💡 Ровный")],
            self.garland_mode.get,
            self._set_mode,
            accent="#db2777",
        )
        self._ref_pal = self._row_pills(
            s2,
            [("classic", "🎄 Классика"), ("warm", "🕯️ Тёплая"), ("cyber", "🟣 Неон"), ("ice", "🧊 Лёд")],
            self.garland_palette.get,
            self._set_palette,
            accent="#059669",
        )

    def _populate_fireworks_win(self, parent):
        s1 = self._section(parent, "ЗАПУСК ФЕЙЕРВЕРКОВ", "#f43f5e")
        self._row_switch(s1, "Автоматический запуск", self.fireworks_enabled, accent="#f43f5e")
        self._row_slider(s1, "Интервал (сек):", self.firework_interval, 2, 30, 1, accent="#f43f5e")
        tk.Button(
            s1,
            text="🎆 Запустить залп сейчас",
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self._spawn_firework_burst,
        ).pack(fill="x", pady=(6, 0))

    def _populate_aurora_win(self, parent):
        s1 = self._section(parent, "СЕВЕРНОЕ СИЯНИЕ И ШЛЕЙФ", "#2dd4bf")
        self._row_switch(s1, "Северное сияние (не пиксельное)", self.aurora_enabled, accent="#14b8a6")
        self._row_switch(s1, "Шлейф за курсором", self.cursor_trail, accent="#a855f7")
        tk.Button(
            s1,
            text="🌬️ Порыв метели на 5 сек",
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self._trigger_storm,
        ).pack(fill="x", pady=(6, 0))

    # --- Коллбэки ---
    def _on_auto_season(self):
        if self.auto_season.get():
            self.season.set(get_current_season())
            self._clear_pile()
            self._rebuild_particles()
        self._ref_season()

    def _set_season(self, v: str):
        self.auto_season.set(False)
        self.season.set(v)
        self._clear_pile()
        self._rebuild_particles()
        self._ref_season()

    def _set_shape(self, v: str):
        self.flake_shape.set(v)
        self._rebuild_particles()
        self._ref_shape()

    def _set_scope(self, v: str):
        self.win_scope.set(v)
        self._ref_scope()

    def _set_style(self, v: str):
        self.garland_style.set(v)
        self._ref_style()

    def _set_plow_mode(self, v: str):
        self.plow_mode.set(v)
        self._ref_plow()

    def _set_mode(self, v: str):
        self.garland_mode.set(v)
        self._ref_mode()

    def _set_palette(self, v: str):
        self.garland_palette.set(v)
        self._ref_pal()

    def _on_pile_toggle(self):
        if not self.pile_enabled.get():
            self._clear_pile()

    def _clear_pile(self):
        self.pile = [0.0] * self.pile_cols
        self.pile_owner = [0] * self.pile_cols
        self.falling_chunks.clear()

    def _trigger_storm(self):
        self.storm_timer = 170
        self.weather_enabled.set(True)

    def _spawn_firework_burst(self):
        cx = random.randint(int(self.screen_w * 0.2), int(self.screen_w * 0.8))
        cy = random.randint(int(self.screen_h * 0.14), int(self.screen_h * 0.42))
        cols = ["#ff3b3b", "#38bdf8", "#facc15", "#c084fc", "#4ade80", "#fb923c"]
        for i in range(24):
            ang = (math.tau * i) / 24 + random.uniform(-0.08, 0.08)
            spd = random.uniform(2.0, 6.2)
            self.fireworks.append(
                {
                    "x": float(cx),
                    "y": float(cy),
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "life": random.randint(18, 28),
                    "color": random.choice(cols),
                }
            )

    # =========================================================================
    # КЛИК-СКВОЗНОЙ ОВЕРЛЕЙ И ПУЛЫ
    # =========================================================================
    def _init_overlay(self):
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg=TRANSPARENT_KEY)
        self.overlay.geometry(f"{self.screen_w}x{self.screen_h}+0+0")

        self.canvas = tk.Canvas(
            self.overlay,
            width=self.screen_w,
            height=self.screen_h,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.overlay.update_idletasks()

        hwnd = user32.GetParent(self.overlay.winfo_id()) or self.overlay.winfo_id()
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            ex_style
            | WS_EX_LAYERED
            | WS_EX_TRANSPARENT
            | WS_EX_TOPMOST
            | WS_EX_TOOLWINDOW
            | WS_EX_NOACTIVATE,
        )
        r = int(TRANSPARENT_KEY[1:3], 16)
        g = int(TRANSPARENT_KEY[3:5], 16)
        b = int(TRANSPARENT_KEY[5:7], 16)
        user32.SetLayeredWindowAttributes(hwnd, (b << 16) | (g << 8) | r, 0, LWA_COLORKEY)

    def _init_pools(self):
        # Непиксельное северное сияние (если есть PIL — мягкий размытый слой; иначе гладкие слои без stipple)
        self.aurora_img_id = self.canvas.create_image(0, 0, anchor="nw", state="hidden")

        for _ in range(135):
            ov = self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            l1 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            l2 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            l3 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            py = self.canvas.create_polygon(-20, -20, -19, -20, -19, -19, fill="#ffffff", outline="", state="hidden")
            self.particle_pool.append((ov, l1, l2, l3, py))

        self.chunk_pool = [
            self.canvas.create_oval(-20, -20, -14, -14, fill="#ffffff", outline="#e2e8f0", width=1, state="hidden")
            for _ in range(110)
        ]

        self.spark_pool = [
            self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            for _ in range(130)
        ]

        # Объёмные сугробы (основа + мягкая шапка)
        self.pile_pool = []
        for _ in range(self.pile_cols):
            base = self.canvas.create_rectangle(-20, -20, -15, -15, fill="#f8fafc", outline="", state="hidden")
            cap = self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            self.pile_pool.append((base, cap))

        # Гирлянда БЕЗ stipple-ореолов: цвет не выходит за границы лампочки!
        for _ in range(260):
            wire = self.canvas.create_line(-20, -20, -10, -20, fill="#1e2433", width=2, state="hidden")
            socket = self.canvas.create_rectangle(-20, -20, -15, -15, fill="#334155", outline="#0f172a", width=1, state="hidden")
            body = self.canvas.create_polygon(-20, -20, -19, -20, -19, -19, fill="#ff3b3b", outline="#0f172a", width=1, state="hidden")
            shine = self.canvas.create_oval(-20, -20, -17, -17, fill="#ffffff", outline="", state="hidden")
            self.bulb_pool.append((wire, socket, body, shine))

        plow_body = self.canvas.create_polygon(-100, -100, -90, -100, -90, -90, fill="#f97316", outline="#0f172a", width=1, state="hidden")
        plow_blade = self.canvas.create_polygon(-100, -100, -90, -100, -90, -90, fill="#eab308", outline="#0f172a", width=1, state="hidden")
        plow_beacon = self.canvas.create_oval(-100, -100, -95, -95, fill="#38bdf8", outline="", state="hidden")
        plow_wheel = self.canvas.create_oval(-100, -100, -95, -95, fill="#1e293b", outline="#94a3b8", width=1, state="hidden")
        self.plow_pool = (plow_body, plow_blade, plow_beacon, plow_wheel)

    # =========================================================================
    # СКАНИРОВАНИЕ ОКОН И РАЗЛЁТ СУГРОБОВ ПРИ СДВИГЕ / ДОСТИЖЕНИИ ВЕРХА
    # =========================================================================
    def _scan_windows(self, initial: bool = False):
        updated = {}
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def cb(hwnd, _lp):
            if self._is_own_window(hwnd):
                return True
            if not hwnd or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                return True
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if ex_style & WS_EX_TOOLWINDOW:
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            if cls_buf.value in (
                "Progman",
                "WorkerW",
                "Shell_TrayWnd",
                "Shell_SecondaryTrayWnd",
                "Windows.UI.Core.CoreWindow",
                "ApplicationFrameWindow",
            ):
                return True
            b = get_window_bounds(hwnd)
            if b and b[0] > -10000 and (b[2] - b[0]) > 140 and (b[3] - b[1]) > 50:
                updated[hwnd] = b
            return True

        user32.EnumWindows(WNDENUMPROC(cb), 0)

        if not initial and self.pile_enabled.get():
            self._shed_snow_from_moved_windows(updated)

        self.window_bounds = updated
        fg = user32.GetForegroundWindow()
        self.active_hwnd = fg if (fg in updated and not self._is_own_window(fg)) else None

    def _shed_snow_from_moved_windows(self, new_bounds: dict):
        s = self._active_season()
        if s == "summer":
            return
        cols = {"winter": "#f8fafc", "spring": "#6ee7b7", "autumn": "#ea580c"}
        c_col = cols.get(s, "#f8fafc")

        for hwnd, old_b in self.window_bounds.items():
            new_b = new_bounds.get(hwnd)
            moved = (new_b is None) or (
                abs(old_b[0] - new_b[0]) > 3
                or abs(old_b[1] - new_b[1]) > 3
                or abs(old_b[2] - new_b[2]) > 3
            )
            if moved:
                c0 = max(0, int(old_b[0] // self.pile_step))
                c1 = min(self.pile_cols - 1, int(old_b[2] // self.pile_step))
                top_y = old_b[1]
                for col in range(c0, c1 + 1):
                    if self.pile_owner[col] == hwnd and self.pile[col] > 0.8:
                        h = self.pile[col]
                        for _ in range(2):
                            if len(self.falling_chunks) < len(self.chunk_pool):
                                self.falling_chunks.append(
                                    {
                                        "x": float(col * self.pile_step + random.uniform(0, self.pile_step)),
                                        "y": float(top_y - h),
                                        "vx": random.uniform(-2.2, 2.2),
                                        "vy": random.uniform(0.4, 2.2),
                                        "r": min(5.5, max(2.4, h * 0.28)),
                                        "color": c_col,
                                    }
                                )
                        self.pile[col] = 0.0
                        self.pile_owner[col] = 0

    def _windows_loop(self):
        self._scan_windows()
        self.root.after(95, self._windows_loop)

    def _blink_loop(self):
        self.blink_phase = (self.blink_phase + 1) % 48
        self.root.after(260, self._blink_loop)

    def _active_season(self) -> str:
        return get_current_season() if self.auto_season.get() else self.season.get()

    def _rebuild_particles(self):
        n = min(len(self.particle_pool), self.count_var.get())
        self.particles = [self._spawn_particle(random_y=True) for _ in range(n)]

    def _spawn_particle(self, random_y: bool = False):
        s = self._active_season()
        sh = self.flake_shape.get()
        if sh == "mix":
            sh = random.choice(["circle", "crystal", "star"])

        cols = {
            "winter": ["#ffffff", "#e0f2fe", "#bae6fd"],
            "spring": ["#6ee7b7", "#34d399", "#a7f3d0", "#bef264"],
            "summer": ["#fef08a", "#fde047", "#bef264"],
            "autumn": ["#f59e0b", "#ea580c", "#dc2626", "#eab308"],
        }

        return {
            "x": random.uniform(0, self.screen_w),
            "y": random.uniform(-self.screen_h, self.screen_h) if random_y else random.uniform(-25, -4),
            "r": random.uniform(2.5, 5.0) if s != "summer" else random.uniform(2.2, 3.6),
            "spd": random.uniform(0.75, 1.35),
            "phase": random.uniform(0, math.tau),
            "ang": random.uniform(0, math.tau),
            "spin": random.uniform(-0.06, 0.06),
            "shape": sh,
            "color": random.choice(cols[s]),
        }

    def _find_landing_surface(self, x: float, prev_y: float, new_y: float, tb_top: int):
        """
        Возвращает (y_поверхности, hwnd_владельца), если частица пересекла верхнюю грань
        окна/вкладки сверху вниз или достигла панели задач. Снизу/сбоку на окно снег не забирается.
        """
        best_y = float(tb_top)
        owner = 0

        for hwnd, b in self.window_bounds.items():
            l, t, r, btm = b
            if l <= x <= r and t < btm and t < tb_top:
                # Пересекает верхнюю кромку окна сверху вниз
                if prev_y <= t + 2 and new_y >= t and t < best_y:
                    best_y = float(t)
                    owner = hwnd

        return best_y, owner

    # =========================================================================
    # НЕПИКСЕЛЬНОЕ СЕВЕРНОЕ СИЯНИЕ
    # =========================================================================
    def _render_aurora_smooth(self):
        if not self.aurora_enabled.get():
            self.canvas.itemconfigure(self.aurora_img_id, state="hidden")
            return

        if HAS_PIL:
            # Рендерим в уменьшенном буфере и растягиваем с плавным GaussianBlur -> без пиксельных точек
            w_sub = max(240, self.screen_w // 3)
            h_sub = 56
            img = Image.new("RGBA", (w_sub, h_sub), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img, "RGBA")

            bands = [
                ((16, 185, 129, 78), 0.7, 0.0),
                ((45, 212, 191, 68), 1.0, 1.8),
                ((56, 189, 248, 56), 1.3, 3.5),
                ((168, 85, 247, 50), 0.9, 5.1),
            ]
            for rgba, freq, phase_off in bands:
                pts = []
                steps = 28
                for i in range(steps + 1):
                    t_norm = i / steps
                    px = t_norm * w_sub
                    wave = math.sin(self.anim_phase * 0.8 + t_norm * 6.5 * freq + phase_off)
                    py = 14 + 14 * (0.5 + 0.5 * wave) + 5 * math.cos(self.anim_phase * 1.2 + t_norm * 11.0)
                    pts.append((px, py))
                poly = [(0, 0)] + pts + [(w_sub, 0)]
                draw.polygon(poly, fill=rgba)

            img = img.filter(ImageFilter.GaussianBlur(radius=9))
            img = img.resize((self.screen_w, h_sub * 3), Image.Resampling.BILINEAR)
            self.aurora_photo = ImageTk.PhotoImage(img)
            self.canvas.itemconfigure(self.aurora_img_id, image=self.aurora_photo, state="normal")
            self.canvas.coords(self.aurora_img_id, 0, 0)
        else:
            self.canvas.itemconfigure(self.aurora_img_id, state="hidden")

    # =========================================================================
    # ГЛАВНЫЙ ЦИКЛ СИМУЛЯЦИИ
    # =========================================================================
    def _anim_loop(self):
        self.anim_phase += 0.055
        if self.storm_timer > 0:
            self.storm_timer -= 1

        if self.fireworks_enabled.get():
            self.fw_ticks -= 1
            if self.fw_ticks <= 0:
                self._spawn_firework_burst()
                self.fw_ticks = max(1, int(self.firework_interval.get() * (1000 / 28)))

        s = self._active_season()
        tb_top = get_taskbar_top(self.screen_h)
        storm_mult = 2.2 if self.storm_timer > 0 else 1.0
        cap_h = float(self.pile_max_cap.get())

        # 0. Северное сияние
        self._render_aurora_smooth()

        # 1. Частицы погоды
        show_weather = self.weather_enabled.get()
        base_spd = self.speed_var.get() * storm_mult
        wind = self.wind_var.get() + (2.4 if self.storm_timer > 0 else 0.0)

        target_n = min(len(self.particle_pool), self.count_var.get())
        while len(self.particles) < target_n:
            self.particles.append(self._spawn_particle(random_y=True))
        while len(self.particles) > target_n:
            self.particles.pop()

        col_colors = {"winter": "#f8fafc", "spring": "#6ee7b7", "autumn": "#ea580c"}
        c_col = col_colors.get(s, "#f8fafc")

        for idx, slot in enumerate(self.particle_pool):
            ov, l1, l2, l3, py = slot
            if not show_weather or idx >= len(self.particles):
                for obj in slot:
                    self.canvas.itemconfigure(obj, state="hidden")
                continue

            p = self.particles[idx]
            prev_y = p["y"]
            p["phase"] += 0.05
            p["ang"] += p["spin"]

            if s == "summer":
                p["x"] += math.cos(p["phase"]) * 1.1 + wind * 0.25
                p["y"] += math.sin(p["phase"] * 0.8) * 0.8 - 0.12
                if p["y"] < 24:
                    p["y"] = tb_top - 30
            else:
                p["y"] += base_spd * p["spd"]
                p["x"] += math.sin(p["phase"]) * 0.85 + wind

            if p["x"] < -12:
                p["x"] = self.screen_w + 12
            elif p["x"] > self.screen_w + 12:
                p["x"] = -12

            if s != "summer":
                col = max(0, min(self.pile_cols - 1, int(p["x"] // self.pile_step)))
                surf_y, owner_hwnd = self._find_landing_surface(p["x"], prev_y, p["y"], tb_top)
                pile_h = self.pile[col] if self.pile_enabled.get() else 0.0

                if p["y"] >= surf_y - pile_h:
                    if self.pile_enabled.get():
                        for d_col, w in ((-1, 0.3), (0, 0.7), (1, 0.3)):
                            c = col + d_col
                            if 0 <= c < self.pile_cols:
                                # Если под колонкой окно, привязываем сугроб к этому окну
                                if owner_hwnd:
                                    self.pile_owner[c] = owner_hwnd
                                next_h = self.pile[c] + w
                                # Когда сугроб достигает заданной высоты или верха экрана — разлетается комьями
                                if next_h >= cap_h or (surf_y - next_h) <= 2.0:
                                    if len(self.falling_chunks) < len(self.chunk_pool):
                                        self.falling_chunks.append(
                                            {
                                                "x": float(c * self.pile_step + 2),
                                                "y": float(surf_y - next_h),
                                                "vx": random.uniform(-1.8, 1.8),
                                                "vy": random.uniform(0.3, 1.6),
                                                "r": random.uniform(2.5, 4.2),
                                                "color": c_col,
                                            }
                                        )
                                    self.pile[c] = max(2.0, next_h * 0.45)
                                else:
                                    self.pile[c] = next_h
                    p.update(self._spawn_particle(random_y=False))

            self._render_particle(slot, p, s)

        # 2. Физика разлетающихся комьев сугроба
        alive_chunks = []
        for ch in self.falling_chunks:
            prev_cy = ch["y"]
            ch["x"] += ch["vx"]
            ch["y"] += ch["vy"]
            ch["vy"] += 0.28
            col = max(0, min(self.pile_cols - 1, int(ch["x"] // self.pile_step)))
            surf_y, owner_hwnd = self._find_landing_surface(ch["x"], prev_cy, ch["y"], tb_top)
            if ch["y"] >= surf_y - self.pile[col]:
                if self.pile_enabled.get() and s != "summer":
                    self.pile[col] = min(cap_h, self.pile[col] + 0.9)
                    if owner_hwnd:
                        self.pile_owner[col] = owner_hwnd
            else:
                alive_chunks.append(ch)
        self.falling_chunks = alive_chunks

        for idx, cid in enumerate(self.chunk_pool):
            if idx < len(self.falling_chunks):
                ch = self.falling_chunks[idx]
                r = ch["r"]
                self.canvas.coords(cid, ch["x"] - r, ch["y"] - r, ch["x"] + r, ch["y"] + r)
                self.canvas.itemconfigure(cid, fill=ch["color"], state="normal")
            else:
                self.canvas.itemconfigure(cid, state="hidden")

        # 3. Отрисовка красивых сугробов (основа + мягкая шапка)
        for i, (base_id, cap_id) in enumerate(self.pile_pool):
            h = self.pile[i] if (self.pile_enabled.get() and s != "summer") else 0.0
            if h > 0.7:
                x1 = i * self.pile_step
                x2 = x1 + self.pile_step + 1
                owner = self.pile_owner[i]
                if owner and owner in self.window_bounds:
                    base_y = self.window_bounds[owner][1]
                else:
                    base_y = tb_top
                top_y = max(1.0, base_y - h)
                self.canvas.coords(base_id, x1, top_y + h * 0.35, x2, base_y + 1)
                self.canvas.itemconfigure(base_id, fill=c_col, state="normal")

                r_cap = max(2.2, self.pile_step * 0.65)
                cy_cap = top_y + r_cap * 0.6
                self.canvas.coords(cap_id, x1 - 1, cy_cap - r_cap * 0.65, x2 + 1, cy_cap + r_cap * 0.65)
                self.canvas.itemconfigure(cap_id, fill="#ffffff" if s == "winter" else c_col, state="normal")
            else:
                self.canvas.itemconfigure(base_id, state="hidden")
                self.canvas.itemconfigure(cap_id, state="hidden")

        # 4. Снегоуборочная машина
        self._update_snowplow(s, tb_top)

        # 5. Шлейф курсора + фейерверки
        if self.cursor_trail.get():
            pt = wintypes.POINT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                if abs(pt.x - self.last_mouse[0]) + abs(pt.y - self.last_mouse[1]) > 5:
                    t_cols = {
                        "winter": ["#ffffff", "#bae6fd", "#7dd3fc"],
                        "spring": ["#86efac", "#f9a8d4", "#fef08a"],
                        "summer": ["#fef08a", "#fde047", "#bef264"],
                        "autumn": ["#fb923c", "#facc15", "#f87171"],
                    }[s]
                    self.sparks.append(
                        {
                            "x": float(pt.x) + random.uniform(-4, 4),
                            "y": float(pt.y) + random.uniform(-4, 4),
                            "vx": random.uniform(-0.8, 0.8),
                            "vy": random.uniform(0.3, 1.3),
                            "life": 11,
                            "color": random.choice(t_cols),
                        }
                    )
                    self.last_mouse = (pt.x, pt.y)

        self.sparks = [
            {**sp, "x": sp["x"] + sp["vx"], "y": sp["y"] + sp["vy"], "life": sp["life"] - 1}
            for sp in self.sparks
            if sp["life"] > 1
        ]
        self.fireworks = [
            {
                **fw,
                "x": fw["x"] + fw["vx"],
                "y": fw["y"] + fw["vy"],
                "vy": fw["vy"] + 0.14,
                "life": fw["life"] - 1,
            }
            for fw in self.fireworks
            if fw["life"] > 1
        ]

        all_sp = self.sparks + self.fireworks
        for idx, sid in enumerate(self.spark_pool):
            if idx < len(all_sp):
                sp = all_sp[idx]
                rad = max(1.4, sp["life"] * 0.18)
                self.canvas.coords(sid, sp["x"] - rad, sp["y"] - rad, sp["x"] + rad, sp["y"] + rad)
                self.canvas.itemconfigure(sid, fill=sp["color"], state="normal")
            else:
                self.canvas.itemconfigure(sid, state="hidden")

        # 6. Гирлянда
        self._render_garlands()

        self.root.after(28, self._anim_loop)

    def _update_snowplow(self, season: str, tb_top: int):
        plow_body, plow_blade, plow_beacon, plow_wheel = self.plow_pool
        can_plow = self.plow_enabled.get() and self.pile_enabled.get() and season != "summer"

        if not can_plow:
            self.plow_active = False
            for obj in self.plow_pool:
                self.canvas.itemconfigure(obj, state="hidden")
            return

        if not self.plow_active:
            self.plow_ticks += 1
            mode = self.plow_mode.get()
            time_ok = self.plow_ticks >= max(1, int(self.plow_interval.get() * (1000 / 28)))
            max_p = max(self.pile) if self.pile else 0.0
            thresh_ok = max_p >= float(self.plow_threshold.get())

            start = (
                (mode == "time" and time_ok)
                or (mode == "threshold" and thresh_ok)
                or (mode == "both" and (time_ok or thresh_ok))
            )
            if start and max_p > 0.5:
                self.plow_active = True
                self.plow_ticks = 0
                self.plow_x = -80.0
            else:
                for obj in self.plow_pool:
                    self.canvas.itemconfigure(obj, state="hidden")
                return

        self.plow_x += 9.5
        px = self.plow_x
        base_y = float(tb_top)

        col_clear = int((px + 25) // self.pile_step)
        for c in range(max(0, col_clear - 4), min(self.pile_cols, col_clear + 2)):
            if self.pile_owner[c] == 0:
                self.pile[c] = 0.0

        if px > self.screen_w + 90:
            self.plow_active = False
            for obj in self.plow_pool:
                self.canvas.itemconfigure(obj, state="hidden")
            return

        self.canvas.coords(
            plow_body,
            px - 34, base_y - 18,
            px + 6, base_y - 18,
            px + 12, base_y - 6,
            px - 34, base_y - 6,
        )
        self.canvas.itemconfigure(plow_body, fill="#f97316", outline="#0f172a", width=1, state="normal")

        self.canvas.coords(
            plow_blade,
            px + 10, base_y - 14,
            px + 22, base_y - 3,
            px + 12, base_y - 3,
        )
        self.canvas.itemconfigure(plow_blade, fill="#facc15", outline="#0f172a", width=1, state="normal")

        b_col = "#38bdf8" if (int(self.anim_phase * 8) % 2 == 0) else "#ef4444"
        self.canvas.coords(plow_beacon, px - 16, base_y - 23, px - 9, base_y - 17)
        self.canvas.itemconfigure(plow_beacon, fill=b_col, state="normal")

        self.canvas.coords(plow_wheel, px - 26, base_y - 8, px - 16, base_y + 2)
        self.canvas.itemconfigure(plow_wheel, fill="#1e293b", outline="#cbd5e1", width=1, state="normal")

    def _render_particle(self, slot, p, season: str):
        ov, l1, l2, l3, py = slot
        for obj in slot:
            self.canvas.itemconfigure(obj, state="hidden")

        x, y, r, col = p["x"], p["y"], p["r"], p["color"]

        if season == "winter":
            sh = p["shape"]
            if sh == "circle":
                self.canvas.coords(ov, x - r, y - r, x + r, y + r)
                self.canvas.itemconfigure(ov, fill=col, state="normal")
            elif sh == "star":
                self.canvas.coords(l1, x - r * 1.4, y, x + r * 1.4, y)
                self.canvas.coords(l2, x, y - r * 1.4, x, y + r * 1.4)
                d = r * 0.9
                self.canvas.coords(l3, x - d, y - d, x + d, y + d)
                self.canvas.itemconfigure(l1, fill=col, width=1.5, state="normal")
                self.canvas.itemconfigure(l2, fill=col, width=1.5, state="normal")
                self.canvas.itemconfigure(l3, fill=col, width=1.2, state="normal")
            else:
                for k, lid in enumerate((l1, l2, l3)):
                    ang = p["ang"] + k * (math.pi / 3)
                    dx = math.cos(ang) * (r * 1.35)
                    dy = math.sin(ang) * (r * 1.35)
                    self.canvas.coords(lid, x - dx, y - dy, x + dx, y + dy)
                    self.canvas.itemconfigure(lid, fill=col, width=1.4, state="normal")

        elif season in ("spring", "autumn"):
            ang = p["ang"]
            dx, dy = math.cos(ang) * (r * 1.5), math.sin(ang) * (r * 1.5)
            px, py_off = -math.sin(ang) * (r * 0.75), math.cos(ang) * (r * 0.75)
            self.canvas.coords(py, x + dx, y + dy, x + px, y + py_off, x - dx, y - dy, x - px, y - py_off)
            self.canvas.itemconfigure(py, fill=col, state="normal")

        else:
            rr = r * (0.65 + 0.35 * math.sin(p["phase"] * 2.5))
            self.canvas.coords(ov, x - rr, y - rr, x + rr, y + rr)
            self.canvas.itemconfigure(ov, fill=col, state="normal")

    def _render_garlands(self):
        palettes = {
            "classic": ["#ff3b3b", "#22c55e", "#38bdf8", "#facc15", "#e879f9"],
            "warm": ["#fef08a", "#fde047", "#fdba74", "#fed7aa", "#fef9c3"],
            "cyber": ["#f43f5e", "#d946ef", "#8b5cf6", "#06b6d4", "#22d3ee"],
            "ice": ["#ffffff", "#e0f2fe", "#7dd3fc", "#38bdf8", "#bae6fd"],
        }
        sc = float(self.garland_scale.get())
        rad_x = 5.0 * sc
        rad_y = 13.0 * sc

        colors = palettes.get(self.garland_palette.get(), palettes["classic"])
        mode = self.garland_mode.get()
        style = self.garland_style.get()
        spacing = max(22, int(self.garland_spacing.get() * max(0.8, min(1.35, sc))))

        lines = []
        if self.top_garland.get():
            lines.append((12, self.screen_w - 12, 2))

        if self.win_garland.get():
            scope = self.win_scope.get()
            for hwnd, b in list(self.window_bounds.items()):
                if scope == "active" and hwnd != self.active_hwnd:
                    continue
                left, top, right, bottom = b
                if left < -10000 or bottom <= top or (right - left) < 130:
                    continue
                l_c = max(6, left + 8)
                r_c = min(self.screen_w - 6, right - 8)
                t_c = max(2, top)
                if r_c - l_c >= 90:
                    lines.append((l_c, r_c, t_c))

        plan = []
        for x0, x1, y_top in lines:
            xs = list(range(x0, x1, spacing))
            if len(xs) < 2:
                continue
            for idx, bx in enumerate(xs):
                nx = xs[idx + 1] if idx + 1 < len(xs) else min(x1, bx + spacing)
                plan.append((bx, nx, y_top, idx))

        sag = 5.0 * sc
        for i, slot in enumerate(self.bulb_pool):
            wire, socket, body, shine = slot
            if i >= len(plan):
                for obj in slot:
                    self.canvas.itemconfigure(obj, state="hidden")
                continue

            bx, nx, y_top, idx = plan[i]
            mx = (bx + nx) * 0.5

            if mode == "rainbow":
                col = colors[(idx + self.blink_phase) % len(colors)]
                lit = True
            else:
                col = colors[idx % len(colors)]
                if mode == "steady":
                    lit = True
                elif mode == "wave":
                    lit = ((idx + self.blink_phase) % 3) != 0
                else:
                    lit = ((idx * 5 + self.blink_phase) % 4) != 0

            self.canvas.coords(wire, bx, y_top + 1, mx, y_top + 1 + sag, nx, y_top + 1)
            self.canvas.itemconfigure(wire, fill="#1e2433", width=max(1.5, 2.0 * sc), state="normal")

            sw = max(2.0, 2.4 * sc)
            sh = max(2.5, 3.5 * sc)
            self.canvas.coords(socket, bx - sw, y_top + 1 + sag * 0.4, bx + sw, y_top + 1 + sag * 0.4 + sh)
            self.canvas.itemconfigure(socket, fill="#334155", outline="#0f172a", width=1, state="normal")

            fill_col = col if lit else "#293248"
            top_b = y_top + 1 + sag * 0.4 + sh

            if style == "icicle":
                pts = [
                    bx - rad_x * 0.72, top_b,
                    bx + rad_x * 0.72, top_b,
                    bx, top_b + rad_y * 1.45,
                ]
            elif style == "star":
                s_r = rad_x * 1.25
                pts = [
                    bx, top_b,
                    bx + s_r * 0.45, top_b + s_r * 0.75,
                    bx + s_r, top_b + s_r,
                    bx + s_r * 0.45, top_b + s_r * 1.25,
                    bx, top_b + s_r * 2.0,
                    bx - s_r * 0.45, top_b + s_r * 1.25,
                    bx - s_r, top_b + s_r,
                    bx - s_r * 0.45, top_b + s_r * 0.75,
                ]
            else:
                r_bulb = max(3.5, rad_x * 1.0)
                cy_b = top_b + r_bulb * 0.9
                pts = []
                steps = 12
                for k in range(steps):
                    ang = (math.tau * k) / steps
                    pts.extend([bx + math.cos(ang) * r_bulb, cy_b + math.sin(ang) * r_bulb])

            self.canvas.coords(body, *pts)
            self.canvas.itemconfigure(body, fill=fill_col, outline="#0f172a", width=1, state="normal")

            if lit:
                s_rad = max(1.0, rad_x * 0.28)
                sx = bx - rad_x * 0.28
                sy = top_b + rad_x * 0.65
                self.canvas.coords(shine, sx - s_rad, sy - s_rad, sx + s_rad, sy + s_rad)
                self.canvas.itemconfigure(shine, fill="#ffffff", state="normal")
            else:
                self.canvas.itemconfigure(shine, state="hidden")


if __name__ == "__main__":
    app = AtmosphereMultiWindowApp()
    app.root.mainloop()
