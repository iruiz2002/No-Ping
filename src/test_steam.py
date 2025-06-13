"""
Test script for Steam integration
"""

import os
import sys
import logging

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.steam.steam_manager import SteamManager

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Create Steam manager
    logger.info("Initializing Steam manager...")
    steam = SteamManager()

    # Get Steam path
    logger.info(f"Steam path: {steam.steam_path}")

    # Get installed games
    logger.info("\nGetting installed games...")
    games = steam.get_installed_games()
    
    if not games:
        logger.warning("No Steam games found!")
        return

    # Print game information
    for game_name, game_data in games.items():
        logger.info(f"\nGame: {game_name}")
        logger.info(f"App ID: {game_data.get('app_id')}")
        logger.info(f"Install Directory: {game_data.get('install_dir')}")
        
        # Get game ports
        app_id = int(game_data.get('app_id', 0))
        if app_id:
            ports = steam.get_game_ports(app_id)
            logger.info(f"Game Ports: {ports}")

    # Print available server regions
    logger.info("\nAvailable server regions:")
    for region in steam.get_server_regions():
        logger.info(f"- {region}")

if __name__ == "__main__":
    main() 