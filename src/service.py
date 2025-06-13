"""
Windows Service for No Ping
Automatically starts and manages game optimization with minimal resource usage
"""

import os
import sys
import logging
import ctypes
from pathlib import Path

# Allow bootstrap to override log directory via env var
_log_root = os.environ.get('NOPING_LOG_DIR') or os.path.join(os.environ.get('PROGRAMDATA', r'C:\ProgramData'), 'NoPing', 'logs')
# Safeguard against race condition where another process creates the dir simultaneously
try:
    Path(_log_root).mkdir(parents=True, exist_ok=True)
except Exception:
    # If directory creation fails, fall back to %TEMP% to avoid crashing the service completely
    _log_root = os.path.join(os.environ.get('TEMP', r'C:\Temp'), 'NoPing', 'logs')
    Path(_log_root).mkdir(parents=True, exist_ok=True)

_log_file = os.path.join(_log_root, 'service.log')

# Configure logging now that the directory is guaranteed to exist
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('NoPingService')

def setup_python_paths():
    """Set up Python paths and DLL directories"""
    try:
        logger.debug("Setting up Python paths...")
        
        # Get Python directory
        python_dir = os.path.dirname(sys.executable)
        service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        logger.debug(f"Python directory: {python_dir}")
        logger.debug(f"Service directory: {service_dir}")
        
        # Add DLL directories
        logger.debug(f"Adding DLL directory: {python_dir}")
        os.add_dll_directory(python_dir)
        
        # Add all DLL subdirectories
        for root, dirs, files in os.walk(python_dir):
            for file in files:
                if file.endswith('.dll'):
                    try:
                        logger.debug(f"Adding DLL subdirectory: {root}/")
                        os.add_dll_directory(root)
                    except Exception:
                        pass
        
        # Add source directory to Python path
        src_dir = os.path.join(service_dir, 'src')
        if src_dir not in sys.path:
            logger.debug(f"Added path to sys.path: {src_dir}")
            sys.path.insert(0, src_dir)
        
        logger.debug("Python paths setup completed")
        logger.debug(f"Final sys.path: {sys.path}")
        
    except Exception as e:
        logger.error(f"Error setting up Python paths: {e}")
        raise

# Set up Python paths before importing any other modules
setup_python_paths()

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import win32timezone  # Required for service to work properly
    logger.debug("Successfully imported win32 modules")
except Exception as e:
    logger.error(f"Error importing win32 modules: {e}")
    raise

import socket
import traceback
from src.steam.steam_manager import SteamManager
from src.network.optimizer import NetworkOptimizer
from src.vpn.vpn_manager import VPNManager
import threading
import time
import psutil
import win32process
import win32con
import win32security
import subprocess
from concurrent.futures import ThreadPoolExecutor

def is_admin():
    """Check if the current process has admin privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_wireguard():
    """Check if WireGuard is installed"""
    try:
        subprocess.run(['wg', '--version'], capture_output=True)
        return True
    except:
        return False

def check_steam():
    """Check if Steam is installed"""
    possible_paths = [
        "C:\\Program Files (x86)\\Steam",
        "C:\\Program Files\\Steam",
        os.path.expanduser("~\\Steam"),
        os.path.expanduser("~\\.steam\\steam")
    ]
    return any(os.path.exists(path) for path in possible_paths)

class NoPingService(win32serviceutil.ServiceFramework):
    _svc_name_ = "NoPingService"
    _svc_display_name_ = "No Ping Optimization Service"
    _svc_description_ = "Automatically optimizes network connection for games"
    _svc_deps_ = ['Tcpip', 'Afd', 'NetBT']

    def __init__(self, args):
        try:
            logger.info("Initializing service...")
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.steam_manager = None
            self.network_optimizer = None
            self.vpn_manager = None
            self.running = False
            self.thread_pool = ThreadPoolExecutor(max_workers=2)
            
            # Check dependencies
            self._has_admin = is_admin()
            self._has_wireguard = check_wireguard()
            self._has_steam = check_steam()
            
            logger.info(f"Admin privileges: {self._has_admin}")
            logger.info(f"WireGuard installed: {self._has_wireguard}")
            logger.info(f"Steam installed: {self._has_steam}")
            
            self._set_process_priority()
            logger.info("Service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing service: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _set_process_priority(self):
        """Set optimal process priority"""
        try:
            logger.debug("Setting process priority...")
            process = psutil.Process(os.getpid())
            process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            
            # Set I/O priority to low
            handle = win32process.GetCurrentProcess()
            win32process.SetPriorityClass(handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)
            logger.debug("Process priority set successfully")
            
        except Exception as e:
            logger.error(f"Error setting process priority: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    def SvcStop(self):
        """Stop the service gracefully"""
        try:
            logger.info('Stopping service...')
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            self.running = False
            
            # Clean up resources
            self.cleanup()
            logger.info('Service stopped successfully')
        except Exception as e:
            logger.error(f"Error stopping service: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    def SvcDoRun(self):
        """Run the service with resource optimization"""
        try:
            logger.info('Starting No Ping service...')
            # Write an event log record that is compatible with pywin32 constants
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            # Report service is starting
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            
            # Log Python environment details
            logger.debug(f"Python executable: {sys.executable}")
            logger.debug(f"Python version: {sys.version}")
            logger.debug(f"sys.path: {sys.path}")
            logger.debug(f"Current directory: {os.getcwd()}")
            
            # Initialize components based on available dependencies
            self.main()
            
        except Exception as e:
            logger.error(f'Service error in SvcDoRun: {e}')
            logger.error(f"Traceback: {traceback.format_exc()}")
            servicemanager.LogErrorMsg(str(e))
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            raise

    def main(self):
        """Main service loop with resource optimization"""
        try:
            logger.info("Entering main service loop")
            self.running = True
            
            # Report service is running
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            
            # Initialize components with minimal settings
            logger.debug("Initializing components...")
            
            # Only initialize Steam manager if Steam is installed
            if self._has_steam:
                self.steam_manager = SteamManager()
                # Populate catalog and enable automatic detection of running games
                try:
                    self.steam_manager.get_installed_games()
                except Exception:
                    logger.warning("Failed to query installed Steam games; auto detection may not work")

                self.steam_manager.enable_auto_game_detection()
            else:
                logger.warning("Steam not found, Steam features will be disabled")
            
            # Initialize network optimizer with admin status
            self.network_optimizer = NetworkOptimizer()
            
            # Only initialize VPN manager if WireGuard is installed
            if self._has_wireguard:
                self.vpn_manager = VPNManager()
            else:
                logger.warning("WireGuard not found, VPN features will be disabled")
                
            logger.debug("Components initialized successfully")
            
            def on_server_change(server_info):
                """Handle server region changes efficiently"""
                try:
                    logger.info(f'Server changed: {server_info}')
                    
                    # Submit optimization tasks to thread pool
                    self.thread_pool.submit(self._handle_server_change, server_info)
                        
                except Exception as e:
                    logger.error(f'Error handling server change: {e}')
                    logger.error(f"Traceback: {traceback.format_exc()}")

            # Start monitoring with reduced frequency if Steam is available
            if self._has_steam:
                logger.debug("Starting server monitoring...")
                self.steam_manager.start_server_monitoring(on_server_change)
            
            # Main service loop with adaptive sleep
            last_check = time.time()
            check_interval = 5  # Start with 5 seconds
            
            logger.info("Entering main loop")
            while self.running:
                try:
                    # Wait for stop event or timeout
                    rc = win32event.WaitForSingleObject(self.stop_event, 1000)
                    if rc == win32event.WAIT_OBJECT_0:
                        logger.info("Stop event received")
                        break
                        
                    current_time = time.time()
                    if current_time - last_check >= check_interval:
                        # Check system load
                        cpu_percent = psutil.cpu_percent()
                        logger.debug(f"CPU usage: {cpu_percent}%")
                        
                        # Adjust check interval based on CPU usage
                        if cpu_percent > 80:
                            check_interval = min(check_interval * 1.5, 30)
                        elif cpu_percent < 20:
                            check_interval = max(check_interval * 0.75, 1)
                        
                        # Only optimize if a supported game is currently running
                        if self.steam_manager and self.steam_manager.current_game:
                            logger.debug("Running network optimization check (game detected)")
                            self.network_optimizer.check_and_optimize()
                        else:
                            logger.debug("No Steam game detected – skipping optimization cycle")
                        last_check = current_time
                        
                except Exception as e:
                    logger.error(f'Error in main loop: {e}')
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    time.sleep(5)  # Prevent rapid error loops
                    
        except Exception as e:
            logger.error(f'Fatal error in main: {e}')
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        finally:
            self.cleanup()

    def _handle_server_change(self, server_info):
        """Handle server change in background thread"""
        try:
            logger.debug(f"Handling server change: {server_info}")
            # Optimize network path
            self.network_optimizer.optimize_path(server_info['region'])
            
            # Check if VPN would help and if VPN is available
            if self._has_wireguard and self.vpn_manager:
                if self.network_optimizer.should_use_vpn():
                    best_vpn = self.vpn_manager.get_best_server(server_info['region'])
                    if best_vpn:
                        self.vpn_manager.connect(best_vpn)
                else:
                    self.vpn_manager.disconnect()
                
        except Exception as e:
            logger.error(f'Error handling server change: {e}')
            logger.error(f"Traceback: {traceback.format_exc()}")

    def cleanup(self):
        """Clean up resources and restore defaults if needed"""
        try:
            logger.info("Cleaning up resources...")
            
            if self.steam_manager:
                logger.debug("Stopping steam manager...")
                self.steam_manager.stop_server_monitoring()
                
            if self.vpn_manager:
                logger.debug("Disconnecting VPN...")
                self.vpn_manager.disconnect()
                
            if self.network_optimizer:
                logger.debug("Cleaning up network optimizer...")
                self.network_optimizer.cleanup()
                
            # Shutdown thread pool
            logger.debug("Shutting down thread pool...")
            self.thread_pool.shutdown(wait=False)
            
            logger.info("Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f'Error during cleanup: {e}')
            logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == '__main__':
    try:
        logger.info("Starting service handler...")
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(NoPingService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32serviceutil.HandleCommandLine(NoPingService)
    except Exception as e:
        logger.error(f"Error in service handler: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise 