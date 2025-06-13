"""
Uninstaller for No Ping Service
"""

import os
import sys
import subprocess
import ctypes
from pathlib import Path

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def uninstall_service():
    if not is_admin():
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return

    try:
        print("Uninstalling No Ping Service...")
        
        # Stop the service
        print("Stopping service...")
        try:
            subprocess.check_call(["net", "stop", "NoPingService"])
        except:
            pass  # Service might already be stopped
        
        # Get the current script directory
        current_dir = Path(__file__).parent.absolute()
        service_path = current_dir / "src" / "service.py"
        
        # Uninstall the service
        print("Removing service...")
        subprocess.check_call([
            sys.executable, str(service_path), "remove"
        ])
        
        print("\nNo Ping Service has been uninstalled successfully!")
        
    except Exception as e:
        print(f"Error uninstalling service: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    uninstall_service() 