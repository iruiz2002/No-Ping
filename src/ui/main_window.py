"""
Main Window Module
Handles the main GUI window using customtkinter
"""

import customtkinter as ctk
from typing import Dict, Any
import json
import os

from src.network.packet_handler import PacketHandler
from src.vpn.vpn_manager import VPNManager
from src.steam.steam_manager import SteamManager

class MainWindow:
    def __init__(self, vpn_manager: VPNManager, packet_handler: PacketHandler):
        """Initialize the main window"""
        self.vpn_manager = vpn_manager
        self.packet_handler = packet_handler
        self.steam_manager = SteamManager()
        
        # Configure theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("No Ping - Game Network Optimizer")
        self.root.geometry("800x600")
        
        self._create_widgets()
        self._load_steam_games()

    def _create_widgets(self):
        """Create and arrange GUI widgets"""
        # Create main frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame, 
            text="No Ping - Game Network Optimizer",
            font=("Helvetica", 24)
        )
        title.pack(pady=20)
        
        # Game selection
        game_frame = ctk.CTkFrame(self.main_frame)
        game_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(game_frame, text="Select Game:").pack(side="left", padx=5)
        self.game_combo = ctk.CTkComboBox(game_frame, values=[])
        self.game_combo.pack(side="left", fill="x", expand=True, padx=5)
        
        # Refresh button
        self.refresh_button = ctk.CTkButton(
            game_frame,
            text="↻",
            width=30,
            command=self._load_steam_games
        )
        self.refresh_button.pack(side="left", padx=5)
        
        # Server selection
        server_frame = ctk.CTkFrame(self.main_frame)
        server_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(server_frame, text="VPN Server:").pack(side="left", padx=5)
        self.server_combo = ctk.CTkComboBox(
            server_frame, 
            values=list(self.vpn_manager.get_server_list().keys())
        )
        self.server_combo.pack(side="left", fill="x", expand=True, padx=5)
        
        # Status
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Status: Ready",
            font=("Helvetica", 12)
        )
        self.status_label.pack(pady=20)
        
        # Game info
        self.game_info = ctk.CTkTextbox(
            self.main_frame,
            height=100,
            state="disabled"
        )
        self.game_info.pack(fill="x", padx=20, pady=10)
        
        # Control buttons
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        self.start_button = ctk.CTkButton(
            button_frame,
            text="Start Optimization",
            command=self._start_optimization
        )
        self.start_button.pack(side="left", padx=5, expand=True)
        
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="Stop",
            command=self._stop_optimization,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5, expand=True)

    def _load_steam_games(self):
        """Load list of installed Steam games"""
        try:
            games = self.steam_manager.get_installed_games()
            if games:
                self.game_combo.configure(values=list(games.keys()))
                self.status_label.configure(text="Steam games loaded successfully")
            else:
                self.status_label.configure(text="No Steam games found")
        except Exception as e:
            self.status_label.configure(text=f"Error loading Steam games: {e}")

    def _update_game_info(self, game_name: str):
        """Update game information display"""
        if not game_name:
            return
            
        game_data = self.steam_manager.installed_games.get(game_name, {})
        if not game_data:
            return
            
        app_id = game_data.get('app_id')
        if not app_id:
            return
            
        # Get server list and ports
        servers = self.steam_manager.get_server_list(int(app_id))
        ports = self.steam_manager.get_game_ports(int(app_id))
        
        # Update info display
        self.game_info.configure(state="normal")
        self.game_info.delete("1.0", "end")
        self.game_info.insert("1.0", f"Game: {game_name}\n")
        self.game_info.insert("end", f"App ID: {app_id}\n")
        self.game_info.insert("end", f"Ports: {', '.join(map(str, ports))}\n")
        self.game_info.insert("end", f"Available Servers: {len(servers)}")
        self.game_info.configure(state="disabled")

    def _start_optimization(self):
        """Start network optimization"""
        game = self.game_combo.get()
        server = self.server_combo.get()
        
        if not game or not server:
            self.status_label.configure(text="Please select both game and server")
            return
            
        try:
            game_data = self.steam_manager.installed_games.get(game, {})
            if not game_data:
                self.status_label.configure(text="Game data not found")
                return
                
            app_id = int(game_data.get('app_id', 0))
            if not app_id:
                self.status_label.configure(text="Invalid game ID")
                return
                
            # Get game ports
            ports = self.steam_manager.get_game_ports(app_id)
            
            # Connect to VPN
            if self.vpn_manager.connect(server):
                # Start packet capture with game ports
                self.packet_handler.start_capture(ports)
                
                self.status_label.configure(text="Optimization running...")
                self.start_button.configure(state="disabled")
                self.stop_button.configure(state="normal")
            else:
                self.status_label.configure(text="Failed to connect to VPN")
                
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}")

    def _stop_optimization(self):
        """Stop network optimization"""
        try:
            self.packet_handler.stop_capture()
            self.vpn_manager.disconnect()
            
            self.status_label.configure(text="Optimization stopped")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}")

    def run(self):
        """Start the main event loop"""
        self.root.mainloop() 