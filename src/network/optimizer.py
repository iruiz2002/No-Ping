"""
Network Optimizer
Implements advanced network optimization techniques
"""

import logging
import subprocess
import socket
import psutil
import winreg
import ctypes
import json
from pathlib import Path
import time
import threading
from typing import Dict, List, Optional
import requests
import win32api
import win32con

class NetworkOptimizer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_region = None
        self.best_routes = {}
        self.monitoring = False
        self.monitoring_thread = None
        self._load_config()
        self._apply_base_optimizations()

    def _load_config(self):
        """Load optimization configuration"""
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'network_config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = self._get_default_config()
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(self.config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default network optimization config"""
        return {
            'tcp_optimization': {
                'TcpNoDelay': 1,
                'TcpAckFrequency': 1,
                'TCPDelAckTicks': 0,
                'TcpInitialRTT': 2,
                'DefaultTTL': 64
            },
            'qos': {
                'game_traffic_priority': 'high',
                'dscp_marking': 46  # Expedited Forwarding
            },
            'buffer_sizes': {
                'tcp_receive': 524288,
                'tcp_send': 524288
            },
            'regions': {
                'NA': {'optimal_ttl': 64, 'routing_preference': 'performance'},
                'EU': {'optimal_ttl': 56, 'routing_preference': 'performance'},
                'AP': {'optimal_ttl': 48, 'routing_preference': 'performance'}
            }
        }

    def _apply_base_optimizations(self):
        """Apply base network optimizations"""
        try:
            # Apply TCP optimizations
            self._optimize_tcp_settings()
            
            # Configure QoS
            self._configure_qos()
            
            # Optimize network adapter
            self._optimize_network_adapter()
            
            # Configure Windows network settings
            self._optimize_windows_network()
            
        except Exception as e:
            self.logger.error(f"Error applying base optimizations: {e}")

    def _optimize_tcp_settings(self):
        """Optimize TCP settings for gaming"""
        try:
            tcp_params = self.config['tcp_optimization']
            
            # Open TCP/IP parameters key
            key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, 
                               winreg.KEY_ALL_ACCESS)
            
            # Set TCP optimization parameters
            for param, value in tcp_params.items():
                try:
                    winreg.SetValueEx(key, param, 0, winreg.REG_DWORD, value)
                except Exception as e:
                    self.logger.error(f"Error setting {param}: {e}")
                    
            winreg.CloseKey(key)
            
        except Exception as e:
            self.logger.error(f"Error optimizing TCP settings: {e}")

    def _configure_qos(self):
        """Configure Quality of Service settings"""
        try:
            # Set up QoS policies for game traffic
            subprocess.run([
                'netsh', 'qos', 'add', 'policy', 'name=GameTraffic',
                f'dscp={self.config["qos"]["dscp_marking"]}',
                'priority=1'
            ], check=True)
            
        except Exception as e:
            self.logger.error(f"Error configuring QoS: {e}")

    def _optimize_network_adapter(self):
        """Optimize network adapter settings"""
        try:
            # Get active network adapter
            active_adapters = self._get_active_adapters()
            
            for adapter in active_adapters:
                try:
                    # Set adapter advanced properties
                    self._set_adapter_properties(adapter)
                except Exception as e:
                    self.logger.error(f"Error optimizing adapter {adapter}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error optimizing network adapter: {e}")

    def _get_active_adapters(self) -> List[str]:
        """Get list of active network adapters"""
        active = []
        try:
            output = subprocess.check_output(
                ['netsh', 'interface', 'show', 'interface'],
                universal_newlines=True
            )
            
            for line in output.split('\n'):
                if 'Connected' in line and 'Ethernet' in line:
                    adapter = line.split()[-1]
                    active.append(adapter)
                    
        except Exception as e:
            self.logger.error(f"Error getting active adapters: {e}")
            
        return active

    def _set_adapter_properties(self, adapter: str):
        """Set optimal properties for network adapter"""
        try:
            # Optimize adapter settings
            properties = {
                'JumboPacket': '9014',  # Enable jumbo frames
                'FlowControl': '3',      # Enable flow control
                'InterruptModeration': '1',  # Enable interrupt moderation
                'ReceiveBuffers': '4096',
                'TransmitBuffers': '4096'
            }
            
            for prop, value in properties.items():
                try:
                    subprocess.run([
                        'netsh', 'interface', 'set', 'interface',
                        adapter, prop, value
                    ], check=True)
                except:
                    pass  # Some properties might not be supported
                    
        except Exception as e:
            self.logger.error(f"Error setting adapter properties: {e}")

    def _optimize_windows_network(self):
        """Optimize Windows network settings"""
        try:
            # Disable auto-tuning
            subprocess.run(['netsh', 'interface', 'tcp', 'set', 'global', 
                          'autotuninglevel=disabled'], check=True)
            
            # Set buffer sizes
            subprocess.run(['netsh', 'interface', 'tcp', 'set', 'global', 
                          f'rss=enabled'], check=True)
            
            # Enable fast path
            subprocess.run(['netsh', 'interface', 'tcp', 'set', 'global', 
                          'fastopen=enabled'], check=True)
            
        except Exception as e:
            self.logger.error(f"Error optimizing Windows network: {e}")

    def optimize_path(self, region: str):
        """Optimize network path for specific region"""
        try:
            if region == self.current_region:
                return
                
            self.current_region = region
            region_config = self.config['regions'].get(region, {})
            
            # Apply region-specific optimizations
            self._set_optimal_ttl(region_config.get('optimal_ttl', 64))
            self._optimize_routing(region)
            
            # Update QoS for the region
            self._update_qos_for_region(region)
            
        except Exception as e:
            self.logger.error(f"Error optimizing path for {region}: {e}")

    def _set_optimal_ttl(self, ttl: int):
        """Set optimal TTL for the region"""
        try:
            key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, 
                               winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, "DefaultTTL", 0, winreg.REG_DWORD, ttl)
            winreg.CloseKey(key)
        except Exception as e:
            self.logger.error(f"Error setting TTL: {e}")

    def _optimize_routing(self, region: str):
        """Optimize routing for the region"""
        try:
            # Get best route for the region
            best_route = self._find_best_route(region)
            
            if best_route:
                # Add route to routing table
                subprocess.run([
                    'route', 'add', best_route['network'], 
                    best_route['gateway'], f'metric {best_route["metric"]}'
                ], check=True)
                
        except Exception as e:
            self.logger.error(f"Error optimizing routing: {e}")

    def _find_best_route(self, region: str) -> Optional[Dict]:
        """Find best route for the region"""
        try:
            # Get current routes
            output = subprocess.check_output(['route', 'print'], 
                                          universal_newlines=True)
            
            # Analyze routes and find best path
            # This is a simplified version - you'd want to implement
            # more sophisticated route selection based on your needs
            routes = self._parse_routes(output)
            
            if routes:
                return min(routes, key=lambda x: x.get('metric', 9999))
                
        except Exception as e:
            self.logger.error(f"Error finding best route: {e}")
            
        return None

    def _parse_routes(self, route_output: str) -> List[Dict]:
        """Parse route command output"""
        routes = []
        try:
            lines = route_output.split('\n')
            for line in lines:
                if line.strip() and line[0].isdigit():
                    parts = line.split()
                    if len(parts) >= 4:
                        routes.append({
                            'network': parts[0],
                            'gateway': parts[2],
                            'metric': int(parts[3])
                        })
        except Exception as e:
            self.logger.error(f"Error parsing routes: {e}")
            
        return routes

    def _update_qos_for_region(self, region: str):
        """Update QoS settings for specific region"""
        try:
            # Set DSCP marking for the region
            dscp = self.config['qos']['dscp_marking']
            subprocess.run([
                'netsh', 'qos', 'add', 'policy', f'name=GameTraffic_{region}',
                f'dscp={dscp}', 'priority=1'
            ], check=True)
            
        except Exception as e:
            self.logger.error(f"Error updating QoS: {e}")

    def should_use_vpn(self) -> bool:
        """Determine if VPN would improve connection"""
        try:
            if not self.current_region:
                return False
                
            # Check current latency
            current_latency = self._measure_latency()
            
            # Get historical best latency for this region
            best_latency = self.best_routes.get(self.current_region, {}).get('best_latency')
            
            # If current latency is significantly worse, suggest VPN
            if best_latency and current_latency > best_latency * 1.2:
                return True
                
        except Exception as e:
            self.logger.error(f"Error checking VPN need: {e}")
            
        return False

    def _measure_latency(self) -> float:
        """Measure current latency"""
        try:
            # Implement actual latency measurement here
            # This is a placeholder
            return 100.0
        except Exception as e:
            self.logger.error(f"Error measuring latency: {e}")
            return 999.0

    def check_and_optimize(self):
        """Check and optimize network conditions"""
        try:
            if self.current_region:
                # Measure current network conditions
                latency = self._measure_latency()
                
                # Update best routes if needed
                if (self.current_region not in self.best_routes or 
                    latency < self.best_routes[self.current_region].get('best_latency', 999)):
                    self.best_routes[self.current_region] = {
                        'best_latency': latency,
                        'timestamp': time.time()
                    }
                    
                # Re-optimize if conditions degraded
                if latency > self.best_routes[self.current_region]['best_latency'] * 1.2:
                    self.optimize_path(self.current_region)
                    
        except Exception as e:
            self.logger.error(f"Error in check_and_optimize: {e}")

    def cleanup(self):
        """Clean up optimizations"""
        try:
            # Remove custom routes
            subprocess.run(['route', 'delete', '*'], check=True)
            
            # Remove QoS policies
            subprocess.run(['netsh', 'qos', 'delete', 'policy', 'all'], 
                         check=True)
            
        except Exception as e:
            self.logger.error(f"Error in cleanup: {e}") 