"""
Test script for server detection with performance optimization
"""

import logging
import psutil
import os
from src.steam.steam_manager import SteamManager
import time
from threading import Event

def get_process_cpu_usage(pid):
    try:
        process = psutil.Process(pid)
        return process.cpu_percent(interval=None)
    except:
        return 0.0

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # Initialize Steam manager
    logger.info("Initializing Steam manager...")
    sm = SteamManager()
    
    # Get installed games
    games = sm.get_installed_games()
    logger.info(f"Found {len(games)} installed games")
    
    # Find Marvel Rivals (case insensitive)
    target_game = None
    for game_name in games:
        if 'marvel' in game_name.lower() and 'rivals' in game_name.lower():
            target_game = game_name
            break
    
    # Define callback for server changes
    def on_server_change(server):
        logger.info(f"Server changed to: {server}")
        logger.info(f"Current server info: {sm.get_current_server()}")
    
    # Set Marvel Rivals as current game
    if target_game:
        logger.info(f"Found game: {target_game}")
        logger.info(f"Game info: {games[target_game]}")
        
        logger.info("Setting Marvel Rivals as current game")
        sm.set_current_game(target_game)
        
        # Start monitoring with reduced polling
        logger.info("Starting server monitoring (optimized)...")
        sm.start_server_monitoring(on_server_change)
        
        stop_event = Event()
        current_pid = os.getpid()
        last_cpu_log = time.time()
        CPU_LOG_INTERVAL = 10  # Log CPU usage every 10 seconds
        
        try:
            while not stop_event.is_set():
                current_time = time.time()
                
                # Log CPU usage periodically
                if current_time - last_cpu_log >= CPU_LOG_INTERVAL:
                    cpu_usage = get_process_cpu_usage(current_pid)
                    logger.info(f"Monitor CPU usage: {cpu_usage:.1f}%")
                    last_cpu_log = current_time
                
                current_server = sm.get_current_server()
                if current_server:
                    logger.info(f"Current server: {current_server}")
                
                # Use event-based waiting instead of busy polling
                stop_event.wait(timeout=10)  # Check every 10 seconds instead of 5
                
        except KeyboardInterrupt:
            logger.info("Stopping monitoring...")
            sm.stop_server_monitoring()
            stop_event.set()
    else:
        logger.error("Marvel Rivals not found in installed games")
        logger.info("Available games:")
        for game in games:
            logger.info(f"- {game}")

if __name__ == "__main__":
    main() 