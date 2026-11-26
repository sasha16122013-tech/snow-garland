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

EVENT_SYSTEM_FOREGROUND = 0x0003
EVENT_OBJECT_LOCATIONCHANGE = 0x800B
WINEVENT_OUTOFCONTEXT = 0x0000
DWMWA_EXTENDED_FRAME_BOUNDS = 9

TRANSPARENT_KEY = "#010203"


def get_current_season_key() -> str:
    month = datetime.date.today().month
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def get_window_real_rect(hwnd):
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


def is_valid_app_window(hwnd, ignore_title: str) -> bool:
    if not hwnd or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
        return False

    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return False
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value
    if not title or title == ignore_title:
        return False

    cls_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls_buf, 256)
    if cls_buf.value in (
        "Progman",
        "WorkerW",
        "Shell_TrayWnd",
        "Shell_SecondaryTrayWnd",
        "Windows.UI.Core.CoreWindow",
    ):
        return False

    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    return not bool(ex_style & WS_EX_TOOLWINDOW)


def is_desktop_focused() -> bool:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return True
    cls_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls_buf, 256)
    return cls_buf.value in ("Progman", "WorkerW")


def get_taskbar_rect():
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    if hwnd:
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top, rect.right, rect.bottom)
    return None


class SeasonsGarlandStudio:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Atmosphere & Garland Studio")
        self.root.geometry("404x640+90+70")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#13141f")
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # Погода и сезоны
        self.particles_enabled = tk.BooleanVar(value=True)
        self.auto_season = tk.BooleanVar(value=False)
        self.selected_season = tk.StringVar(value="winter")
        self.only_desktop = tk.BooleanVar(value=False)
        self.accumulate_taskbar = tk.BooleanVar(value=True)
        self.flake_shape = tk.StringVar(value="crystal")
        self.particle_count = tk.IntVar(value=95)
        self.particle_speed = tk.DoubleVar(value=2.4)
        self.wind_strength = tk.DoubleVar(value=0.4)

        # Гирлянда
        self.garland_enabled = tk.BooleanVar(value=True)
        self.garland_target = tk.StringVar(value="all")
        self.garland_mode = tk.StringVar(value="wave")
        self.garland_palette = tk.StringVar(value="classic")
        self.garland_density = tk.IntVar(value=34)

        # Фишки
        self.cursor_sparkle = tk.BooleanVar(value=True)

        # Состояние анимации
        self.particles = []
        self.trail_sparks = []
        self.last_mouse = (0, 0)
        self.blink_step = 0

        self.pile_step = 4
        self.pile_cols = (self.screen_w // self.pile_step) + 2
        self.snow_pile = [0.0] * self.pile_cols

        self.tracked_windows = {}
        self.active_hwnd = None

        self._build_ui()
        self._init_overlay()
        self._setup_win_event_hook()
        self._refresh_all_windows()
        self._rebuild_particles()

        self._loop_animation()
        self._loop_garland_blink()
        self._loop_window_sync()

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#1b1d2e", height=58)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="✨ ATMOSPHERE & GARLAND",
            bg="#1b1d2e",
            fg="#e2e8f0",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=18, pady=14)

        season_labels = {
            "winter": "❄️ Зима",
            "spring": "🌿 Весна",
            "summer": "✨ Лето",
            "autumn": "🍁 Осень",
        }
        tk.Label(
            header,
            text=f"Сейчас: {season_labels[get_current_season_key()]}",
            bg="#262940",
            fg="#93c5fd",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
        ).pack(side="right", padx=16)

        tab_bar = tk.Frame(self.root, bg="#13141f")
        tab_bar.pack(fill="x", padx=16, pady=(12, 6))

        self.tab_frames = {}
        self.tab_buttons = {}

        for key, label in [
            ("weather", "❄️ Погода и Сезоны"),
            ("garland", "💡 Гирлянда на окнах"),
            ("magic", "🪄 Фишки"),
        ]:
            btn = tk.Button(
                tab_bar,
                text=label,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                bd=0,
                padx=10,
                pady=7,
                cursor="hand2",
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", expand=True, fill="x", padx=3)
            self.tab_buttons[key] = btn
            self.tab_frames[key] = tk.Frame(self.root, bg="#13141f")

        self._build_weather_tab(self.tab_frames["weather"])
        self._build_garland_tab(self.tab_frames["garland"])
        self._build_magic_tab(self.tab_frames["magic"])
        self._switch_tab("weather")

    def _switch_tab(self, active_key: str):
        for key, frame in self.tab_frames.items():
            frame.pack_forget()
            btn = self.tab_buttons[key]
            if key == active_key:
                btn.configure(bg="#3b82f6", fg="#ffffff")
            else:
                btn.configure(bg="#1e2030", fg="#94a3b8")
        self.tab_frames[active_key].pack(fill="both", expand=True, padx=16, pady=6)

    def _card(self, parent, title: str):
        box = tk.Frame(
            parent,
            bg="#1a1c2b",
            highlightbackground="#2a2e45",
            highlightthickness=1,
        )
        box.pack(fill="x", pady=6)
        tk.Label(
            box,
            text=title,
            bg="#1a1c2b",
            fg="#93c5fd",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(8, 4))
        inner = tk.Frame(box, bg="#1a1c2b")
        inner.pack(fill="x", padx=12, pady=(0, 10))
        return inner

    def _chk(self, parent, text: str, var: tk.BooleanVar, cmd=None):
        cb = tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            command=cmd,
            bg="#1a1c2b",
            fg="#e2e8f0",
            selectcolor="#2d3250",
            activebackground="#1a1c2b",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        cb.pack(anchor="w", pady=2)
        return cb

    def _build_weather_tab(self, parent):
        c1 = self._card(parent, "РЕЖИМ АТМОСФЕРЫ")
        self._chk(c1, "Включить эффекты погоды", self.particles_enabled)
        self._chk(
            c1,
            "Авто-сезон (подстраивать под время года)",
            self.auto_season,
            cmd=self._on_auto_season_toggle,
        )

        seasons_row = tk.Frame(c1, bg="#1a1c2b")
        seasons_row.pack(fill="x", pady=(6, 2))
        self.season_btns = {}
        for s_key, s_text in [
            ("winter", "❄️ Зима"),
            ("spring", "🌿 Весна"),
            ("summer", "✨ Лето"),
            ("autumn", "🍁 Осень"),
        ]:
            b = tk.Button(
                seasons_row,
                text=s_text,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                bd=0,
                pady=5,
                cursor="hand2",
                command=lambda k=s_key: self._select_season(k),
            )
            b.pack(side="left", expand=True, fill="x", padx=2)
            self.season_btns[s_key] = b
        self._update_season_buttons_style()

        c2 = self._card(parent, "ПОВЕДЕНИЕ И ПАНЕЛЬ ЗАДАЧ")
        self._chk(c2, "Только на рабочем столе (не перекрывать окна)", self.only_desktop)
        self._chk(
            c2,
            "Накапливать снег / листья на панели задач",
            self.accumulate_taskbar,
            cmd=self._on_pile_toggle,
        )
        tk.Button(
            c2,
            text="🧹 Очистить сугробы на панели задач",
            bg="#262940",
            fg="#cbd5e1",
            activebackground="#333856",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            pady=4,
            cursor="hand2",
            command=self._clear_pile,
        ).pack(fill="x", pady=(4, 0))

        c3 = self._card(parent, "ФОРМА СНЕЖИНОК (ДЛЯ ЗИМЫ)")
        shapes_row = tk.Frame(c3, bg="#1a1c2b")
        shapes_row.pack(fill="x", pady=2)
        self.shape_btns = {}
        for sh_key, sh_text in [
            ("circle", "• Круглые"),
            ("crystal", "❄ Ажурные"),
            ("star", "✦ Звёзды"),
            ("mix", "🎲 Микс"),
        ]:
            b = tk.Button(
                shapes_row,
                text=sh_text,
                font=("Segoe UI", 9),
                relief="flat",
                bd=0,
                pady=5,
                cursor="hand2",
                command=lambda k=sh_key: self._select_shape(k),
            )
            b.pack(side="left", expand=True, fill="x", padx=2)
            self.shape_btns[sh_key] = b
        self._update_shape_buttons_style()

        c4 = self._card(parent, "ИНТЕНСИВНОСТЬ И ВЕТЕР")
        self._slider(
            c4, "Количество частиц:", self.particle_count, 20, 220, 1, self._rebuild_particles
        )
        self._slider(c4, "Скорость падения:", self.particle_speed, 0.6, 6.0, 0.2)
        self._slider(c4, "Боковой ветер:", self.wind_strength, -2.5, 2.5, 0.1)

    def _build_garland_tab(self, parent):
        c1 = self._card(parent, "ОСНОВНОЕ")
        self._chk(c1, "Включить гирлянду на окнах", self.garland_enabled)

        target_row = tk.Frame(c1, bg="#1a1c2b")
        target_row.pack(fill="x", pady=(6, 2))
        self.target_btns = {}
        for t_key, t_lbl in [("all", "На всех окнах"), ("active", "Только на активном окне")]:
            b = tk.Button(
                target_row,
                text=t_lbl,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                pady=5,
                cursor="hand2",
                command=lambda k=t_key: self._select_target(k),
            )
            b.pack(side="left", expand=True, fill="x", padx=2)
            self.target_btns[t_key] = b
        self._update_target_buttons_style()

        c2 = self._card(parent, "РЕЖИМ СВЕЧЕНИЯ")
        modes_row = tk.Frame(c2, bg="#1a1c2b")
        modes_row.pack(fill="x", pady=2)
        self.mode_btns = {}
        for m_key, m_lbl in [
            ("wave", "🌊 Волна"),
            ("twinkle", "✨ Мерцание"),
            ("steady", "💡 Горит"),
            ("neon", "⚡ Бегущий"),
        ]:
            b = tk.Button(
                modes_row,
                text=m_lbl,
                font=("Segoe UI", 9),
                relief="flat",
                pady=5,
                cursor="hand2",
                command=lambda k=m_key: self._select_mode(k),
            )
            b.pack(side="left", expand=True, fill="x", padx=2)
            self.mode_btns[m_key] = b
        self._update_mode_buttons_style()

        c3 = self._card(parent, "ЦВЕТОВАЯ ПАЛИТРА")
        pal_row = tk.Frame(c3, bg="#1a1c2b")
        pal_row.pack(fill="x", pady=2)
        self.pal_btns = {}
        for p_key, p_lbl in [
            ("classic", "🎄 Классика"),
            ("warm", "🕯️ Тёплый"),
            ("cyber", "🟣 Неон"),
            ("ice", "🧊 Лёд"),
        ]:
            b = tk.Button(
                pal_row,
                text=p_lbl,
                font=("Segoe UI", 9),
                relief="flat",
                pady=5,
                cursor="hand2",
                command=lambda k=p_key: self._select_palette(k),
            )
            b.pack(side="left", expand=True, fill="x", padx=2)
            self.pal_btns[p_key] = b
        self._update_palette_buttons_style()

        c4 = self._card(parent, "ПЛОТНОСТЬ ЛАМПОЧЕК")
        self._slider(c4, "Шаг между лампочками (px):", self.garland_density, 22, 65, 2)

    def _build_magic_tab(self, parent):
        c1 = self._card(parent, "ИНТЕРАКТИВНЫЕ ФИШКИ")
        self._chk(c1, "Волшебный шлейф искр за курсором мыши", self.cursor_sparkle)
        tk.Label(
            c1,
            text=(
                "Когда двигаешь мышку по экрану, за курсором летят\n"
                "сезонные искорки: снежинки зимой, весенние лепестки,\n"
                "летние светлячки или осенние огоньки."
            ),
            bg="#1a1c2b",
            fg="#94a3b8",
            justify="left",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(6, 0))

    def _slider(self, parent, label: str, var, from_, to, res, cmd=None):
        row = tk.Frame(parent, bg="#1a1c2b")
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg="#1a1c2b", fg="#cbd5e1", font=("Segoe UI", 9)).pack(
            side="left"
        )
        scale = tk.Scale(
            row,
            variable=var,
            from_=from_,
            to=to,
            resolution=res,
            orient="horizontal",
            bg="#1a1c2b",
            fg="#93c5fd",
            troughcolor="#262940",
            highlightthickness=0,
            bd=0,
            length=150,
            command=(lambda _v: cmd()) if cmd else None,
        )
        scale.pack(side="right")

    def _on_auto_season_toggle(self):
        if self.auto_season.get():
            self.selected_season.set(get_current_season_key())
            self._clear_pile()
            self._rebuild_particles()
        self._update_season_buttons_style()

    def _select_season(self, key: str):
        self.auto_season.set(False)
        self.selected_season.set(key)
        self._clear_pile()
        self._rebuild_particles()
        self._update_season_buttons_style()

    def _update_season_buttons_style(self):
        cur = get_current_season_key() if self.auto_season.get() else self.selected_season.get()
        for k, b in self.season_btns.items():
            b.configure(
                bg="#3b82f6" if k == cur else "#262940",
                fg="#ffffff" if k == cur else "#94a3b8",
            )

    def _select_shape(self, key: str):
        self.flake_shape.set(key)
        self._rebuild_particles()
        self._update_shape_buttons_style()

    def _update_shape_buttons_style(self):
        cur = self.flake_shape.get()
        for k, b in self.shape_btns.items():
            b.configure(
                bg="#3b82f6" if k == cur else "#262940",
                fg="#ffffff" if k == cur else "#94a3b8",
            )

    def _select_target(self, key: str):
        self.garland_target.set(key)
        self._update_target_buttons_style()

    def _update_target_buttons_style(self):
        cur = self.garland_target.get()
        for k, b in self.target_btns.items():
            b.configure(
                bg="#3b82f6" if k == cur else "#262940",
                fg="#ffffff" if k == cur else "#94a3b8",
            )

    def _select_mode(self, key: str):
        self.garland_mode.set(key)
        self._update_mode_buttons_style()

    def _update_mode_buttons_style(self):
        cur = self.garland_mode.get()
        for k, b in self.mode_btns.items():
            b.configure(
                bg="#3b82f6" if k == cur else "#262940",
                fg="#ffffff" if k == cur else "#94a3b8",
            )

    def _select_palette(self, key: str):
        self.garland_palette.set(key)
        self._update_palette_buttons_style()

    def _update_palette_buttons_style(self):
        cur = self.garland_palette.get()
        for k, b in self.pal_btns.items():
            b.configure(
                bg="#3b82f6" if k == cur else "#262940",
                fg="#ffffff" if k == cur else "#94a3b8",
            )

    def _on_pile_toggle(self):
        if not self.accumulate_taskbar.get():
            self._clear_pile()

    def _clear_pile(self):
        self.snow_pile = [0.0] * self.pile_cols

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

    def _setup_win_event_hook(self):
        WinEventProcType = ctypes.WINFUNCTYPE(
            None,
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.HWND,
            wintypes.LONG,
            wintypes.LONG,
            wintypes.DWORD,
            wintypes.DWORD,
        )

        def callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
            if idObject != 0 or not hwnd:
                return
            if event == EVENT_SYSTEM_FOREGROUND:
                self.active_hwnd = hwnd
            if is_valid_app_window(hwnd, "Atmosphere & Garland Studio"):
                rect = get_window_real_rect(hwnd)
                if rect and rect[0] > -10000:
                    self.tracked_windows[hwnd] = rect

        self._win_event_cb = WinEventProcType(callback)
        self._hook = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_OBJECT_LOCATIONCHANGE,
            0,
            self._win_event_cb,
            0,
            0,
            WINEVENT_OUTOFCONTEXT,
        )

    def _refresh_all_windows(self):
        new_map = {}
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_cb(hwnd, lParam):
            if is_valid_app_window(hwnd, "Atmosphere & Garland Studio"):
                rect = get_window_real_rect(hwnd)
                if rect and rect[0] > -10000 and (rect[2] - rect[0]) > 120:
                    new_map[hwnd] = rect
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        self.tracked_windows = new_map
        fg = user32.GetForegroundWindow()
        if is_valid_app_window(fg, "Atmosphere & Garland Studio"):
            self.active_hwnd = fg

    def _loop_window_sync(self):
        self._refresh_all_windows()
        self.root.after(250, self._loop_window_sync)

    def _active_season(self) -> str:
        if self.auto_season.get():
            return get_current_season_key()
        return self.selected_season.get()

    def _rebuild_particles(self):
        self.particles = [self._spawn_particle(random_y=True) for _ in range(self.particle_count.get())]

    def _spawn_particle(self, random_y: bool = False):
        season = self._active_season()
        shape = self.flake_shape.get()
        if shape == "mix":
            shape = random.choice(["circle", "crystal", "star"])

        leaf_colors = {
            "spring": ["#6ee7b7", "#34d399", "#a7f3d0", "#86efac", "#bef264"],
            "autumn": ["#f59e0b", "#ea580c", "#dc2626", "#eab308", "#d97706"],
        }

        color = "#ffffff"
        if season in leaf_colors:
            color = random.choice(leaf_colors[season])
        elif season == "summer":
            color = random.choice(["#fef08a", "#fde047", "#bef264"])

        return {
            "x": random.uniform(0, self.screen_w),
            "y": random.uniform(-self.screen_h, self.screen_h) if random_y else random.uniform(-30, -5),
            "r": random.uniform(2.5, 5.5) if season != "summer" else random.uniform(2.0, 3.8),
            "speed_mult": random.uniform(0.65, 1.35),
            "phase": random.uniform(0, math.tau),
            "angle": random.uniform(0, math.tau),
            "spin": random.uniform(-0.07, 0.07),
            "shape": shape,
            "color": color,
        }

    def _loop_garland_blink(self):
        self.blink_step = (self.blink_step + 1) % 24
        self.root.after(320, self._loop_garland_blink)

    def _loop_animation(self):
        self.canvas.delete("all")

        season = self._active_season()
        tb_rect = get_taskbar_rect()
        tb_top = tb_rect[1] if tb_rect else (self.screen_h - 48)

        can_draw_weather = self.particles_enabled.get() and (
            not self.only_desktop.get() or is_desktop_focused()
        )

        if can_draw_weather:
            base_speed = self.particle_speed.get()
            wind = self.wind_strength.get()

            for p in self.particles:
                p["phase"] += 0.04
                p["angle"] += p["spin"]

                if season == "summer":
                    p["x"] += math.cos(p["phase"]) * 1.1 + wind * 0.3
                    p["y"] += math.sin(p["phase"] * 0.8) * 0.8 - 0.15
                    if p["y"] < 20:
                        p["y"] = tb_top - 30
                else:
                    p["y"] += base_speed * p["speed_mult"]
                    p["x"] += math.sin(p["phase"]) * 0.9 + wind

                if p["x"] < -10:
                    p["x"] = self.screen_w + 10
                elif p["x"] > self.screen_w + 10:
                    p["x"] = -10

                if season != "summer":
                    col = max(0, min(self.pile_cols - 1, int(p["x"] // self.pile_step)))
                    pile_h = self.snow_pile[col] if self.accumulate_taskbar.get() else 0
                    if p["y"] >= tb_top - pile_h:
                        if self.accumulate_taskbar.get():
                            for offset, weight in ((-1, 0.35), (0, 0.7), (1, 0.35)):
                                c_idx = col + offset
                                if 0 <= c_idx < self.pile_cols:
                                    self.snow_pile[c_idx] = min(26.0, self.snow_pile[c_idx] + weight)
                        p.update(self._spawn_particle(random_y=False))
                        continue

                self._draw_particle(p, season)

        if self.accumulate_taskbar.get() and season != "summer":
            pile_color = {
                "winter": "#f8fafc",
                "spring": "#6ee7b7",
                "autumn": "#ea580c",
            }.get(season, "#ffffff")

            for i in range(self.pile_cols - 1):
                h = self.snow_pile[i]
                if h > 0.4:
                    x1 = i * self.pile_step
                    self.canvas.create_rectangle(
                        x1, tb_top - h, x1 + self.pile_step + 1, tb_top + 2,
                        fill=pile_color, outline=""
                    )

        if self.cursor_sparkle.get():
            pt = wintypes.POINT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                if abs(pt.x - self.last_mouse[0]) + abs(pt.y - self.last_mouse[1]) > 3:
                    spark_colors = {
                        "winter": ["#ffffff", "#bae6fd", "#7dd3fc"],
                        "spring": ["#86efac", "#f9a8d4", "#fef08a"],
                        "summer": ["#fef08a", "#fde047", "#bef264"],
                        "autumn": ["#fb923c", "#facc15", "#f87171"],
                    }[season]
                    self.trail_sparks.append({
                        "x": pt.x + random.uniform(-4, 4),
                        "y": pt.y + random.uniform(-4, 4),
                        "vx": random.uniform(-0.8, 0.8),
                        "vy": random.uniform(0.4, 1.5),
                        "life": 14,
                        "color": random.choice(spark_colors),
                    })
                self.last_mouse = (pt.x, pt.y)

            alive_sparks = []
            for sp in self.trail_sparks:
                sp["x"] += sp["vx"]
                sp["y"] += sp["vy"]
                sp["life"] -= 1
                if sp["life"] > 0:
                    sz = max(1.2, sp["life"] * 0.25)
                    self.canvas.create_oval(
                        sp["x"] - sz, sp["y"] - sz, sp["x"] + sz, sp["y"] + sz,
                        fill=sp["color"], outline=""
                    )
                    alive_sparks.append(sp)
            self.trail_sparks = alive_sparks

        if self.garland_enabled.get():
            self._draw_garlands()

        self.root.after(16, self._loop_animation)

    def _draw_particle(self, p: dict, season: str):
        x, y, r = p["x"], p["y"], p["r"]
        color = p["color"]

        if season == "winter":
            shape = p["shape"]
            if shape == "circle":
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")
            elif shape == "star":
                self.canvas.create_line(x - r * 1.3, y, x + r * 1.3, y, fill=color, width=1.5)
                self.canvas.create_line(x, y - r * 1.3, x, y + r * 1.3, fill=color, width=1.5)
                d = r * 0.85
                self.canvas.create_line(x - d, y - d, x + d, y + d, fill=color, width=1)
                self.canvas.create_line(x - d, y + d, x + d, y - d, fill=color, width=1)
            else:
                for k in range(3):
                    ang = p["angle"] + k * (math.pi / 3)
                    dx = math.cos(ang) * (r * 1.35)
                    dy = math.sin(ang) * (r * 1.35)
                    self.canvas.create_line(x - dx, y - dy, x + dx, y + dy, fill=color, width=1.4)

        elif season in ("spring", "autumn"):
            ang = p["angle"]
            dx, dy = math.cos(ang) * (r * 1.5), math.sin(ang) * (r * 1.5)
            px, py = -math.sin(ang) * (r * 0.75), math.cos(ang) * (r * 0.75)
            self.canvas.create_polygon(
                [x + dx, y + dy, x + px, y + py, x - dx, y - dy, x - px, y - py],
                fill=color,
                outline="",
            )

        elif season == "summer":
            rr = r * (0.6 + 0.4 * math.sin(p["phase"] * 2.5))
            self.canvas.create_oval(x - rr, y - rr, x + rr, y + rr, fill=color, outline="")

    def _draw_garlands(self):
        palettes = {
            "classic": ["#ff3b3b", "#22c55e", "#3b82f6", "#facc15", "#e879f9"],
            "warm": ["#fef08a", "#fde047", "#fdba74", "#fed7aa", "#fef9c3"],
            "cyber": ["#f43f5e", "#d946ef", "#8b5cf6", "#06b6d4", "#22d3ee"],
            "ice": ["#ffffff", "#e0f2fe", "#7dd3fc", "#38bdf8", "#bae6fd"],
        }
        colors = palettes.get(self.garland_palette.get(), palettes["classic"])
        mode = self.garland_mode.get()
        spacing = self.garland_density.get()

        target_hwnds = (
            [self.active_hwnd]
            if self.garland_target.get() == "active" and self.active_hwnd in self.tracked_windows
            else list(self.tracked_windows.keys())
        )

        for hwnd in target_hwnds:
            rect = get_window_real_rect(hwnd)
            if not rect:
                continue
            left, top, right, bottom = rect
            if left < -10000 or bottom <= top or right - left < 120:
                continue

            left_c = max(0, left)
            right_c = min(self.screen_w, right)
            if right_c - left_c < 90:
                continue

            bulb_xs = list(range(left_c + 18, right_c - 16, spacing))
            if len(bulb_xs) < 2:
                continue

            wire_pts = []
            for idx, bx in enumerate(bulb_xs):
                wire_pts.extend([bx, top + 2])
                if idx < len(bulb_xs) - 1:
                    wire_pts.extend([(bx + bulb_xs[idx + 1]) / 2, top + 7])

            self.canvas.create_line(*wire_pts, fill="#1f2430", width=2, smooth=True)

            for idx, bx in enumerate(bulb_xs):
                base_col = colors[idx % len(colors)]
                is_lit = True
                if mode == "wave":
                    is_lit = ((idx + self.blink_step) % 3) != 0
                elif mode == "twinkle":
                    is_lit = ((idx * 7 + self.blink_step) % 4) != 0
                elif mode == "neon":
                    is_lit = ((idx - self.blink_step) % len(colors)) == 0

                self.canvas.create_rectangle(
                    bx - 2.5, top + 1, bx + 2.5, top + 5, fill="#2d3343", outline=""
                )
                if is_lit:
                    self.canvas.create_oval(
                        bx - 8, top + 4, bx + 8, top + 20,
                        fill=base_col, stipple="gray25", outline=""
                    )
                    self.canvas.create_oval(
                        bx - 4.5, top + 5, bx + 4.5, top + 17,
                        fill=base_col, outline="#111827", width=1
                    )
                    self.canvas.create_oval(
                        bx - 2, top + 7, bx, top + 11, fill="#ffffff", outline=""
                    )
                else:
                    self.canvas.create_oval(
                        bx - 4, top + 5, bx + 4, top + 16,
                        fill="#334155", outline="#1e293b", width=1
                    )

    def quit_app(self):
        try:
            if getattr(self, "_hook", None):
                user32.UnhookWinEvent(self._hook)
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    app = SeasonsGarlandStudio()
    app.root.mainloop()
