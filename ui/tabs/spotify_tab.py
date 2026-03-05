import sys
import os
import logging
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtGui import QPixmap, QFont, QPainter, QPainterPath
# 🎯 補上了 QEvent 和 QPoint 方便處理手勢
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QEvent, QPoint
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest

# Dynamically add the project root to sys.path so we can import config.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import config

LOG_LEVEL = logging.INFO if getattr(config, 'DEBUG', 0) == 1 else logging.WARNING
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class SpotifyTab(QWidget):
    # 🎯 新增控制相關的訊號，用來發送給 main.py 執行真實的 API 呼叫
    track_ended = pyqtSignal()
    next_track = pyqtSignal()
    prev_track = pyqtSignal()
    toggle_playback = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("SpotifyTab")
        self.current_cover_url = ""

        # 播放狀態變數
        self.current_progress_ms = 0
        self.current_duration_ms = 0
        self.is_playing = False

        # 紀錄觸控位置的變數
        self.touch_start_pos = None

        # 非同步下載圖片管理器
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._on_image_downloaded)

        self._setup_ui()

        # 建立本地進度計時器 (每 1000ms 跑一次)
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self._increment_progress)

    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "SpotifyTab { background-color: #121212; border-radius: 20px; } QLabel { background: transparent; }")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(40, 20, 40, 40)
        main_layout.setSpacing(50)

        # --- Left Side: Album Cover (Smart Touch Zone) ---
        self.cover_label = QLabel(self)
        self.cover_label.setFixedSize(400, 400)
        self.cover_label.setStyleSheet("background-color: #282828; border-radius: 20px;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setText("No Cover")

        self.cover_label.installEventFilter(self)

        main_layout.addWidget(self.cover_label)

        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        right_layout.setSpacing(10)

        self.track_label = QLabel("Waiting for Spotify...", self)
        self.track_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        self.track_label.setStyleSheet("color: white;")
        self.track_label.setWordWrap(True)
        right_layout.addWidget(self.track_label)

        right_layout.addSpacing(20)

        self.artist_label = QLabel("Artist\n\nAlbum", self)
        self.artist_label.setFont(QFont("Arial", 24))
        self.artist_label.setStyleSheet("color: #B3B3B3; line-height: 1.0;")
        right_layout.addWidget(self.artist_label)

        right_layout.addSpacing(60)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #535353;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 5px;
            }
        """)
        right_layout.addWidget(self.progress_bar)

        self.time_label = QLabel("0:00 / 0:00", self)
        self.time_label.setFont(QFont("Arial", 16))
        self.time_label.setStyleSheet("color: #B3B3B3;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(self.time_label)

        main_layout.addLayout(right_layout)
        self.logo_label = QLabel(self)

        logo_path = os.path.join(BASE_DIR, "assets", "spotify_logo.png")
        logo_pixmap = QPixmap(logo_path)

        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaled(
                50, 50,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(scaled_logo)
        else:
            self.logger.warning(f"找不到 Spotify Logo 圖片: {logo_path}")
            self.logo_label.setText("Spotify")
            self.logo_label.setStyleSheet("color: #1DB954; font-weight: bold; font-size: 24px;")

        self.logo_label.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 🎯 鎖定在右上角：X 座標 = 總寬度 - Logo寬度 - 右邊距(40)
        # Y 座標 = 上邊距(30)
        if hasattr(self, 'logo_label'):
            x_pos = self.width() - self.logo_label.width() - 40
            y_pos = 30
            self.logo_label.move(x_pos, y_pos)

    def eventFilter(self, source, event):
        if source == self.cover_label:
            if event.type() == QEvent.Type.MouseButtonPress:
                self.touch_start_pos = event.pos()
                return True

            elif event.type() == QEvent.Type.MouseButtonRelease and self.touch_start_pos is not None:
                diff_x = event.pos().x() - self.touch_start_pos.x()
                diff_y = event.pos().y() - self.touch_start_pos.y()

                # 判斷是否為滑動 (X軸位移大於 50 像素)
                if abs(diff_x) > 50:
                    if diff_x > 0:
                        self.logger.info("Swipe Right on Cover -> Next Track")
                        self.prev_track.emit()  # 右滑下一首
                    else:
                        self.logger.info("Swipe Left on Cover -> Prev Track")
                        self.next_track.emit()

                # 判斷是否為單純點擊 (位移極小)
                elif abs(diff_x) < 10 and abs(diff_y) < 10:
                    self.logger.info("Tapped on Cover -> Toggle Playback")

                    # 💡 本地先行：立刻反轉播放狀態並控制進度條，不用等 API
                    self.is_playing = not self.is_playing
                    if self.is_playing:
                        self.progress_timer.start(1000)
                    else:
                        self.progress_timer.stop()

                    self.toggle_playback.emit()  # 通知後端真的去暫停/播放

                self.touch_start_pos = None
                return True

        return super().eventFilter(source, event)

    def _increment_progress(self):
        if self.is_playing:
            self.current_progress_ms += 1000
            if self.current_progress_ms >= self.current_duration_ms:
                self.current_progress_ms = self.current_duration_ms
                self.is_playing = False
                self.progress_timer.stop()
                self.logger.info("Track ended locally. Requesting immediate update...")
                self.track_ended.emit()
            self._update_progress_bar_ui()

    def _update_progress_bar_ui(self):
        if self.current_duration_ms > 0:
            self.progress_bar.setMaximum(self.current_duration_ms)
            self.progress_bar.setValue(self.current_progress_ms)

            cur_min, cur_sec = divmod(self.current_progress_ms // 1000, 60)
            dur_min, dur_sec = divmod(self.current_duration_ms // 1000, 60)
            self.time_label.setText(f"{cur_min}:{cur_sec:02d} / {dur_min}:{dur_sec:02d}")

    def update_ui(self, data: dict):
        if "error" in data and data["error"]:
            self.track_label.setText("Spotify Offline")
            self.artist_label.setText(data["error"])
            self.is_playing = False
            self.progress_timer.stop()
            return

        self.track_label.setText(data.get("track_name", "Unknown Track"))
        artist = data.get("artist_name", "Unknown Artist")
        album = data.get("album_name", "Unknown Album")
        self.artist_label.setText(f"{artist}\n\n{album}")

        self.is_playing = data.get("is_playing", False)
        self.current_progress_ms = data.get("progress_ms", 0)
        self.current_duration_ms = data.get("duration_ms", 1)

        self._update_progress_bar_ui()

        if self.is_playing and not self.progress_timer.isActive():
            self.progress_timer.start(1000)
        elif not self.is_playing:
            self.progress_timer.stop()

        new_url = data.get("cover_url", "")
        if new_url and new_url != self.current_cover_url:
            self._load_image_from_url(new_url)
            self.current_cover_url = new_url

    def _load_image_from_url(self, url: str):
        if url:
            self.network_manager.get(QNetworkRequest(QUrl(url)))

    def _get_rounded_pixmap(self, pixmap: QPixmap, radius: int = 15) -> QPixmap:
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded

    def _on_image_downloaded(self, reply):
        if reply.error() == reply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            scaled_pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            rounded_pixmap = self._get_rounded_pixmap(scaled_pixmap, 15)
            self.cover_label.setPixmap(rounded_pixmap)
        reply.deleteLater()


# --- Unit Test Block ---
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.path)
    window = SpotifyTab()
    window.resize(1150, 480)
    window.show()

    dummy_data = {
        "track_name": "Bohemian Rhapsody",
        "artist_name": "Queen",
        "album_name": "A Night at the Opera",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273e8b066f70c206551210d902b",
        "progress_ms": 150000,
        "duration_ms": 354000,
        "is_playing": True,
        "error": None
    }

    window.update_ui(dummy_data)
    sys.exit(app.exec())