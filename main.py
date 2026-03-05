import sys
import os
import threading
import logging
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QStackedWidget
from PyQt6.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal

import config

# 載入後端 API 模組
from backend.hardware_collector import HardwareCollector
from backend.spotify_client import SpotifyClient
from backend.weather_client import WeatherClient

# 載入前端 UI 模組
from ui.panels.clock_panel import ClockPanel
from ui.tabs.performance_tab import PerformanceTab
from ui.tabs.weather_tab import WeatherTab
from ui.tabs.spotify_tab import SpotifyTab


# ==========================================
# BACKGROUND WORKERS (確保 UI 不卡頓)
# ==========================================
class HardwareWorker(QThread):
    data_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.collector = HardwareCollector()

    def run(self):
        stats = self.collector.fetch_system_stats()
        self.data_updated.emit(stats)


class SpotifyWorker(QThread):
    data_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.client = SpotifyClient()

    def run(self):
        data = self.client.fetch_current_playback()
        self.data_updated.emit(data)


class FullWeatherWorker(QThread):
    data_updated = pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.client = WeatherClient()

    def run(self):
        data = self.client.fetch_full_weather()
        if "error" not in data or not data["error"]:
            code = data.get("current", {}).get("code", -1)
            data["condition_desc"] = self.client.get_weather_desc(code)
        self.data_updated.emit(data)

# ==========================================
# MAIN DASHBOARD WINDOW
# ==========================================
class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("Dashboard")

        # 為了支援左右手勢滑動
        self.swipe_start_pos = QPoint()

        self._setup_window()
        self._setup_ui()
        self._start_background_tasks()

    def _handle_tab_swipe(self, direction):
        current_index = self.right_stack.currentIndex()
        max_index = self.right_stack.count() - 1

        if direction == -1 and current_index < max_index:
            self.right_stack.setCurrentIndex(current_index + 1)
        elif direction == 1 and current_index > 0:
            self.right_stack.setCurrentIndex(current_index - 1)

    def _setup_window(self):
        """set the window to 1920x480"""
        self.setWindowTitle("Smart Dashboard")
        self.setFixedSize(1920, 480)
        self.setObjectName("Dashboard")
        self.setStyleSheet("#Dashboard { background-color: #202020; }")

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

    def _force_spotify_update(self):
        self.logger.info("Forcing immediate Spotify API update because track ended.")
        self.sp_worker.start()
        self.sp_timer.start(5000)

    def _handle_next_track(self):
        self.logger.info("Executing Next Track...")
        threading.Thread(target=self.sp_worker.client.next_track).start()
        QTimer.singleShot(500, self._force_spotify_update)

    def _handle_prev_track(self):
        self.logger.info("Executing Previous Track...")
        threading.Thread(target=self.sp_worker.client.previous_track).start()
        QTimer.singleShot(500, self._force_spotify_update)

    def _handle_toggle_playback(self):
        if self.spotify_tab.is_playing:
            self.logger.info("Executing Play...")
            threading.Thread(target=self.sp_worker.client.start_playback).start()
        else:
            self.logger.info("Executing Pause...")
            threading.Thread(target=self.sp_worker.client.pause_playback).start()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        self.clock_panel = ClockPanel()
        main_layout.addWidget(self.clock_panel)

        self.perf_tab = PerformanceTab()
        self.weather_tab = WeatherTab()
        self.spotify_tab = SpotifyTab()

        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(self.perf_tab)
        self.right_stack.addWidget(self.weather_tab)
        self.right_stack.addWidget(self.spotify_tab)

        self.weather_tab.swipe_horizontal.connect(self._handle_tab_swipe)

        main_layout.addWidget(self.right_stack)


        # 將積木依序加入堆疊 (Index 0: 效能, Index 1: 天氣, Index 2: 音樂)
        self.right_stack.addWidget(self.perf_tab)
        self.right_stack.addWidget(self.weather_tab)
        self.right_stack.addWidget(self.spotify_tab)

        main_layout.addWidget(self.right_stack)

    def _start_background_tasks(self):
        """啟動所有背景資料抓取任務"""
        # --- 硬體監控 (每 2 秒更新一次) ---
        self.hw_worker = HardwareWorker()
        self.hw_worker.data_updated.connect(self.perf_tab.update_ui)
        self.hw_timer = QTimer(self)
        self.hw_timer.timeout.connect(self.hw_worker.start)
        self.hw_timer.start(2000)
        self.hw_worker.start()  # 立即觸發第一次

        # --- Spotify 狀態 (每 5 秒更新一次) ---
        self.sp_worker = SpotifyWorker()
        self.sp_worker.data_updated.connect(self.spotify_tab.update_ui)
        self.sp_timer = QTimer(self)
        self.sp_timer.timeout.connect(self.sp_worker.start)
        self.sp_timer.start(5000)
        self.sp_worker.start()  # 立即觸發第一次
        self.spotify_tab.track_ended.connect(self._force_spotify_update)
        self.spotify_tab.next_track.connect(self._handle_next_track)
        self.spotify_tab.prev_track.connect(self._handle_prev_track)
        self.spotify_tab.toggle_playback.connect(self._handle_toggle_playback)

        self.weather_worker = FullWeatherWorker()
        self.weather_worker.data_updated.connect(self.weather_tab.update_ui)
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.weather_worker.start)
        self.weather_timer.start(900000)
        self.weather_worker.start()  # 立即觸發第一次

    # ==========================================
    # GESTURE CONTROLS (左右滑動切換面板)
    # ==========================================
    def mousePressEvent(self, event):
        self.swipe_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        diff_x = event.pos().x() - self.swipe_start_pos.x()

        # 設定滑動閾值，避免誤觸 (大於 100px 才算滑動)
        current_index = self.right_stack.currentIndex()
        max_index = self.right_stack.count() - 1

        if diff_x < -100:
            # 往左滑 (Swipe Left) -> 下一頁
            if current_index < max_index:
                self.right_stack.setCurrentIndex(current_index + 1)
        elif diff_x > 100:
            # 往右滑 (Swipe Right) -> 上一頁
            if current_index > 0:
                self.right_stack.setCurrentIndex(current_index - 1)

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


if __name__ == "__main__":
    LOG_LEVEL = logging.INFO if getattr(config, 'DEBUG', 0) == 1 else logging.WARNING
    logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')

    app = QApplication(sys.path)


    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())