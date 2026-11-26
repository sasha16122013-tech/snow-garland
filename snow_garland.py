import ctypes
from ctypes import wintypes
import random
import tkinter as tk

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
LWA_COLORKEY = 0x00000001

TRANSPARENT_KEY = "#010203"


def get_active_window_rect(ignore_title: str = "Winter Vibe"):
    """Возвращает координаты (left, top, right, bottom) активного окна через Windows API."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd or not user32.IsWindowVisible(hwnd):
        return None

    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value

    if not title or title == ignore_title:
        return None

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None

    if rect.left < -10000 or rect.top < -10000:
        return None

    return (rect.left, rect.top, rect.right, rect.bottom)


class SnowGarlandApp:
    """Приложение на стандартном tkinter без внешних зависимостей."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Winter Vibe")
        self.root.geometry("310x215+120+120")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        # Состояния переключателей
        self.full_snow_var = tk.BooleanVar(value=False)
        self.taskbar_snow_var = tk.BooleanVar(value=False)
        self.garland_var = tk.BooleanVar(value=False)

        self._build_menu()

        # Создаём прозрачное оверлей-окно поверх всего экрана
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg=TRANSPARENT_KEY)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.taskbar_height = 48
        self.overlay.geometry(f"{self.screen_w}x{self.screen_h}+0+0")

        self.canvas = tk.Canvas(
            self.overlay,
            width=self.screen_w,
            height=self.screen_h,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Делаем фон прозрачным по color-key и пропускаем клики мыши сквозь оверлей
        self.overlay.update_idletasks()
        self._apply_click_through()

        # Частицы снега
        self.snowflakes = [self._make_flake(taskbar=False) for _ in range(110)]
        self.taskbar_flakes = [self._make_flake(taskbar=True) for _ in range(65)]

        self.blink_phase = 0
        self.garland_colors = ["#ff3b3b", "#38ff7a", "#3b9eff", "#ffd83b", "#d95cff"]

        self._tick_animation()
        self._tick_blink()

    def _apply_click_through(self):
        """Настраивает прозрачность фона и пропуск кликов через WinAPI."""
        hwnd = user32.GetParent(self.overlay.winfo_id())
        if not hwnd:
            hwnd = self.overlay.winfo_id()

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        new_style = (
            ex_style
            | WS_EX_LAYERED
            | WS_EX_TRANSPARENT
            | WS_EX_TOPMOST
            | WS_EX_TOOLWINDOW
        )
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

        # Преобразуем HEX-цвет #RRGGBB в COLORREF (0x00BBGGRR)
        r = int(TRANSPARENT_KEY[1:3], 16)
        g = int(TRANSPARENT_KEY[3:5], 16)
        b = int(TRANSPARENT_KEY[5:7], 16)
        color_ref = (b << 16) | (g << 8) | r
        user32.SetLayeredWindowAttributes(hwnd, color_ref, 0, LWA_COLORKEY)

    def _build_menu(self):
        title_lbl = tk.Label(
            self.root,
            text="❄️ Winter Desktop Vibe",
            bg="#1e1e2e",
            fg="#89b4fa",
            font=("Segoe UI", 14, "bold"),
        )
        title_lbl.pack(anchor="w", padx=16, pady=(14, 8))

        chk_opts = {
            "bg": "#1e1e2e",
            "fg": "#cdd6f4",
            "selectcolor": "#313244",
            "activebackground": "#1e1e2e",
            "activeforeground": "#ffffff",
            "font": ("Segoe UI", 11),
            "bd": 0,
            "highlightthickness": 0,
        }

        tk.Checkbutton(
            self.root,
            text="Снег по всему рабочему столу",
            variable=self.full_snow_var,
            **chk_opts,
        ).pack(anchor="w", padx=16, pady=4)

        tk.Checkbutton(
            self.root,
            text="Снег на панели задач (Винда)",
            variable=self.taskbar_snow_var,
            **chk_opts,
        ).pack(anchor="w", padx=16, pady=4)

        tk.Checkbutton(
            self.root,
            text="Гирлянда на активном окне",
            variable=self.garland_var,
            **chk_opts,
        ).pack(anchor="w", padx=16, pady=4)

        btn_exit = tk.Button(
            self.root,
            text="Закрыть приложение",
            bg="#f38ba8",
            fg="#11111b",
            activebackground="#eba0ac",
            activeforeground="#11111b",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=12,
            pady=6,
            command=self.quit_app,
        )
        btn_exit.pack(pady=(12, 10))

    def _make_flake(self, taskbar: bool):
        if taskbar:
            return {
                "x": random.uniform(0, self.screen_w),
                "y": random.uniform(self.screen_h - 140, self.screen_h - self.taskbar_height),
                "r": random.uniform(1.5, 3.2),
                "speed": random.uniform(0.9, 2.2),
                "drift": random.uniform(-0.5, 0.5),
            }
        return {
            "x": random.uniform(0, self.screen_w),
            "y": random.uniform(-self.screen_h, 0),
            "r": random.uniform(2.0, 4.5),
            "speed": random.uniform(1.5, 3.8),
            "drift": random.uniform(-0.8, 0.8),
        }

    def _tick_blink(self):
        self.blink_phase = (self.blink_phase + 1) % len(self.garland_colors)
        self.root.after(500, self._tick_blink)

    def _tick_animation(self):
        self.canvas.delete("all")

        # 1. Снег по всему экрану
        if self.full_snow_var.get():
            for f in self.snowflakes:
                f["y"] += f["speed"]
                f["x"] += f["drift"]
                if f["y"] > self.screen_h:
                    f["y"] = random.uniform(-20, -5)
                    f["x"] = random.uniform(0, self.screen_w)

                r = f["r"]
                self.canvas.create_oval(
                    f["x"] - r,
                    f["y"] - r,
                    f["x"] + r,
                    f["y"] + r,
                    fill="#ffffff",
                    outline="",
                )

        # 2. Снег на панели задач Windows
        if self.taskbar_snow_var.get():
            top_bar = self.screen_h - self.taskbar_height
            self.canvas.create_rectangle(
                0,
                top_bar,
                self.screen_w,
                top_bar + 4,
                fill="#ffffff",
                outline="",
            )
            for f in self.taskbar_flakes:
                f["y"] += f["speed"]
                f["x"] += f["drift"]
                if f["y"] > self.screen_h:
                    f["y"] = self.screen_h - random.uniform(85, 135)
                    f["x"] = random.uniform(0, self.screen_w)

                r = f["r"]
                self.canvas.create_oval(
                    f["x"] - r,
                    f["y"] - r,
                    f["x"] + r,
                    f["y"] + r,
                    fill="#ffffff",
                    outline="",
                )

        # 3. Гирлянда на активном окне
        if self.garland_var.get():
            rect = get_active_window_rect("Winter Vibe")
            if rect:
                left, top, right, _ = rect
                left = max(0, left)
                right = min(self.screen_w, right)
                top = max(0, top)

                if right - left > 100:
                    self.canvas.create_line(
                        left + 10,
                        top + 2,
                        right - 10,
                        top + 2,
                        fill="#262626",
                        width=2,
                    )
                    spacing = 35
                    idx = 0
                    for x in range(left + 20, right - 20, spacing):
                        color = self.garland_colors[
                            (idx + self.blink_phase) % len(self.garland_colors)
                        ]
                        self.canvas.create_oval(
                            x - 5,
                            top + 2,
                            x + 5,
                            top + 13,
                            fill=color,
                            outline="#1a1a1a",
                        )
                        idx += 1

        self.root.after(16, self._tick_animation)

    def quit_app(self):
        self.root.destroy()


if __name__ == "__main__":
    app = SnowGarlandApp()
    app.root.mainloop()
