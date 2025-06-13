"""
Steam Integration Module
Handles Steam game detection and server information
"""

import os
import vdf
import json
import logging
from typing import Dict, List, Optional

class SteamManager:
    def __init__(self):
        """Initialize Steam manager"""
        self.logger = logging.getLogger(__name__)
        self.steam_path = self._find_steam_path()
        self.installed_games = {}
        
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
        """Get list of installed Steam games"""
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
                                games[app_data.get('name', '')] = {
                                    'app_id': app_id,
                                    'install_dir': app_data.get('installdir', ''),
                                    'launch_options': app_data.get('LaunchOptions', '')
                                }
            
            self.installed_games = games
            self.logger.info(f"Found {len(games)} installed games")
            return games
            
        except Exception as e:
            self.logger.error(f"Error reading Steam games: {e}")
            return {}

    def get_game_ports(self, app_id: int) -> List[int]:
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
            1599340: [27015, 27016, 27017]  # Lost Ark
        }
        
        return common_ports.get(app_id, [27015])  # Default to common Source engine port

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