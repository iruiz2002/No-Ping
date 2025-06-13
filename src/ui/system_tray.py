"""
System Tray Module
Provides system tray integration for background operation
"""

import os
import sys
import pystray
from PIL import Image
import threading
from typing import Callable, Optional
import logging

class SystemTray:
    def __init__(self, on_start: Callable, on_stop: Callable):
        """Initialize system tray icon"""
        self.logger = logging.getLogger(__name__)
        self.on_start = on_start
        self.on_stop = on_stop
        self.is_running = False
        self.auto_mode = True
        
        # Create a default icon (you can replace this with your own icon)
        icon_size = 64
        icon_image = Image.new('RGB', (icon_size, icon_size), 'blue')
        
        # Create system tray icon
        self.icon = pystray.Icon(
            "No Ping",
            icon_image,
            "No Ping - Game Network Optimizer",
            self._create_menu()
        )
        
    def _create_menu(self):
        """Create system tray menu"""
        return pystray.Menu(
            pystray.MenuItem(
                "Auto-Mode",
                self._toggle_auto_mode,
                checked=lambda item: self.auto_mode
            ),
            pystray.MenuItem(
                "Manual Optimization",
                self._toggle_optimization,
                checked=lambda item: self.is_running
            ),
            pystray.MenuItem(
                "Exit",
                self._quit_app
            )
        )
        
    def _toggle_auto_mode(self):
        """Toggle auto-mode on/off"""
        try:
            self.auto_mode = not self.auto_mode
            self.logger.info(f"Auto-mode {'enabled' if self.auto_mode else 'disabled'}")
            
            # Stop optimization when disabling auto-mode
            if not self.auto_mode and self.is_running:
                self._toggle_optimization()
                
        except Exception as e:
            self.logger.error(f"Error toggling auto-mode: {e}")
        
    def _toggle_optimization(self):
        """Toggle optimization on/off"""
        try:
            if not self.is_running:
                self.on_start()
                self.is_running = True
                self.logger.info("Optimization started")
            else:
                self.on_stop()
                self.is_running = False
                self.logger.info("Optimization stopped")
        except Exception as e:
            self.logger.error(f"Error toggling optimization: {e}")
            
    def _quit_app(self):
        """Quit the application"""
        try:
            if self.is_running:
                self.on_stop()
            self.icon.stop()
        except Exception as e:
            self.logger.error(f"Error quitting app: {e}")
            
    def run(self):
        """Run the system tray icon"""
        self.icon.run() 