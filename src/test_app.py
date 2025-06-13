#!/usr/bin/env python3
"""
Test script for No Ping functionality
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.background import BackgroundService

def main():
    """Test the application functionality"""
    # Configure logging to show debug messages
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("noping_test.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting test run...")
        
        # Start background service
        service = BackgroundService()
        
        # Print instructions
        print("\nNo Ping Test Instructions:")
        print("1. Look for the system tray icon (blue circle with 'NP')")
        print("2. You should see a notification that No Ping is running")
        print("3. Right-click the icon to see the menu")
        print("4. Launch any Steam game to test game detection")
        print("5. Press Ctrl+C to exit\n")
        
        # Run the service
        service.run()
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Error during test: {e}")
        sys.exit(1)
    finally:
        logger.info("Test complete")
        sys.exit(0)

if __name__ == "__main__":
    main() 