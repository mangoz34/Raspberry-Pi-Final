import sys
import os
import logging
import config
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer, QDateTime, Qt, QThread, pyqtSignal, QVariantAnimation, QRect, QRectF
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor, QPen

# Dynamically add the project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from backend.weather_client import WeatherClient


class WeatherWorker(QThread):
    weather_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.client = WeatherClient()

    def run(self):
        data = self.client.fetch_current_weather()
        data['icon'] = self.client.get_weather_icon(data.get('weather_code', -1))
        self.weather_updated.emit(data)


class FlipDigit(QWidget):
    """
    An animated custom widget that simulates a mechanical flip clock.
    """

    def __init__(self, text="00"):
        super().__init__()
        self.setFixedSize(150, 155)

        self.current_text = text
        self.next_text = text
        self.anim_progress = 0.0
        self.is_animating = False

        self.animation = QVariantAnimation(self)
        self.animation.setDuration(400)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.valueChanged.connect(self._on_anim_step)
        self.animation.finished.connect(self._on_anim_finished)

    def set_text(self, text):
        if self.current_text != text and not self.is_animating:
            self.next_text = text
            self.is_animating = True
            self.animation.start()

    def _on_anim_step(self, value):
        self.anim_progress = value
        self.update()

    def _on_anim_finished(self):
        self.is_animating = False
        self.current_text = self.next_text
        self.anim_progress = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        mid_y = h // 2

        if not self.is_animating:
            self._draw_half(painter, self.current_text, is_top=True, scale=1.0)
            self._draw_half(painter, self.current_text, is_top=False, scale=1.0)
        else:
            self._draw_half(painter, self.next_text, is_top=True, scale=1.0)
            self._draw_half(painter, self.current_text, is_top=False, scale=1.0)

            if self.anim_progress < 0.5:
                scale = 1.0 - (self.anim_progress * 2)
                self._draw_half(painter, self.current_text, is_top=True, scale=scale)
            else:
                scale = (self.anim_progress - 0.5) * 2
                self._draw_half(painter, self.next_text, is_top=False, scale=scale)

        # 畫中間分割線
        painter.setPen(QPen(QColor("#121212"), 3))
        # painter.setPen(QPen(QColor(255, 255, 255, 80), 2))
        painter.drawLine(0, mid_y, w, mid_y)
        painter.end()

    def _draw_half(self, painter, text, is_top, scale):
        painter.save()
        w = self.width()
        h = self.height()
        mid_y = h // 2

        if is_top:
            clip_rect = QRect(0, 0, w, mid_y)
        else:
            clip_rect = QRect(0, mid_y, w, h - mid_y)
        painter.setClipRect(clip_rect)

        painter.translate(0, mid_y)
        painter.scale(1.0, scale)
        painter.translate(0, -mid_y)

        painter.setBrush(QColor(44, 44, 46, 100))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 12, 12)

        painter.setPen(QColor("#E0E0E0"))
        painter.setFont(QFont("Arial", 105, QFont.Weight.Bold))
        painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()


class ClockPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(770)
        self.logger = logging.getLogger("ClockPanel")

        # 🎯 1. 新增：在初始化時只讀取一次圖片並放入記憶體
        self.raw_bg_pixmap = None
        self.cached_bg_pixmap = None
        self._load_background_image()

        self._setup_ui()

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        self.weather_worker = WeatherWorker()
        self.weather_worker.weather_updated.connect(self._update_weather_ui)

        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.weather_worker.start)
        self.weather_timer.start(900000)

        self.weather_worker.start()

    def _load_background_image(self):
        if getattr(config, 'SET_BACKGROUND_IMAGE', 0) == 1:
            img_name = getattr(config, 'BACKGROUND_IMAGE_PATH', 'assets/clock_bg.png')
            img_path = os.path.join(BASE_DIR, img_name)

            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                self.raw_bg_pixmap = pixmap
            else:
                self.logger.error(f"Cannot load background image from: {img_path}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.raw_bg_pixmap and not self.raw_bg_pixmap.isNull():
            self.cached_bg_pixmap = self.raw_bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QLabel { background: transparent; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 60, 40, 40)
        main_layout.addStretch(1)

        # --- TIME ROW ---
        time_layout = QHBoxLayout()
        time_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_layout.setSpacing(15)

        current = QDateTime.currentDateTime()
        self.hour_card = FlipDigit(current.toString("HH"))
        self.minute_card = FlipDigit(current.toString("mm"))
        self.second_card = FlipDigit(current.toString("ss"))

        def create_colon():
            lbl = QLabel(":")
            lbl.setFont(QFont("Arial", 75, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #E0E0E0;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setContentsMargins(0, 0, 0, 15)
            return lbl

        time_layout.addWidget(self.hour_card)
        time_layout.addWidget(create_colon())
        time_layout.addWidget(self.minute_card)
        time_layout.addWidget(create_colon())
        time_layout.addWidget(self.second_card)

        main_layout.addLayout(time_layout)
        main_layout.addStretch(1)

        # --- BOTTOM ROW ---
        bottom_layout = QHBoxLayout()

        self.date_label = QLabel(current.toString("ddd, MMM d"))
        self.date_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.date_label.setStyleSheet("color: #E0E0E0;")
        bottom_layout.addWidget(self.date_label, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)

        bottom_layout.addStretch(1)

        self.weather_label = QLabel("Locating... ☁️ --°C")
        self.weather_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.weather_label.setStyleSheet("color: #E0E0E0;")
        bottom_layout.addWidget(self.weather_label,
                                alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(bottom_layout)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 20, 20)
        painter.setClipPath(path)

        # 直接從記憶體拿出處理好的 cached_bg_pixmap 來畫
        if getattr(config, 'SET_BACKGROUND_IMAGE', 0) == 1 and self.cached_bg_pixmap:
            x_offset = (self.cached_bg_pixmap.width() - self.width()) // 2
            y_offset = (self.cached_bg_pixmap.height() - self.height()) // 2

            # 將記憶體中的圖片畫上去 (耗時接近 0 毫秒)
            painter.drawPixmap(0, 0, self.cached_bg_pixmap, x_offset, y_offset, self.width(), self.height())

            # 疊加半透明遮罩
            painter.fillPath(path, QColor(0, 0, 0, 0))
        else:
            painter.fillPath(path, QColor("#121212"))

    def _update_clock(self):
        current = QDateTime.currentDateTime()
        self.hour_card.set_text(current.toString("HH"))
        self.minute_card.set_text(current.toString("mm"))
        self.second_card.set_text(current.toString("ss"))
        self.date_label.setText(current.toString("ddd, MMM d"))

    def _update_weather_ui(self, data):
        if data.get("error"):
            self.logger.warning(f"Weather update failed: {data['error']}")
            self.weather_label.setText("Offline ☁️ --°C")
            return

        temp = data.get("temp", "--")
        icon = data.get("icon", "☁️")
        city = data.get("city", "Unknown")
        self.weather_label.setText(f"{city}  {icon} {temp}°C")


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.path)
    window = ClockPanel()
    window.resize(770, 480)
    window.show()
    sys.exit(app.exec())