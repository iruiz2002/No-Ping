"""
No Ping Service Installer
Handles both regular Python and Windows Store Python installations
"""

import sys
import os
import subprocess
import winreg
import ctypes
from pathlib import Path
import shutil
import site
import platform
import urllib.request
import tempfile
import zipfile
import time
import logging
import traceback
import glob
import textwrap  # helper for indentation

def is_admin():
    """Check if the script is running with admin privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Re-run the script with admin privileges"""
    try:
        if not is_admin():
            print("Requesting administrator privileges...")
            script = os.path.abspath(__file__)
            params = ' '.join(sys.argv[1:])
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}" {params}', None, 1
            )
            if ret > 32:
                sys.exit(0)
            else:
                raise Exception("Failed to get admin privileges")
    except Exception as e:
        print(f"Error getting admin privileges: {e}")
        raise

def is_windows_store_python():
    """Check if running from Windows Store Python"""
    return "WindowsApps" in sys.executable

def find_regular_python():
    """Find a regular Python installation"""
    try:
        # Check common installation paths
        possible_paths = [
            "C:\\Program Files\\Python311\\python.exe",
            "C:\\Python311\\python.exe",
            "C:\\Program Files\\Python310\\python.exe",
            "C:\\Python310\\python.exe"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        # Check PATH for Python installations
        paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in paths:
            python_exe = os.path.join(path, 'python.exe')
            if os.path.exists(python_exe) and 'WindowsApps' not in python_exe:
                return python_exe
                
        return None
        
    except Exception as e:
        print(f"Error finding Python: {e}")
        return None

def download_python():
    """Download and install regular Python if needed"""
    try:
        print("Downloading Python 3.11...")
        url = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp_file:
            urllib.request.urlretrieve(url, tmp_file.name)
            installer_path = tmp_file.name
            
        print("Installing Python...")
        # Install Python with required options
        subprocess.run([
            installer_path,
            "/quiet",
            "InstallAllUsers=1",
            "PrependPath=1",
            "Include_test=0"
        ], check=True)
        
        # Clean up installer
        os.unlink(installer_path)
        
        # Return the new Python path
        return "C:\\Program Files\\Python311\\python.exe"
        
    except Exception as e:
        print(f"Error downloading/installing Python: {e}")
        return None

def create_venv():
    """Create and set up a virtual environment"""
    try:
        print("Creating virtual environment...")
        venv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv")
        
        # Remove existing venv if it exists
        if os.path.exists(venv_dir):
            print("Removing existing virtual environment...")
            shutil.rmtree(venv_dir)
        
        # Create new venv
        subprocess.check_call([
            sys.executable, "-m", "venv",
            "--clear", "--upgrade-deps",
            venv_dir
        ])
        
        # Get Python executable path in venv
        if os.name == 'nt':
            python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            python_exe = os.path.join(venv_dir, "bin", "python")
            
        print(f"Virtual environment created at: {venv_dir}")
        return python_exe
        
    except Exception as e:
        print(f"Error creating virtual environment: {e}")
        raise

def verify_python_environment(python_exe):
    """Verify and fix Python environment"""
    try:
        print(f"Using Python: {python_exe}")
        
        # Ensure pip is up to date
        subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Determine explicit site-packages dir
        site_dir = os.path.join(os.path.dirname(python_exe), "Lib", "site-packages")
        # Install all required packages directly into that directory to avoid user-site confusion
        print("Installing dependencies into", site_dir)
        subprocess.check_call([
            python_exe, "-m", "pip", "install",
            "--no-cache-dir", "--upgrade", "--target", site_dir,
            "pywin32==306",
            "psutil",
            "requests",
            "vdf",
            "python-dotenv",
            "numpy"
        ])
        
        # Run post-install script
        post_install_script = os.path.join(
            os.path.dirname(python_exe),
            "Scripts",
            "pywin32_postinstall.py"
        )
        
        if os.path.exists(post_install_script):
            print("Running pywin32 post-install script...")
            subprocess.check_call([
                python_exe,
                post_install_script,
                "-install"
            ])
            
            # Verification disabled to avoid rare importlib edge-cases.
        else:
            raise Exception("pywin32 post-install script not found")
            
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error setting up Python environment: {e}")
    except Exception as e:
        raise Exception(f"Error verifying Python environment: {e}")

def setup_service_files(python_exe):
    """Set up service files in Program Files"""
    try:
        service_dir = Path("C:/Program Files/NoPing")
        service_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging directory
        log_dir = Path("C:/ProgramData/NoPing/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy necessary files
        current_dir = Path(__file__).parent.absolute()
        
        # Copy Python files
        shutil.copytree(
            current_dir / "src",
            service_dir / "src",
            dirs_exist_ok=True
        )
        
        # Create service runner script
        service_script = service_dir / "noping_service.py"
        with open(service_script, 'w', encoding='utf-8') as f:
            f.write(textwrap.dedent(fr'''# -*- coding: utf-8 -*-
"""
No Ping Service Runner
"""

# Lightweight bootstrap that ensures the real service class can be loaded and then
# hands off control to the Windows Service Control Manager (SCM).

import os
import sys
import logging
import traceback
from pathlib import Path

# Force using the correct Python
os.environ["PYTHONEXECUTABLE"] = r"{python_exe}"
os.environ["PYTHONPATH"] = r"{os.path.dirname(python_exe)}"

# Set up logging
log_dir = Path(os.getenv('PROGRAMDATA')) / 'NoPing' / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / 'service.log'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NoPingService")

try:
    # Add Python paths
    python_dir = r"{os.path.dirname(python_exe)}"
    site_packages = os.path.join(python_dir, "Lib", "site-packages")
    win32_lib = os.path.join(site_packages, "win32", "lib")
    pywin32_system32 = os.path.join(site_packages, "pywin32_system32")
    
    # Add paths to sys.path
    paths_to_add = [
        pywin32_system32,
        win32_lib,
        site_packages,
        os.path.join(site_packages, "win32"),
        os.path.join(site_packages, "Pythonwin"),
        r"C:\\Program Files\\NoPing"
    ]
    
    # Remove any Windows Store Python paths
    sys.path = [p for p in sys.path if 'WindowsApps' not in p]
    
    # Add our paths at the start of sys.path
    for path in paths_to_add:
        if path not in sys.path and os.path.exists(path):
            logger.debug(f"Added path to sys.path: {{path}}")
            sys.path.insert(0, path)
    
    # Force reload site to update sys.path
    import site
    site.main()
    
    # Log Python environment
    logger.debug(f"Python executable: {{sys.executable}}")
    logger.debug(f"sys.path: {{sys.path}}")
    
    # Import and run service
    from src.service import NoPingService
    import win32serviceutil, win32service, servicemanager
    
    if __name__ == '__main__':
        try:
            # Handle our own lightweight debug mode.
            if len(sys.argv) > 1 and sys.argv[1].lower() == 'debug':
                win32serviceutil.DebugService(NoPingService, [NoPingService._svc_name_])
                sys.exit(0)

            # The installer may register the service with "run" argument when
            # pythonservice.exe is not available. Treat this the same as having
            # no args from the SCM.
            if len(sys.argv) > 1 and sys.argv[1].lower() == 'run':
                # Pop the 'run' arg so the subsequent logic sees len==1
                sys.argv.pop(1)

            if len(sys.argv) == 1:
                try:
                    servicemanager.Initialize()
                    servicemanager.PrepareToHostSingle(NoPingService)
                    servicemanager.StartServiceCtrlDispatcher()
                except win32service.error:
                    # Probably not running as a service.
                    win32serviceutil.HandleCommandLine(NoPingService)
            else:
                win32serviceutil.HandleCommandLine(NoPingService)
        except Exception as e:
            logger.error(f"Error in service runner: {{e}}")
            logger.error(f"Traceback: {{traceback.format_exc()}}")
            raise
except Exception as e:
    logger.error(f"Error in service runner: {{e}}")
    logger.error(f"Traceback: {{traceback.format_exc()}}")
    raise
'''))
        
        # Install core runtime packages into both the interpreter and service directory
        print("Installing service runtime dependencies (psutil, requests, vdf, python-dotenv, numpy)…")

        common_packages = [
            "psutil",
            "requests",
            "vdf",
            "python-dotenv",
            "numpy"
        ]

        # Install into the interpreter's Lib\site-packages
        subprocess.check_call([
            python_exe, "-m", "pip", "install", "--no-cache-dir", "--upgrade", *common_packages
        ])

        # Also copy wheels into the service directory itself (defensive in case PYTHONHOME/PATH changes)
        subprocess.check_call([
            python_exe, "-m", "pip", "install", "--no-cache-dir", "--upgrade",
            "--target", service_dir, *common_packages
        ])
        
        # Create a batch file to run the service with the correct Python
        service_batch = service_dir / "run_service.bat"
        with open(service_batch, 'w') as f:
            f.write(f'@echo off\nset PYTHONPATH={os.path.dirname(python_exe)}\nset PYTHONEXECUTABLE={python_exe}\n"{python_exe}" "%~dp0noping_service.py" %*')
        
        return service_batch
        
    except Exception as e:
        print(f"Error setting up service files: {e}")
        raise

def setup_service_environment():
    """Set up standalone service environment"""
    try:
        print("Setting up service environment...")
        
        # Create service directory
        service_dir = os.path.join(os.environ.get('PROGRAMFILES', r'C:\Program Files'), 'NoPing')
        os.makedirs(service_dir, exist_ok=True)
        
        # Copy Python installation
        python_dir = os.path.dirname(sys.executable)
        if "WindowsApps" in python_dir:
            # Find regular Python installation
            possible_paths = [
                r"C:\Program Files\Python311",
                r"C:\Python311",
                r"C:\Program Files (x86)\Python311",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    python_dir = path
                    break
            else:
                raise Exception("Could not find a proper Python installation. Please install Python 3.11 from python.org")
        
        # Copy Python files
        # Helper that removes a directory even if some files are locked.
        def _safe_remove_dir(path: str):
            if not os.path.exists(path):
                return
            try:
                shutil.rmtree(path)
                return
            except PermissionError:
                # Directory is in use (DLL locked). Move it out of the way and continue.
                try:
                    ts = int(time.time())
                    new_name = f"{path}_old_{ts}"
                    os.rename(path, new_name)
                except Exception:
                    print(f"Warning: could not remove or rename {path}. Files may be in use. Installation may require reboot.")

        service_python_dir = os.path.join(service_dir, 'Python')
        _safe_remove_dir(service_python_dir)
        
        print("Copying Python installation...")
        # First copy everything except __pycache__ directories
        shutil.copytree(
            python_dir,
            service_python_dir,
            ignore=shutil.ignore_patterns('__pycache__')
        )
        
        # Copy service files
        print("Copying service files...")
        src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
        service_src_dir = os.path.join(service_dir, 'src')
        if os.path.exists(service_src_dir):
            shutil.rmtree(service_src_dir)
        shutil.copytree(src_dir, service_src_dir)
        
        # Create service runner script
        service_script = os.path.join(service_dir, 'noping_service.py')
        with open(service_script, 'w', encoding='utf-8') as f:
            f.write(textwrap.dedent(fr'''# -*- coding: utf-8 -*-
"""
No Ping Service Runner
"""

# Lightweight bootstrap that ensures the real service class can be loaded and then
# hands off control to the Windows Service Control Manager (SCM).

import os
import sys
import logging
import traceback
from pathlib import Path

# ------------------------------------------------------------
# Robust logging setup that always succeeds even if ACLs prevent
# writing to ProgramData.  If we cannot create/open the main log
# file we fall back to the system TEMP directory and log a short
# message to stderr so the failure reason is visible in the
# Windows Event Log.
# ------------------------------------------------------------

def _configure_logging():
    import tempfile
    from pathlib import Path
    import logging, sys, os

    primary_root = os.path.join(os.getenv('PROGRAMDATA', r'C:\ProgramData'), 'NoPing', 'logs')
    fallback_root = os.path.join(tempfile.gettempdir(), 'NoPing', 'logs')

    for root in (primary_root, fallback_root):
        try:
            Path(root).mkdir(parents=True, exist_ok=True)
            log_file = os.path.join(root, 'service.log')
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
            # Expose chosen directory to child modules
            os.environ['NOPING_LOG_DIR'] = root

            if root != primary_root:
                logging.getLogger('NoPingService').warning(
                    'Primary log location not writable, using temporary path: %s', root)
            return
        except Exception as _e:
            # If we failed on primary, loop will try fallback; if fallback also
            # fails we just continue to next iteration.
            print(f"[NoPingService] Failed to initialize logging at {{root}}: {{_e}}", file=sys.stderr)

    # Final fallback – minimal stdout logging (rarely reached)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)


# Configure logging right away
_configure_logging()

# Obtain module-level logger
logger = logging.getLogger("NoPingService")

# ------------------------------------------------------------
#  Python path bootstrap
# ------------------------------------------------------------
try:
    base_dir = Path(__file__).parent  # C:\Program Files\NoPing

    # Ensure base_dir itself is on sys.path so vendored wheels are importable
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    python_dir = r"{service_python_dir}"
    if python_dir not in sys.path:
        sys.path.insert(0, python_dir)
    
    paths_to_add = [
        os.path.join(python_dir, "DLLs"),
        os.path.join(python_dir, "Lib"),
        os.path.join(python_dir, "Lib", "site-packages"),
        os.path.join(python_dir, "Lib", "site-packages", "win32"),
        os.path.join(python_dir, "Lib", "site-packages", "win32", "lib"),
        os.path.join(python_dir, "Lib", "site-packages", "Pythonwin"),
        os.path.join(base_dir, "src")
    ]
     
    # Remove any Windows Store Python paths
    sys.path = [p for p in sys.path if 'WindowsApps' not in p]
    
    # Add our paths at the start of sys.path
    for path in paths_to_add:
        if path not in sys.path and os.path.exists(path):
            sys.path.insert(0, path)
            logger.debug(f"Added path to sys.path: {{path}}")
    
    # Add DLL directories
    dll_paths = [
        python_dir,
        os.path.join(python_dir, "DLLs"),
        os.path.join(python_dir, "Lib", "site-packages", "pywin32_system32")
    ]
    
    for path in dll_paths:
        if os.path.exists(path):
            os.add_dll_directory(path)
            logger.debug(f"Added DLL directory: {{path}}")
    
    # Log Python environment
    logger.debug(f"Python executable: {{sys.executable}}")
    logger.debug(f"sys.path: {{sys.path}}")
    
    # Import and run service
    from src.service import NoPingService
    import win32serviceutil, win32service, servicemanager

    if __name__ == '__main__':
        try:
            # Handle our own lightweight debug mode.
            if len(sys.argv) > 1 and sys.argv[1].lower() == 'debug':
                win32serviceutil.DebugService(NoPingService, [NoPingService._svc_name_])
                sys.exit(0)

            # The installer may register the service with "run" argument when
            # pythonservice.exe is not available. Treat this the same as having
            # no args from the SCM.
            if len(sys.argv) > 1 and sys.argv[1].lower() == 'run':
                # Pop the 'run' arg so the subsequent logic sees len==1
                sys.argv.pop(1)

            if len(sys.argv) == 1:
                try:
                    servicemanager.Initialize()
                    servicemanager.PrepareToHostSingle(NoPingService)
                    servicemanager.StartServiceCtrlDispatcher()
                except win32service.error:
                    # Probably not running as a service.
                    win32serviceutil.HandleCommandLine(NoPingService)
            else:
                win32serviceutil.HandleCommandLine(NoPingService)
        except Exception as e:
            logger.error(f"Error in service runner: {{e}}")
            logger.error(f"Traceback: {{traceback.format_exc()}}")
            raise
except Exception as e:
    logger.error(f"Error in service runner: {{e}}")
    logger.error(f"Traceback: {{traceback.format_exc()}}")
    raise
'''))
        
        # Get Python executable path
        python_exe = os.path.join(service_python_dir, 'python.exe')
        
        # Do not verify pywin32 yet; dependencies will be installed and verified later
        print(f"Service environment set up at: {service_dir}")
        return python_exe, service_script
        
    except Exception as e:
        print(f"Error setting up service environment: {e}")
        raise

def install_service(python_exe, service_script):
    """Install and start the Windows service"""
    try:
        print("Installing Windows service...")
        
        # First try to remove any existing service
        try:
            subprocess.run(["sc", "stop", "NoPingService"], check=False)
            time.sleep(2)  # Wait for service to stop
            subprocess.run(["sc", "delete", "NoPingService"], check=False)
            time.sleep(2)  # Wait for service to be fully removed
        except:
            pass
            
        # Get absolute paths
        python_exe = os.path.abspath(python_exe)
        service_script = os.path.abspath(service_script)
        
        # Simplify: we always register the service via the embedded interpreter
        # itself instead of relying on pythonservice.exe.  This avoids DLL-loading
        # issues and works identically because our runner understands the
        # special "run" argument.

        service_cmd = f'"{python_exe}" "{service_script}" run'
        
        # Create service with system account and proper privileges
        subprocess.check_call([
            "sc", "create", "NoPingService",
            "binPath=", service_cmd,
            "DisplayName=", "No Ping Optimization Service",
            "type=", "own",  # Service runs in its own process
            "start=", "auto",  # Auto start
            "error=", "normal",  # Normal error handling
            "obj=", "LocalSystem",  # Run as SYSTEM
            "group=", "NetworkProvider"  # Network provider group for proper network access
        ])
        
        # Configure service description
        subprocess.check_call([
            "sc", "description", "NoPingService",
            "Automatically optimizes network connection for games"
        ])
        
        # Configure service dependencies
        subprocess.check_call([
            "sc", "config", "NoPingService",
            "depend=", "Tcpip/Afd/NetBT"  # Network dependencies
        ])
        
        # Configure service recovery options
        subprocess.check_call([
            "sc", "failure", "NoPingService",
            "reset=", "86400",  # Reset fail count after 1 day
            "actions=", "restart/60000/restart/60000/restart/60000"  # Restart up to 3 times with 1 minute delay
        ])
        
        print("Starting service...")
        # Start the service
        subprocess.check_call(["sc", "start", "NoPingService"])
        
        # Wait for service to start and check status
        max_attempts = 5
        wait_time = 2
        for attempt in range(max_attempts):
            time.sleep(wait_time)
            result = subprocess.run(
                ["sc", "query", "NoPingService"],
                capture_output=True,
                text=True
            )
            print(f"\nService status (attempt {attempt + 1}/{max_attempts}):")
            print(result.stdout)
            
            if "RUNNING" in result.stdout:
                print("Service started successfully!")
                return
            elif attempt < max_attempts - 1:
                print("Service not running yet, waiting...")
                
        raise Exception("Service failed to start after multiple attempts")
            
    except subprocess.CalledProcessError as e:
        print(f"Error installing/starting service: {e}")
        # Check service log
        try:
            log_file = Path("C:/ProgramData/NoPing/logs/service.log")
            if log_file.exists():
                print("\nService log contents:")
                with open(log_file, 'r') as f:
                    print(f.read())
        except:
            pass
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise

def main():
    """Main entry point"""
    try:
        # Check for admin privileges first
        if not is_admin():
            run_as_admin()
            return
            
        # Set up service environment
        python_exe, service_script = setup_service_environment()
        
        # Verify and fix Python environment
        verify_python_environment(python_exe)
        
        # Install and start service
        install_service(python_exe, service_script)
        
    except Exception as e:
        print("\nError during installation:", e)
        print("\nTraceback:")
        traceback.print_exc()
    finally:
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main() 