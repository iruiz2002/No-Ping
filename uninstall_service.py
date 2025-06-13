"""
Uninstaller for No Ping Service
Handles both regular Python and Windows Store Python installations
"""

import os
import sys
import subprocess
import ctypes
from pathlib import Path
import shutil
import time

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
            # Give it some time to stop
            time.sleep(2)
        except:
            pass  # Service might already be stopped
        
        # Try both possible service script locations
        service_paths = [
            Path("C:/Program Files/NoPing/noping_service.py"),
            Path(__file__).parent / "src" / "service.py"
        ]
        
        service_removed = False
        for service_path in service_paths:
            if service_path.exists():
                print(f"Removing service using {service_path}...")
                try:
                    subprocess.check_call([
                        sys.executable, str(service_path), "remove"
                    ])
                    service_removed = True
                    break
                except:
                    continue
        
        if not service_removed:
            print("Warning: Could not remove service using service scripts")
            # Try manual removal
            try:
                subprocess.check_call(["sc", "delete", "NoPingService"])
            except:
                pass
        
        # Clean up installation directory
        install_dir = Path("C:/Program Files/NoPing")
        if install_dir.exists():
            print("Removing installation files...")
            try:
                shutil.rmtree(install_dir)
            except Exception as e:
                print(f"Warning: Could not remove all files: {e}")
        
        print("\nNo Ping Service has been uninstalled successfully!")
        
    except Exception as e:
        print(f"Error uninstalling service: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    uninstall_service() 