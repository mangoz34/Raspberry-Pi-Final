import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import sys
import logging

# Dynamically add the project root to sys.path so we can import config.py
# This ensures the script works whether run from root or directly from the backend folder.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import config

# Configure the global logger based on config.py
LOG_LEVEL = logging.INFO if getattr(config, 'DEBUG', 0) == 1 else logging.WARNING
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class SpotifyClient:
    def __init__(self, base_dir=None):
        """
        Initialize the Spotify API client.
        """
        self.logger = logging.getLogger("SpotifyClient")
        self.base_dir = base_dir if base_dir else BASE_DIR

        if getattr(config, 'DEBUG', 0) == 1:
            self.logger.info("Debug mode enabled. SpotifyClient initializing...")

        secret_path = os.path.join(self.base_dir, '__secret_key__')
        creds = self._parse_key_value_file(secret_path)

        if not creds:
            self.logger.error("Failed to load credentials. SpotifyClient initialization aborted.")
            self.sp = None
            return

        try:
            # Establish Spotify connection object
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=creds.get('ClientID'),
                client_secret=creds.get('ClientSecret'),
                redirect_uri='http://127.0.0.1:8888/callback',
                scope='user-read-playback-state user-read-currently-playing user-modify-playback-state'
            ))
            self.logger.info("Spotify API authorization initialized successfully.")
        except Exception as e:
            self.logger.error(f"Error during Spotify API authorization: {e}")
            self.sp = None

    def _parse_key_value_file(self, file_path):
        """
        Helper method to parse simple key=value text files for secrets.
        """
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip() or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        data[key.strip()] = value.strip().strip("'").strip('"')
            return data
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            return {}

    def fetch_current_playback(self):
        """
        Fetch the current playback status and return a standardized dictionary for UI consumption.
        """
        if not self.sp:
            self.logger.warning("API not initialized. Cannot fetch playback.")
            return {"error": "API not initialized. Please check credentials."}

        try:
            current_track = self.sp.current_user_playing_track()

            if current_track and current_track.get('item'):
                item = current_track['item']

                # Handle edge cases where images might be missing
                images = item.get('album', {}).get('images', [])
                cover_url = images[0]['url'] if images else ""

                result = {
                    "is_playing": current_track.get('is_playing', False),
                    "track_name": item.get('name', 'Unknown Track'),
                    "artist_name": item['artists'][0]['name'] if item.get('artists') else 'Unknown Artist',
                    "album_name": item.get('album', {}).get('name', 'Unknown Album'),
                    "cover_url": cover_url,
                    "progress_ms": current_track.get('progress_ms', 0),
                    "duration_ms": item.get('duration_ms', 0),
                    "error": None
                }
                self.logger.info(f"Successfully fetched playback: {result['track_name']} by {result['artist_name']}")
                return result
            else:
                self.logger.info("No track is currently playing.")
                return {
                    "is_playing": False,
                    "error": "No track is currently playing."
                }

        except spotipy.exceptions.SpotifyException as e:
            self.logger.warning(f"Spotify API exception: {e}")
            return {"error": "API connection issue or rate limit reached."}

        except Exception as e:
            self.logger.error(f"Unexpected network or data extraction error: {e}")
            return {"error": "Network connection interrupted."}

    def start_playback(self):
        try:
            self.sp.start_playback()
            return True
        except Exception as e:
            self.logger.error(f"Failed to play: {e}")
            return False

    def pause_playback(self):
        try:
            self.sp.pause_playback()
            return True
        except Exception as e:
            self.logger.error(f"Failed to pause: {e}")
            return False

    def next_track(self):
        try:
            self.sp.next_track()
            return True
        except Exception as e:
            self.logger.error(f"Failed to skip to next: {e}")
            return False

    def previous_track(self):
        try:
            self.sp.previous_track()
            return True
        except Exception as e:
            self.logger.error(f"Failed to skip to previous: {e}")
            return False


# Unit test block
if __name__ == '__main__':
    client = SpotifyClient()
    print("--- Testing fetch_current_playback ---")
    result = client.fetch_current_playback()
    for key, value in result.items():
        print(f"{key}: {value}")