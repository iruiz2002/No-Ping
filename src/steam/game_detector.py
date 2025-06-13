"""
Game Detector Module
Automatically detects running Steam games
"""

import psutil
import time
import logging
import os
from typing import Optional, Dict, Callable
import threading

class GameDetector:
    # Steam's internal processes to ignore
    IGNORE_PROCESSES = {
        'steam.exe',
        'steamservice.exe',
        'steamwebhelper.exe',
        'GameOverlayUI.exe',
        'Steam.exe',
        'cef.win7x64.exe',
        'steamclean.exe'
    }

    def __init__(self, steam_path: str, on_game_launched: Callable[[str], None], on_game_closed: Callable[[], None]):
        """Initialize game detector"""
        self.logger = logging.getLogger(__name__)
        self.steam_path = steam_path
        self.on_game_launched = on_game_launched
        self.on_game_closed = on_game_closed
        self.current_game: Optional[str] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        
    def _is_steam_game(self, process: psutil.Process) -> bool:
        """Check if a process is a Steam game"""
        try:
            if not process.exe():
                return False
                
            # Skip Steam's internal processes
            if process.name().lower() in self.IGNORE_PROCESSES:
                return False
                
            # Check if process is from Steam directory
            exe_path = process.exe().lower()
            steam_path = self.steam_path.lower()
            
            # Check if it's in the Steam directory and specifically in the common or steamapps directory
            return (steam_path in exe_path and 
                   ('common' in exe_path or 'steamapps' in exe_path))
                   
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
            
    def _get_game_name(self, process: psutil.Process) -> Optional[str]:
        """Get game name from process"""
        try:
            # Get the executable path
            exe_path = process.exe()
            if not exe_path:
                return None
                
            # Get the directory structure
            path_parts = exe_path.lower().split(os.sep)
            
            # Find 'common' or 'steamapps' directory index
            try:
                common_idx = path_parts.index('common')
                if common_idx + 1 < len(path_parts):
                    return path_parts[common_idx + 1].title()
            except ValueError:
                pass
                
            try:
                steamapps_idx = path_parts.index('steamapps')
                if steamapps_idx + 2 < len(path_parts):
                    return path_parts[steamapps_idx + 2].title()
            except ValueError:
                pass
                
            # Fallback: Get parent directory name
            parent_dir = os.path.basename(os.path.dirname(exe_path))
            if parent_dir and parent_dir.lower() not in ['bin', 'binaries', 'win64', 'win32']:
                return parent_dir.title()
                
            # Last resort: use process name
            return process.name().replace('.exe', '').title()
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
            
    def _monitor_games(self):
        """Monitor for Steam games"""
        self.logger.info("Starting game detection...")
        
        while self.is_running:
            try:
                # Look for Steam games in running processes
                found_game = False
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        if proc.exe():  # Only check processes with valid executables
                            self.logger.debug(f"Checking process: {proc.name()} ({proc.exe()})")
                            if self._is_steam_game(proc):
                                game_name = self._get_game_name(proc)
                                if game_name:
                                    found_game = True
                                    if self.current_game != game_name:
                                        self.logger.info(f"Detected game: {game_name}")
                                        self.current_game = game_name
                                        self.on_game_launched(game_name)
                                    break
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
                # If no game is running but we had one before
                if not found_game and self.current_game:
                    self.logger.info(f"Game closed: {self.current_game}")
                    self.current_game = None
                    self.on_game_closed()
                    
                # Sleep to prevent high CPU usage
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Error monitoring games: {e}")
                time.sleep(2)
                
    def start(self):
        """Start game detection"""
        if self.is_running:
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_games)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """Stop game detection"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None 