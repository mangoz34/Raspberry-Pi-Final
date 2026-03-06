import os
import sys
import time
import logging
import platform
import psutil
import socket

# Dynamically add the project root to sys.path so we can import config.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import config

# Configure the global logger based on config.py
LOG_LEVEL = logging.INFO if getattr(config, 'DEBUG', 0) == 1 else logging.WARNING
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class HardwareCollector:
    def __init__(self):
        """
        Initialize the HardwareCollector.
        Detects the OS to provide mock data on Mac and real data on Raspberry Pi.
        """
        self.logger = logging.getLogger("HardwareCollector")
        self.is_linux = platform.system() == "Linux"

        # Variables for network speed calculation
        self.last_net_time = time.time()
        self.last_net_io = psutil.net_io_counters()

        if getattr(config, 'DEBUG', 0) == 1:
            os_name = "Linux (Raspberry Pi)" if self.is_linux else "Darwin (Mac OS / Mock Mode)"
            self.logger.info(f"HardwareCollector initialized. Running on: {os_name}")

    def _get_cpu_temperature(self):
        """
        Read CPU temperature from Linux sysfs. Returns a mock value on Mac.
        """
        if not self.is_linux:
            return 45.5  # Mock temperature for Mac

        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_millicelsius = int(f.read().strip())
                return temp_millicelsius / 1000.0
        except Exception as e:
            self.logger.warning(f"Failed to read CPU temperature: {e}")
            return 0.0

    def _get_cpu_frequency(self):
        """
        Read current CPU frequency in MHz from Linux sysfs. Returns a mock value on Mac.
        """
        if not self.is_linux:
            return 2400.0  # Mock frequency in MHz for Mac

        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "r") as f:
                freq_khz = int(f.read().strip())
                return freq_khz / 1000.0
        except Exception as e:
            self.logger.warning(f"Failed to read CPU frequency: {e}")
            return 0.0

    def _get_network_speed(self):
        """
        Calculate network TX/RX speed in KB/s.
        """
        current_time = time.time()
        current_net_io = psutil.net_io_counters()

        time_delta = current_time - self.last_net_time
        if time_delta <= 0:
            time_delta = 1.0  # Prevent division by zero

        # Calculate bytes per second, then convert to KB/s
        tx_speed = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / time_delta / 1024.0
        rx_speed = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / time_delta / 1024.0

        # Update state for the next calculation
        self.last_net_time = current_time
        self.last_net_io = current_net_io

        return round(tx_speed, 2), round(rx_speed, 2)

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def fetch_system_stats(self):
        """
        Fetch all hardware statistics and return them as a standardized dictionary for UI.
        """
        tx_kbps, rx_kbps = self._get_network_speed()
        ip_address = self.get_ip_address()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        stats = {
            "cpu_usage_percent": psutil.cpu_percent(interval=None),
            "cpu_temp_c": round(self._get_cpu_temperature(), 1),
            "cpu_freq_mhz": round(self._get_cpu_frequency(), 0),
            "mem_usage_percent": mem.percent,
            "mem_used_gb": round(mem.used / (1024 ** 3), 2),
            "mem_total_gb": round(mem.total / (1024 ** 3), 2),
            "disk_usage_percent": disk.percent,
            "ip_address": ip_address,
            "disk_used_gb": round(disk.used / (1024 ** 3), 1),
            "disk_total_gb": round(disk.total / (1024 ** 3), 1),
            "net_tx_kbps": tx_kbps,
            "net_rx_kbps": rx_kbps
        }

        if getattr(config, 'DEBUG', 0) == 1:
            self.logger.info(f"System Stats Fetched: CPU={stats['cpu_usage_percent']}% Temp={stats['cpu_temp_c']}C")

        return stats


# Unit test block
if __name__ == '__main__':
    collector = HardwareCollector()
    print("--- Testing fetch_system_stats ---")

    # Run a few times to see the network speed calculation and CPU usage changes
    for i in range(3):
        print(f"\nSample {i + 1}:")
        stats = collector.fetch_system_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        time.sleep(1)  # Wait 1 second before next sample