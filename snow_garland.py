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
MENU_TITLE = "Atmosphere Studio Pro"


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


def get_taskbar_top(screen_h: int) -> int:
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    if hwnd:
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            if 0 < rect.top < screen_h:
                return rect.top
    return screen_h - 48


class SwitchPill(tk.Canvas):
    def __init__(self, parent, var: tk.BooleanVar, command=None, accent="#38bdf8", bg="#141926"):
        super().__init__(parent, width=42, height=22, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.var = var
        self.command = command
        self.accent = accent
        self.bind("<Button-1>", self._on_click)
        self.var.trace_add("write", lambda *_: self._draw())
        self._draw()

    def _on_click(self, _e=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        on = self.var.get()
        col = self.accent if on else "#252c40"
        self.create_oval(1, 1, 21, 21, fill=col, outline="")
        self.create_oval(21, 1, 41, 21, fill=col, outline="")
        self.create_rectangle(11, 1, 31, 21, fill=col, outline="")
        kx = 31 if on else 11
        self.create_oval(kx - 7.5, 3.5, kx + 7.5, 18.5, fill="#ffffff", outline="")


class AtmosphereStudioApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(MENU_TITLE)
        self.root.geometry("454x735+90+55")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0b0e17")

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

        # --- Погода и сезоны ---
        self.weather_enabled = tk.BooleanVar(value=True)
        self.auto_season = tk.BooleanVar(value=False)
        self.season = tk.StringVar(value="winter")       # winter, spring, summer, autumn
        self.pile_enabled = tk.BooleanVar(value=True)
        self.flake_shape = tk.StringVar(value="crystal") # circle, crystal, star, mix
        self.count_var = tk.IntVar(value=70)
        self.speed_var = tk.DoubleVar(value=2.1)
        self.wind_var = tk.DoubleVar(value=0.3)

        # --- Снегоуборочная машина ---
        self.plow_enabled = tk.BooleanVar(value=True)
        self.plow_mode = tk.StringVar(value="both")     # time, threshold, both
        self.plow_interval = tk.IntVar(value=25)       # секунд между рейсами
        self.plow_threshold = tk.IntVar(value=14)      # высота сугроба (px) для авто-рейса
        self.plow_x = -120.0
        self.plow_active = False
        self.plow_timer_ticks = 0

        # --- Гирлянда ---
        self.top_garland = tk.BooleanVar(value=True)
        self.win_garland = tk.BooleanVar(value=True)
        self.win_scope = tk.StringVar(value="all")       # all, active
        self.garland_style = tk.StringVar(value="bulb")  # bulb, icicle, star
        self.garland_scale = tk.DoubleVar(value=1.0)     # Плавная крутилка размера от 0.65 до 1.75
        self.garland_mode = tk.StringVar(value="rainbow")# rainbow, wave, twinkle, steady
        self.garland_palette = tk.StringVar(value="classic")
        self.garland_spacing = tk.IntVar(value=38)

        # --- Фейерверки и северное сияние ---
        self.fireworks_enabled = tk.BooleanVar(value=True)
        self.firework_interval = tk.IntVar(value=7)
        self.aurora_enabled = tk.BooleanVar(value=True)
        self.cursor_trail = tk.BooleanVar(value=True)
        self.storm_timer = 0
        self.fw_cooldown_ticks = 60

        # --- Данные симуляции ---
        self.particles = []
        self.falling_chunks = []  # Физика падающего сугроба при сдвиге окна/вкладки
        self.sparks = []
        self.fireworks = []
        self.last_mouse = (-1, -1)
        self.blink_phase = 0
        self.anim_phase = 0.0
        self.window_bounds = {}   # hwnd -> (l, t, r, b)
        self.prev_window_bounds = {}
        self.active_hwnd = None
        self.dragging = False
        self._drag_xy = (0, 0)

        # Накопление сугробов по колонкам экрана
        self.pile_step = 5
        self.pile_cols = (self.screen_w // self.pile_step) + 2
        self.pile = [0.0] * self.pile_cols
        self.pile_owner = [0] * self.pile_cols  # hwnd окна под сугробом или 0 (панель задач)

        # Пулы объектов Canvas
        self.particle_pool = []
        self.chunk_pool = []
        self.spark_pool = []
        self.pile_pool = []
        self.bulb_pool = []
        self.aurora_pool = []
        self.plow_pool = []

        self._build_ui()
        self._init_overlay()
        self._init_pools()
        self._scan_windows(initial=True)
        self._rebuild_particles()

        self._anim_loop()
        self._blink_loop()
        self._windows_loop()

    # =========================================================================
    # МГНОВЕННОЕ ПЕРЕТАСКИВАНИЕ ОКНА МЕНЮ БЕЗ ЛАГОВ
    # =========================================================================
    def _drag_start(self, e):
        self.dragging = True
        self._drag_xy = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _drag_move(self, e):
        x = e.x_root - self._drag_xy[0]
        y = e.y_root - self._drag_xy[1]
        self.root.geometry(f"+{x}+{y}")

    def _drag_stop(self, _e):
        self.dragging = False
        self._scan_windows()

    # =========================================================================
    # ИНТЕРФЕЙС
    # =========================================================================
    def _build_ui(self):
        shell = tk.Frame(
            self.root,
            bg="#0b0e17",
            highlightbackground="#22293e",
            highlightthickness=1,
        )
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg="#111625", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        header.bind("<ButtonPress-1>", self._drag_start)
        header.bind("<B1-Motion>", self._drag_move)
        header.bind("<ButtonRelease-1>", self._drag_stop)

        tk.Frame(header, bg="#38bdf8", height=2).pack(fill="x", side="top")

        title_box = tk.Frame(header, bg="#111625")
        title_box.pack(side="left", padx=16, pady=10)
        title_box.bind("<ButtonPress-1>", self._drag_start)
        title_box.bind("<B1-Motion>", self._drag_move)
        title_box.bind("<ButtonRelease-1>", self._drag_stop)

        lbl_t = tk.Label(
            title_box,
            text="✦ ATMOSPHERE STUDIO",
            bg="#111625",
            fg="#f8fafc",
            font=("Segoe UI", 12, "bold"),
        )
        lbl_t.pack(anchor="w")
        lbl_t.bind("<ButtonPress-1>", self._drag_start)
        lbl_t.bind("<B1-Motion>", self._drag_move)
        lbl_t.bind("<ButtonRelease-1>", self._drag_stop)

        s_names = {"winter": "❄️ Зима", "spring": "🌿 Весна", "summer": "✨ Лето", "autumn": "🍁 Осень"}
        lbl_s = tk.Label(
            title_box,
            text=f"Сезон: {s_names[get_current_season()]} • Быстрый запуск",
            bg="#111625",
            fg="#64748b",
            font=("Segoe UI", 8, "bold"),
        )
        lbl_s.pack(anchor="w")
        lbl_s.bind("<ButtonPress-1>", self._drag_start)
        lbl_s.bind("<B1-Motion>", self._drag_move)
        lbl_s.bind("<ButtonRelease-1>", self._drag_stop)

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
            pady=3,
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
            pady=3,
            cursor="hand2",
            command=self.root.destroy,
        ).pack(side="left", padx=3)

        tab_bar = tk.Frame(shell, bg="#111625", padx=4, pady=4)
        tab_bar.pack(fill="x", padx=16, pady=(10, 6))

        self.tab_frames = {}
        self.tab_btns = {}
        for key, text in [
            ("weather", "❄️ Погода и Сугробы"),
            ("garland", "💡 Гирлянда"),
            ("extras", "🎆 Фейерверки и Аврора"),
        ]:
            b = tk.Button(
                tab_bar,
                text=text,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                bd=0,
                pady=6,
                cursor="hand2",
                command=lambda k=key: self._switch_tab(k),
            )
            b.pack(side="left", expand=True, fill="x", padx=2)
            self.tab_btns[key] = b
            self.tab_frames[key] = tk.Frame(shell, bg="#0b0e17")

        self._build_weather_tab(self.tab_frames["weather"])
        self._build_garland_tab(self.tab_frames["garland"])
        self._build_extras_tab(self.tab_frames["extras"])
        self._switch_tab("weather")

    def _minimize(self):
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.bind("", self._on_restore)

    def _on_restore(self, _e=None):
        if self.root.state() == "normal":
            self.root.unbind("")
            self.root.overrideredirect(True)

    def _switch_tab(self, key: str):
        for k, f in self.tab_frames.items():
            f.pack_forget()
            act = k == key
            self.tab_btns[k].configure(
                bg="#2563eb" if act else "#111625",
                fg="#ffffff" if act else "#64748b",
            )
        self.tab_frames[key].pack(fill="both", expand=True, padx=16, pady=2)

    def _card(self, parent, title: str, accent="#38bdf8"):
        c = tk.Frame(parent, bg="#141926", highlightbackground="#1f273d", highlightthickness=1)
        c.pack(fill="x", pady=4)
        tk.Label(c, text=title, bg="#141926", fg=accent, font=("Segoe UI", 8, "bold")).pack(
            anchor="w", padx=12, pady=(6, 2)
        )
        body = tk.Frame(c, bg="#141926")
        body.pack(fill="x", padx=12, pady=(0, 8))
        return body

    def _toggle(self, parent, title: str, sub: str, var: tk.BooleanVar, cmd=None, accent="#38bdf8"):
        row = tk.Frame(parent, bg="#141926")
        row.pack(fill="x", pady=2)
        left = tk.Frame(row, bg="#141926")
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=title, bg="#141926", fg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        if sub:
            tk.Label(left, text=sub, bg="#141926", fg="#64748b", font=("Segoe UI", 8)).pack(anchor="w")
        sw = SwitchPill(row, var, command=cmd, accent=accent, bg="#141926")
        sw.pack(side="right", padx=(8, 0))
        return sw

    def _pills(self, parent, items, getter, setter, accent="#2563eb"):
        row = tk.Frame(parent, bg="#0f1320", padx=3, pady=3)
        row.pack(fill="x", pady=(3, 2))
        btns = {}
        for k, lbl in items:
            b = tk.Button(
                row,
                text=lbl,
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                bd=0,
                pady=4,
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

    def _scale(self, parent, lbl: str, var, lo, hi, step, cmd=None):
        row = tk.Frame(parent, bg="#141926")
        row.pack(fill="x", pady=0)
        tk.Label(row, text=lbl, bg="#141926", fg="#cbd5e1", font=("Segoe UI", 9)).pack(side="left")
        tk.Scale(
            row,
            variable=var,
            from_=lo,
            to=hi,
            resolution=step,
            orient="horizontal",
            bg="#141926",
            fg="#38bdf8",
            troughcolor="#1e263b",
            activebackground="#38bdf8",
            highlightthickness=0,
            bd=0,
            length=165,
            command=(lambda _v: cmd()) if cmd else None,
        ).pack(side="right")

    def _build_weather_tab(self, parent):
        c1 = self._card(parent, "СЕЗОН И АВТОПОДСТРОЙКА", "#38bdf8")
        self._toggle(c1, "Снег / листья / светлячки", "Работает поверх или на окнах и панели задач", self.weather_enabled)
        self._toggle(
            c1,
            "Авто-сезон по календарю",
            "Автоматически подстраивает под время года",
            self.auto_season,
            cmd=self._on_auto_season,
            accent="#10b981",
        )
        self._ref_season = self._pills(
            c1,
            [("winter", "❄️ Зима"), ("spring", "🌿 Весна"), ("summer", "✨ Лето"), ("autumn", "🍁 Осень")],
            self._active_season,
            self._set_season,
        )

        c2 = self._card(parent, "СУГРОБЫ И ФИЗИКА ОКОН", "#60a5fa")
        self._toggle(
            c2,
            "Накапливать на окнах и панели задач",
            "На пустом столе падает вниз, на окнах и вкладках копится",
            self.pile_enabled,
            cmd=self._on_pile_toggle,
        )
        tk.Button(
            c2,
            text="🧹 Очистить все сугробы / листья",
            bg="#1e263b",
            fg="#e2e8f0",
            activebackground="#2b3654",
            activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            pady=4,
            cursor="hand2",
            command=self._clear_pile,
        ).pack(fill="x", pady=(3, 0))

        c3 = self._card(parent, "СНЕГОУБОРОЧНАЯ МАШИНА (СНЕГ И ЛИСТЬЯ)", "#f59e0b")
        self._toggle(
            c3,
            "Уборочная машина",
            "Проезжает по панели задач и убирает снег/листья",
            self.plow_enabled,
            accent="#f59e0b",
        )
        self._ref_plow_mode = self._pills(
            c3,
            [("both", "⏱️+📏 По времени и сугробу"), ("time", "⏱️ Только по времени"), ("threshold", "📏 Только по высоте")],
            self.plow_mode.get,
            self._set_plow_mode,
            accent="#d97706",
        )
        self._scale(c3, "Интервал рейса (сек):", self.plow_interval, 5, 120, 5)
        self._scale(c3, "Порог сугроба (px):", self.plow_threshold, 6, 26, 2)

        c4 = self._card(parent, "СНЕЖИНКИ И ПОТОК", "#a5b4fc")
        self._ref_shape = self._pills(
            c4,
            [("circle", "• Хлопья"), ("crystal", "❄ Ажурные"), ("star", "✦ Звёзды"), ("mix", "🎲 Микс")],
            self.flake_shape.get,
            self._set_shape,
            accent="#6366f1",
        )
        self._scale(c4, "Количество:", self.count_var, 15, 130, 1, self._rebuild_particles)
        self._scale(c4, "Скорость:", self.speed_var, 0.6, 6.0, 0.2)
        self._scale(c4, "Ветер:", self.wind_var, -2.5, 2.5, 0.1)

    def _build_garland_tab(self, parent):
        c1 = self._card(parent, "ГДЕ И ВИД ГИРЛЯНДЫ", "#fbbf24")
        self._toggle(c1, "Гирлянда вверху экрана", "Вдоль верхнего края монитора", self.top_garland, accent="#f59e0b")
        self._toggle(c1, "Гирлянда на окнах", "Закрепляется на рамках окон", self.win_garland, accent="#f59e0b")
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

        c2 = self._card(parent, "РАЗМЕР (КРУТИЛКА) И РЕЖИМ", "#f472b6")
        self._scale(c2, "Размер гирлянды:", self.garland_scale, 0.65, 1.75, 0.05)
        self._ref_mode = self._pills(
            c2,
            [("rainbow", "🌈 Перелив"), ("wave", "🌊 Волна"), ("twinkle", "✨ Мерцание"), ("steady", "💡 Ровный")],
            self.garland_mode.get,
            self._set_mode,
            accent="#db2777",
        )

        c3 = self._card(parent, "ЦВЕТА И ШАГ", "#34d399")
        self._ref_pal = self._pills(
            c3,
            [("classic", "🎄 Классика"), ("warm", "🕯️ Тёплая"), ("cyber", "🟣 Неон"), ("ice", "🧊 Лёд")],
            self.garland_palette.get,
            self._set_palette,
            accent="#059669",
        )
        self._scale(c3, "Шаг лампочек (px):", self.garland_spacing, 24, 72, 2)

    def _build_extras_tab(self, parent):
        c1 = self._card(parent, "АВТО-ФЕЙЕРВЕРКИ", "#f43f5e")
        self._toggle(
            c1,
            "Включить фейерверки",
            "Запускаются автоматически по выбранному интервалу",
            self.fireworks_enabled,
            accent="#f43f5e",
        )
        self._scale(c1, "Интервал запуска (сек):", self.firework_interval, 2, 30, 1)
        tk.Button(
            c1,
            text="🎆 Запустить фейерверк сейчас",
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self._spawn_firework_burst,
        ).pack(fill="x", pady=(6, 0))

        c2 = self._card(parent, "СЕВЕРНОЕ СИЯНИЕ И ФИШКИ", "#2dd4bf")
        self._toggle(
            c2,
            "Северное сияние вверху экрана",
            "Волнообразные всполохи зелёного, бирюзового и фиолетового",
            self.aurora_enabled,
            accent="#14b8a6",
        )
        self._toggle(c2, "Шлейф за курсором", "Искорки при движении мыши", self.cursor_trail, accent="#a855f7")
        tk.Button(
            c2,
            text="🌬️ Порыв метели на 5 сек",
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self._trigger_storm,
        ).pack(fill="x", pady=(4, 0))

    # --- Коллбэки ---
    def _on_auto_season(self):
        if self.auto_season.get():
            self.season.set(get_current_season())
            self._clear_pile()
            self._rebuild_particles()
        self._ref_season()

    def _set_season(self, val: str):
        self.auto_season.set(False)
        self.season.set(val)
        self._clear_pile()
        self._rebuild_particles()
        self._ref_season()

    def _set_shape(self, val: str):
        self.flake_shape.set(val)
        self._rebuild_particles()
        self._ref_shape()

    def _set_scope(self, val: str):
        self.win_scope.set(val)
        self._ref_scope()

    def _set_style(self, val: str):
        self.garland_style.set(val)
        self._ref_style()

    def _set_plow_mode(self, val: str):
        self.plow_mode.set(val)
        self._ref_plow_mode()

    def _set_mode(self, val: str):
        self.garland_mode.set(val)
        self._ref_mode()

    def _set_palette(self, val: str):
        self.garland_palette.set(val)
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
        # Ленты северного сияния (полигоны волн)
        aurora_cols = ["#10b981", "#2dd4bf", "#38bdf8", "#a855f7"]
        for i in range(4):
            self.aurora_pool.append(
                self.canvas.create_polygon(
                    -20, -20, -10, -20, -10, -10,
                    fill=aurora_cols[i],
                    stipple="gray25",
                    outline="",
                    smooth=True,
                    state="hidden",
                )
            )

        for _ in range(135):
            ov = self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            l1 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            l2 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            l3 = self.canvas.create_line(-20, -20, -20, -20, fill="#ffffff", width=1, state="hidden")
            py = self.canvas.create_polygon(-20, -20, -19, -20, -19, -19, fill="#ffffff", outline="", state="hidden")
            self.particle_pool.append((ov, l1, l2, l3, py))

        # Падающие комья сугробов при сдвиге окон/вкладок
        self.chunk_pool = [
            self.canvas.create_oval(-20, -20, -14, -14, fill="#ffffff", outline="#cbd5e1", width=1, state="hidden")
            for _ in range(90)
        ]

        self.spark_pool = [
            self.canvas.create_oval(-20, -20, -15, -15, fill="#ffffff", outline="", state="hidden")
            for _ in range(130)
        ]

        self.pile_pool = [
            self.canvas.create_polygon(
                -20, -20, -15, -20, -15, -15, -20, -15,
                fill="#ffffff", outline="", state="hidden"
            )
            for _ in range(self.pile_cols)
        ]

        # Для каждого элемента гирлянды: провод + ореол + тело + блик
        for _ in range(260):
            wire = self.canvas.create_line(-20, -20, -10, -20, fill="#1e2433", width=2, state="hidden")
            glow = self.canvas.create_oval(-20, -20, -10, -10, fill="#ff3b3b", stipple="gray25", outline="", state="hidden")
            body = self.canvas.create_polygon(-20, -20, -19, -20, -19, -19, fill="#ff3b3b", outline="#0f172a", width=1, state="hidden")
            shine = self.canvas.create_oval(-20, -20, -17, -17, fill="#ffffff", outline="", state="hidden")
            self.bulb_pool.append((wire, glow, body, shine))

        # Снегоуборочная машина (корпус + ковш + мигалка + колесо)
        plow_body = self.canvas.create_polygon(-100, -100, -90, -100, -90, -90, fill="#f97316", outline="#0f172a", width=1, state="hidden")
        plow_blade = self.canvas.create_polygon(-100, -100, -90, -100, -90, -90, fill="#eab308", outline="#0f172a", width=1, state="hidden")
        plow_beacon = self.canvas.create_oval(-100, -100, -95, -95, fill="#38bdf8", outline="", state="hidden")
        plow_wheel = self.canvas.create_oval(-100, -100, -95, -95, fill="#1e293b", outline="#94a3b8", width=1, state="hidden")
        self.plow_pool = (plow_body, plow_blade, plow_beacon, plow_wheel)

    # =========================================================================
    # СКАНИРОВАНИЕ ОКОН И ФИЗИКА СДВИГА СУГРОБОВ
    # =========================================================================
    def _scan_windows(self, initial: bool = False):
        updated = {}
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def cb(hwnd, _lp):
            if is_real_window(hwnd):
                b = get_window_bounds(hwnd)
                if b and b[0] > -10000 and (b[2] - b[0]) > 140 and (b[3] - b[1]) > 50:
                    updated[hwnd] = b
            return True

        user32.EnumWindows(WNDENUMPROC(cb), 0)

        if not initial and self.pile_enabled.get():
            self._handle_window_movement_snow(updated)

        self.prev_window_bounds = self.window_bounds
        self.window_bounds = updated
        fg = user32.GetForegroundWindow()
        self.active_hwnd = fg if is_real_window(fg) else None

    def _handle_window_movement_snow(self, new_bounds: dict):
        """Когда окно или вкладка сдвигается/уходит, лежащий сверху сугроб срывается и падает вниз."""
        s = self._active_season()
        if s == "summer":
            return

        col_colors = {"winter": "#f8fafc", "spring": "#6ee7b7", "autumn": "#ea580c"}
        c_col = col_colors.get(s, "#f8fafc")

        for hwnd, old_b in self.window_bounds.items():
            new_b = new_bounds.get(hwnd)
            moved = False
            if not new_b:
                moved = True
            else:
                # Если верхняя кромка или горизонтальные границы сдвинулись более чем на 4px
                if (
                    abs(old_b[0] - new_b[0]) > 4
                    or abs(old_b[1] - new_b[1]) > 4
                    or abs(old_b[2] - new_b[2]) > 4
                ):
                    moved = True

            if moved:
                c_start = max(0, int(old_b[0] // self.pile_step))
                c_end = min(self.pile_cols - 1, int(old_b[2] // self.pile_step))
                surf_y = old_b[1]
                for col in range(c_start, c_end + 1, 2):
                    if self.pile_owner[col] == hwnd and self.pile[col] > 1.2:
                        h = self.pile[col]
                        if len(self.falling_chunks) < len(self.chunk_pool):
                            self.falling_chunks.append(
                                {
                                    "x": float(col * self.pile_step + 2),
                                    "y": float(surf_y - h),
                                    "vx": random.uniform(-1.4, 1.4),
                                    "vy": random.uniform(0.5, 2.0),
                                    "r": min(6.5, max(2.8, h * 0.35)),
                                    "color": c_col,
                                }
                            )
                        self.pile[col] = 0.0
                        self.pile_owner[col] = 0

    def _windows_loop(self):
        if not self.dragging:
            self._scan_windows()
        self.root.after(110, self._windows_loop)

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

    def _get_surface_at_x(self, x: float, current_y: float, tb_top: int):
        """Находит ближайшую поверхность ниже текущей высоты: окно/вкладку или панель задач."""
        best_y = float(tb_top)
        owner = 0

        for hwnd, b in self.window_bounds.items():
            l, t, r, btm = b
            if l <= x <= r and t < btm:
                # Поверхность окна/вкладки выше панели задач и ниже текущих координат снежинки
                if t < tb_top and current_y <= t + 8 and t < best_y:
                    best_y = float(t)
                    owner = hwnd

        return best_y, owner

    # =========================================================================
    # ОСНОВНОЙ ЦИКЛ АНИМАЦИИ
    # =========================================================================
    def _anim_loop(self):
        if self.dragging:
            self.root.after(25, self._anim_loop)
            return

        self.anim_phase += 0.06
        if self.storm_timer > 0:
            self.storm_timer -= 1

        # Авто-фейерверки по интервалу
        if self.fireworks_enabled.get():
            self.fw_cooldown_ticks -= 1
            if self.fw_cooldown_ticks <= 0:
                self._spawn_firework_burst()
                self.fw_cooldown_ticks = max(1, int(self.firework_interval.get() * (1000 / 28)))

        s = self._active_season()
        tb_top = get_taskbar_top(self.screen_h)
        storm_mult = 2.2 if self.storm_timer > 0 else 1.0

        # 0. Настоящее северное сияние (мерцающие переливающиеся лучи-шторы вверху экрана)
        if self.aurora_enabled.get():
            aurora_pal = [
                ["#10b981", "#34d399", "#2dd4bf", "#a7f3d0"],
                ["#2dd4bf", "#38bdf8", "#818cf8", "#34d399"],
                ["#34d399", "#a3e635", "#2dd4bf", "#38bdf8"],
                ["#818cf8", "#c084fc", "#2dd4bf", "#34d399"],
            ]
            cols_a = aurora_pal[int(self.anim_phase * 1.5) % len(aurora_pal)]
            for idx, rid in enumerate(self.aurora_pool):
                base_x = (self.screen_w * (0.12 + idx * 0.25)) + math.sin(self.anim_phase * 0.7 + idx * 1.7) * 140
                spread = 170 + 55 * math.cos(self.anim_phase * 1.1 + idx)
                tip_y = 48 + 34 * math.sin(self.anim_phase * 1.4 + idx * 2.1)
                pts = [
                    base_x - spread, 0,
                    base_x - spread * 0.35, tip_y * 0.75,
                    base_x, tip_y,
                    base_x + spread * 0.35, tip_y * 0.7,
                    base_x + spread, 0,
                ]
                self.canvas.coords(rid, *pts)
                self.canvas.itemconfigure(rid, fill=cols_a[idx % len(cols_a)], state="normal")
        else:
            for rid in self.aurora_pool:
                self.canvas.itemconfigure(rid, state="hidden")

        # 1. Частицы погоды (падают на пустом рабочем столе вниз до панели задач, а на окнах/вкладках оседают сверху)
        show_weather = self.weather_enabled.get()
        base_spd = self.speed_var.get() * storm_mult
        wind = self.wind_var.get() + (2.4 if self.storm_timer > 0 else 0.0)

        target_n = min(len(self.particle_pool), self.count_var.get())
        while len(self.particles) < target_n:
            self.particles.append(self._spawn_particle(random_y=True))
        while len(self.particles) > target_n:
            self.particles.pop()

        for idx, slot in enumerate(self.particle_pool):
            ov, l1, l2, l3, py = slot
            if not show_weather or idx >= len(self.particles):
                for obj in slot:
                    self.canvas.itemconfigure(obj, state="hidden")
                continue

            p = self.particles[idx]
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
                surf_y, owner_hwnd = self._get_surface_at_x(p["x"], p["y"], tb_top)
                pile_h = self.pile[col] if self.pile_enabled.get() else 0.0
                if p["y"] >= surf_y - pile_h:
                    if self.pile_enabled.get():
                        for d_col, w in ((-1, 0.35), (0, 0.75), (1, 0.35)):
                            c = col + d_col
                            if 0 <= c < self.pile_cols:
                                self.pile[c] = min(26.0, self.pile[c] + w)
                                if owner_hwnd:
                                    self.pile_owner[c] = owner_hwnd
                    p.update(self._spawn_particle(random_y=False))

            self._render_particle(slot, p, s)

        # 2. Физика падающих комьев сугроба при сдвиге окон/вкладок
        next_chunks = []
        for ch in self.falling_chunks:
            ch["x"] += ch["vx"]
            ch["y"] += ch["vy"]
            ch["vy"] += 0.28
            col = max(0, min(self.pile_cols - 1, int(ch["x"] // self.pile_step)))
            surf_y, owner_hwnd = self._get_surface_at_x(ch["x"], ch["y"], tb_top)
            if ch["y"] >= surf_y - self.pile[col]:
                if self.pile_enabled.get() and s != "summer":
                    self.pile[col] = min(26.0, self.pile[col] + 1.2)
                    if owner_hwnd:
                        self.pile_owner[col] = owner_hwnd
            else:
                next_chunks.append(ch)
        self.falling_chunks = next_chunks

        for idx, cid in enumerate(self.chunk_pool):
            if idx < len(self.falling_chunks):
                ch = self.falling_chunks[idx]
                r = ch["r"]
                self.canvas.coords(cid, ch["x"] - r, ch["y"] - r, ch["x"] + r, ch["y"] + r)
                self.canvas.itemconfigure(cid, fill=ch["color"], state="normal")
            else:
                self.canvas.itemconfigure(cid, state="hidden")

        # 3. Красивые сугробы и листва (на окнах/вкладках и на панели задач)
        pile_cols = {"winter": "#f8fafc", "spring": "#6ee7b7", "autumn": "#ea580c"}
        p_col = pile_cols.get(s, "#f8fafc")
        for i, poly_id in enumerate(self.pile_pool):
            h = self.pile[i] if (self.pile_enabled.get() and s != "summer") else 0.0
            if h > 0.6:
                x1 = i * self.pile_step
                x2 = x1 + self.pile_step + 1
                owner = self.pile_owner[i]
                if owner and owner in self.window_bounds:
                    base_y = self.window_bounds[owner][1]
                else:
                    base_y = tb_top
                # Скруглённая шапка сугроба
                arch = min(4.0, h * 0.35)
                pts = [
                    x1, base_y + 1,
                    x1, base_y - h + arch,
                    (x1 + x2) * 0.5, base_y - h,
                    x2, base_y - h + arch,
                    x2, base_y + 1,
                ]
                self.canvas.coords(poly_id, *pts)
                self.canvas.itemconfigure(poly_id, fill=p_col, state="normal")
            else:
                self.canvas.itemconfigure(poly_id, state="hidden")

        # 4. Снегоуборочная машина (убирает снег и листья по времени или по высоте сугроба)
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

        # 6. Гирлянда с плавным масштабом от крутилки
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
            self.plow_timer_ticks += 1
            mode = self.plow_mode.get()
            time_reached = self.plow_timer_ticks >= max(1, int(self.plow_interval.get() * (1000 / 28)))
            max_pile = max(self.pile) if self.pile else 0.0
            thresh_reached = max_pile >= float(self.plow_threshold.get())

            should_start = False
            if mode == "time" and time_reached:
                should_start = True
            elif mode == "threshold" and thresh_reached:
                should_start = True
            elif mode == "both" and (time_reached or thresh_reached):
                should_start = True

            if should_start and max_pile > 0.5:
                self.plow_active = True
                self.plow_timer_ticks = 0
                self.plow_x = -80.0
            else:
                for obj in self.plow_pool:
                    self.canvas.itemconfigure(obj, state="hidden")
                return

        # Машинка едет слева направо по верхнему краю панели задач и счищает сугробы
        self.plow_x += 9.5
        px = self.plow_x
        base_y = float(tb_top)

        # Очищаем колонки сугробов под машиной
        col_clear = int((px + 25) // self.pile_step)
        for c in range(max(0, col_clear - 4), min(self.pile_cols, col_clear + 2)):
            self.pile[c] = 0.0
            self.pile_owner[c] = 0

        if px > self.screen_w + 90:
            self.plow_active = False
            for obj in self.plow_pool:
                self.canvas.itemconfigure(obj, state="hidden")
            return

        # Корпус машинки
        self.canvas.coords(
            plow_body,
            px - 34, base_y - 18,
            px + 6, base_y - 18,
            px + 12, base_y - 6,
            px - 34, base_y - 6,
        )
        self.canvas.itemconfigure(plow_body, fill="#f97316", outline="#0f172a", width=1, state="normal")

        # Передний отвал
        self.canvas.coords(
            plow_blade,
            px + 10, base_y - 14,
            px + 22, base_y - 3,
            px + 12, base_y - 3,
        )
        self.canvas.itemconfigure(plow_blade, fill="#facc15", outline="#0f172a", width=1, state="normal")

        # Мигалка сверху
        b_col = "#38bdf8" if (int(self.anim_phase * 8) % 2 == 0) else "#ef4444"
        self.canvas.coords(plow_beacon, px - 16, base_y - 23, px - 9, base_y - 17)
        self.canvas.itemconfigure(plow_beacon, fill=b_col, state="normal")

        # Колесо
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
        glow_r = 10.5 * sc

        colors = palettes.get(self.garland_palette.get(), palettes["classic"])
        mode = self.garland_mode.get()
        style = self.garland_style.get()
        spacing = max(22, int(self.garland_spacing.get() * max(0.8, min(1.35, sc))))

        lines = []
        if self.top_garland.get():
            lines.append((12, self.screen_w - 12, 2))

        if self.win_garland.get():
            scope = self.win_scope.get()
            for hwnd in list(self.window_bounds.keys()):
                if scope == "active" and hwnd != self.active_hwnd:
                    continue
                b = get_window_bounds(hwnd)
                if not b:
                    continue
                self.window_bounds[hwnd] = b
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
            wire, glow, body, shine = slot
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

            fill_col = col if lit else "#293248"

            if style == "icicle":
                pts = [
                    bx - rad_x * 0.75, y_top + 2,
                    bx + rad_x * 0.75, y_top + 2,
                    bx, y_top + 2 + rad_y * 1.55,
                ]
            elif style == "star":
                s_r = rad_x * 1.25
                pts = [
                    bx, y_top + 1,
                    bx + s_r * 0.45, y_top + 1 + s_r * 0.75,
                    bx + s_r, y_top + 1 + s_r,
                    bx + s_r * 0.45, y_top + 1 + s_r * 1.25,
                    bx, y_top + 1 + s_r * 2.0,
                    bx - s_r * 0.45, y_top + 1 + s_r * 1.25,
                    bx - s_r, y_top + 1 + s_r,
                    bx - s_r * 0.45, y_top + 1 + s_r * 0.75,
                ]
            else:
                # Аккуратная круглая лампочка с коротким патроном сверху
                r_bulb = max(3.5, rad_x * 1.05)
                cy_b = y_top + 3 + r_bulb + 2.0 * sc
                pts = []
                steps = 12
                for k in range(steps):
                    ang = (math.tau * k) / steps
                    pts.extend([bx + math.cos(ang) * r_bulb, cy_b + math.sin(ang) * r_bulb])

            self.canvas.coords(body, *pts)
            self.canvas.itemconfigure(body, fill=fill_col, outline="#0f172a", width=1, state="normal")

            if lit:
                cy_glow = y_top + 3 + rad_y * 0.75
                self.canvas.coords(glow, bx - glow_r, cy_glow - glow_r, bx + glow_r, cy_glow + glow_r)
                self.canvas.itemconfigure(glow, fill=col, state="normal")

                s_rad = max(1.1, rad_x * 0.32)
                sx = bx - rad_x * 0.28
                sy = y_top + 5 + rad_y * 0.45
                self.canvas.coords(shine, sx - s_rad, sy - s_rad, sx + s_rad, sy + s_rad)
                self.canvas.itemconfigure(shine, fill="#ffffff", state="normal")
            else:
                self.canvas.itemconfigure(glow, state="hidden")
                self.canvas.itemconfigure(shine, state="hidden")


if __name__ == "__main__":
    app = AtmosphereStudioApp()
    app.root.mainloop()
