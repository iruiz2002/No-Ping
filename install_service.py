"""
Installer for No Ping Service
"""

import os
import sys
import subprocess
import winreg
import ctypes
from pathlib import Path

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def install_service():
    if not is_admin():
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return

    try:
        print("Installing No Ping Service...")
        
        # Install required Python packages
        print("Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32", "psutil", "requests"])
        
        # Get the current script directory
        current_dir = Path(__file__).parent.absolute()
        
        # Create service command
        python_path = sys.executable
        service_path = current_dir / "src" / "service.py"
        
        # Install the service
        print("Installing Windows service...")
        subprocess.check_call([
            python_path, str(service_path), 
            "--startup", "auto", "install"
        ])
        
        # Start the service
        print("Starting service...")
        subprocess.check_call([
            "net", "start", "NoPingService"
        ])
        
        print("\nNo Ping Service has been installed and started successfully!")
        print("The service will automatically start when Windows boots.")
        print("\nTo uninstall the service, run: python uninstall_service.py")
        
    except Exception as e:
        print(f"Error installing service: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    install_service() 