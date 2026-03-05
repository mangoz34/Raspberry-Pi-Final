import sys
import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QStackedWidget)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QFont

# Dynamically add the project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import config

LOG_LEVEL = logging.INFO if getattr(config, 'DEBUG', 0) == 1 else logging.WARNING
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class WeatherTab(QWidget):

    swipe_horizontal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("WeatherTab")
        self.swipe_start_pos = QPoint()
        self._setup_ui()

    def _get_gradient_by_code(self, code):
        """根據 WMO 天氣代碼，回傳對應的高質感漸層 CSS"""
        # 晴天 (Clear)
        if code == 0:
            return "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4A90E2, stop:1 #1C5898)"
        # 多雲/起霧 (Cloudy/Fog) - 使用原本的莫蘭迪藍
        elif code in [1, 2, 3, 45, 48]:
            return "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #586E8C, stop:1 #3B4D66)"
        # 下雪 (Snow)
        elif code in [71, 73, 75, 77, 85, 86]:
            return "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7597B0, stop:1 #4E6E8A)"
        # 下雨/雷雨 (Rain/Storm)
        elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]:
            return "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2C3E50, stop:1 #1A252F)"
        # 預設 (Default)
        else:
            return "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #586E8C, stop:1 #3B4D66)"

    def _get_icon_by_code(self, code):
        """將 WMO 天氣代碼轉換為 UI 顯示的 Emoji 圖示"""
        if code == 0:
            return "☀️"
        elif code in [1, 2, 3]:
            return "⛅"
        elif code in [45, 48]:
            return "☁️"
        elif code in [51, 53, 55, 56, 57]:
            return "🌧️"
        elif code in [61, 63, 65, 66, 67]:
            return "🌧️"
        elif code in [71, 73, 75, 77]:
            return "❄️"
        elif code in [80, 81, 82]:
            return "🌦️"
        elif code in [85, 86]:
            return "❄️"
        elif code in [95, 96, 99]:
            return "⛈️"
        else:
            return "☁️"

    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("WeatherTab { background-color: #121212; border-radius: 20px; } QLabel { background: transparent; }")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 30)

        self.card_frame = QFrame()
        # 初始背景設為莫蘭迪藍
        self.card_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #586E8C, stop:1 #3B4D66);
                border-radius: 25px;
            }
        """)
        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(50, 40, 50, 30)

        # ==========================================
        # TOP SECTION: Current Weather Info
        # ==========================================
        top_layout = QHBoxLayout()

        left_info_layout = QVBoxLayout()
        self.condition_label = QLabel("Loading...")
        self.condition_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        self.condition_label.setStyleSheet("color: white; background: transparent;")

        self.details_label = QLabel("--   💧 --%")
        self.details_label.setFont(QFont("Arial", 22, QFont.Weight.Medium))
        self.details_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")

        left_info_layout.addWidget(self.condition_label)
        left_info_layout.addWidget(self.details_label)
        left_info_layout.addStretch()

        right_info_layout = QVBoxLayout()
        right_info_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        right_info_layout.setSpacing(0)

        self.current_temp_label = QLabel("--°")
        self.current_temp_label.setFont(QFont("Arial", 95, QFont.Weight.Bold))
        self.current_temp_label.setStyleSheet("color: white; background: transparent;")
        self.current_temp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        self.high_low_label = QLabel("↑ --°   ↓ --°")
        self.high_low_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.high_low_label.setStyleSheet(
            "color: rgba(255, 255, 255, 0.8); background: transparent; padding-right: 12px;")
        self.high_low_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        right_info_layout.addWidget(self.current_temp_label)
        right_info_layout.addWidget(self.high_low_label)
        right_info_layout.addStretch()

        top_layout.addLayout(left_info_layout)
        top_layout.addLayout(right_info_layout)

        card_layout.addLayout(top_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); margin-top: 20px; margin-bottom: 20px;")
        line.setFixedHeight(1)
        card_layout.addWidget(line)

        # ==========================================
        # BOTTOM SECTION: Stacked Widget for Hourly/Daily
        # ==========================================
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background: transparent;")

        # Page 0: Hourly Forecast
        self.page_hourly = QWidget()
        self.layout_hourly = QHBoxLayout(self.page_hourly)
        self.layout_hourly.setContentsMargins(0, 0, 0, 0)
        self.hourly_columns = []
        for _ in range(7):
            col_layout, lbls = self._create_forecast_column("--", "☁️", "--°", "--%")
            self.layout_hourly.addLayout(col_layout)
            self.hourly_columns.append(lbls)  # 儲存 label 參考以便日後更新
        self.stacked_widget.addWidget(self.page_hourly)

        # Page 1: Daily Forecast
        self.page_daily = QWidget()
        self.layout_daily = QHBoxLayout(self.page_daily)
        self.layout_daily.setContentsMargins(0, 0, 0, 0)
        self.daily_columns = []
        for _ in range(7):
            col_layout, lbls = self._create_forecast_column("--", "☁️", "--°", "--°")
            self.layout_daily.addLayout(col_layout)
            self.daily_columns.append(lbls)  # 儲存 label 參考以便日後更新
        self.stacked_widget.addWidget(self.page_daily)

        card_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(self.card_frame)

    def _create_forecast_column(self, title, icon, temp, subtext):
        col = QVBoxLayout()
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.setSpacing(8)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_icon = QLabel(icon)
        lbl_icon.setFont(QFont("Arial", 42))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_temp = QLabel(temp)
        lbl_temp.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        lbl_temp.setStyleSheet("color: white;")
        lbl_temp.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_sub = QLabel(subtext)
        lbl_sub.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        lbl_sub.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        col.addWidget(lbl_title)
        col.addWidget(lbl_icon)
        col.addWidget(lbl_temp)
        col.addWidget(lbl_sub)

        # 回傳 layout 以及裡面的 labels，方便後續 update_ui 更新數值
        return col, (lbl_title, lbl_icon, lbl_temp, lbl_sub)

    # ==========================================
    # DATA UPDATE LOGIC
    # ==========================================
    def update_ui(self, weather_data):
        """接收從 backend 傳來的天氣資料，動態更新所有 UI 數值與背景"""
        if "error" in weather_data and weather_data["error"]:
            self.condition_label.setText("Offline")
            return

        # --- 1. 動態切換背景漸層色 ---
        current_code = weather_data.get("current", {}).get("code", 1)
        gradient_css = self._get_gradient_by_code(current_code)
        self.card_frame.setStyleSheet(f"""
            QFrame {{
                background: {gradient_css};
                border-radius: 25px;
            }}
        """)

        # --- 2. 更新上方主要資訊 ---
        condition_text = weather_data.get("condition_desc", "Cloudy")
        city = weather_data.get("city", "Unknown")
        humidity = weather_data.get("current", {}).get("humidity", "--")
        temp = weather_data.get("current", {}).get("temp", "--")

        daily_max = weather_data.get("daily", {}).get("max", ["--"])[0]
        daily_min = weather_data.get("daily", {}).get("min", ["--"])[0]

        self.condition_label.setText(condition_text)
        self.details_label.setText(f"{city}   💧 {humidity}%")
        self.current_temp_label.setText(f"{temp}°")

        if daily_max != "--":
            self.high_low_label.setText(f"↑ {int(round(daily_max))}°   ↓ {int(round(daily_min))}°")

        # --- 3. 🎯 更新下方「每 3 小時」預報陣列 ---
        hourly_data = weather_data.get("hourly", {})
        if hourly_data and "time" in hourly_data:
            times = hourly_data["time"]
            temps = hourly_data["temp"]
            pops = hourly_data["pop"]  # 降雨機率
            codes = hourly_data["code"]

            # 智慧尋找：找出大於或等於「現在時刻」的資料點索引
            now = datetime.now()
            start_idx = 0
            for idx, t_str in enumerate(times):
                if datetime.fromisoformat(t_str) >= now:
                    start_idx = idx
                    break

            # 將 7 根柱子的 UI 依序填入 (每次跳 3 小時)
            for i in range(7):
                idx = start_idx + (i * 3)
                if idx < len(times):
                    dt = datetime.fromisoformat(times[idx])
                    hour_str = dt.strftime("%H")  # 抓取小時數字 (e.g., "12", "15")

                    # 從 init 存起來的 self.hourly_columns 取出對應的 4 個 QLabel
                    lbl_title, lbl_icon, lbl_temp, lbl_sub = self.hourly_columns[i]

                    lbl_title.setText(hour_str)
                    lbl_icon.setText(self._get_icon_by_code(codes[idx]))
                    lbl_temp.setText(f"{int(round(temps[idx]))}°")
                    lbl_sub.setText(f"{pops[idx]}%")

        # --- 4. 🎯 更新下方「未來 7 天」預報陣列 ---
        daily_data = weather_data.get("daily", {})
        if daily_data and "time" in daily_data:
            times = daily_data["time"]
            max_temps = daily_data["max"]
            min_temps = daily_data["min"]
            codes = daily_data["code"]

            # 一週預報的長度最多就是 7 天
            for i in range(min(7, len(times))):
                dt = datetime.fromisoformat(times[i])
                day_str = dt.strftime("%a")  # 抓取星期縮寫 (e.g., "Mon", "Tue")

                # 將第一天標示為「今天」
                if i == 0:
                    day_str = "Today"

                # 取出對應的 4 個 QLabel 並填值
                lbl_title, lbl_icon, lbl_temp, lbl_sub = self.daily_columns[i]

                lbl_title.setText(day_str)
                lbl_icon.setText(self._get_icon_by_code(codes[i]))
                lbl_temp.setText(f"{int(round(max_temps[i]))}°")
                lbl_sub.setText(f"{int(round(min_temps[i]))}°")

    # ==========================================
    # GESTURE CONTROLS
    # ==========================================
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.stacked_widget.setCurrentIndex(0)
        elif delta < 0:
            self.stacked_widget.setCurrentIndex(1)

    def mousePressEvent(self, event):
        self.swipe_start_pos = event.pos()

    def mouseReleaseEvent(self, event):
        end_pos = event.pos()
        diff_y = end_pos.y() - self.swipe_start_pos.y()
        diff_x = end_pos.x() - self.swipe_start_pos.x()

        # 判斷是垂直滑動還是水平滑動
        if abs(diff_y) > abs(diff_x):
            if diff_y > 50:
                self.stacked_widget.setCurrentIndex(0)
            elif diff_y < -50:
                self.stacked_widget.setCurrentIndex(1)
        else:
            if diff_x < -100:
                self.swipe_horizontal.emit(-1)  # 往左滑
            elif diff_x > 100:
                self.swipe_horizontal.emit(1)  # 往右滑


# --- Unit Test Block ---
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    import random

    app = QApplication(sys.path)
    window = WeatherTab()
    window.resize(1150, 480)
    window.show()

    # 模擬測試：每 2 秒隨機切換一種天氣狀態，讓你預覽背景顏色的變換！
    test_codes = [0, 2, 61, 71]  # 晴天, 多雲, 下雨, 下雪
    desc_map = {0: "Sunny", 2: "Cloudy", 61: "Rainy", 71: "Snowy"}


    def simulate_weather_change():
        code = random.choice(test_codes)
        mock_data = {
            "city": "Toyama",
            "condition_desc": desc_map[code],
            "current": {"temp": random.randint(5, 30), "humidity": random.randint(40, 90), "code": code},
            "daily": {"max": [random.randint(20, 30)], "min": [random.randint(5, 15)]},
            "error": None
        }
        window.update_ui(mock_data)


    timer = QTimer()
    timer.timeout.connect(simulate_weather_change)
    timer.start(2000)  # 每 2 秒跳換一次

    # 初始呼叫一次
    simulate_weather_change()

    sys.exit(app.exec())