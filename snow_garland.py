import ctypes
from ctypes import wintypes
import datetime
import math
import random
import tkinter as tk

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
LWA_COLORKEY = 0x00000001

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_NOZORDER = 0x0004

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2

TRANSPARENT_KEY = "#010203"
MENU_TITLE = "Atmosphere Studio"


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


def pin_topmost_noactivate(hwnd):
    if hwnd:
        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )


class SmoothSlider(tk.Canvas):
    def __init__(self, parent, variable, lo, hi, step=1, accent="#38bdf8", bg="#141926", is_float=False):
        super().__init__(parent, width=170, height=20, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
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

    def _val_from_x(self, x: float):
        pad = 8.0
        usable = max(1.0, float(self.winfo_reqwidth()) - 2 * pad)
        ratio = max(0.0, min(1.0, (x - pad) / usable))
        raw = self.lo + ratio * (self.hi - self.lo)
        snapped = round(raw / self.step) * self.step
        clamped = max(self.lo, min(self.hi, snapped))
        if self.is_float:
            return round(clamped, 2)
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
        pad = 8.0
        cy = 10.0
        cur = float(self.var.get())
        span = max(1e-9, self.hi - self.lo)
        ratio = max(0.0, min(1.0, (cur - self.lo) / span))
        kx = pad + ratio * (w - 2 * pad)

        self.create_line(pad, cy, w - pad, cy, fill="#242c42", width=4, capstyle="round")
        if kx > pad:
            self.create_line(pad, cy, kx, cy, fill=self.accent, width=4, capstyle="round")
        self.create_oval(kx - 6, cy - 6, kx + 6, cy + 6, fill="#ffffff", outline=self.accent, width=2)


class SwitchPill(tk.Canvas):
    def __init__(self, parent, var: tk.BooleanVar, command=None, accent="#38bdf8", bg="#141926"):
        super().__init__(parent, width=38, height=18, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
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
        self.create_oval(1, 1, 17, 17, fill=col, outline="")
        self.create_oval(21, 1, 37, 17, fill=col, outline="")
        self.create_rectangle(9, 1, 29, 17, fill=col, outline="")
        kx = 29 if on else 9
        self.create_oval(kx - 6, 3, kx + 6, 15, fill="#ffffff", outline="")


class AtmosphereStudioApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(MENU_TITLE)
        self.menu_w = 560
        self.menu_h = 640
        self.menu_x = 90
        self.menu_y = 60
        self.root.geometry(f"{self.menu_w}x{self.menu_h}+{self.menu_x}+{self.menu_y}")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0b0e17")

        try:
            self.root.update_idletasks()
            self.root_hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            dwmapi.DwmSetWindowAttribute(
                self.root_hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
                ctypes.sizeof(ctypes.c_int),
            )
            pin_topmost_noactivate(self.root_hwnd)
        except Exception:
            self.root_hwnd = None

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # --- Снег и Метель ---
        self.weather_enabled = tk.BooleanVar(value=True)
        self.auto_season = tk.BooleanVar(value=False)
        self.season = tk.StringVar(value="winter")
        self.flake_shape = tk.StringVar(value="crystal")
        self.count_var = tk.IntVar(value=70)
        self.speed_var = tk.DoubleVar(value=2.0)
        self.wind_var = tk.DoubleVar(value=0.25)
        self.blizzard_var = tk.DoubleVar(value=0.0)
        self.storm_timer = 0

        # --- Сугробы ---
        self.pile_enabled = tk.BooleanVar(value=True)
        self.pile_max_cap = tk.IntVar(value=22)

        # --- Машина ---
        self.plow_enabled = tk.BooleanVar(value=True)
        self.plow_mode = tk.StringVar(value="both")
        self.plow_interval = tk.IntVar(value=20)
        self.plow_threshold = tk.IntVar(value=10)
        self.plow_speed = tk.DoubleVar(value=7.5)
        self.plow_blade_w = tk.IntVar(value=22)

        self.plow_x = -80.0
        self.plow_y = float(get_taskbar_top(self.screen_h))
        self.plow_active = False
        self.plow_ticks = 0
        self.plow_force_once = False

        # --- Гирлянда ---
        self.top_garland = tk.BooleanVar(value=True)
        self.win_garland = tk.BooleanVar(value=True)
        self.win_scope = tk.StringVar(value="all")
        self.garland_style = tk.StringVar(value="bulb")
        self.garland_scale = tk.DoubleVar(value=1.0)
        self.garland_mode = tk.StringVar(value="rainbow")
        self.garland_palette = tk.StringVar(value="classic")
        self.garland_spacing = tk.IntVar(value=38)
        self._garland_dirty = True

        # --- Салют (Фейерверки) ---
        self.fireworks_enabled = tk.BooleanVar(value=True)
        self.firework_interval = tk.IntVar(value=6)
        self.firework_power = tk.DoubleVar(value=1.0)
        self.fw_ticks = 45

        # --- Аврора и шлейф ---
        self.aurora_enabled = tk.BooleanVar(value=True)
        self.aurora_height = tk.IntVar(value=18)
        self.aurora_speed = tk.DoubleVar(value=1.0)
        self.cursor_trail = tk.BooleanVar(value=True)

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
        self.dragging = False
        self._drag_root_xy = (0, 0)
        self._drag_win_xy = (0, 0)

        self.pile_step = 5
        self.pile_cols = (self.screen_w // self.pile_step) + 2
        self.pile = [0.0] * self.pile_cols
        self.pile_owner = [0] * self.pile_cols

        self.particle_pool = []
        self.chunk_pool = []
        self.spark_pool = []
        self.pile_pool = []
        self.bulb_pool = []
        self.aurora_lines = []
        self.plow_pool = ()
        self.overlay_hwnd = None
        self.my_hwnds = set()

        self._build_ui()
        self._init_overlay()
        self._init_pools()
        self._collect_my_hwnds()
        self._scan_windows(initial=True)
        self._rebuild_particles()

        self._anim_loop()
        self._blink_loop()
        self._windows_loop()
        self._topmost_loop()

    def _collect_my_hwnds(self):
        self.my_hwnds.clear()
        for h in (self.root_hwnd, self.overlay_hwnd):
            if h:
                self.my_hwnds.add(h)

    def _is_own_window(self, hwnd) -> bool:
        if hwnd in self.my_hwnds:
            return True
        return user32.GetParent(hwnd) in self.my_hwnds

    def _topmost_loop(self):
        if not self.dragging:
            try:
                if self.overlay_hwnd:
                    pin_topmost_noactivate(self.overlay_hwnd)
                if self.root_hwnd and self.root.state() == "normal":
                    pin_topmost_noactivate(self.root_hwnd)
            except Exception:
                pass
        self.root.after(500, self._topmost_loop)

    # =========================================================================
    # БЫСТРОЕ ПЕРЕТАСКИВАНИЕ БЕЗ ЛАГОВ (MoveWindow)
    # =========================================================================
    def _drag_start(self, e):
        self.dragging = True
        self._drag_root_xy = (e.x_root, e.y_root)
        self._drag_win_xy = (self.menu_x, self.menu_y)

    def _drag_move(self, e):
        nx = self._drag_win_xy[0] + (e.x_root - self._drag_root_xy[0])
        ny = self._drag_win_xy[1] + (e.y_root - self._drag_root_xy[1])
        self.menu_x = nx
        self.menu_y = ny
        if self.root_hwnd:
            user32.SetWindowPos(
                self.root_hwnd,
                0,
                nx,
                ny,
                0,
                0,
                SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
            )
        else:
            self.root.geometry(f"+{nx}+{ny}")

    def _drag_stop(self, _e):
        self.dragging = False
        self.root.geometry(f"{self.menu_w}x{self.menu_h}+{self.menu_x}+{self.menu_y}")
        self._garland_dirty = True
        if self.root_hwnd:
            pin_topmost_noactivate(self.root_hwnd)
        self._scan_windows()

    # =========================================================================
    # МЕНЮ: ВКЛАДКИ ДЛЯ КАЖДОЙ ФУНКЦИИ
    # =========================================================================
    def _build_ui(self):
        shell = tk.Frame(self.root, bg="#0b0e17", highlightbackground="#222a40", highlightthickness=1)
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg="#111625", height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, bg="#38bdf8", height=2).pack(fill="x", side="top")

        title_box = tk.Frame(header, bg="#111625")
        title_box.pack(side="left", padx=14, pady=6)

        lbl_t = tk.Label(title_box, text="✦ ATMOSPHERE STUDIO", bg="#111625", fg="#f8fafc", font=("Segoe UI", 11, "bold"))
        lbl_t.pack(anchor="w")

        s_names = {"winter": "❄️ Зима", "spring": "🌿 Весна", "summer": "✨ Лето", "autumn": "🍁 Осень"}
        lbl_s = tk.Label(
            title_box,
            text=f"Сезон: {s_names[get_current_season()]} • Поверх окон",
            bg="#111625",
            fg="#64748b",
            font=("Segoe UI", 8, "bold"),
        )
        lbl_s.pack(anchor="w")

        for w in (header, title_box, lbl_t, lbl_s):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<ButtonRelease-1>", self._drag_stop)

        btns_box = tk.Frame(header, bg="#111625")
        btns_box.pack(side="right", padx=12)

        tk.Button(
            btns_box,
            text="—",
            bg="#192036",
            fg="#94a3b8",
            activebackground="#25304f",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            width=3,
            pady=2,
            cursor="hand2",
            command=self._minimize,
        ).pack(side="left", padx=3)

        tk.Button(
            btns_box,
            text="✕",
            bg="#192036",
            fg="#f87171",
            activebackground="#ef4444",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            width=3,
            pady=2,
            cursor="hand2",
            command=self.root.destroy,
        ).pack(side="left", padx=3)

        tab_bar = tk.Frame(shell, bg="#111625", padx=3, pady=3)
        tab_bar.pack(fill="x", padx=12, pady=(8, 6))

        tab_defs = [
            ("snow", "❄️ Снег"),
            ("piles", "⛄ Сугробы"),
            ("plow", "🚜 Машина"),
            ("garland", "💡 Гирлянда"),
            ("fireworks", "🎆 Салют"),
            ("aurora", "🌌 Аврора"),
        ]

        self.tab_frames = {}
        self.tab_btns = {}
        for key, text in tab_defs:
            b = tk.Button(
                tab_bar,
                text=text,
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                bd=0,
                pady=6,
                cursor="hand2",
                command=lambda k=key: self._switch_tab(k),
            )
            b.pack(side="left", expand=True, fill="x", padx=1)
            self.tab_btns[key] = b
            self.tab_frames[key] = tk.Frame(shell, bg="#0b0e17")

        self._build_snow_tab(self.tab_frames["snow"])
        self._build_piles_tab(self.tab_frames["piles"])
        self._build_plow_tab(self.tab_frames["plow"])
        self._build_garland_tab(self.tab_frames["garland"])
        self._build_fireworks_tab(self.tab_frames["fireworks"])
        self._build_aurora_tab(self.tab_frames["aurora"])
        self._switch_tab("snow")

    def _minimize(self):
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.bind("", self._on_restore)

    def _on_restore(self, _e=None):
        if self.root.state() == "normal":
            self.root.unbind("")
            self.root.overrideredirect(True)
            if self.root_hwnd:
                pin_topmost_noactivate(self.root_hwnd)

    def _switch_tab(self, key: str):
        for k, f in self.tab_frames.items():
            f.pack_forget()
            act = k == key
            self.tab_btns[k].configure(
                bg="#2563eb" if act else "#111625",
                fg="#ffffff" if act else "#64748b",
            )
        self.tab_frames[key].pack(fill="both", expand=True, padx=14, pady=4)

    def _card(self, parent, title: str, accent="#38bdf8"):
        c = tk.Frame(parent, bg="#141926", highlightbackground="#1f273d", highlightthickness=1)
        c.pack(fill="x", pady=5)
        tk.Label(c, text=title, bg="#141926", fg=accent, font=("Segoe UI", 8, "bold")).pack(
            anchor="w", padx=12, pady=(7, 3)
        )
        body = tk.Frame(c, bg="#141926")
        body.pack(fill="x", padx=12, pady=(0, 9))
        return body

    def _toggle(self, parent, title: str, sub: str, var: tk.BooleanVar, cmd=None, accent="#38bdf8"):
        row = tk.Frame(parent, bg="#141926")
        row.pack(fill="x", pady=3)
        left = tk.Frame(row, bg="#141926")
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=title, bg="#141926", fg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        if sub:
            tk.Label(left, text=sub, bg="#141926", fg="#64748b", font=("Segoe UI", 8)).pack(anchor="w")
        SwitchPill(row, var, command=cmd, accent=accent, bg="#141926").pack(side="right", padx=(8, 0))

    def _pills(self, parent, items, getter, setter, accent="#2563eb"):
        row = tk.Frame(parent, bg="#0f1320", padx=3, pady=3)
        row.pack(fill="x", pady=(4, 2))
        btns = {}
        for k, lbl in items:
            b = tk.Button(
                row,
                text=lbl,
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                bd=0,
                pady=5,
                cursor="hand2",
                command=lambda val=k: setter(val),
            )
            b.pack(side="left", expand=True, fill="x", padx=2)
            btns[k] = b

        def refresh():
            cur = getter()
            for k, b in btns.items():
                is_c = k == cur
                b.configure(
                    bg=accent if is_c else "#0f1320",
                    fg="#ffffff" if is_c else "#64748b",
                )

        refresh()
        return refresh

    def _slider_row(self, parent, lbl: str, var, lo, hi, step=1, accent="#38bdf8", is_float=False, cmd=None):
        row = tk.Frame(parent, bg="#141926")
        row.pack(fill="x", pady=2)
        tk.Label(row, text=lbl, bg="#141926", fg="#cbd5e1", font=("Segoe UI", 9)).pack(side="left")
        v_lbl = tk.Label(row, text="", bg="#141926", fg=accent, font=("Segoe UI", 9, "bold"), width=5, anchor="e")
        v_lbl.pack(side="right", padx=(4, 0))

        def on_var(*_a):
            val = var.get()
            v_lbl.config(text=f"{val:.2f}" if is_float else f"{val}")
            if cmd:
                cmd()

        var.trace_add("write", on_var)
        on_var()

        SmoothSlider(row, var, lo, hi, step=step, accent=accent, bg="#141926", is_float=is_float).pack(side="right")

    # --- Вкладка 1: Снег и Метель ---
    def _build_snow_tab(self, parent):
        c1 = self._card(parent, "ОСАДКИ, СЕЗОН И МЕТЕЛЬ", "#38bdf8")
        self._toggle(c1, "Включить осадки / листья / светлячки", "На пустом месте падают ниже до панели задач, на окнах оседают", self.weather_enabled)
        self._toggle(c1, "Авто-сезон по календарю", "Выбирает сезон по текущему месяцу", self.auto_season, cmd=self._on_auto_season, accent="#10b981")
        self._ref_season = self._pills(
            c1,
            [("winter", "❄️ Зима"), ("spring", "🌿 Весна"), ("summer", "✨ Лето"), ("autumn", "🍁 Осень")],
            self._active_season,
            self._set_season,
        )
        self._ref_shape = self._pills(
            c1,
            [("circle", "• Хлопья"), ("crystal", "❄ Кристаллы"), ("star", "✦ Звёзды"), ("mix", "🎲 Микс")],
            self.flake_shape.get,
            self._set_shape,
            accent="#6366f1",
        )

        c2 = self._card(parent, "СКОРОСТЬ, ВЕТЕР И МЕТЕЛЬ", "#a5b4fc")
        self._slider_row(c2, "Плотность:", self.count_var, 15, 130, 1, accent="#38bdf8", cmd=self._rebuild_particles)
        self._slider_row(c2, "Скорость:", self.speed_var, 0.6, 6.0, 0.2, accent="#38bdf8", is_float=True)
        self._slider_row(c2, "Ветер:", self.wind_var, -2.5, 2.5, 0.1, accent="#38bdf8", is_float=True)
        self._slider_row(c2, "Метель (порывы):", self.blizzard_var, 0.0, 3.0, 0.1, accent="#7dd3fc", is_float=True)
        tk.Button(
            c2,
            text="🌬️ Порыв метели на 5 сек",
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            pady=4,
            cursor="hand2",
            command=self._trigger_storm,
        ).pack(fill="x", pady=(4, 0))

    # --- Вкладка 2: Сугробы ---
    def _build_piles_tab(self, parent):
        c1 = self._card(parent, "СУГРОБЫ И ФИЗИКА ПАДЕНИЯ", "#60a5fa")
        self._toggle(
            c1,
            "Накапливать сугробы и листья",
            "При сдвиге окна или лимите высоты небольшие комья падают вниз",
            self.pile_enabled,
            cmd=self._on_pile_toggle,
        )
        self._slider_row(c1, "Лимит высоты сугроба (px):", self.pile_max_cap, 8, 45, 1, accent="#60a5fa")
        tk.Button(
            c1,
            text="🧹 Очистить сугробы и листья",
            bg="#1e263b",
            fg="#e2e8f0",
            activebackground="#2b3654",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self._clear_pile,
        ).pack(fill="x", pady=(6, 0))

    # --- Вкладка 3: Машина ---
    def _build_plow_tab(self, parent):
        c1 = self._card(parent, "СНЕГОУБОРОЧНАЯ МАШИНА", "#f59e0b")
        self._toggle(
            c1,
            "Уборочная машина",
            "Едет по низу, заезжает на окна Windows, чистит и уходит вправо",
            self.plow_enabled,
            accent="#f59e0b",
        )
        self._ref_plow = self._pills(
            c1,
            [("both", "⏱️+📏 Оба"), ("time", "⏱️ По времени"), ("threshold", "📏 По порогу")],
            self.plow_mode.get,
            self._set_plow_mode,
            accent="#d97706",
        )
        self._slider_row(c1, "Скорость тачки:", self.plow_speed, 3.0, 15.0, 0.5, accent="#f59e0b", is_float=True)
        self._slider_row(c1, "Ширина отвала (px):", self.plow_blade_w, 12, 34, 2, accent="#f59e0b")
        self._slider_row(c1, "Интервал рейса (сек):", self.plow_interval, 5, 120, 5, accent="#f59e0b")
        self._slider_row(c1, "Порог сугроба (px):", self.plow_threshold, 4, 30, 1, accent="#f59e0b")
        tk.Button(
            c1,
            text="🚜 Вызвать тачку сейчас",
            bg="#b45309",
            fg="#ffffff",
            activebackground="#92400e",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=5,
            cursor="hand2",
            command=self._call_plow_now,
        ).pack(fill="x", pady=(6, 0))

    # --- Вкладка 4: Гирлянда ---
    def _build_garland_tab(self, parent):
        c1 = self._card(parent, "РАСПОЛОЖЕНИЕ И ФОРМА", "#fbbf24")
        self._toggle(c1, "Гирлянда вверху экрана", "Вдоль верхнего края монитора", self.top_garland, cmd=self._mark_garland_dirty, accent="#f59e0b")
        self._toggle(c1, "Гирлянда на окнах", "Крепится на верхних рамках окон", self.win_garland, cmd=self._mark_garland_dirty, accent="#f59e0b")
        self._ref_scope = self._pills(
            c1,
            [("all", "На всех окнах"), ("active", "Только активное")],
            self.win_scope.get,
            self._set_scope,
            accent="#d97706",
        )
        self._ref_style = self._pills(
            c1,
            [("bulb", "💡 Лампочки"), ("icicle", "🧊 Сосульки"), ("star", "✦ Звёзды")],
            self.garland_style.get,
            self._set_style,
            accent="#ea580c",
        )

        c2 = self._card(parent, "РАЗМЕР, РЕЖИМ И ЦВЕТА", "#f472b6")
        self._slider_row(c2, "Размер гирлянды:", self.garland_scale, 0.6, 1.8, 0.05, accent="#f472b6", is_float=True, cmd=self._mark_garland_dirty)
        self._slider_row(c2, "Шаг между лампочками (px):", self.garland_spacing, 24, 72, 2, accent="#f472b6", cmd=self._mark_garland_dirty)
        self._ref_mode = self._pills(
            c2,
            [("rainbow", "🌈 Перелив"), ("wave", "🌊 Волна"), ("twinkle", "✨ Мерцание"), ("steady", "💡 Ровный")],
            self.garland_mode.get,
            self._set_mode,
            accent="#db2777",
        )
        self._ref_pal = self._pills(
            c2,
            [("classic", "🎄 Классика"), ("warm", "🕯️ Тёплая"), ("cyber", "🟣 Неон"), ("ice", "🧊 Лёд")],
            self.garland_palette.get,
            self._set_palette,
            accent="#059669",
        )

    # --- Вкладка 5: Салют ---
    def _build_fireworks_tab(self, parent):
        c1 = self._card(parent, "НАСТРОЙКА САЛЮТА", "#f43f5e")
        self._toggle(c1, "Автоматический салют", "Запускает залпы через выбранный интервал", self.fireworks_enabled, accent="#f43f5e")
        self._slider_row(c1, "Интервал запуска (сек):", self.firework_interval, 2, 30, 1, accent="#f43f5e")
        self._slider_row(c1, "Сила залпа:", self.firework_power, 0.5, 2.0, 0.1, accent="#f43f5e", is_float=True)
        tk.Button(
            c1,
            text="🎆 Запустить салют сейчас",
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self._spawn_firework_burst,
        ).pack(fill="x", pady=(6, 0))

    # --- Вкладка 6: Аврора и шлейф ---
    def _build_aurora_tab(self, parent):
        c1 = self._card(parent, "НАСТРОЙКА АВРОРЫ", "#2dd4bf")
        self._toggle(c1, "Северное сияние вверху экрана", "Мягкие переливающиеся волны у верхней кромки", self.aurora_enabled, accent="#14b8a6")
        self._slider_row(c1, "Высота волн (px):", self.aurora_height, 8, 42, 2, accent="#2dd4bf")
        self._slider_row(c1, "Скорость сияния:", self.aurora_speed, 0.2, 3.0, 0.1, accent="#2dd4bf", is_float=True)

        c2 = self._card(parent, "ШЛЕЙФ КУРСОРА", "#c084fc")
        self._toggle(c2, "Шлейф за курсором", "Искорки при движении мыши", self.cursor_trail, accent="#a855f7")

    # --- Коллбэки ---
    def _mark_garland_dirty(self):
        self._garland_dirty = True

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
        self._garland_dirty = True
        self._ref_scope()

    def _set_style(self, v: str):
        self.garland_style.set(v)
        self._garland_dirty = True
        self._ref_style()

    def _set_plow_mode(self, v: str):
        self.plow_mode.set(v)
        self._ref_plow()

    def _set_mode(self, v: str):
        self.garland_mode.set(v)
        self._garland_dirty = True
        self._ref_mode()

    def _set_palette(self, v: str):
        self.garland_palette.set(v)
        self._garland_dirty = True
        self._ref_pal()

    def _on_pile_toggle(self):
        if not self.pile_enabled.get():
            self._clear_pile()

    def _clear_pile(self):
        self.pile = [0.0] * self.pile_cols
        self.pile_owner = [0] * self.pile_cols
        self.falling_chunks.clear()

    def _call_plow_now(self):
        self.plow_enabled.set(True)
        self.pile_enabled.set(True)
        self.plow_force_once = True
        self.plow_active = True
        self.plow_ticks = 0
        self.plow_x = -60.0
        self.plow_y = float(get_taskbar_top(self.screen_h))

    def _trigger_storm(self):
        self.storm_timer = 170
        self.weather_enabled.set(True)

    def _spawn_firework_burst(self):
        pwr = float(self.firework_power.get())
        cx = random.randint(int(self.screen_w * 0.2), int(self.screen_w * 0.8))
        cy = random.randint(int(self.screen_h * 0.14), int(self.screen_h * 0.42))
        cols = ["#ff3b3b", "#38bdf8", "#facc15", "#c084fc", "#4ade80", "#fb923c"]
        n_sparks = int(min(44, max(16, 24 * pwr)))
        for i in range(n_sparks):
            ang = (math.tau * i) / n_sparks + random.uniform(-0.08, 0.08)
            spd = random.uniform(2.0, 5.8) * (0.75 + 0.35 * pwr)
            self.fireworks.append(
                {
                    "x": float(cx),
                    "y": float(cy),
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "life": int(min(36, max(14, 22 * (0.8 + 0.2 * pwr)))),
                    "color": random.choice(cols),
                }
            )

    # =========================================================================
    # КЛИК-СКВОЗНОЙ ОВЕРЛЕЙ ПОВЕРХ ВСЕХ ОКОН
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
        self.overlay_hwnd = hwnd
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
        pin_topmost_noactivate(hwnd)

    def _init_pools(self):
        aurora_cols = ["#0f766e", "#0d9488", "#0284c7", "#0369a1", "#2563eb", "#6d28d9", "#10b981", "#06b6d4"]
        for col in aurora_cols:
            lid = self.canvas.create_line(-50, -50, 50, -50, fill=col, width=7, capstyle="round", smooth=True, state="hidden")
            self.aurora_lines.append(lid)

        for _ in range(135):
            ov = self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            l1 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            l2 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            l3 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            py = self.canvas.create_polygon(-20, -20, -19, -20, -19, -19, fill="#ffffff", outline="", state="hidden")
            self.particle_pool.append((ov, l1, l2, l3, py))

        self.chunk_pool = [
            self.canvas.create_oval(-20, -20, -14, -14, fill="#ffffff", outline="#e2e8f0", width=1, state="hidden")
            for _ in range(60)
        ]

        self.spark_pool = [
            self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            for _ in range(130)
        ]

        self.pile_pool = []
        for _ in range(self.pile_cols):
            base = self.canvas.create_rectangle(-20, -20, -15, -15, fill="#f8fafc", outline="", state="hidden")
            cap = self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            self.pile_pool.append((base, cap))

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
    # СКАНИРОВАНИЕ ОКОН И АККУРАТНОЕ ОСЫПАНИЕ
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

        if updated != self.window_bounds:
            self._garland_dirty = True

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
                abs(old_b[0] - new_b[0]) > 4
                or abs(old_b[1] - new_b[1]) > 4
                or abs(old_b[2] - new_b[2]) > 4
            )
            if moved:
                c0 = max(0, int(old_b[0] // self.pile_step))
                c1 = min(self.pile_cols - 1, int(old_b[2] // self.pile_step))
                top_y = old_b[1]
                for col in range(c0, c1 + 1, 3):
                    if self.pile_owner[col] == hwnd and self.pile[col] > 1.5:
                        h = min(8.0, self.pile[col])
                        if len(self.falling_chunks) < len(self.chunk_pool):
                            self.falling_chunks.append(
                                {
                                    "x": float(col * self.pile_step + 2),
                                    "y": float(top_y - h),
                                    "vx": random.uniform(-0.8, 0.8),
                                    "vy": random.uniform(0.3, 1.1),
                                    "r": 1.8,
                                    "color": c_col,
                                }
                            )
                    for dc in (0, 1, 2):
                        idx = col + dc
                        if idx < self.pile_cols and self.pile_owner[idx] == hwnd:
                            self.pile[idx] = 0.0
                            self.pile_owner[idx] = 0

    def _windows_loop(self):
        if not self.dragging:
            self._scan_windows()
        self.root.after(160, self._windows_loop)

    def _blink_loop(self):
        if not self.dragging:
            self.blink_phase = (self.blink_phase + 1) % 48
            self._garland_dirty = True
        self.root.after(300, self._blink_loop)

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
        best_y = float(tb_top)
        owner = 0

        for hwnd, b in self.window_bounds.items():
            l, t, r, btm = b
            if l <= x <= r and t < btm and t < tb_top:
                if prev_y <= t + 2 and new_y >= t and t < best_y:
                    best_y = float(t)
                    owner = hwnd

        return best_y, owner

    def _render_aurora_waves(self):
        if not self.aurora_enabled.get() or self.dragging:
            for lid in self.aurora_lines:
                self.canvas.itemconfigure(lid, state="hidden")
            return

        segs = 16
        h_amp = float(self.aurora_height.get()) * 0.55
        spd_mult = float(self.aurora_speed.get())
        for idx, lid in enumerate(self.aurora_lines):
            base_y = 12.0 + idx * 4.5
            amp = max(3.0, h_amp * (0.65 + (idx % 3) * 0.25))
            freq = 0.0045 + idx * 0.0007
            spd = self.anim_phase * spd_mult * (0.9 + idx * 0.14)
            coords = []
            for k in range(segs + 1):
                x = (self.screen_w * k) / segs
                y = base_y + amp * math.sin(x * freq + spd + idx * 0.9)
                coords.extend([x, y])
            self.canvas.coords(lid, *coords)
            self.canvas.itemconfigure(lid, width=6.0 + (idx % 2) * 2.0, state="normal")

    def _anim_loop(self):
        if not self.dragging:
            self.anim_phase += 0.055
            if self.storm_timer > 0:
                self.storm_timer -= 1

            if self.fireworks_enabled.get():
                self.fw_ticks -= 1
                if self.fw_ticks <= 0:
                    self._spawn_firework_burst()
                    self.fw_ticks = max(1, int(self.firework_interval.get() * (1000 / 32)))

        s = self._active_season()
        tb_top = get_taskbar_top(self.screen_h)
        storm_boost = 1.8 if self.storm_timer > 0 else 1.0
        blizzard_lvl = float(self.blizzard_var.get()) + (1.6 if self.storm_timer > 0 else 0.0)
        cap_h = float(self.pile_max_cap.get())

        self._render_aurora_waves()

        show_weather = self.weather_enabled.get()
        base_spd = self.speed_var.get() * storm_boost * (1.0 + blizzard_lvl * 0.25)
        wind = self.wind_var.get() + blizzard_lvl * 1.15

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
            p["phase"] += 0.05 + blizzard_lvl * 0.03
            p["ang"] += p["spin"] * (1.0 + blizzard_lvl * 0.6)

            if not self.dragging:
                if s == "summer":
                    p["x"] += math.cos(p["phase"]) * 1.1 + wind * 0.25
                    p["y"] += math.sin(p["phase"] * 0.8) * 0.8 - 0.12
                    if p["y"] < 24:
                        p["y"] = tb_top - 30
                else:
                    p["y"] += base_spd * p["spd"]
                    p["x"] += math.sin(p["phase"]) * (0.85 + blizzard_lvl * 0.6) + wind

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
                            for d_col, w in ((-1, 0.25), (0, 0.65), (1, 0.25)):
                                c = col + d_col
                                if 0 <= c < self.pile_cols:
                                    if owner_hwnd:
                                        self.pile_owner[c] = owner_hwnd
                                    next_h = self.pile[c] + w
                                    if next_h >= cap_h or (surf_y - next_h) <= 2.0:
                                        if len(self.falling_chunks) < len(self.chunk_pool):
                                            self.falling_chunks.append(
                                                {
                                                    "x": float(c * self.pile_step + 2),
                                                    "y": float(surf_y - next_h),
                                                    "vx": random.uniform(-0.8, 0.8),
                                                    "vy": random.uniform(0.3, 1.0),
                                                    "r": 1.8,
                                                    "color": c_col,
                                                }
                                            )
                                        self.pile[c] = max(1.5, next_h * 0.7)
                                    else:
                                        self.pile[c] = next_h
                        p.update(self._spawn_particle(random_y=False))

            self._render_particle(slot, p, s)

        if not self.dragging:
            alive_chunks = []
            for ch in self.falling_chunks:
                prev_cy = ch["y"]
                ch["x"] += ch["vx"]
                ch["y"] += ch["vy"]
                ch["vy"] += 0.22
                col = max(0, min(self.pile_cols - 1, int(ch["x"] // self.pile_step)))
                surf_y, owner_hwnd = self._find_landing_surface(ch["x"], prev_cy, ch["y"], tb_top)
                if ch["y"] >= surf_y - self.pile[col]:
                    if self.pile_enabled.get() and s != "summer":
                        self.pile[col] = min(cap_h, self.pile[col] + 0.4)
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

        self._update_snowplow(s, tb_top)

        if not self.dragging and self.cursor_trail.get():
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

        if not self.dragging:
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

        if self._garland_dirty and not self.dragging:
            self._render_garlands()
            self._garland_dirty = False

        self.root.after(32, self._anim_loop)

    def _target_plow_y(self, px: float, tb_top: int) -> float:
        """Едет внизу по панели задач; если под колесами/отвалом есть окно — забирается на его верх."""
        target = float(tb_top)
        for _hwnd, b in self.window_bounds.items():
            l, t, r, btm = b
            if l - 8 <= px <= r + 8 and t < btm and t < target:
                target = float(t)
        return max(16.0, target)

    def _update_snowplow(self, season: str, tb_top: int):
        plow_body, plow_blade, plow_beacon, plow_wheel = self.plow_pool
        can_plow = self.plow_enabled.get() and self.pile_enabled.get() and season != "summer"

        if not can_plow:
            self.plow_active = False
            self.plow_force_once = False
            for obj in self.plow_pool:
                self.canvas.itemconfigure(obj, state="hidden")
            return

        if not self.plow_active:
            if not self.dragging:
                self.plow_ticks += 1
            mode = self.plow_mode.get()
            time_ok = self.plow_ticks >= max(1, int(self.plow_interval.get() * (1000 / 32)))
            max_p = max(self.pile) if self.pile else 0.0
            thresh_ok = max_p >= float(self.plow_threshold.get())

            start = (
                (mode == "time" and time_ok)
                or (mode == "threshold" and thresh_ok)
                or (mode == "both" and (time_ok or thresh_ok))
            )
            if start and (max_p > 0.5 or self.plow_force_once):
                self.plow_active = True
                self.plow_ticks = 0
                self.plow_x = -60.0
                self.plow_y = float(tb_top)
            else:
                for obj in self.plow_pool:
                    self.canvas.itemconfigure(obj, state="hidden")
                return

        spd = float(self.plow_speed.get())
        blade_w = float(self.plow_blade_w.get())

        if not self.dragging:
            self.plow_x += spd
            goal_y = self._target_plow_y(self.plow_x + 10.0, tb_top)
            climb_step = max(4.0, spd * 0.9)
            if self.plow_y > goal_y:
                self.plow_y = max(goal_y, self.plow_y - climb_step)
            elif self.plow_y < goal_y:
                self.plow_y = min(goal_y, self.plow_y + climb_step)

        px = self.plow_x
        py = self.plow_y

        col_c = int((px + blade_w * 0.5) // self.pile_step)
        span_cols = max(2, int(blade_w // self.pile_step) + 1)
        for c in range(max(0, col_c - span_cols), min(self.pile_cols, col_c + 2)):
            owner = self.pile_owner[c]
            surf_at_c = float(self.window_bounds[owner][1]) if (owner and owner in self.window_bounds) else float(tb_top)
            if abs(py - surf_at_c) <= 16.0:
                self.pile[c] = 0.0
                self.pile_owner[c] = 0

        if px > self.screen_w + 80:
            self.plow_active = False
            self.plow_force_once = False
            for obj in self.plow_pool:
                self.canvas.itemconfigure(obj, state="hidden")
            return

        self.canvas.coords(
            plow_body,
            px - 34, py - 18,
            px + 6, py - 18,
            px + 12, py - 6,
            px - 34, py - 6,
        )
        self.canvas.itemconfigure(plow_body, fill="#f97316", outline="#0f172a", width=1, state="normal")

        self.canvas.coords(
            plow_blade,
            px + 10, py - 14,
            px + 10 + blade_w * 0.55, py - 2,
            px + 11, py - 2,
        )
        self.canvas.itemconfigure(plow_blade, fill="#facc15", outline="#0f172a", width=1, state="normal")

        b_col = "#38bdf8" if (int(self.anim_phase * 8) % 2 == 0) else "#ef4444"
        self.canvas.coords(plow_beacon, px - 16, py - 23, px - 9, py - 17)
        self.canvas.itemconfigure(plow_beacon, fill=b_col, state="normal")

        self.canvas.coords(plow_wheel, px - 26, py - 8, px - 16, py + 2)
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
        spacing = max(24, int(self.garland_spacing.get() * max(0.85, min(1.35, sc))))

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
                steps = 10
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
    app = AtmosphereStudioApp()
    app.root.mainloop()
