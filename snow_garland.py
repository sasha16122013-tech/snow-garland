import ctypes
from ctypes import wintypes
import random
import sys

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

user32 = ctypes.windll.user32


def get_active_window_rect(ignore_title: str = "Winter Vibe Settings"):
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

    # Игнорируем свёрнутые окна с координатами около -32000
    if rect.left < -10000 or rect.top < -10000:
        return None

    return (rect.left, rect.top, rect.right, rect.bottom)


class DesktopOverlay(QWidget):
    """Прозрачное окно поверх всего экрана, пропускающее клики мыши."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.screen_w = screen.width()
        self.screen_h = screen.height()
        self.taskbar_height = 48

        # Состояния переключателей
        self.enable_full_snow = False
        self.enable_taskbar_snow = False
        self.enable_garland = False

        # Частицы снега
        self.snowflakes = [self._create_flake() for _ in range(120)]
        self.taskbar_flakes = [self._create_taskbar_flake() for _ in range(70)]

        # Переменные для гирлянды
        self.active_rect = None
        self.blink_phase = 0
        self.garland_colors = [
            QColor(255, 50, 50),   # Красный
            QColor(50, 255, 100),  # Зелёный
            QColor(50, 150, 255),  # Синий
            QColor(255, 220, 50),  # Жёлтый
            QColor(220, 80, 255),  # Фиолетовый
        ]

        # Таймер анимации (~60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

        # Таймер мигания гирлянды
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.update_blink)
        self.blink_timer.start(500)

    def _create_flake(self):
        return {
            "x": random.uniform(0, self.screen_w),
            "y": random.uniform(-self.screen_h, 0),
            "r": random.uniform(2, 5),
            "speed": random.uniform(1.5, 4.0),
            "drift": random.uniform(-0.8, 0.8),
        }

    def _create_taskbar_flake(self):
        return {
            "x": random.uniform(0, self.screen_w),
            "y": random.uniform(self.screen_h - 150, self.screen_h - self.taskbar_height),
            "r": random.uniform(1.5, 3.5),
            "speed": random.uniform(0.8, 2.2),
            "drift": random.uniform(-0.5, 0.5),
        }

    def update_blink(self):
        self.blink_phase = (self.blink_phase + 1) % len(self.garland_colors)

    def update_animation(self):
        if self.enable_full_snow:
            for f in self.snowflakes:
                f["y"] += f["speed"]
                f["x"] += f["drift"]
                if f["y"] > self.screen_h:
                    f["y"] = random.uniform(-20, -5)
                    f["x"] = random.uniform(0, self.screen_w)

        if self.enable_taskbar_snow:
            for f in self.taskbar_flakes:
                f["y"] += f["speed"]
                f["x"] += f["drift"]
                if f["y"] > self.screen_h:
                    f["y"] = self.screen_h - random.uniform(90, 140)
                    f["x"] = random.uniform(0, self.screen_w)

        if self.enable_garland:
            self.active_rect = get_active_window_rect("Winter Vibe Settings")
        else:
            self.active_rect = None

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Снег по всему экрану
        if self.enable_full_snow:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 210)))
            for f in self.snowflakes:
                painter.drawEllipse(QPointF(f["x"], f["y"]), f["r"], f["r"])

        # 2. Снег на панели задач Windows
        if self.enable_taskbar_snow:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 160)))
            painter.drawRect(0, self.screen_h - self.taskbar_height, self.screen_w, 4)

            painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
            for f in self.taskbar_flakes:
                painter.drawEllipse(QPointF(f["x"], f["y"]), f["r"], f["r"])

        # 3. Гирлянда на верхней рамке активного окна
        if self.enable_garland and self.active_rect:
            left, top, right, _ = self.active_rect
            left = max(0, left)
            right = min(self.screen_w, right)
            top = max(0, top)

            if right - left > 100:
                painter.setPen(QPen(QColor(30, 30, 30, 200), 2))
                painter.drawLine(left + 10, top + 2, right - 10, top + 2)

                spacing = 35
                idx = 0
                for x in range(left + 20, right - 20, spacing):
                    color = self.garland_colors[
                        (idx + self.blink_phase) % len(self.garland_colors)
                    ]

                    glow = QColor(color)
                    glow.setAlpha(70)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(glow))
                    painter.drawEllipse(QPointF(x, top + 8), 11, 11)

                    painter.setBrush(QBrush(color))
                    painter.drawEllipse(QPointF(x, top + 8), 4.5, 6)
                    idx += 1


class ControlMenu(QWidget):
    """Окно меню с переключателями эффектов."""

    def __init__(self, overlay: DesktopOverlay):
        super().__init__()
        self.overlay = overlay
        self.setWindowTitle("Winter Vibe Settings")
        self.setFixedSize(310, 230)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLabel#title {
                font-size: 17px;
                font-weight: bold;
                color: #89b4fa;
                margin-bottom: 5px;
            }
            QCheckBox {
                spacing: 10px;
                padding: 6px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #585b70;
                background: #313244;
            }
            QCheckBox::indicator:checked {
                background: #a6e3a1;
                border-color: #a6e3a1;
            }
            QPushButton {
                background-color: #f38ba8;
                color: #11111b;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
        """)

        layout = QVBoxLayout()

        title = QLabel("❄️ Winter Desktop Vibe")
        title.setObjectName("title")
        layout.addWidget(title)

        self.cb_full_snow = QCheckBox("Снег по всему рабочему столу")
        self.cb_full_snow.toggled.connect(self.toggle_full_snow)
        layout.addWidget(self.cb_full_snow)

        self.cb_taskbar_snow = QCheckBox("Снег на панели задач (Винда)")
        self.cb_taskbar_snow.toggled.connect(self.toggle_taskbar_snow)
        layout.addWidget(self.cb_taskbar_snow)

        self.cb_garland = QCheckBox("Гирлянда на активном окне")
        self.cb_garland.toggled.connect(self.toggle_garland)
        layout.addWidget(self.cb_garland)

        btn_exit = QPushButton("Закрыть приложение")
        btn_exit.clicked.connect(QApplication.instance().quit)
        layout.addWidget(btn_exit)

        self.setLayout(layout)

    def toggle_full_snow(self, checked: bool):
        self.overlay.enable_full_snow = checked

    def toggle_taskbar_snow(self, checked: bool):
        self.overlay.enable_taskbar_snow = checked

    def toggle_garland(self, checked: bool):
        self.overlay.enable_garland = checked

    def closeEvent(self, event):
        QApplication.instance().quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = DesktopOverlay()
    overlay.show()

    menu = ControlMenu(overlay)
    menu.show()

    sys.exit(app.exec())
