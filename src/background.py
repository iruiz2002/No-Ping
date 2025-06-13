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
import signal
import time

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.network.packet_handler import PacketHandler
from src.vpn.vpn_manager import VPNManager
from src.steam.steam_manager import SteamManager
from src.steam.game_detector import GameDetector
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
        
        # Initialize game detector
        self.game_detector = GameDetector(
            steam_path=self.steam_manager.steam_path,
            on_game_launched=self._on_game_launched,
            on_game_closed=self._on_game_closed
        )
        
        # Create system tray
        self.tray = None
        self.init_system_tray()
        
        # State
        self.auto_mode = False
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
    def init_system_tray(self, max_retries=3):
        """Initialize system tray with retries"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                if self.tray:
                    try:
                        self.tray.stop()
                    except:
                        pass
                
                self.tray = SystemTray(
                    on_start=self.start_optimization,
                    on_stop=self.stop_optimization
                )
                self.tray.run()
                return True
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Failed to initialize system tray (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(1)  # Wait before retrying
                
        self.logger.error("Failed to initialize system tray after all retries")
        return False
        
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("Shutdown signal received")
        self.stop()
        
    def _load_settings(self) -> dict:
        """Load settings from file"""
        settings_file = "settings.json"
        default_settings = {
            "preferred_server": "US East",
            "last_game": None,
            "auto_mode": True  # Enable auto-mode by default
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
            
    def _get_game_data(self, game_name: str) -> Optional[dict]:
        """Get game data from Steam"""
        games = self.steam_manager.get_installed_games()
        
        # Try exact match
        if game_name in games:
            return {
                "name": game_name,
                "data": games[game_name]
            }
            
        # Try case-insensitive match
        game_name_lower = game_name.lower()
        for name, data in games.items():
            if name.lower() == game_name_lower:
                return {
                    "name": name,
                    "data": data
                }
                
        return None
        
    def _on_game_launched(self, game_name: str):
        """Handle game launch event"""
        if not self.settings.get("auto_mode", True):
            return
            
        self.logger.info(f"Game launched: {game_name}")
        self.start_optimization(game_name)
        
    def _on_game_closed(self):
        """Handle game close event"""
        if not self.settings.get("auto_mode", True):
            return
            
        self.logger.info("Game closed")
        self.stop_optimization()
        
    def start_optimization(self, game_name: Optional[str] = None):
        """Start network optimization"""
        try:
            # Get game data
            if game_name:
                game = self._get_game_data(game_name)
            else:
                # Use last game or first available
                games = self.steam_manager.get_installed_games()
                if self.settings["last_game"] and self.settings["last_game"] in games:
                    game = {
                        "name": self.settings["last_game"],
                        "data": games[self.settings["last_game"]]
                    }
                elif games:
                    game_name = next(iter(games))
                    game = {
                        "name": game_name,
                        "data": games[game_name]
                    }
                else:
                    game = None
                    
            if not game:
                self.logger.error("No game selected")
                return
                
            # Get game ports
            app_id = int(game["data"].get('app_id', 0))
            if not app_id:
                self.logger.error("Invalid game ID")
                return
                
            ports = self.steam_manager.get_game_ports(app_id)
            
            # Connect to VPN and get optimal routes
            server = self.settings["preferred_server"]
            if self.vpn_manager.connect(server):
                # Get optimal routes
                routes = self.vpn_manager.get_optimal_routes(server)
                if routes:
                    self.logger.info(f"Using optimal routes: {routes}")
                    # Start packet capture with optimization
                    self.packet_handler.start_capture(ports, target_ips=routes)
                else:
                    # Fallback to basic capture
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
        
        try:
            # Start game detection
            if self.settings.get("auto_mode", True):
                self.game_detector.start()
                self.logger.info("Auto-mode enabled")
                
            # Keep the main thread alive
            while self.running:
                # Check if system tray is working
                if not self.tray or not self.tray.thread or not self.tray.thread.is_alive():
                    self.logger.warning("System tray not running, attempting to reinitialize...")
                    if not self.init_system_tray():
                        self.logger.error("Failed to reinitialize system tray")
                        break
                time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error in background service: {e}")
        finally:
            self.stop()
            
    def stop(self):
        """Stop the background service"""
        self.running = False
        
        # Stop all components
        self.game_detector.stop()
        self.stop_optimization()
        if self.tray:
            self.tray.stop()
        
        self.logger.info("Background service stopped")

if __name__ == "__main__":
    service = BackgroundService()
    service.run() 