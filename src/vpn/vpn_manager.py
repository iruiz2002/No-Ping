"""
VPN Manager Module
Handles WireGuard VPN connections and routing
"""

import os
import subprocess
import logging
from typing import Optional, Dict
import json

class VPNManager:
    def __init__(self):
        """Initialize the VPN manager"""
        self.current_server: Optional[str] = None
        self.is_connected = False
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Load server configurations
        self.servers = self._load_server_configs()

    def connect(self, server_name: str) -> bool:
        """Connect to a specific VPN server"""
        if self.is_connected:
            self.disconnect()
            
        if server_name not in self.servers:
            self.logger.error(f"Server '{server_name}' not found in configuration")
            return False
            
        try:
            # Use WireGuard CLI to establish connection
            config_path = self.servers[server_name]
            subprocess.run(['wg-quick', 'up', config_path], check=True)
            
            self.current_server = server_name
            self.is_connected = True
            self.logger.info(f"Connected to VPN server: {server_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to connect to VPN: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the current VPN server"""
        if not self.is_connected or not self.current_server:
            return True
            
        try:
            config_path = self.servers[self.current_server]
            subprocess.run(['wg-quick', 'down', config_path], check=True)
            
            self.current_server = None
            self.is_connected = False
            self.logger.info("Disconnected from VPN")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to disconnect from VPN: {e}")
            return False

    def get_server_list(self) -> Dict[str, str]:
        """Get list of available VPN servers"""
        return self.servers

    def _load_server_configs(self) -> Dict[str, str]:
        """Load WireGuard server configurations from config directory"""
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                'config', 'wireguard')
        servers = {}
        
        try:
            # Load server list from servers.json if it exists
            json_path = os.path.join(config_dir, 'servers.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    servers = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load server configurations: {e}")
        
        return servers

    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.is_connected:
            self.disconnect() 