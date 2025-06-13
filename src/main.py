#!/usr/bin/env python3
"""
No Ping - Main Entry Point
A network optimization tool for reducing game latency
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.background import BackgroundService

def main():
    """Main entry point of the application"""
    # Load environment variables
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("noping.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Start background service
        service = BackgroundService()
        service.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")
        sys.exit(0)

if __name__ == "__main__":
    main() 