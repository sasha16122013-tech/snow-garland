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

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2

TRANSPARENT_KEY = "#010203"
MENU_TITLE = "Winter & Seasons Studio"


def get_current_season_key() -> str:
    month = datetime.date.today().month
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
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


def is_real_window(hwnd) -> bool:
    if not hwnd or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
        return False

    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if ex_style & WS_EX_TOOLWINDOW:
        return False

    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return False

    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value.strip()
    if not title or title == MENU_TITLE:
        return False

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
        return False

    return True


def is_desktop_active() -> bool:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return True
    cls_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls_buf, 256)
    return cls_buf.value in ("Progman", "WorkerW")


def get_taskbar_top(screen_h: int) -> int:
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    if hwnd:
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            if 0 < rect.top < screen_h:
                return rect.top
    return screen_h - 48


class ModernToggle(tk.Canvas):
    """Плавный iOS/Windows 11 переключатель-тумблер."""

    def __init__(self, parent, variable: tk.BooleanVar, command=None, accent="#38bdf8", bg="#141824"):
        super().__init__(parent, width=44, height=24, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.var = variable
        self.command = command
        self.accent = accent
        self.off_bg = "#262d42"
        self.knob_x = 32.0 if self.var.get() else 12.0
        self.bind("<Button-1>", self._toggle)
        self.var.trace_add("write", lambda *_: self._animate())
        self._draw()

    def _toggle(self, _event=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def _animate(self):
        target = 32.0 if self.var.get() else 12.0
        diff = target - self.knob_x
        if abs(diff) < 0.8:
            self.knob_x = target
            self._draw()
            return
        self.knob_x += diff * 0.42
        self._draw()
        self.after(14, self._animate)

    def _draw(self):
        self.delete("all")
        active = self.var.get()
        track_col = self.accent if active else self.off_bg
        # Капсула трека
        self.create_oval(2, 2, 22, 22, fill=track_col, outline="")
        self.create_oval(22, 2, 42, 22, fill=track_col, outline="")
        self.create_rectangle(12, 2, 32, 22, fill=track_col, outline="")
        # Тень и бегунок
        kx = self.knob_x
        self.create_oval(kx - 8.5, 4.5, kx + 8.5, 21.5, fill="#0b0e17", outline="")
        self.create_oval(kx - 8.5, 3.5, kx + 8.5, 20.5, fill="#ffffff", outline="")


class SeasonsGarlandStudio:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(MENU_TITLE)
        self.root.geometry("440x680+95+65")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)  # Кастомная безрамочная шапка
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0b0e17")

        # Скругление углов окна на Windows 11
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

        # --- Настройки погоды и сезонов ---
        self.weather_enabled = tk.BooleanVar(value=True)
        self.auto_season = tk.BooleanVar(value=False)
        self.season = tk.StringVar(value="winter")
        self.only_desktop = tk.BooleanVar(value=False)
        self.pile_enabled = tk.BooleanVar(value=True)
        self.flake_shape = tk.StringVar(value="crystal")
        self.count_var = tk.IntVar(value=85)
        self.speed_var = tk.DoubleVar(value=2.2)
        self.wind_var = tk.DoubleVar(value=0.35)

        # --- Настройки гирлянды ---
        self.top_garland_enabled = tk.BooleanVar(value=True)
        self.win_garland_enabled = tk.BooleanVar(value=True)
        self.win_garland_scope = tk.StringVar(value="all")
        self.garland_mode = tk.StringVar(value="rainbow")
        self.garland_palette = tk.StringVar(value="classic")
        self.garland_spacing = tk.IntVar(value=36)

        # --- Фишки ---
        self.cursor_trail = tk.BooleanVar(value=True)
        self.aurora_enabled = tk.BooleanVar(value=True)
        self.storm_timer = 0
        self.fireworks = []

        # --- Состояние симуляции ---
        self.particles = []
        self.sparks = []
        self.last_mouse = (-1, -1)
        self.blink_phase = 0
        self.anim_time = 0.0
        self.window_list = []
        self.active_hwnd = None
        self.is_dragging_menu = False
        self._drag_offset = (0, 0)

        self.pile_step = 4
        self.pile_cols = (self.screen_w // self.pile_step) + 2
        self.pile = [0.0] * self.pile_cols

        self.particle_items = []
        self.spark_items = []
        self.pile_items = []
        self.bulb_pool = []
        self.aurora_items = []

        self._build_ui()
        self._init_overlay()
        self._init_canvas_pools()
        self._refresh_windows()
        self._rebuild_particles()

        self._anim_loop()
        self._blink_loop()
        self._windows_loop()

    # =========================================================================
    # ПЕРЕТАСКИВАНИЕ КАСТОМНОГО ОКНА БЕЗ ЛАГОВ
    # =========================================================================
    def _start_drag(self, event):
        self.is_dragging_menu = True
        self._drag_offset = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _on_drag(self, event):
        nx = event.x_root - self._drag_offset[0]
        ny = event.y_root - self._drag_offset[1]
        self.root.geometry(f"+{nx}+{ny}")

    def _end_drag(self, _event):
        self.is_dragging_menu = False

    # =========================================================================
    # ПРЕМИУМ ИНТЕРФЕЙС
    # =========================================================================
    def _build_ui(self):
        # Внешняя неоновая рамка
        shell = tk.Frame(
            self.root,
            bg="#0b0e17",
            highlightbackground="#232a42",
            highlightthickness=1,
        )
        shell.pack(fill="both", expand=True)

        # Кастомная шапка (Titlebar)
        header = tk.Frame(shell, bg="#111524", height=62)
        header.pack(fill="x")
        header.pack_propagate(False)

        header.bind("<ButtonPress-1>", self._start_drag)
        header.bind("<B1-Motion>", self._on_drag)
        header.bind("<ButtonRelease-1>", self._end_drag)

        # Акцентная полоса сверху
        accent_bar = tk.Frame(header, bg="#38bdf8", height=2)
        accent_bar.pack(fill="x", side="top")

        title_wrap = tk.Frame(header, bg="#111524")
        title_wrap.pack(side="left", padx=16, pady=10)
        title_wrap.bind("<ButtonPress-1>", self._start_drag)
        title_wrap.bind("<B1-Motion>", self._on_drag)
        title_wrap.bind("<ButtonRelease-1>", self._end_drag)

        lbl_main = tk.Label(
            title_wrap,
            text="✦ ATMOSPHERE STUDIO",
            bg="#111524",
            fg="#f8fafc",
            font=("Segoe UI", 12, "bold"),
        )
        lbl_main.pack(anchor="w")
        lbl_main.bind("<ButtonPress-1>", self._start_drag)
        lbl_main.bind("<B1-Motion>", self._on_drag)
        lbl_main.bind("<ButtonRelease-1>", self._end_drag)

        now_map = {
            "winter": "❄️ Зима",
            "spring": "🌿 Весна",
            "summer": "✨ Лето",
            "autumn": "🍁 Осень",
        }
        lbl_sub = tk.Label(
            title_wrap,
            text=f"Десктоп-эффекты • Сейчас: {now_map[get_current_season_key()]}",
            bg="#111524",
            fg="#64748b",
            font=("Segoe UI", 8, "bold"),
        )
        lbl_sub.pack(anchor="w")
        lbl_sub.bind("<ButtonPress-1>", self._start_drag)
        lbl_sub.bind("<B1-Motion>", self._on_drag)
        lbl_sub.bind("<ButtonRelease-1>", self._end_drag)

        # Кнопки управления окном (Свернуть / Закрыть)
        win_btns = tk.Frame(header, bg="#111524")
        win_btns.pack(side="right", padx=12)

        btn_min = tk.Button(
            win_btns,
            text="—",
            bg="#1a2035",
            fg="#94a3b8",
            activebackground="#262f4d",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            width=3,
            pady=3,
            cursor="hand2",
            command=self._minimize_menu,
        )
        btn_min.pack(side="left", padx=3)

        btn_close = tk.Button(
            win_btns,
            text="✕",
            bg="#1a2035",
            fg="#f87171",
            activebackground="#ef4444",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            width=3,
            pady=3,
            cursor="hand2",
            command=self.quit_app,
        )
        btn_close.pack(side="left", padx=3)

        # Панель вкладок (Segmented Control)
        nav_wrap = tk.Frame(shell, bg="#111524", padx=4, pady=4)
        nav_wrap.pack(fill="x", padx=16, pady=(12, 8))

        self.tabs = {}
        self.nav_btns = {}
        for key, title in [
            ("weather", "❄️ Погода и Сезоны"),
            ("garland", "💡 Гирлянды"),
            ("extras", "🎆 Фишки и Шоу"),
        ]:
            btn = tk.Button(
                nav_wrap,
                text=title,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                bd=0,
                pady=7,
                cursor="hand2",
                command=lambda k=key: self._select_tab(k),
            )
            btn.pack(side="left", expand=True, fill="x", padx=2)
            self.nav_btns[key] = btn
            self.tabs[key] = tk.Frame(shell, bg="#0b0e17")

        self._build_weather_tab(self.tabs["weather"])
        self._build_garland_tab(self.tabs["garland"])
        self._build_extras_tab(self.tabs["extras"])
        self._select_tab("weather")

    def _minimize_menu(self):
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.bind("", self._restore_borderless)

    def _restore_borderless(self, _event=None):
        if self.root.state() == "normal":
            self.root.unbind("")
            self.root.overrideredirect(True)

    def _select_tab(self, key: str):
        for k, frame in self.tabs.items():
            frame.pack_forget()
            active = k == key
            self.nav_btns[k].configure(
                bg="#2563eb" if active else "#111524",
                fg="#ffffff" if active else "#64748b",
            )
        self.tabs[key].pack(fill="both", expand=True, padx=16, pady=2)

    def _card(self, parent, title: str, accent="#38bdf8"):
        wrap = tk.Frame(
            parent,
            bg="#141824",
            highlightbackground="#1f263b",
            highlightthickness=1,
        )
        wrap.pack(fill="x", pady=6)
        tk.Label(
            wrap,
            text=title,
            bg="#141824",
            fg=accent,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", padx=14, pady=(9, 4))
        body = tk.Frame(wrap, bg="#141824")
        body.pack(fill="x", padx=14, pady=(0, 11))
        return body

    def _toggle_row(self, parent, title: str, subtitle: str, var: tk.BooleanVar, cmd=None, accent="#38bdf8"):
        row = tk.Frame(parent, bg="#141824")
        row.pack(fill="x", pady=4)

        txt_col = tk.Frame(row, bg="#141824")
        txt_col.pack(side="left", fill="x", expand=True)

        tk.Label(
            txt_col,
            text=title,
            bg="#141824",
            fg="#f1f5f9",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        if subtitle:
            tk.Label(
                txt_col,
                text=subtitle,
                bg="#141824",
                fg="#64748b",
                font=("Segoe UI", 8),
            ).pack(anchor="w")

        sw = ModernToggle(row, variable=var, command=cmd, accent=accent, bg="#141824")
        sw.pack(side="right", padx=(8, 0))
        return sw

    def _pill_group(self, parent, items, current_getter, on_click, accent="#2563eb"):
        row = tk.Frame(parent, bg="#0f131f", padx=3, pady=3)
        row.pack(fill="x", pady=(6, 2))
        btns = {}
        for k, label in items:
            b = tk.Button(
                row,
                text=label,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                bd=0,
                pady=5,
                cursor="hand2",
                command=lambda val=k: on_click(val),
            )
            b.pack(side="left", expand=True, fill="x", padx=2)
            btns[k] = b

        def refresh_style():
            cur = current_getter()
            for k, b in btns.items():
                is_cur = k == cur
                b.configure(
                    bg=accent if is_cur else "#0f131f",
                    fg="#ffffff" if is_cur else "#64748b",
                )

        refresh_style()
        return refresh_style

    def _slider(self, parent, label: str, var, low, high, step, cmd=None):
        row = tk.Frame(parent, bg="#141824")
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg="#141824", fg="#cbd5e1", font=("Segoe UI", 9)).pack(side="left")
        tk.Scale(
            row,
            variable=var,
            from_=low,
            to=high,
            resolution=step,
            orient="horizontal",
            bg="#141824",
            fg="#38bdf8",
            troughcolor="#1e2538",
            activebackground="#38bdf8",
            highlightthickness=0,
            bd=0,
            length=165,
            command=(lambda _v: cmd()) if cmd else None,
        ).pack(side="right")

    def _build_weather_tab(self, parent):
        c1 = self._card(parent, "АТМОСФЕРА И СЕЗОНЫ", "#38bdf8")
        self._toggle_row(
            c1,
            "Эффекты погоды",
            "Снег, весенние листья, светлячки или листопад",
            self.weather_enabled,
        )
        self._toggle_row(
            c1,
            "Авто-сезон по календарю",
            "Автоматически ставит текущее время года",
            self.auto_season,
            cmd=self._on_auto_season,
            accent="#10b981",
        )
        self._refresh_season_ui = self._pill_group(
            c1,
            [
                ("winter", "❄️ Зима"),
                ("spring", "🌿 Весна"),
                ("summer", "✨ Лето"),
                ("autumn", "🍁 Осень"),
            ],
            self._active_season,
            self._set_season,
        )

        c2 = self._card(parent, "РАБОЧИЙ СТОЛ И СУГРОБЫ", "#60a5fa")
        self._toggle_row(
            c2,
            "Только на рабочем столе",
            "Скрывать снег, когда открыто любое окно",
            self.only_desktop,
        )
        self._toggle_row(
            c2,
            "Накапливать на панели задач",
            "Снег и листья образуют сугробы внизу экрана",
            self.pile_enabled,
            cmd=self._on_pile_toggle,
        )
        tk.Button(
            c2,
            text="🧹 Очистить сугробы на панели задач",
            bg="#1e2538",
            fg="#e2e8f0",
            activebackground="#2b3550",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=5,
            cursor="hand2",
            command=self._clear_pile,
        ).pack(fill="x", pady=(6, 0))

        c3 = self._card(parent, "ФОРМА СНЕЖИНОК", "#a5b4fc")
        self._refresh_shape_ui = self._pill_group(
            c3,
            [
                ("circle", "• Хлопья"),
                ("crystal", "❄ Кристаллы"),
                ("star", "✦ Звёзды"),
                ("mix", "🎲 Микс"),
            ],
            self.flake_shape.get,
            self._set_shape,
            accent="#6366f1",
        )

        c4 = self._card(parent, "ДИНАМИКА ПОТОКА", "#7dd3fc")
        self._slider(c4, "Плотность частиц:", self.count_var, 20, 160, 1, self._rebuild_particles)
        self._slider(c4, "Скорость падения:", self.speed_var, 0.6, 6.0, 0.2)
        self._slider(c4, "Сила ветра:", self.wind_var, -2.5, 2.5, 0.1)

    def _build_garland_tab(self, parent):
        c1 = self._card(parent, "РАСПОЛОЖЕНИЕ ГИРЛЯНДЫ", "#fbbf24")
        self._toggle_row(
            c1,
            "Гирлянда в самом верху экрана",
            "Праздничная лента вдоль верхней грани монитора",
            self.top_garland_enabled,
            accent="#f59e0b",
        )
        self._toggle_row(
            c1,
            "Гирлянда на окнах Windows",
            "Крепится прямо на рамки открытых программ",
            self.win_garland_enabled,
            accent="#f59e0b",
        )
        self._refresh_scope_ui = self._pill_group(
            c1,
            [("all", "На всех окнах"), ("active", "Только активное окно")],
            self.win_garland_scope.get,
            self._set_scope,
            accent="#d97706",
        )

        c2 = self._card(parent, "АНИМАЦИЯ ОГОНЬКОВ", "#f472b6")
        self._refresh_mode_ui = self._pill_group(
            c2,
            [
                ("rainbow", "🌈 Перелив"),
                ("wave", "🌊 Волна"),
                ("twinkle", "✨ Искры"),
                ("steady", "💡 Ровный"),
            ],
            self.garland_mode.get,
            self._set_mode,
            accent="#db2777",
        )

        c3 = self._card(parent, "ПАЛИТРА СВЕЧЕНИЯ", "#34d399")
        self._refresh_pal_ui = self._pill_group(
            c3,
            [
                ("classic", "🎄 Новый год"),
                ("warm", "🕯️ Тёплый"),
                ("cyber", "🟣 Киберпанк"),
                ("ice", "🧊 Ледяной"),
            ],
            self.garland_palette.get,
            self._set_palette,
            accent="#059669",
        )

        c4 = self._card(parent, "ПЛОТНОСТЬ ЛАМП", "#93c5fd")
        self._slider(c4, "Расстояние (px):", self.garland_spacing, 24, 68, 2)

    def _build_extras_tab(self, parent):
        c1 = self._card(parent, "ВИЗУАЛЬНЫЕ ЭФФЕКТЫ", "#c084fc")
        self._toggle_row(
            c1,
            "Северное сияние вверху экрана",
            "Мягкое переливающееся свечение у верхней кромки",
            self.aurora_enabled,
            accent="#10b981",
        )
        self._toggle_row(
            c1,
            "Волшебный шлейф за курсором",
            "Искорки и снежинки при движении мыши",
            self.cursor_trail,
            accent="#a855f7",
        )

        c2 = self._card(parent, "СПЕЦЭФФЕКТЫ ПО КЛИКУ", "#f43f5e")
        tk.Button(
            c2,
            text="🌬️ Вызвать снежную бурю / порыв ветра (6 сек)",
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self._trigger_storm,
        ).pack(fill="x", pady=(4, 6))

        tk.Button(
            c2,
            text="🎆 Запустить праздничный фейерверк",
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self._trigger_firework,
        ).pack(fill="x", pady=2)

    # --- Коллбэки ---
    def _on_auto_season(self):
        if self.auto_season.get():
            self.season.set(get_current_season_key())
            self._clear_pile()
            self._rebuild_particles()
        self._refresh_season_ui()

    def _set_season(self, s: str):
        self.auto_season.set(False)
        self.season.set(s)
        self._clear_pile()
        self._rebuild_particles()
        self._refresh_season_ui()

    def _set_shape(self, sh: str):
        self.flake_shape.set(sh)
        self._rebuild_particles()
        self._refresh_shape_ui()

    def _set_scope(self, sc: str):
        self.win_garland_scope.set(sc)
        self._refresh_scope_ui()

    def _set_mode(self, m: str):
        self.garland_mode.set(m)
        self._refresh_mode_ui()

    def _set_palette(self, p: str):
        self.garland_palette.set(p)
        self._refresh_pal_ui()

    def _on_pile_toggle(self):
        if not self.pile_enabled.get():
            self._clear_pile()

    def _clear_pile(self):
        self.pile = [0.0] * self.pile_cols

    def _trigger_storm(self):
        self.storm_timer = 250
        self.weather_enabled.set(True)

    def _trigger_firework(self):
        for _ in range(2):
            cx = random.randint(int(self.screen_w * 0.18), int(self.screen_w * 0.82))
            cy = random.randint(int(self.screen_h * 0.14), int(self.screen_h * 0.44))
            palette = ["#ff3b3b", "#38bdf8", "#facc15", "#a855f7", "#4ade80", "#fb923c"]
            for i in range(30):
                ang = (math.tau * i) / 30 + random.uniform(-0.07, 0.07)
                spd = random.uniform(2.0, 6.8)
                self.fireworks.append(
                    {
                        "x": float(cx),
                        "y": float(cy),
                        "vx": math.cos(ang) * spd,
                        "vy": math.sin(ang) * spd,
                        "life": random.randint(24, 38),
                        "color": random.choice(palette),
                    }
                )

    # =========================================================================
    # КЛИК-СКВОЗНОЙ ОВЕРЛЕЙ И ПУЛ ОБЪЕКТОВ
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

    def _init_canvas_pools(self):
        # Полосы северного сияния в верхней кромке
        aurora_cols = ["#064e3b", "#065f46", "#047857", "#0d9488", "#0284c7", "#1d4ed8"]
        for i in range(28):
            rid = self.canvas.create_rectangle(
                -20, -20, -10, -10,
                fill=aurora_cols[i % len(aurora_cols)],
                stipple="gray25",
                outline="",
                state="hidden",
            )
            self.aurora_items.append(rid)

        # Пул частиц погоды
        for _ in range(170):
            ov = self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            l1 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            l2 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            l3 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            py = self.canvas.create_polygon(-20, -20, -19, -20, -19, -19, fill="#ffffff", outline="", state="hidden")
            self.particle_items.append((ov, l1, l2, l3, py))

        # Пул искр и салюта
        self.spark_items = [
            self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            for _ in range(160)
        ]

        # Пул сугробов
        self.pile_items = [
            self.canvas.create_rectangle(-20, -20, -10, -10, fill="#ffffff", outline="", state="hidden")
            for _ in range(self.pile_cols)
        ]

        # Пул лампочек гирлянды (провод + внешний ореол + внутренний ореол + цоколь + колба + блик)
        for _ in range(280):
            wire = self.canvas.create_line(-20, -20, -10, -20, fill="#1e2433", width=2, state="hidden")
            outer_glow = self.canvas.create_oval(-20, -20, -10, -10, fill="#ff3b3b", stipple="gray12", outline="", state="hidden")
            inner_glow = self.canvas.create_oval(-20, -20, -10, -10, fill="#ff3b3b", stipple="gray50", outline="", state="hidden")
            cap = self.canvas.create_rectangle(-20, -20, -15, -15, fill="#334155", outline="", state="hidden")
            bulb = self.canvas.create_oval(-20, -20, -12, -12, fill="#ff3b3b", outline="#0f172a", width=1, state="hidden")
            shine = self.canvas.create_oval(-20, -20, -17, -17, fill="#ffffff", outline="", state="hidden")
            self.bulb_pool.append((wire, outer_glow, inner_glow, cap, bulb, shine))

    # =========================================================================
    # ОПРОС ОКОН И АНИМАЦИЯ
    # =========================================================================
    def _refresh_windows(self):
        found = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_cb(hwnd, _lparam):
            if is_real_window(hwnd):
                b = get_window_bounds(hwnd)
                if b and b[0] > -10000 and (b[2] - b[0]) > 140 and (b[3] - b[1]) > 60:
                    found.append((hwnd, b))
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        self.window_list = found
        fg = user32.GetForegroundWindow()
        self.active_hwnd = fg if is_real_window(fg) else None

    def _windows_loop(self):
        if not self.is_dragging_menu:
            self._refresh_windows()
        self.root.after(200, self._windows_loop)

    def _blink_loop(self):
        self.blink_phase = (self.blink_phase + 1) % 48
        self.root.after(240, self._blink_loop)

    def _active_season(self) -> str:
        return get_current_season_key() if self.auto_season.get() else self.season.get()

    def _rebuild_particles(self):
        n = min(len(self.particle_items), self.count_var.get())
        self.particles = [self._spawn_particle(random_y=True) for _ in range(n)]

    def _spawn_particle(self, random_y: bool = False):
        s = self._active_season()
        sh = self.flake_shape.get()
        if sh == "mix":
            sh = random.choice(["circle", "crystal", "star"])

        color_map = {
            "winter": ["#ffffff", "#e0f2fe", "#bae6fd"],
            "spring": ["#6ee7b7", "#34d399", "#a7f3d0", "#bef264"],
            "summer": ["#fef08a", "#fde047", "#bef264"],
            "autumn": ["#f59e0b", "#ea580c", "#dc2626", "#eab308"],
        }

        return {
            "x": random.uniform(0, self.screen_w),
            "y": random.uniform(-self.screen_h, self.screen_h) if random_y else random.uniform(-25, -4),
            "r": random.uniform(2.5, 5.2) if s != "summer" else random.uniform(2.2, 3.8),
            "spd": random.uniform(0.7, 1.35),
            "phase": random.uniform(0, math.tau),
            "ang": random.uniform(0, math.tau),
            "spin": random.uniform(-0.06, 0.06),
            "shape": sh,
            "color": random.choice(color_map[s]),
        }

    def _anim_loop(self):
        if self.is_dragging_menu:
            self.root.after(18, self._anim_loop)
            return

        self.anim_time += 0.06
        if self.storm_timer > 0:
            self.storm_timer -= 1

        s = self._active_season()
        tb_top = get_taskbar_top(self.screen_h)
        storm_boost = 2.3 if self.storm_timer > 0 else 1.0

        # 0. Северное сияние
        if self.aurora_enabled.get():
            seg_w = (self.screen_w / len(self.aurora_items)) + 2
            for i, rid in enumerate(self.aurora_items):
                wave_h = 18 + 14 * math.sin(self.anim_time + i * 0.45) + 8 * math.cos(self.anim_time * 0.7 - i * 0.3)
                x1 = i * (self.screen_w / len(self.aurora_items))
                self.canvas.coords(rid, x1, 0, x1 + seg_w, max(6, wave_h))
                self.canvas.itemconfigure(rid, state="normal")
        else:
            for rid in self.aurora_items:
                self.canvas.itemconfigure(rid, state="hidden")

        # 1. Погода
        show_weather = self.weather_enabled.get() and (
            not self.only_desktop.get() or is_desktop_active()
        )
        base_spd = self.speed_var.get() * storm_boost
        wind = self.wind_var.get() + (2.5 if self.storm_timer > 0 else 0.0)

        target_n = min(len(self.particle_items), self.count_var.get())
        while len(self.particles) < target_n:
            self.particles.append(self._spawn_particle(random_y=True))
        while len(self.particles) > target_n:
            self.particles.pop()

        for idx, slot in enumerate(self.particle_items):
            ov, l1, l2, l3, py = slot
            if not show_weather or idx >= len(self.particles):
                self.canvas.itemconfigure(ov, state="hidden")
                self.canvas.itemconfigure(l1, state="hidden")
                self.canvas.itemconfigure(l2, state="hidden")
                self.canvas.itemconfigure(l3, state="hidden")
                self.canvas.itemconfigure(py, state="hidden")
                continue

            p = self.particles[idx]
            p["phase"] += 0.045
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
                pile_h = self.pile[col] if self.pile_enabled.get() else 0.0
                if p["y"] >= tb_top - pile_h:
                    if self.pile_enabled.get():
                        for d_col, w in ((-1, 0.3), (0, 0.65), (1, 0.3)):
                            c = col + d_col
                            if 0 <= c < self.pile_cols:
                                self.pile[c] = min(24.0, self.pile[c] + w)
                    p.update(self._spawn_particle(random_y=False))

            self._render_particle(slot, p, s)

        # 2. Сугробы
        pile_colors = {"winter": "#f8fafc", "spring": "#6ee7b7", "autumn": "#ea580c"}
        p_col = pile_colors.get(s, "#f8fafc")
        for i, rect_id in enumerate(self.pile_items):
            h = self.pile[i] if (self.pile_enabled.get() and s != "summer") else 0.0
            if h > 0.5:
                x1 = i * self.pile_step
                self.canvas.coords(rect_id, x1, tb_top - h, x1 + self.pile_step + 1, tb_top + 2)
                self.canvas.itemconfigure(rect_id, fill=p_col, state="normal")
            else:
                self.canvas.itemconfigure(rect_id, state="hidden")

        # 3. Шлейф курсора + салют
        if self.cursor_trail.get():
            pt = wintypes.POINT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                if abs(pt.x - self.last_mouse[0]) + abs(pt.y - self.last_mouse[1]) > 4:
                    trail_cols = {
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
                            "vy": random.uniform(0.3, 1.4),
                            "life": 13,
                            "color": random.choice(trail_cols),
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
                "vy": fw["vy"] + 0.12,
                "life": fw["life"] - 1,
            }
            for fw in self.fireworks
            if fw["life"] > 1
        ]

        all_sparks = self.sparks + self.fireworks
        for idx, item_id in enumerate(self.spark_items):
            if idx < len(all_sparks):
                sp = all_sparks[idx]
                rad = max(1.4, sp["life"] * 0.17)
                self.canvas.coords(item_id, sp["x"] - rad, sp["y"] - rad, sp["x"] + rad, sp["y"] + rad)
                self.canvas.itemconfigure(item_id, fill=sp["color"], state="normal")
            else:
                self.canvas.itemconfigure(item_id, state="hidden")

        # 4. Гирлянда
        self._render_garlands()

        self.root.after(20, self._anim_loop)

    def _render_particle(self, slot, p, season: str):
        ov, l1, l2, l3, py = slot
        x, y, r, col = p["x"], p["y"], p["r"], p["color"]

        self.canvas.itemconfigure(ov, state="hidden")
        self.canvas.itemconfigure(l1, state="hidden")
        self.canvas.itemconfigure(l2, state="hidden")
        self.canvas.itemconfigure(l3, state="hidden")
        self.canvas.itemconfigure(py, state="hidden")

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
                for k, line_id in enumerate((l1, l2, l3)):
                    ang = p["ang"] + k * (math.pi / 3)
                    dx = math.cos(ang) * (r * 1.35)
                    dy = math.sin(ang) * (r * 1.35)
                    self.canvas.coords(line_id, x - dx, y - dy, x + dx, y + dy)
                    self.canvas.itemconfigure(line_id, fill=col, width=1.4, state="normal")

        elif season in ("spring", "autumn"):
            ang = p["ang"]
            dx, dy = math.cos(ang) * (r * 1.5), math.sin(ang) * (r * 1.5)
            px, py_off = -math.sin(ang) * (r * 0.75), math.cos(ang) * (r * 0.75)
            self.canvas.coords(
                py,
                x + dx, y + dy,
                x + px, y + py_off,
                x - dx, y - dy,
                x - px, y - py_off,
            )
            self.canvas.itemconfigure(py, fill=col, state="normal")

        else:
            pulse = 0.65 + 0.35 * math.sin(p["phase"] * 2.5)
            rr = r * pulse
            self.canvas.coords(ov, x - rr, y - rr, x + rr, y + rr)
            self.canvas.itemconfigure(ov, fill=col, state="normal")

    def _render_garlands(self):
        palettes = {
            "classic": ["#ff3b3b", "#22c55e", "#38bdf8", "#facc15", "#e879f9"],
            "warm": ["#fef08a", "#fde047", "#fdba74", "#fed7aa", "#fef9c3"],
            "cyber": ["#f43f5e", "#d946ef", "#8b5cf6", "#06b6d4", "#22d3ee"],
            "ice": ["#ffffff", "#e0f2fe", "#7dd3fc", "#38bdf8", "#bae6fd"],
        }
        colors = palettes.get(self.garland_palette.get(), palettes["classic"])
        mode = self.garland_mode.get()
        spacing = max(24, self.garland_spacing.get())

        lines_to_draw = []
        if self.top_garland_enabled.get():
            lines_to_draw.append((12, self.screen_w - 12, 2))

        if self.win_garland_enabled.get():
            scope = self.win_garland_scope.get()
            for hwnd, _cached in self.window_list:
                if scope == "active" and hwnd != self.active_hwnd:
                    continue
                b = get_window_bounds(hwnd)
                if not b:
                    continue
                left, top, right, bottom = b
                if left < -10000 or bottom <= top or (right - left) < 130:
                    continue
                l_c = max(6, left + 8)
                r_c = min(self.screen_w - 6, right - 8)
                t_c = max(2, top)
                if r_c - l_c >= 90:
                    lines_to_draw.append((l_c, r_c, t_c))

        bulbs_plan = []
        for x_start, x_end, y_top in lines_to_draw:
            xs = list(range(x_start, x_end, spacing))
            if len(xs) < 2:
                continue
            for idx, bx in enumerate(xs):
                next_x = xs[idx + 1] if idx + 1 < len(xs) else min(x_end, bx + spacing)
                bulbs_plan.append((bx, next_x, y_top, idx))

        for i, slot in enumerate(self.bulb_pool):
            wire, outer_glow, inner_glow, cap, bulb, shine = slot
            if i >= len(bulbs_plan):
                for obj in slot:
                    self.canvas.itemconfigure(obj, state="hidden")
                continue

            bx, next_x, y_top, idx = bulbs_plan[i]
            mid_x = (bx + next_x) * 0.5

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

            self.canvas.coords(wire, bx, y_top + 1, mid_x, y_top + 6, next_x, y_top + 1)
            self.canvas.itemconfigure(wire, fill="#1e2433", width=2, state="normal")

            self.canvas.coords(cap, bx - 2.5, y_top, bx + 2.5, y_top + 4)
            self.canvas.itemconfigure(cap, fill="#334155", state="normal")

            if lit:
                self.canvas.coords(outer_glow, bx - 12, y_top, bx + 12, y_top + 24)
                self.canvas.itemconfigure(outer_glow, fill=col, state="normal")

                self.canvas.coords(inner_glow, bx - 7.5, y_top + 3, bx + 7.5, y_top + 19)
                self.canvas.itemconfigure(inner_glow, fill=col, state="normal")

                self.canvas.coords(bulb, bx - 4.5, y_top + 4, bx + 4.5, y_top + 16)
                self.canvas.itemconfigure(bulb, fill=col, outline="#0f172a", width=1, state="normal")

                self.canvas.coords(shine, bx - 2, y_top + 6, bx, y_top + 10)
                self.canvas.itemconfigure(shine, fill="#ffffff", state="normal")
            else:
                self.canvas.itemconfigure(outer_glow, state="hidden")
                self.canvas.itemconfigure(inner_glow, state="hidden")
                self.canvas.coords(bulb, bx - 4, y_top + 4, bx + 4, y_top + 15)
                self.canvas.itemconfigure(bulb, fill="#283147", outline="#1e293b", width=1, state="normal")
                self.canvas.itemconfigure(shine, state="hidden")

    def quit_app(self):
        self.root.destroy()


if __name__ == "__main__":
    app = SeasonsGarlandStudio()
    app.root.mainloop()
