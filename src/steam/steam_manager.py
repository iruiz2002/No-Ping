"""
Steam Integration Module
Handles Steam game detection and server information
"""

import os
import vdf
import logging
from typing import Dict, List, Optional
from steam.client import SteamClient
from steam.core.msg import MsgProto
from steam.enums.emsg import EMsg

class SteamManager:
    def __init__(self):
        """Initialize Steam manager"""
        self.client = SteamClient()
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
            return games
            
        except Exception as e:
            self.logger.error(f"Error reading Steam games: {e}")
            return {}

    def get_server_list(self, app_id: int) -> List[Dict]:
        """Get server list for a specific game"""
        try:
            if not self.client.logged_on:
                self.client.anonymous_login()
                
            # Request server list
            message = MsgProto(EMsg.ClientGMSServerQuery)
            message.body.app_id = app_id
            message.body.geo_location_ip = 0
            message.body.region_code = 0
            
            response = self.client.send_message_and_wait(message, EMsg.ClientGMSServerQueryResponse)
            
            servers = []
            if response and hasattr(response.body, 'servers'):
                for server in response.body.servers:
                    servers.append({
                        'addr': server.server_ip,
                        'port': server.server_port,
                        'region': server.region
                    })
                    
            return servers
            
        except Exception as e:
            self.logger.error(f"Error getting server list: {e}")
            return []

    def get_game_ports(self, app_id: int) -> List[int]:
        """Get network ports used by a game"""
        # Common game ports
        common_ports = {
            730: [27015, 27016, 27017, 27018, 27019, 27020],  # CS:GO
            570: [27015, 27016, 27017, 27018, 27019, 27020],  # Dota 2
            440: [27015, 27016, 27017, 27018, 27019, 27020],  # Team Fortress 2
        }
        
        return common_ports.get(app_id, [27015])  # Default to common Source engine port

    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.client and self.client.logged_on:
            self.client.logout() 