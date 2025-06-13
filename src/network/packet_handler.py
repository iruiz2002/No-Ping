"""
Packet Handler Module
Handles packet interception and routing using WinDivert
"""

import pydivert
import logging
from typing import Optional, List, Dict
import threading
import time
import subprocess
import statistics
import json

class PacketHandler:
    def __init__(self):
        """Initialize the packet handler"""
        self.windivert: Optional[pydivert.WinDivert] = None
        self.game_ports: List[int] = []
        self.is_running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.ping_stats: Dict[str, float] = {}
        self.best_route: Optional[str] = None
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _monitor_ping(self, target_ips: List[str]):
        """Monitor ping to different endpoints"""
        while self.is_running:
            try:
                for ip in target_ips:
                    try:
                        # Run ping command
                        result = subprocess.run(
                            ['ping', '-n', '1', '-w', '1000', ip],
                            capture_output=True,
                            text=True
                        )
                        
                        # Extract ping time from output
                        if "time=" in result.stdout:
                            time_str = result.stdout.split("time=")[1].split("ms")[0].strip()
                            ping_time = float(time_str)
                            self.ping_stats[ip] = ping_time
                            self.logger.info(f"Ping to {ip}: {ping_time}ms")
                            
                            # Update routing if we found a better path
                            if self.best_route is None or ping_time < self.ping_stats.get(self.best_route, float('inf')):
                                self.best_route = ip
                                self.logger.info(f"New best route: {ip} ({ping_time}ms)")
                                
                    except Exception as e:
                        self.logger.error(f"Error pinging {ip}: {e}")
                        
                # Sleep between ping cycles
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error in ping monitoring: {e}")
                time.sleep(5)

    def start_capture(self, ports: List[int], target_ips: Optional[List[str]] = None):
        """Start capturing packets for specified game ports"""
        if self.is_running:
            return
            
        self.game_ports = ports
        filter_string = self._build_filter_string()
        
        try:
            # Start packet capture
            self.windivert = pydivert.WinDivert(filter_string)
            self.windivert.open()
            self.is_running = True
            self.logger.info(f"Started packet capture for ports: {ports}")
            
            # Start ping monitoring if target IPs are provided
            if target_ips:
                self.monitoring_thread = threading.Thread(
                    target=self._monitor_ping,
                    args=(target_ips,)
                )
                self.monitoring_thread.daemon = True
                self.monitoring_thread.start()
                
            # Start packet processing
            self._process_packets()
            
        except Exception as e:
            self.logger.error(f"Failed to start packet capture: {e}")
            raise

    def _process_packets(self):
        """Process captured packets"""
        try:
            while self.is_running:
                # Read a packet
                packet = self.windivert.recv()
                
                if packet:
                    # Check if this is a game packet
                    if (packet.dst_port in self.game_ports or 
                        packet.src_port in self.game_ports):
                        
                        # If we have a better route, modify the packet
                        if self.best_route:
                            # Store original destination
                            original_dst = packet.dst_addr
                            
                            # Route through the best path
                            packet.dst_addr = self.best_route
                            
                            # Log the routing decision
                            self.logger.debug(
                                f"Routing packet: {original_dst} -> {self.best_route} "
                                f"(ping: {self.ping_stats.get(self.best_route, 0)}ms)"
                            )
                    
                    # Send the packet
                    self.windivert.send(packet)
                    
        except Exception as e:
            self.logger.error(f"Error processing packets: {e}")
            self.stop_capture()

    def stop_capture(self):
        """Stop packet capture"""
        if self.windivert and self.is_running:
            try:
                self.is_running = False
                if self.monitoring_thread:
                    self.monitoring_thread.join(timeout=1)
                self.windivert.close()
                self.logger.info("Stopped packet capture")
            except Exception as e:
                self.logger.error(f"Error stopping packet capture: {e}")
                raise

    def _build_filter_string(self) -> str:
        """Build WinDivert filter string for game ports"""
        if not self.game_ports:
            return "false"  # No ports specified, don't capture anything
            
        port_filters = [f"tcp.DstPort == {port} or udp.DstPort == {port} or " +
                       f"tcp.SrcPort == {port} or udp.SrcPort == {port}" 
                       for port in self.game_ports]
        return "(" + " or ".join(port_filters) + ")"

    def get_stats(self) -> Dict[str, Dict]:
        """Get current optimization statistics"""
        return {
            "ping_stats": self.ping_stats,
            "best_route": self.best_route,
            "active_ports": self.game_ports,
            "is_running": self.is_running
        }

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_capture() 