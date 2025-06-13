"""
Background Service
Runs No Ping optimization in the background
"""

import os
import sys
import logging
from typing import Optional
import json
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.network.packet_handler import PacketHandler
from src.vpn.vpn_manager import VPNManager
from src.steam.steam_manager import SteamManager
from src.ui.system_tray import SystemTray

class BackgroundService:
    def __init__(self):
        """Initialize background service"""
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("noping.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables
        load_dotenv()
        
        # Initialize components
        self.vpn_manager = VPNManager()
        self.packet_handler = PacketHandler()
        self.steam_manager = SteamManager()
        
        # Load or create settings
        self.settings = self._load_settings()
        
        # Create system tray
        self.tray = SystemTray(
            on_start=self.start_optimization,
            on_stop=self.stop_optimization
        )
        
    def _load_settings(self) -> dict:
        """Load settings from file"""
        settings_file = "settings.json"
        default_settings = {
            "preferred_server": "US East",
            "last_game": None
        }
        
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            
        return default_settings
        
    def _save_settings(self):
        """Save settings to file"""
        try:
            with open("settings.json", 'w') as f:
                json.dump(self.settings, f)
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            
    def _get_active_game(self) -> Optional[dict]:
        """Get currently running Steam game"""
        games = self.steam_manager.get_installed_games()
        
        # For now, return the last used game or first available game
        if self.settings["last_game"] and self.settings["last_game"] in games:
            return {
                "name": self.settings["last_game"],
                "data": games[self.settings["last_game"]]
            }
        elif games:
            game_name = next(iter(games))
            return {
                "name": game_name,
                "data": games[game_name]
            }
            
        return None
        
    def start_optimization(self):
        """Start network optimization"""
        try:
            # Get active game
            game = self._get_active_game()
            if not game:
                self.logger.error("No game selected")
                return
                
            # Get game ports
            app_id = int(game["data"].get('app_id', 0))
            if not app_id:
                self.logger.error("Invalid game ID")
                return
                
            ports = self.steam_manager.get_game_ports(app_id)
            
            # Connect to VPN
            server = self.settings["preferred_server"]
            if self.vpn_manager.connect(server):
                # Start packet capture
                self.packet_handler.start_capture(ports)
                self.logger.info(f"Started optimization for {game['name']}")
                
                # Save settings
                self.settings["last_game"] = game["name"]
                self._save_settings()
            else:
                self.logger.error("Failed to connect to VPN")
                
        except Exception as e:
            self.logger.error(f"Error starting optimization: {e}")
            
    def stop_optimization(self):
        """Stop network optimization"""
        try:
            self.packet_handler.stop_capture()
            self.vpn_manager.disconnect()
            self.logger.info("Stopped optimization")
            
        except Exception as e:
            self.logger.error(f"Error stopping optimization: {e}")
            
    def run(self):
        """Run the background service"""
        self.logger.info("Starting No Ping background service...")
        self.tray.run()

if __name__ == "__main__":
    service = BackgroundService()
    service.run() 