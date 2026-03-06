import sys
import os
import logging
import platform
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QRectF

# Dynamically add the project root to sys.path so we can import config.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import config

# Configure the global logger based on config.py
LOG_LEVEL = logging.INFO if getattr(config, 'DEBUG', 0) == 1 else logging.WARNING
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class CustomGauge(QWidget):
    """
    A custom circular gauge widget using QPainter.
    """

    def __init__(self, title="GAUGE"):
        super().__init__()
        self.setFixedSize(350, 350)
        self.title = title
        self.value = 0.0
        self.info_text = "N/A"

    def update_value(self, value, info_text):
        self.value = max(0.0, min(100.0, value))
        self.info_text = info_text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(20, 20, self.width() - 40, self.height() - 40)

        # 1. Draw Background Track (Dark Gray)
        start_angle = 225 * 16
        span_angle = -270 * 16
        pen_bg = QPen(QColor("#2A2A2A"), 20, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, start_angle, span_angle)

        # 2. Draw Value Arc (White/Light Gray)
        val_span_angle = int(-270 * (self.value / 100.0) * 16)
        pen_val = QPen(QColor("#E0E0E0"), 20, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_val)
        painter.drawArc(rect, start_angle, val_span_angle)

        # 3. Draw Text Inside the Gauge
        # Title
        painter.setPen(QColor("#888888"))
        painter.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title_rect = QRectF(rect.x(), rect.y() + 60, rect.width(), 40)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.title)

        # Main Percentage Value
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Arial", 52, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{int(self.value)}%")

        # Additional Info
        painter.setPen(QColor("#AAAAAA"))
        painter.setFont(QFont("Arial", 18, QFont.Weight.Medium))
        info_rect = QRectF(rect.x(), rect.bottom() - 80, rect.width(), 40)
        painter.drawText(info_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, self.info_text)

        painter.end()


class PerformanceTab(QWidget):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("PerformanceTab")

        if getattr(config, 'DEBUG', 0) == 1:
            self.logger.info("Initializing PerformanceTab UI components...")

        self._setup_ui()

    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("PerformanceTab { background-color: #121212; border-radius: 20px; } QLabel { background: transparent; }")

        main_layout = QHBoxLayout(self)

        main_layout.setContentsMargins(15, 80, 50, 20)
        main_layout.setSpacing(50)

        # --- Left: CPU Gauge ---
        self.cpu_gauge = CustomGauge(title="CPU CORE")
        main_layout.addWidget(self.cpu_gauge, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Center: System Information & Network ---
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setContentsMargins(30, 0, 0, 0)

        # 1. System Specifications Block
        sys_info_layout = QVBoxLayout()
        sys_info_layout.setSpacing(15)

        header_label = QLabel("SYSTEM INFORMATION")
        header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #777777; letter-spacing: 2px;")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sys_info_layout.addWidget(header_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #333333;")
        line.setFixedHeight(1)
        sys_info_layout.addWidget(line)

        self.sys_labels = {}
        specs = [
            ("BOARD", "Raspberry Pi 4B"),
            ("CPU", "Cortex-A72 (ARMv8)"),
            ("OS", f"{platform.system()} {platform.release()}"),
            ("IP", "127.0.0.1"),
            ("DISK", "0.0 GB / 0.0 GB")
        ]

        for key, default_val in specs:
            row = QHBoxLayout()

            k_lbl = QLabel(f"{key}:")
            k_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            k_lbl.setStyleSheet("color: #888888;")

            v_lbl = QLabel(default_val)
            v_lbl.setFont(QFont("Arial", 14, QFont.Weight.Medium))
            v_lbl.setStyleSheet("color: #E0E0E0;")
            v_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            row.addWidget(k_lbl)
            row.addWidget(v_lbl)
            self.sys_labels[key] = v_lbl
            sys_info_layout.addLayout(row)

        center_layout.addLayout(sys_info_layout)

        center_layout.addSpacing(15)
        net_layout = QHBoxLayout()

        def create_net_box(title, color):
            box = QVBoxLayout()
            lbl_title = QLabel(title)
            lbl_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            lbl_title.setStyleSheet("color: #777777;")
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_val = QLabel("0.0")
            lbl_val.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            lbl_val.setStyleSheet(f"color: {color};")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

            box.addWidget(lbl_title)
            box.addWidget(lbl_val)
            return box, lbl_val

        tx_box, self.tx_label = create_net_box("NET TX (KB/s)", "#E0E0E0")
        rx_box, self.rx_label = create_net_box("NET RX (KB/s)", "#E0E0E0")

        net_layout.addLayout(tx_box)

        v_line = QFrame()
        v_line.setFrameShape(QFrame.Shape.VLine)
        v_line.setStyleSheet("background-color: #333333;")
        v_line.setFixedWidth(1)
        net_layout.addWidget(v_line)

        net_layout.addLayout(rx_box)
        center_layout.addLayout(net_layout)

        main_layout.addLayout(center_layout)

        # --- Right: RAM Gauge ---
        self.ram_gauge = CustomGauge(title="MEMORY")
        main_layout.addWidget(self.ram_gauge, alignment=Qt.AlignmentFlag.AlignCenter)

    def update_ui(self, stats: dict):
        cpu_usage = stats.get("cpu_usage_percent", 0.0)
        cpu_temp = stats.get("cpu_temp_c", 0.0)
        cpu_freq = stats.get("cpu_freq_mhz", 0.0) / 1000.0
        cpu_info = f"{cpu_temp} °C  |  {cpu_freq:.1f} GHz"
        self.cpu_gauge.update_value(cpu_usage, cpu_info)

        mem_usage = stats.get("mem_usage_percent", 0.0)
        mem_used = stats.get("mem_used_gb", 0.0)
        mem_total = stats.get("mem_total_gb", 0.0)
        mem_info = f"{mem_used:.1f} GB / {mem_total:.1f} GB"
        self.ram_gauge.update_value(mem_usage, mem_info)

        self.tx_label.setText(f"{stats.get('net_tx_kbps', 0.0):.1f}")
        self.rx_label.setText(f"{stats.get('net_rx_kbps', 0.0):.1f}")

        if "disk_used_gb" in stats and "disk_total_gb" in stats:
            self.sys_labels["DISK"].setText(f"{stats['disk_used_gb']:.1f} GB / {stats['disk_total_gb']:.1f} GB")

        if "ip_address" in stats:
            self.sys_labels["IP"].setText(stats["ip_address"])


# --- Unit Test Block ---
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    import random

    app = QApplication(sys.path)
    window = PerformanceTab()
    window.resize(1150, 480)
    window.show()


    def simulate_data():
        dummy_stats = {
            "cpu_usage_percent": random.uniform(20.0, 85.0),
            "cpu_temp_c": round(random.uniform(40.0, 65.0), 1),
            "cpu_freq_mhz": random.choice([1500, 1800, 2400]),
            "mem_usage_percent": random.uniform(40.0, 60.0),
            "mem_used_gb": random.uniform(2.5, 4.5),
            "mem_total_gb": 8.0,
            "disk_used_gb": 12.4,
            "disk_total_gb": 32.0,
            "net_tx_kbps": random.uniform(10.0, 150.0),
            "net_rx_kbps": random.uniform(50.0, 800.0),
            "ip_address": "192.168.1.105"
        }
        window.update_ui(dummy_stats)


    timer = QTimer()
    timer.timeout.connect(simulate_data)
    timer.start(1000)

    sys.exit(app.exec())