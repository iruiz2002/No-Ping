"""
Packet Handler Module
Handles packet interception and routing using WinDivert
"""

import pydivert
import logging
from typing import Optional, List

class PacketHandler:
    def __init__(self):
        """Initialize the packet handler"""
        self.windivert: Optional[pydivert.WinDivert] = None
        self.game_ports: List[int] = []
        self.is_running = False
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def start_capture(self, ports: List[int]):
        """Start capturing packets for specified game ports"""
        if self.is_running:
            return
            
        self.game_ports = ports
        filter_string = self._build_filter_string()
        
        try:
            self.windivert = pydivert.WinDivert(filter_string)
            self.windivert.open()
            self.is_running = True
            self.logger.info(f"Started packet capture for ports: {ports}")
        except Exception as e:
            self.logger.error(f"Failed to start packet capture: {e}")
            raise

    def stop_capture(self):
        """Stop packet capture"""
        if self.windivert and self.is_running:
            try:
                self.windivert.close()
                self.is_running = False
                self.logger.info("Stopped packet capture")
            except Exception as e:
                self.logger.error(f"Error stopping packet capture: {e}")
                raise

    def _build_filter_string(self) -> str:
        """Build WinDivert filter string for game ports"""
        if not self.game_ports:
            return "false"  # No ports specified, don't capture anything
            
        port_filters = [f"tcp.DstPort == {port} or udp.DstPort == {port}" 
                       for port in self.game_ports]
        return "(" + " or ".join(port_filters) + ")"

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_capture() 