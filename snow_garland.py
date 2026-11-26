import sys
import random
import win32gui
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QCheckBox, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont


class DesktopOverlay(QWidget):
    """Прозрачное окно поверх всего экрана, пропускающее клики."""
    def __init__(self):
        super().__init__()
        # Настройки окна: без рамок, поверх всех окон, прозрачное для кликов мыши
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Растягиваем на весь экран
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.screen_w = screen.width()
        self.screen_h = screen.height()
        self.taskbar_height = 48  # Примерная высота панели задач Win 11

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
            QColor(50, 255, 100),  # Зеленый
            QColor(50, 150, 255),  # Синий
            QColor(255, 220, 50),  # Желтый
            QColor(220, 80, 255)   # Фиолетовый
        ]

        # Таймер анимации (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

        # Таймер мигания гирлянды
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.update_blink)
        self.blink_timer.start(500)

    def _create_flake(self):
        return {
            'x': random.uniform(0, self.screen_w),
            'y': random.uniform(-self.screen_h, 0),
            'r': random.uniform(2, 5),
            'speed': random.uniform(1.5, 4.0),
            'drift': random.uniform(-0.8, 0.8)
        }

    def _create_taskbar_flake(self):
        return {
            'x': random.uniform(0, self.screen_w),
            'y': random.uniform(self.screen_h - 150, self.screen_h - self.taskbar_height),
            'r': random.uniform(1.5, 3.5),
            'speed': random.uniform(0.8, 2.2),
            'drift': random.uniform(-0.5, 0.5)
        }

    def update_blink(self):
        self.blink_phase = (self.blink_phase + 1) % len(self.garland_colors)

    def update_animation(self):
        # Обновляем снег по всему экрану
        if self.enable_full_snow:
            for f in self.snowflakes:
                f['y'] += f['speed']
                f['x'] += f['drift']
                if f['y'] > self.screen_h:
                    f['y'] = random.uniform(-20, -5)
                    f['x'] = random.uniform(0, self.screen_w)

        # Обновляем снег на панели задач
        if self.enable_taskbar_snow:
            for f in self.taskbar_flakes:
                f['y'] += f['speed']
                f['x'] += f['drift']
                if f['y'] > self.screen_h:
                    f['y'] = self.screen_h - random.uniform(90, 140)
                    f['x'] = random.uniform(0, self.screen_w)

        # Ищем координаты активного окна для гирлянды
        if self.enable_garland:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd and win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    # Не вешаем гирлянду на само меню настроек или пустой рабочий стол
                    if title and title != "Winter Vibe Settings":
                        rect = win32gui.GetWindowRect(hwnd)
                        # Игнорируем свернутые окна с координатами -32000
                        if rect[0] > -10000:
                            self.active_rect = rect
                        else:
                            self.active_rect = None
                    else:
                        self.active_rect = None
            except Exception:
                self.active_rect = None

        self.update()  # Перерисовать экран

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Рисуем снег по всему экрану
        if self.enable_full_snow:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 210)))
            for f in self.snowflakes:
                painter.drawEllipse(QPointF(f['x'], f['y']), f['r'], f['r'])

        # 2. Рисуем снег и сугроб на панели задач Windows
        if self.enable_taskbar_snow:
            painter.setPen(Qt.PenStyle.NoPen)
            # Легкий слой снега по верхнему краю панели задач
            painter.setBrush(QBrush(QColor(255, 255, 255, 160)))
            painter.drawRect(0, self.screen_h - self.taskbar_height, self.screen_w, 4)

            # Падающие снежинки в зоне панели задач
            painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
            for f in self.taskbar_flakes:
                painter.drawEllipse(QPointF(f['x'], f['y']), f['r'], f['r'])

        # 3. Рисуем гирлянду на верхней рамке активного окна
        if self.enable_garland and self.active_rect:
            left, top, right, bottom = self.active_rect
            left = max(0, left)
            right = min(self.screen_w, right)
            top = max(0, top)

            if right - left > 100:
                # Провод гирлянды
                painter.setPen(QPen(QColor(30, 30, 30, 200), 2))
                painter.drawLine(left + 10, top + 2, right - 10, top + 2)

                # Лампочки каждые 35 пикселей
                spacing = 35
                idx = 0
                for x in range(left + 20, right - 20, spacing):
                    color = self.garland_colors[(idx + self.blink_phase) % len(self.garland_colors)]
                    
                    # Свечение (ореол)
                    glow = QColor(color)
                    glow.setAlpha(70)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(glow))
                    painter.drawEllipse(QPointF(x, top + 8), 11, 11)

                    # Сама лампочка
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

        # Темная стильная тема
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

        # Чекбоксы
        self.cb_full_snow = QCheckBox("Снег по всему рабочему столу")
        self.cb_full_snow.toggled.connect(self.toggle_full_snow)
        layout.addWidget(self.cb_full_snow)

        self.cb_taskbar_snow = QCheckBox("Снег на панели задач (Винда)")
        self.cb_taskbar_snow.toggled.connect(self.toggle_taskbar_snow)
        layout.addWidget(self.cb_taskbar_snow)

        self.cb_garland = QCheckBox("Гирлянда на активном окне")
        self.cb_garland.toggled.connect(self.toggle_garland)
        layout.addWidget(self.cb_garland)

        # Кнопка выхода
        btn_exit = QPushButton("Закрыть приложение")
        btn_exit.clicked.connect(QApplication.instance().quit)
        layout.addWidget(btn_exit)

        self.setLayout(layout)

    def toggle_full_snow(self, checked):
        self.overlay.enable_full_snow = checked

    def toggle_taskbar_snow(self, checked):
        self.overlay.enable_taskbar_snow = checked

    def toggle_garland(self, checked):
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
