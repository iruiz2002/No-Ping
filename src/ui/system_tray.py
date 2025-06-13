"""
System Tray Module
Provides system tray integration for background operation
"""

import os
import sys
import pystray
from PIL import Image, ImageDraw
import threading
from typing import Callable, Optional
import logging
import tempfile
import time

class SystemTray:
    def __init__(self, on_start: Callable, on_stop: Callable):
        """Initialize system tray icon"""
        self.logger = logging.getLogger(__name__)
        self.on_start = on_start
        self.on_stop = on_stop
        self.is_running = False
        self.auto_mode = True
        self.icon = None
        self.thread = None
        self.icon_ready = threading.Event()
        
        try:
            # Create a more visible icon
            self.icon_image = self._create_icon()
            self.logger.info("Icon image created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create icon image: {e}")
            raise
        
    def _create_icon(self) -> Image.Image:
        """Create a distinctive icon"""
        # Create a new image with a white background
        icon_size = 64
        image = Image.new('RGB', (icon_size, icon_size), 'white')
        draw = ImageDraw.Draw(image)
        
        # Draw a blue circle
        margin = 4
        draw.ellipse(
            [margin, margin, icon_size - margin, icon_size - margin],
            fill='blue'
        )
        
        # Draw "NP" text in white
        try:
            # Try to draw text if PIL has ImageFont support
            from PIL import ImageFont
            font = ImageFont.load_default()
            text = "NP"
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Center the text
            x = (icon_size - text_width) // 2
            y = (icon_size - text_height) // 2
            draw.text((x, y), text, fill='white', font=font)
        except Exception:
            # Fallback: draw a simple white rectangle if text drawing fails
            center = icon_size // 2
            size = 10
            draw.rectangle(
                [center - size, center - size, center + size, center + size],
                fill='white'
            )
        
        return image
        
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
            pystray.MenuItem("Status", self._show_status),
            pystray.MenuItem(
                "Exit",
                self._quit_app
            )
        )
    
    def _show_status(self):
        """Show current status"""
        status = "Running" if self.is_running else "Stopped"
        mode = "Auto" if self.auto_mode else "Manual"
        if self.icon:
            self.icon.notify(
                f"Status: {status}\nMode: {mode}",
                "No Ping Status"
            )
        
    def _toggle_auto_mode(self):
        """Toggle auto-mode on/off"""
        try:
            self.auto_mode = not self.auto_mode
            self.logger.info(f"Auto-mode {'enabled' if self.auto_mode else 'disabled'}")
            
            # Show notification
            if self.icon:
                self.icon.notify(
                    f"Auto-mode {'enabled' if self.auto_mode else 'disabled'}",
                    "No Ping"
                )
            
            # Stop optimization when disabling auto-mode
            if not self.auto_mode and self.is_running:
                self._toggle_optimization()
                
        except Exception as e:
            self.logger.error(f"Error toggling auto-mode: {e}")
            if self.icon:
                self.icon.notify(
                    "Failed to toggle auto-mode",
                    "No Ping Error"
                )
        
    def _toggle_optimization(self):
        """Toggle optimization on/off"""
        try:
            if not self.is_running:
                self.on_start()
                self.is_running = True
                self.logger.info("Optimization started")
                if self.icon:
                    self.icon.notify(
                        "Optimization started",
                        "No Ping"
                    )
            else:
                self.on_stop()
                self.is_running = False
                self.logger.info("Optimization stopped")
                if self.icon:
                    self.icon.notify(
                        "Optimization stopped",
                        "No Ping"
                    )
        except Exception as e:
            self.logger.error(f"Error toggling optimization: {e}")
            if self.icon:
                self.icon.notify(
                    "Failed to toggle optimization",
                    "No Ping Error"
                )
            
    def _quit_app(self):
        """Quit the application"""
        try:
            if self.is_running:
                self.on_stop()
            if self.icon:
                self.icon.notify(
                    "Shutting down...",
                    "No Ping"
                )
                self.icon.stop()
        except Exception as e:
            self.logger.error(f"Error quitting app: {e}")
            
    def _run_icon(self):
        """Run the system tray icon in a separate thread"""
        try:
            # Create the icon instance
            self.icon = pystray.Icon(
                "NoPing",
                self.icon_image,
                "No Ping - Game Network Optimizer",
                self._create_menu()
            )
            
            # Set up icon ready callback
            def setup(icon):
                self.logger.info("System tray icon is ready")
                self.icon_ready.set()
                
            self.icon.visible = True
            
            # Show startup notification
            self.icon.notify(
                "No Ping is running in the background.\nClick the system tray icon to manage optimization.",
                "No Ping Started"
            )
            
            # Run the icon
            self.logger.info("Starting system tray icon...")
            self.icon.run(setup=setup)
        except Exception as e:
            self.logger.error(f"Error running system tray: {e}")
            self.icon_ready.set()  # Set the event even on failure
            raise

    def run(self):
        """Run the system tray icon"""
        if self.thread is not None:
            return
            
        # Create and start the thread
        self.thread = threading.Thread(target=self._run_icon)
        self.thread.daemon = True
        self.thread.start()
        
        # Wait for the icon to be ready or timeout
        if not self.icon_ready.wait(timeout=5.0):
            self.logger.error("Timed out waiting for system tray icon to initialize")
            # Try to recover
            if self.icon:
                try:
                    self.icon.stop()
                except Exception as e:
                    self.logger.error(f"Error stopping icon after timeout: {e}")
            if self.thread:
                self.thread.join(timeout=1)
            raise RuntimeError("Failed to initialize system tray icon")
        
    def stop(self):
        """Stop the system tray icon"""
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                self.logger.error(f"Error stopping icon: {e}")
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None 