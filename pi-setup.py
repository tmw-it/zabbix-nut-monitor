#!/usr/bin/env python3

"""
Raspberry Pi Setup Script for Zabbix NUT Monitor
This script performs initial system setup and orchestrates the configuration
of Zabbix Agent and Network UPS Tools (NUT).

Exit Codes:
    1: Script not run as root
    2: System update failed
    3: Dependencies installation failed
    4: Zabbix agent installation failed
    5: Zabbix configuration failed
    6: NUT installation failed
    7: NUT configuration failed
    8: Unexpected error
"""

import os
import sys
import time
import subprocess
import shutil
from pathlib import Path

def check_root():
    """Check if script is running with root privileges."""
    if os.geteuid() != 0:
        print("This script must be run as root (sudo).")
        print("Please run: sudo python3 pi-setup.py")
        sys.exit(1)

def run_command(command, error_msg=None):
    """Run a shell command and handle errors."""
    try:
        process = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(process.stdout)
        return True
    except subprocess.CalledProcessError as e:
        if error_msg:
            print(f"Error: {error_msg}")
        print(f"Command failed: {e.stderr}")
        return False

def system_update():
    """Perform system update and upgrade."""
    print("\n=== Step 1: Updating System ===")
    if not run_command("apt-get update", "Failed to update package list"):
        print("System update failed")
        sys.exit(2)
    if not run_command("apt-get upgrade -y", "Failed to upgrade packages"):
        print("System upgrade failed")
        sys.exit(2)
    print("✓ System update completed successfully")

def install_dependencies():
    """Install required Python and system packages."""
    print("\n=== Step 2: Installing Dependencies ===")
    packages = [
        "python3",
        "python3-pip",
        "python3-yaml",
        "python3-bcrypt",
        "usbutils"  # for lsusb command
    ]
    
    if not run_command(f"apt-get install -y {' '.join(packages)}", 
                      "Failed to install Python dependencies"):
        print("Dependencies installation failed")
        sys.exit(3)
    print("✓ Dependencies installed successfully")

def install_and_configure_zabbix():
    """Install and configure Zabbix Agent."""
    print("\n=== Step 3: Installing Zabbix Agent 7.0 ===")
    
    # Add Zabbix 7.0 repository for Ubuntu
    if not run_command(
        "wget https://repo.zabbix.com/zabbix/7.0/ubuntu/pool/main/z/zabbix-release/zabbix-release_7.0-1+ubuntu24.04_all.deb && " +
        "dpkg -i zabbix-release_7.0-1+ubuntu24.04_all.deb && " +
        "apt-get update",
        "Failed to add Zabbix repository"):
        print("Zabbix repository setup failed")
        sys.exit(4)
    
    if not run_command("apt-get install -y zabbix-agent",
                      "Failed to install Zabbix agent"):
        print("Zabbix agent installation failed")
        sys.exit(4)
    print("✓ Zabbix agent installed successfully")

    # Create lib directory and backup default configs
    print("\n=== Backing up default Zabbix configuration ===")
    try:
        os.makedirs("/etc/zabbix/lib", exist_ok=True)
        if os.path.exists("/etc/zabbix/zabbix_agentd.conf"):
            shutil.move("/etc/zabbix/zabbix_agentd.conf", "/etc/zabbix/lib/")
            print("✓ Moved default zabbix_agentd.conf to lib directory")
    except Exception as e:
        print(f"Error backing up Zabbix configuration: {e}")
        sys.exit(4)

    print("\n=== Configuring Zabbix ===")
    if not run_command("python3 zabbix/zabbix-config.py",
                      "Failed to configure Zabbix"):
        print("Zabbix configuration failed")
        sys.exit(5)
    print("✓ Zabbix configured successfully")

def install_and_configure_nut():
    """Install and configure Network UPS Tools."""
    print("\n=== Step 4: Installing NUT ===")
    if not run_command("apt-get install -y nut nut-client",
                      "Failed to install NUT"):
        print("NUT installation failed")
        sys.exit(6)
    print("✓ NUT installed successfully")

    # Create lib directory and backup default configs
    print("\n=== Backing up default NUT configuration ===")
    try:
        os.makedirs("/etc/nut/lib", exist_ok=True)
        # Move all files from /etc/nut to /etc/nut/lib except the lib directory itself
        for item in os.listdir("/etc/nut"):
            if item != "lib":
                src = os.path.join("/etc/nut", item)
                dst = os.path.join("/etc/nut/lib", item)
                shutil.move(src, dst)
        print("✓ Moved default NUT configuration files to lib directory")
    except Exception as e:
        print(f"Error backing up NUT configuration: {e}")
        sys.exit(6)

    print("\n=== Configuring NUT ===")
    if not run_command("python3 nut/nut-config.py",
                      "Failed to configure NUT"):
        print("NUT configuration failed")
        sys.exit(7)
    print("✓ NUT configured successfully")

def schedule_reboot():
    """Schedule system reboot with countdown."""
    print("\n=== Step 5: Setup Complete - Scheduling Reboot ===")
    print("System will reboot in 30 seconds.")
    print("Press Enter to reboot now, or any other key to cancel.")
    
    try:
        for i in range(30, 0, -1):
            print(f"\rRebooting in {i} seconds... ", end="", flush=True)
            # Wait for either 1 second or check for keypress
            try:
                result = subprocess.run("read -t 1 -n 1", shell=True, executable="/bin/bash")
                if result.returncode == 0:  # A key was pressed
                    # Check if it was Enter (empty input)
                    char = subprocess.run("echo -n $REPLY", shell=True, executable="/bin/bash", 
                                       capture_output=True, text=True).stdout
                    if char == "":  # Enter was pressed
                        print("\nRebooting now...")
                        break
                    else:  # Any other key was pressed
                        print("\nReboot cancelled. Please reboot manually when ready.")
                        sys.exit(0)
            except subprocess.CalledProcessError:
                continue
        
        os.system("reboot")
    except Exception as e:
        print(f"\nError during reboot scheduling: {e}")
        print("Please reboot manually when ready.")
        sys.exit(0)

def main():
    """Main setup function."""
    try:
        # Check for root privileges
        check_root()
        
        # Execute steps in order
        system_update()
        install_dependencies()
        install_and_configure_zabbix()
        install_and_configure_nut()
        schedule_reboot()
        
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(8)

if __name__ == "__main__":
    main() 