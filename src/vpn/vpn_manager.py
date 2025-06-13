"""
VPN Manager Module
Handles VPN connections using WireGuard
"""

import os
import subprocess
import json
import logging
from typing import Dict, List, Optional, Tuple
import requests
import time
import threading
import statistics

class VPNManager:
    def __init__(self):
        """Initialize VPN manager"""
        self.logger = logging.getLogger(__name__)
        self.servers = self._load_server_configs()
        self.current_server = None
        self.is_connected = False
        self.route_stats = {}
        self.optimal_routes: Dict[str, List[str]] = {}
        
    def connect(self, server_name: str) -> bool:
        """Connect to a VPN server"""
        if server_name not in self.servers:
            self.logger.error(f"Server '{server_name}' not found")
            return False
            
        if self.is_connected:
            if self.current_server == server_name:
                return True
            self.disconnect()
            
        try:
            # Get optimal routes for the server
            routes = self._discover_optimal_routes(server_name)
            if not routes:
                self.logger.error(f"No optimal routes found for {server_name}")
                return False
                
            # Connect to VPN
            config_path = self.servers[server_name]
            subprocess.run(['wg-quick', 'up', config_path], check=True)
            
            self.current_server = server_name
            self.is_connected = True
            self.logger.info(f"Connected to VPN server: {server_name}")
            
            # Store optimal routes
            self.optimal_routes[server_name] = routes
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to connect to VPN: {e}")
            return False
            
    def _discover_optimal_routes(self, server_name: str) -> List[str]:
        """Discover optimal routes for a server"""
        try:
            # Get server endpoints
            endpoints = self._get_server_endpoints(server_name)
            if not endpoints:
                return []
                
            # Test routes
            route_stats = []
            for endpoint in endpoints:
                stats = self._test_route(endpoint)
                if stats:
                    route_stats.append((endpoint, stats))
                    
            # Sort by latency
            route_stats.sort(key=lambda x: x[1]['latency'])
            
            # Return top 3 routes
            return [route for route, _ in route_stats[:3]]
            
        except Exception as e:
            self.logger.error(f"Error discovering routes: {e}")
            return []
            
    def _test_route(self, endpoint: str) -> Optional[Dict]:
        """Test a route's performance"""
        try:
            # Ping test
            ping_times = []
            for _ in range(3):
                result = subprocess.run(
                    ['ping', '-n', '1', '-w', '1000', endpoint],
                    capture_output=True,
                    text=True
                )
                if "time=" in result.stdout:
                    time_str = result.stdout.split("time=")[1].split("ms")[0].strip()
                    ping_times.append(float(time_str))
                time.sleep(0.5)
                
            if not ping_times:
                return None
                
            # Calculate statistics
            stats = {
                'latency': statistics.mean(ping_times),
                'jitter': statistics.stdev(ping_times) if len(ping_times) > 1 else 0,
                'packet_loss': (3 - len(ping_times)) / 3 * 100
            }
            
            self.logger.debug(f"Route {endpoint} stats: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error testing route {endpoint}: {e}")
            return None
            
    def _get_server_endpoints(self, server_name: str) -> List[str]:
        """Get list of endpoints for a server"""
        try:
            # Read server configuration
            config_path = self.servers[server_name]
            with open(config_path, 'r') as f:
                config = f.read()
                
            # Extract endpoint
            for line in config.split('\n'):
                if line.startswith('Endpoint = '):
                    endpoint = line.split(' = ')[1].split(':')[0]
                    
                    # Try to resolve additional IPs
                    try:
                        response = requests.get(f'https://dns.google/resolve?name={endpoint}')
                        if response.status_code == 200:
                            data = response.json()
                            if 'Answer' in data:
                                return [answer['data'] for answer in data['Answer']]
                    except:
                        pass
                        
                    # Return at least the configured endpoint
                    return [endpoint]
                    
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting endpoints for {server_name}: {e}")
            return []

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
        
    def get_optimal_routes(self, server_name: str) -> List[str]:
        """Get optimal routes for a server"""
        return self.optimal_routes.get(server_name, [])

    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.is_connected:
            self.disconnect() 