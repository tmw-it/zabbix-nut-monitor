#!/usr/bin/env python3

"""
Zabbix Configuration Script
Copies and configures Zabbix monitoring files for NUT integration.
"""

import os
import sys
import shutil
import subprocess
import socket
from pathlib import Path

def check_root():
    """Check if script is running with root privileges."""
    if os.geteuid() != 0:
        print("This script must be run as root (sudo).")
        print("Please run: sudo python3 zabbix/zabbix-config.py")
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

def get_host_ip():
    """Get the host's IP address."""
    try:
        # Create a socket connection to force getting the default route IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host_ip = s.getsockname()[0]
        s.close()
        return host_ip
    except Exception as e:
        print(f"Error getting host IP: {e}")
        sys.exit(1)

def get_hostname():
    """Get the system's hostname."""
    try:
        return socket.gethostname()
    except Exception as e:
        print(f"Error getting hostname: {e}")
        sys.exit(1)

def get_zabbix_server_ip():
    """Prompt user for Zabbix server/proxy IP address."""
    while True:
        server_ip = input("\nEnter Zabbix Server/Proxy IP address: ").strip()
        try:
            # Validate IP address format
            socket.inet_aton(server_ip)
            return server_ip
        except socket.error:
            print("Invalid IP address format. Please try again.")

def configure_zabbix_agent():
    """Configure Zabbix agent settings."""
    print("\n=== Configuring Zabbix Agent ===")
    
    # Get system information
    host_ip = get_host_ip()
    hostname = get_hostname()
    server_ip = get_zabbix_server_ip()
    
    # Create backup of original config
    config_file = "/etc/zabbix/zabbix_agent.conf"
    backup_file = "/etc/zabbix/zabbix_agent.conf.bak"
    
    if os.path.exists(config_file):
        shutil.copy2(config_file, backup_file)
        print(f"✓ Created backup of original config: {backup_file}")
    
    # Update configuration
    try:
        with open(config_file, 'r') as f:
            config_lines = f.readlines()
        
        new_config = []
        for line in config_lines:
            if line.startswith('Server='):
                new_config.append(f"Server={server_ip}\n")
            elif line.startswith('ServerActive='):
                new_config.append(f"ServerActive={server_ip}\n")
            elif line.startswith('Hostname='):
                new_config.append(f"Hostname={hostname}\n")
            elif line.startswith('SourceIP='):
                new_config.append(f"SourceIP={host_ip}\n")
            elif line.startswith('ListenIP='):
                new_config.append(f"ListenIP={host_ip}\n")
            else:
                new_config.append(line)
        
        with open(config_file, 'w') as f:
            f.writelines(new_config)
        
        print(f"✓ Updated Zabbix agent configuration:")
        print(f"  - SourceIP: {host_ip}")
        print(f"  - ListenIP: {host_ip}")
        print(f"  - Hostname: {hostname}")
        print(f"  - Server: {server_ip}")
        print(f"  - ServerActive: {server_ip}")
        
        return True
    except Exception as e:
        print(f"Error updating Zabbix configuration: {e}")
        # Restore backup if it exists
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, config_file)
            print("Restored configuration from backup")
        return False

def copy_zabbix_files():
    """Copy Zabbix configuration files to system."""
    print("\n=== Copying Zabbix Files ===")
    
    # Get the script's directory (zabbix/)
    script_dir = Path(__file__).parent.resolve()
    
    try:
        # Create target directories if they don't exist
        os.makedirs("/etc/zabbix", exist_ok=True)
        
        # Copy everything from zabbix/ to /etc/zabbix/ except zabbix-config.py
        for item in script_dir.iterdir():
            if item.name != "zabbix-config.py":
                target_path = Path("/etc/zabbix") / item.name
                if item.is_dir():
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    shutil.copytree(item, target_path)
                    print(f"✓ Copied directory: {item.name}")
                else:
                    if target_path.exists():
                        os.remove(target_path)
                    shutil.copy2(item, target_path)
                    print(f"✓ Copied file: {item.name}")
        
        return True
    except Exception as e:
        print(f"Error copying files: {e}")
        return False

def set_permissions():
    """Set correct permissions for Zabbix files."""
    print("\n=== Setting File Permissions ===")
    
    commands = [
        "chown -R zabbix:zabbix /etc/zabbix/sh",
        "chmod -R a+x /etc/zabbix/sh",
        "chown -R zabbix:zabbix /etc/zabbix/zabbix_agentd.d"
    ]
    
    for cmd in commands:
        if not run_command(cmd, f"Failed to set permissions with: {cmd}"):
            return False
    return True

def restart_zabbix_agent():
    """Restart Zabbix agent service."""
    print("\n=== Restarting Zabbix Agent ===")
    return run_command("systemctl restart zabbix-agent",
                      "Failed to restart Zabbix agent")

def main():
    """Main configuration function."""
    try:
        # Check for root privileges
        check_root()
        
        # Perform configuration steps
        steps = [
            ("Copying Zabbix Files", copy_zabbix_files),
            ("Configuring Zabbix Agent", configure_zabbix_agent),
            ("Setting Permissions", set_permissions),
            ("Restarting Zabbix Agent", restart_zabbix_agent)
        ]
        
        for step_name, step_func in steps:
            print(f"\nExecuting: {step_name}")
            if not step_func():
                print(f"\nError: {step_name} failed. Configuration incomplete.")
                sys.exit(1)
        
        print("\nZabbix configuration completed successfully.")
        
    except KeyboardInterrupt:
        print("\nConfiguration interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 