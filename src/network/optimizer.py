"""
Network Optimizer with hardware-optimized implementation
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
import win32security
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from collections import deque
import os

def is_admin():
    """Check if the current process has admin privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class NetworkOptimizer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_region = None
        self.best_routes = {}
        self.monitoring = False
        self.monitoring_thread = None
        self._has_admin = is_admin()
        
        if not self._has_admin:
            self.logger.warning("No administrative privileges. Some optimizations will be limited.")
        
        # Performance optimizations
        self._route_cache = {}
        self._latency_history = deque(maxlen=100)
        self._last_optimization = 0
        self._optimization_interval = 5  # seconds
        self._thread_pool = ThreadPoolExecutor(max_workers=2)
        self._adaptive_interval = True
        self._min_interval = 1
        self._max_interval = 30
        
        try:
            self._load_config()
            # Initialize with minimal optimizations
            self._apply_minimal_optimizations()
        except Exception as e:
            self.logger.error(f"Error during initialization: {e}", exc_info=True)
            # Continue with defaults even if initialization fails
            self.config = self._get_default_config()

    def _load_config(self):
        """Load optimization configuration"""
        try:
            # Prefer a per-user writable location; fall back to the packaged copy
            user_config_root = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'NoPing'
            user_config_root.mkdir(parents=True, exist_ok=True)
            config_path = user_config_root / 'network_config.json'

            packaged_default = Path(__file__).parent.parent / 'config' / 'network_config.json'

            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
                self.logger.debug("Successfully loaded network configuration")
            else:
                self.logger.info("No config file found, creating default configuration")
                self.config = self._get_default_config()
                try:
                    with open(config_path, 'w') as f:
                        json.dump(self.config, f, indent=4)
                except PermissionError:
                    # Read-only environments (service running without admin). Use in-memory defaults.
                    self.logger.warning("Cannot write user config – running with defaults only")
        except Exception as e:
            self.logger.error(f"Error loading config: {e}", exc_info=True)
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get hardware-optimized default configuration"""
        return {
            'tcp_optimization': {
                'TcpNoDelay': 1,
                'TcpAckFrequency': 1,
                'TCPDelAckTicks': 0,
                'TcpInitialRTT': 1,
                'DefaultTTL': 64,
                'TCPCongestionControl': 'bbr',  # Modern congestion control
                'TCPFastOpen': 1,
                'TCPFastOpenCookieSize': 1024
            },
            'qos': {
                'game_traffic_priority': 'high',
                'dscp_marking': 46,  # Expedited Forwarding
                'packet_scheduler': 'low_latency'
            },
            'buffer_sizes': {
                'tcp_receive': 262144,  # Optimized for modern networks
                'tcp_send': 262144,
                'udp_receive': 65536,
                'udp_send': 65536
            },
            'regions': {
                'NA': {'optimal_ttl': 64, 'routing_preference': 'latency'},
                'EU': {'optimal_ttl': 56, 'routing_preference': 'latency'},
                'AP': {'optimal_ttl': 48, 'routing_preference': 'latency'}
            },
            'hardware_optimization': {
                'cpu_priority': 'above_normal',
                'io_priority': 'high',
                'network_throttling_index': 0,  # Disable throttling
                'interrupt_moderation': 0,  # Minimize latency
                'receive_buffers': 1024,
                'transmit_buffers': 1024
            }
        }

    def _apply_minimal_optimizations(self):
        """Apply only essential optimizations to minimize resource usage"""
        try:
            self.logger.info("Applying minimal optimizations...")
            
            # Apply basic TCP optimizations
            if self._has_admin:
                self._optimize_tcp_minimal()
            else:
                self.logger.warning("Skipping TCP optimizations due to insufficient privileges")
            
            # Set basic QoS
            if self._has_admin:
                self._configure_qos_minimal()
            else:
                self.logger.warning("Skipping QoS configuration due to insufficient privileges")
            
            # Optimize network adapter with minimal settings
            if self._has_admin:
                self._optimize_adapter_minimal()
            else:
                self.logger.warning("Skipping adapter optimization due to insufficient privileges")
            
            self.logger.info("Minimal optimizations applied successfully")
            
        except Exception as e:
            self.logger.error(f"Error applying minimal optimizations: {e}", exc_info=True)
            # Continue even if optimizations fail

    def _optimize_tcp_minimal(self):
        """Apply minimal TCP optimizations"""
        try:
            self.logger.debug("Applying minimal TCP optimizations...")
            key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
            
            try:
                # Try to open with write access first
                access_level = winreg.KEY_ALL_ACCESS
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, access_level)
            except PermissionError:
                self.logger.warning("No write access to TCP parameters, trying read-only")
                # Fall back to read-only if we don't have write access
                access_level = winreg.KEY_READ
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, access_level)
            
            with key:
                if access_level == winreg.KEY_ALL_ACCESS:
                    # Only set critical parameters
                    critical_params = {
                        'TcpNoDelay': 1,
                        'DefaultTTL': 64,
                        'TCPFastOpen': 1
                    }
                    for param, value in critical_params.items():
                        try:
                            winreg.SetValueEx(key, param, 0, winreg.REG_DWORD, value)
                            self.logger.debug(f"Set TCP parameter {param}={value}")
                        except Exception as e:
                            self.logger.warning(f"Failed to set TCP parameter {param}: {e}")
                else:
                    self.logger.warning("Running in read-only mode, TCP optimizations skipped")
                        
        except Exception as e:
            self.logger.error(f"Error in minimal TCP optimization: {e}", exc_info=True)

    def _configure_qos_minimal(self):
        """Configure minimal QoS settings"""
        try:
            self.logger.debug("Configuring minimal QoS settings...")
            # Only set basic QoS policy
            result = subprocess.run([
                'netsh', 'qos', 'add', 'policy', 'name=GameTraffic',
                'dscp=46', 'priority=1'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.debug("QoS policy set successfully")
            else:
                self.logger.warning(f"Failed to set QoS policy: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error configuring QoS: {e}", exc_info=True)

    def _optimize_adapter_minimal(self):
        """Apply minimal adapter optimizations"""
        try:
            self.logger.debug("Applying minimal adapter optimizations...")
            adapters = self._get_active_adapters()
            
            if not adapters:
                self.logger.warning("No active network adapters found")
                return
                
            for adapter in adapters:
                self.logger.debug(f"Optimizing adapter: {adapter}")
                # Only set critical properties
                properties = {
                    'FlowControl': '0',  # Disable for lower latency
                    'InterruptModeration': '0'  # Minimize latency
                }
                for prop, value in properties.items():
                    try:
                        result = subprocess.run([
                            'netsh', 'interface', 'set', 'interface',
                            adapter, prop, value
                        ], capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            self.logger.debug(f"Set adapter property {prop}={value}")
                        else:
                            self.logger.warning(f"Failed to set adapter property {prop}: {result.stderr}")
                    except Exception as e:
                        self.logger.warning(f"Error setting adapter property {prop}: {e}")
        except Exception as e:
            self.logger.error(f"Error optimizing adapter: {e}", exc_info=True)

    def _get_active_adapters(self) -> List[str]:
        """Get list of active network adapters"""
        try:
            result = subprocess.run(
                ['netsh', 'interface', 'show', 'interface'],
                capture_output=True, text=True, check=True
            )
            
            adapters = []
            for line in result.stdout.split('\n')[3:]:  # Skip header lines
                if 'Connected' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        adapters.append(parts[3])
            
            return adapters
        except Exception as e:
            self.logger.error(f"Error getting active adapters: {e}", exc_info=True)
            return []

    def check_and_optimize(self):
        """Check and optimize network performance"""
        try:
            current_time = time.time()
            if current_time - self._last_optimization < self._optimization_interval:
                return
                
            self._last_optimization = current_time
            
            # Measure current latency
            latency = self._measure_latency()
            if latency is None:
                return
                
            self._latency_history.append(latency)
            
            # Check if optimization is needed
            if self._needs_optimization(latency):
                self.logger.info(f"High latency detected ({latency}ms), applying optimizations")
                self._apply_minimal_optimizations()
            
        except Exception as e:
            self.logger.error(f"Error in check_and_optimize: {e}", exc_info=True)

    def _measure_latency(self) -> Optional[float]:
        """Measure current network latency"""
        try:
            # Use a well-known reliable server
            host = "8.8.8.8"  # Google DNS
            count = 4
            
            result = subprocess.run(
                ['ping', '-n', str(count), host],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                self.logger.warning(f"Ping failed: {result.stderr}")
                return None
                
            # Parse average time from ping output
            for line in result.stdout.split('\n'):
                if 'Average' in line:
                    try:
                        avg = float(line.split('=')[1].split('ms')[0].strip())
                        return avg
                    except:
                        pass
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error measuring latency: {e}", exc_info=True)
            return None

    def _needs_optimization(self, current_latency: float) -> bool:
        """Determine if optimization is needed based on latency history"""
        if len(self._latency_history) < 3:
            return False
            
        avg_latency = np.mean(list(self._latency_history)[:-1])
        return current_latency > (avg_latency * 1.5) or current_latency > 100

    def cleanup(self):
        """Clean up resources and restore defaults if needed"""
        try:
            self.logger.info("Cleaning up network optimizer...")
            
            if self._thread_pool:
                self._thread_pool.shutdown(wait=False)
            
            if self._has_admin:
                self._restore_defaults()
            
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}", exc_info=True)

    def _restore_defaults(self):
        """Restore default network settings"""
        try:
            if not self._has_admin:
                self.logger.warning("Cannot restore defaults without admin privileges")
                return
                
            self.logger.info("Restoring default network settings...")
            
            # Remove QoS policy
            subprocess.run(['netsh', 'qos', 'delete', 'policy', 'name=GameTraffic'],
                         capture_output=True)
            
            # Restore default TCP settings
            key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, 
                                  winreg.KEY_ALL_ACCESS) as key:
                    default_params = {
                        'TcpNoDelay': 0,
                        'DefaultTTL': 128,
                        'TCPFastOpen': 0
                    }
                    for param, value in default_params.items():
                        try:
                            winreg.SetValueEx(key, param, 0, winreg.REG_DWORD, value)
                        except:
                            pass
            except:
                self.logger.warning("Could not restore TCP parameters")
            
            # Restore default routes if needed
            if self._has_admin:
                try:
                    subprocess.run(['route', 'delete', '*'], check=True)
                except Exception as e:
                    self.logger.warning(f"Error restoring routes: {e}")
            
            self.logger.info("Default settings restored")
            
        except Exception as e:
            self.logger.error(f"Error restoring defaults: {e}", exc_info=True)

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