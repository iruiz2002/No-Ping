"""
Windows Service for No Ping
Automatically starts and manages game optimization
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import logging
from pathlib import Path
from steam.steam_manager import SteamManager
from network.optimizer import NetworkOptimizer
from vpn.vpn_manager import VPNManager
import threading
import time

class NoPingService(win32serviceutil.ServiceFramework):
    _svc_name_ = "NoPingService"
    _svc_display_name_ = "No Ping Optimization Service"
    _svc_description_ = "Automatically optimizes network connection for games"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.steam_manager = None
        self.network_optimizer = None
        self.vpn_manager = None
        self.running = False

        # Set up logging
        log_dir = Path(os.getenv('PROGRAMDATA')) / 'NoPing' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'service.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def SvcStop(self):
        """Stop the service"""
        self.logger.info('Stopping service...')
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        """Run the service"""
        try:
            self.logger.info('Starting No Ping service...')
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PID_INFO,
                ('Service starting...', '')
            )
            self.main()
            
        except Exception as e:
            self.logger.error(f'Service error: {e}')
            servicemanager.LogErrorMsg(str(e))

    def main(self):
        """Main service loop"""
        try:
            self.running = True
            
            # Initialize components
            self.steam_manager = SteamManager()
            self.network_optimizer = NetworkOptimizer()
            self.vpn_manager = VPNManager()
            
            def on_server_change(server_info):
                """Handle server region changes"""
                try:
                    self.logger.info(f'Server changed: {server_info}')
                    
                    # Optimize network path
                    self.network_optimizer.optimize_path(server_info['region'])
                    
                    # Update VPN if needed
                    if self.network_optimizer.should_use_vpn():
                        best_vpn = self.vpn_manager.get_best_server(server_info['region'])
                        self.vpn_manager.connect(best_vpn)
                    else:
                        self.vpn_manager.disconnect()
                        
                except Exception as e:
                    self.logger.error(f'Error handling server change: {e}')

            # Start monitoring
            self.steam_manager.start_server_monitoring(on_server_change)
            
            # Main service loop
            while self.running:
                try:
                    # Check if any optimization is needed
                    self.network_optimizer.check_and_optimize()
                    
                    # Wait for stop event or timeout
                    rc = win32event.WaitForSingleObject(self.stop_event, 5000)
                    if rc == win32event.WAIT_OBJECT_0:
                        break
                        
                except Exception as e:
                    self.logger.error(f'Error in main loop: {e}')
                    time.sleep(5)  # Prevent rapid error loops
                    
        except Exception as e:
            self.logger.error(f'Fatal error in main: {e}')
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        try:
            if self.steam_manager:
                self.steam_manager.stop_server_monitoring()
            if self.vpn_manager:
                self.vpn_manager.disconnect()
            if self.network_optimizer:
                self.network_optimizer.cleanup()
        except Exception as e:
            self.logger.error(f'Error during cleanup: {e}')

def install_and_start():
    """Install and start the service"""
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(NoPingService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(NoPingService)

if __name__ == '__main__':
    install_and_start() 