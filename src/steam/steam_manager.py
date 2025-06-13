"""
Steam Integration Module
Handles Steam game detection and server information
"""

import os
import vdf
import json
import logging
from typing import Dict, List, Optional, Tuple
import re
import time
import threading
from pathlib import Path
import psutil
import requests
from threading import Event

class SteamManager:
    def __init__(self):
        """Initialize Steam manager"""
        self.logger = logging.getLogger(__name__)
        self.steam_path = self._find_steam_path()
        self.installed_games = {}
        self.current_game: Optional[Dict] = None
        self.current_server: Optional[Dict] = None
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_monitoring = Event()
        self.on_server_change = None
        self._last_log_check = 0
        self._log_check_interval = 5  # Check logs every 5 seconds
        self._last_log_size = 0
        self._current_log_file = None
        
    def _find_steam_path(self) -> str:
        """Find Steam installation directory"""
        possible_paths = [
            "C:\\Program Files (x86)\\Steam",
            "C:\\Program Files\\Steam",
            os.path.expanduser("~\\Steam"),
            os.path.expanduser("~\\.steam\\steam")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"Found Steam installation at: {path}")
                return path
                
        self.logger.warning("Steam installation not found")
        return ""

    def get_installed_games(self) -> Dict[str, Dict]:
        """Get list of installed games"""
        if not self.steam_path:
            return {}
            
        try:
            # Read Steam's libraryfolders.vdf
            library_file = os.path.join(self.steam_path, "steamapps", "libraryfolders.vdf")
            if not os.path.exists(library_file):
                self.logger.error(f"Library file not found: {library_file}")
                return {}
                
            with open(library_file, 'r', encoding='utf-8') as f:
                library_data = vdf.load(f)
                
            games = {}
            # Parse library folders
            for library in library_data.get('libraryfolders', {}).values():
                if isinstance(library, dict):
                    apps = library.get('apps', {})
                    for app_id in apps:
                        manifest_path = os.path.join(
                            library.get('path', ''),
                            'steamapps',
                            f'appmanifest_{app_id}.acf'
                        )
                        if os.path.exists(manifest_path):
                            with open(manifest_path, 'r', encoding='utf-8') as f:
                                manifest = vdf.load(f)
                                app_data = manifest.get('AppState', {})
                                
                                # Get additional game info
                                game_info = self._get_game_info(app_id)
                                
                                games[app_data.get('name', '')] = {
                                    'app_id': app_id,
                                    'install_dir': app_data.get('installdir', ''),
                                    'launch_options': app_data.get('LaunchOptions', ''),
                                    'server_log_pattern': game_info.get('server_log_pattern', ''),
                                    'server_regions': game_info.get('server_regions', []),
                                    'network_ports': game_info.get('network_ports', []),
                                    'log_dir': self._find_game_log_dir(app_data.get('installdir', ''), app_id)
                                }
            
            self.installed_games = games
            self.logger.info(f"Found {len(games)} installed games")
            return games
            
        except Exception as e:
            self.logger.error(f"Error reading Steam games: {e}")
            return {}

    def _get_game_info(self, app_id: str) -> Dict:
        """Get additional game information from Steam API"""
        try:
            # Try to get game info from Steam API
            response = requests.get(f"https://store.steampowered.com/api/appdetails?appids={app_id}")
            if response.status_code == 200:
                data = response.json()
                if data and data.get(str(app_id), {}).get('success', False):
                    game_data = data[str(app_id)]['data']
                    return {
                        'server_regions': self._extract_regions_from_description(game_data.get('detailed_description', '')),
                        'network_ports': self._get_network_ports(app_id),
                        'server_log_pattern': self._get_server_log_pattern(app_id)
                    }
        except:
            pass
        return {}

    def _extract_regions_from_description(self, description: str) -> List[str]:
        """Extract server regions from game description"""
        region_patterns = [
            r'(?:servers?|regions?) (?:in|:)?\s*(?:the)?\s*((?:North|South|East|West|Central|Southeast|Northeast)?\s*(?:America|Asia|Europe|US|EU|NA|SA|SEA|OCE|JP|KR))',
            r'((?:NA|EU|AS|SA|OCE|SEA|JP|KR))\s*servers?'
        ]
        
        regions = set()
        for pattern in region_patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE)
            regions.update(match.group(1).strip() for match in matches)
        
        return list(regions)

    def _get_network_ports(self, app_id: int) -> List[int]:
        """Get network ports used by a game"""
        # Common game ports for popular games
        common_ports = {
            730: [27015, 27016, 27017, 27018, 27019, 27020],  # CS:GO
            570: [27015, 27016, 27017, 27018, 27019, 27020],  # Dota 2
            440: [27015, 27016, 27017, 27018, 27019, 27020],  # Team Fortress 2
            252490: [28015, 28016, 28017],  # Rust
            346110: [27015, 27016, 7777, 7778],  # ARK
            4000: [27015, 27016, 27017],  # Garry's Mod
            1938090: [7777, 7778, 7779],  # Ready or Not
            1172470: [7777, 7778, 7779],  # Apex Legends
            359550: [27015, 27016, 27017],  # Rainbow Six Siege
            1599340: [27015, 27016, 27017],  # Lost Ark
            2583530: [7000, 7001, 7002, 7003, 7004, 7005]  # Marvel Rivals
        }
        
        return common_ports.get(app_id, [27015])  # Default to common Source engine port

    def _get_server_log_pattern(self, app_id: int) -> str:
        """Get log pattern for server detection"""
        patterns = {
            2583530: r"Selected Region:\s*([A-Z]+)",  # Marvel Rivals
            730: r"Connected to \[(A-Za-z]+\]",  # CS:GO
            570: r"Connected to \[(A-Za-z]+\]",  # Dota 2
            1172470: r"Net_ParseConnectionString:\s+([A-Za-z0-9\-\.]+)"  # Apex Legends
        }
        return patterns.get(app_id, r"")

    def _find_game_log_dir(self, install_dir: str, app_id: str) -> Optional[str]:
        """Find game's log directory"""
        common_log_paths = [
            "logs",
            "log",
            "game/logs",
            "game/log",
            "Saved/Logs",
            f"{install_dir}/logs",
            f"{install_dir}/log",
            os.path.join(self.steam_path, "logs")
        ]
        
        for path in common_log_paths:
            full_path = os.path.join(self.steam_path, "steamapps/common", path)
            if os.path.exists(full_path):
                return full_path
                
        return None

    def start_server_monitoring(self, on_server_change=None):
        """Start monitoring for server changes"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
            
        self.on_server_change = on_server_change
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(target=self._monitor_server_changes)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

    def stop_server_monitoring(self):
        """Stop server monitoring"""
        self.stop_monitoring.set()
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1)
            self.monitoring_thread = None

    def _monitor_server_changes(self):
        """Monitor for server changes in game logs"""
        while not self.stop_monitoring.is_set():
            try:
                if self.current_game:
                    current_time = time.time()
                    
                    # Only check logs periodically
                    if current_time - self._last_log_check >= self._log_check_interval:
                        new_server = self._detect_current_server()
                        if new_server and new_server != self.current_server:
                            self.current_server = new_server
                            if self.on_server_change:
                                self.on_server_change(new_server)
                        self._last_log_check = current_time
                        
            except Exception as e:
                self.logger.error(f"Error monitoring server changes: {e}")
            
            # Use event-based waiting instead of sleep
            self.stop_monitoring.wait(timeout=1)

    def _detect_current_server(self) -> Optional[Dict]:
        """Detect current game server"""
        if not self.current_game:
            return None
            
        try:
            # Get log directory
            log_dir = self.current_game.get('log_dir')
            if not log_dir:
                return None
                
            # Find most recent log file
            log_files = list(Path(log_dir).glob("*.log"))
            if not log_files:
                return None
                
            latest_log = max(log_files, key=os.path.getmtime)
            
            # Only read the file if it's changed
            current_size = os.path.getsize(latest_log)
            if (self._current_log_file != latest_log or 
                current_size != self._last_log_size):
                
                # Get pattern for this game
                pattern = self.current_game.get('server_log_pattern')
                if not pattern:
                    return None
                    
                # Read only the new portion of the file
                with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                    if self._current_log_file != latest_log:
                        # New file, read last few lines
                        f.seek(max(0, current_size - 8192))  # Read last 8KB
                        lines = f.readlines()[-100:]  # Last 100 lines
                    else:
                        # Same file, read only new content
                        f.seek(self._last_log_size)
                        lines = f.readlines()
                
                self._current_log_file = latest_log
                self._last_log_size = current_size
                
                # Look for server information
                for line in reversed(lines):
                    match = re.search(pattern, line)
                    if match:
                        return {
                            'region': match.group(1),
                            'timestamp': time.time()
                        }
                    
        except Exception as e:
            self.logger.error(f"Error detecting server: {e}")
            
        return None

    def set_current_game(self, game_name: str):
        """Set the current game being monitored"""
        if game_name in self.installed_games:
            self.current_game = self.installed_games[game_name]
            self.current_server = None
            return True
        return False

    def get_server_regions(self) -> List[str]:
        """Get list of available server regions"""
        return [
            "US East",
            "US West",
            "Europe",
            "Asia",
            "Australia",
            "South America",
            "South Africa"
        ]

    def get_current_server(self) -> Optional[Dict]:
        """Get current server information"""
        return self.current_server 