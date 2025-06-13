#!/usr/bin/env python3
"""
No Ping - Main Entry Point
A network optimization tool for reducing game latency
"""

import os
import sys
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.network.packet_handler import PacketHandler
from src.vpn.vpn_manager import VPNManager
from src.ui.main_window import MainWindow

def main():
    """Main entry point of the application"""
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize components
        vpn_manager = VPNManager()
        packet_handler = PacketHandler()
        
        # Start UI
        app = MainWindow(vpn_manager, packet_handler)
        app.run()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 