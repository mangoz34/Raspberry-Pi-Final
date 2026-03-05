import os
import sys
import logging
import requests

# Dynamically add the project root to sys.path so we can import config.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import config

LOG_LEVEL = logging.INFO if getattr(config, 'DEBUG', 0) == 1 else logging.WARNING
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class WeatherClient:
    def __init__(self):
        self.logger = logging.getLogger("WeatherClient")
        self.city = "Unknown"
        self.lat = None
        self.lon = None

    def fetch_location_by_ip(self):
        """Fetch location details based on current public IP."""
        try:
            response = requests.get("http://ip-api.com/json/", timeout=5)
            data = response.json()
            if data.get('status') == 'success':
                self.city = data['city']
                self.lat = data['lat']
                self.lon = data['lon']
                self.logger.info(f"Location detected: {self.city} ({self.lat}, {self.lon})")
                return True
        except Exception as e:
            self.logger.error(f"Failed to detect location: {e}")
        return False

    def fetch_current_weather(self):
        """Fetch current weather using Open-Meteo."""
        # 如果還沒取得經緯度，先嘗試定位
        if self.lat is None or self.lon is None:
            if not self.fetch_location_by_ip():
                return {"error": "Location unknown"}

        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&current_weather=true"
            response = requests.get(url, timeout=5)
            data = response.json()
            current = data['current_weather']

            result = {
                "temp": int(round(current['temperature'])),
                "weather_code": current['weathercode'],  # WMO Weather code
                "city": self.city,
                "error": None
            }
            self.logger.info(f"Weather fetched: {result['temp']}°C in {self.city}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to fetch weather: {e}")
            return {"error": str(e)}

    def get_weather_icon(self, code):
        """Convert WMO weather codes to emojis for UI display."""
        if code == 0:
            return "☀️"
        elif code in [1, 2, 3]:
            return "⛅"
        elif code in [45, 48]:
            return "🌫️"
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
            return "🌡️"

    def fetch_full_weather(self):
        """Fetch current, hourly, and daily weather using Open-Meteo."""
        if self.lat is None or self.lon is None:
            if not self.fetch_location_by_ip():
                return {"error": "Location unknown"}

        try:
            # 組合出同時抓取 current, hourly, daily 的超長 API 網址
            url = (f"https://api.open-meteo.com/v1/forecast?"
                   f"latitude={self.lat}&longitude={self.lon}&"
                   f"current=temperature_2m,relative_humidity_2m,weather_code&"
                   f"hourly=temperature_2m,precipitation_probability,weather_code&"
                   f"daily=weather_code,temperature_2m_max,temperature_2m_min&"
                   f"timezone=auto")

            response = requests.get(url, timeout=5)
            data = response.json()

            # 整理回傳的字典，供 UI 直接使用
            result = {
                "city": self.city,
                "current": {
                    "temp": int(round(data['current']['temperature_2m'])),
                    "humidity": data['current']['relative_humidity_2m'],
                    "code": data['current']['weather_code'],
                },
                "hourly": {
                    "time": data['hourly']['time'],
                    "temp": data['hourly']['temperature_2m'],
                    "pop": data['hourly']['precipitation_probability'],
                    "code": data['hourly']['weather_code']
                },
                "daily": {
                    "time": data['daily']['time'],
                    "max": data['daily']['temperature_2m_max'],
                    "min": data['daily']['temperature_2m_min'],
                    "code": data['daily']['weather_code']
                },
                "error": None
            }
            self.logger.info(f"Full weather fetched for {self.city}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to fetch full weather: {e}")
            return {"error": str(e)}

    def get_weather_desc(self, code):
        """Convert WMO codes to text descriptions (like iOS Weather)."""
        if code == 0:
            return "Clear"
        elif code in [1, 2, 3]:
            return "Cloudy"
        elif code in [45, 48]:
            return "Foggy"
        elif code in [51, 53, 55, 56, 57]:
            return "Drizzle"
        elif code in [61, 63, 65, 66, 67]:
            return "Rain"
        elif code in [71, 73, 75, 77]:
            return "Snow"
        elif code in [80, 81, 82]:
            return "Showers"
        elif code in [95, 96, 99]:
            return "Thunderstorm"
        else:
            return "Unknown"


# --- Unit Test Block ---
if __name__ == "__main__":
    client = WeatherClient()
    print("Fetching location and weather...")
    result = client.fetch_current_weather()
    print(result)
    if not result.get("error"):
        print(f"Icon: {client.get_weather_icon(result['weather_code'])}")