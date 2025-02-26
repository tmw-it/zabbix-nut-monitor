#!/usr/bin/env python3

import os
import yaml
import socket
from string import Template
import glob
import subprocess
import re
import bcrypt
import getpass
import sys
import shutil

def get_user_config():
    """Interactively get user configuration"""
    print("\nNUT User Configuration")
    print("---------------------")
    
    # Get username
    username = input("Enter NUT username: ").strip()
    while not username:
        print("Username cannot be empty")
        username = input("Enter NUT username: ").strip()
    
    # Get password securely (won't show on screen)
    while True:
        password = getpass.getpass("Enter password: ")
        if not password:
            print("Password cannot be empty")
            continue
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords don't match")
            continue
        break
    
    # Hash the password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Get user mode
    while True:
        mode = input("Select user mode (1-Primary, 2-Secondary): ").strip()
        if mode == "1":
            user_mode = "primary"
            break
        elif mode == "2":
            user_mode = "secondary"
            break
        print("Please enter 1 for Primary or 2 for Secondary")
    
    # Get device location
    location = input("Enter device location (e.g., Server Room, Office): ").strip()
    while not location:
        print("Location cannot be empty")
        location = input("Enter device location: ").strip()
    
    return {
        'username': username,
        'password_hash': password_hash,
        'user_mode': user_mode,
        'location': location
    }

def detect_ups_devices(vendor_mappings):
    """Detect UPS devices using lsusb command"""
    try:
        # Run lsusb command and capture output
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if result.returncode != 0:
            print("Warning: Failed to run lsusb command")
            return []

        ups_devices = []
        # Parse each line of lsusb output
        for line in result.stdout.splitlines():
            # Example line: Bus 001 Device 003: ID 0764:0601 Cyber Power System, Inc. PR1500LCDRT2U UPS
            match = re.search(r'ID (\w+):(\w+)\s+(.+)$', line)
            if match:
                vendor_id, product_id, description = match.groups()
                if vendor_id.lower() in vendor_mappings:
                    ups_devices.append({
                        'vendor_id': vendor_id.lower(),
                        'product_id': product_id.lower(),
                        'description': description,
                        'vendor_name': vendor_mappings[vendor_id],
                        'bus_device': re.search(r'Bus (\d+) Device (\d+):', line).groups()
                    })
        
        return ups_devices
    except Exception as e:
        print(f"Warning: Error detecting UPS devices: {e}")
        return []

def load_config():
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Add hostname to config
    config['hostname'] = socket.gethostname()
    
    # Get vendor mappings from config
    vendor_mappings = config.get('vendors', {})
    
    # Detect UPS devices and add to config
    ups_devices = detect_ups_devices(vendor_mappings)
    config['ups_devices'] = ups_devices
    
    # Count occurrences of each vendor
    vendor_counts = {}
    for device in ups_devices:
        vendor_name = device['vendor_name'].lower()
        vendor_counts[vendor_name] = vendor_counts.get(vendor_name, 0) + 1
    
    # Assign names based on vendor counts
    vendor_indices = {}
    for i, device in enumerate(ups_devices):
        vendor_name = device['vendor_name'].lower()
        if vendor_counts[vendor_name] > 1:
            # Multiple units from this vendor, use numbering
            vendor_indices[vendor_name] = vendor_indices.get(vendor_name, 0) + 1
            config[f'ups{i+1}'] = f"{vendor_name}{vendor_indices[vendor_name]}"
        else:
            # Single unit from this vendor, no number needed
            config[f'ups{i+1}'] = vendor_name
    
    # Get user configuration
    user_config = get_user_config()
    config.update(user_config)
    
    return config

def process_template(template_path, output_path, config):
    """Process a template file and write the result to the output file."""
    try:
        with open(template_path, 'r') as f:
            template_content = f.read()
    except FileNotFoundError:
        print(f"Error: Template file not found: {template_path}")
        return
    except Exception as e:
        print(f"Error reading template file {template_path}: {e}")
        return

    # If output file exists, read existing manual configurations
    manual_config = ""
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r') as f:
                content = f.read()
                if '### MANUAL CONFIGURATIONS ###' in content:
                    manual_config = content.split('### MANUAL CONFIGURATIONS ###')[1]
        except Exception as e:
            print(f"Warning: Could not read existing manual configurations from {output_path}: {e}")

    # Process the template based on file type
    if 'upsd.users' in output_path:
        # Prepare user configuration
        user_config = f"""[{config['username']}]
  password = {config['password_hash']}
  upsmon {config['user_mode']}"""
        result = template_content.replace('$USER_CONFIG', user_config)
    elif 'ups.conf' in output_path:
        # Prepare UPS device configurations
        ups_configs = []
        for i, device in enumerate(config.get('ups_devices', []), 1):
            ups_config = f"""[{config.get(f'ups{i}', f'ups{i}')}]
  driver = usbhid-ups
  port = auto
  desc = "{config['location']} - {device['description']}"
  vendorid = {device['vendor_id']}
  productid = {device['product_id']}"""
            ups_configs.append(ups_config)
        
        result = template_content.replace('$UPS_CONFIGS', '\n\n'.join(ups_configs) if ups_configs else '# No UPS devices detected')
    elif 'upsmon.conf' in output_path:
        # Prepare monitor lines for each UPS
        monitor_lines = []
        for i, device in enumerate(config.get('ups_devices', []), 1):
            ups_name = config.get(f'ups{i}', f'ups{i}')
            monitor_line = f"MONITOR {ups_name}@{config['hostname']} 1 {config['username']} {config['password_hash']} {config['user_mode']}"
            monitor_lines.append(monitor_line)
        
        # If no UPS devices found, add a comment
        if not monitor_lines:
            monitor_lines = ['# No UPS devices detected']
        
        result = template_content.replace('MONITOR $UPS1@localhost 1 $username $password $user_mode', '\n'.join(monitor_lines))
    else:
        # For other templates, process all variables
        result = template_content
        for key, value in config.items():
            result = result.replace(f'${key}', str(value))

    # If we found manual configurations, ensure they're preserved
    if manual_config:
        result = result.split('### MANUAL CONFIGURATIONS ###')[0] + '### MANUAL CONFIGURATIONS ###' + manual_config
    
    try:
        with open(output_path, 'w') as f:
            f.write(result)
        print(f"Generated {output_path}")
    except Exception as e:
        print(f"Error writing output file {output_path}: {e}")

def copy_static_files(script_dir):
    """Copy static configuration files that don't need processing"""
    static_files = [
        'upsd.conf.template',
        'nut.conf.template',
        'upssched.conf.template',
        'upsset.conf.template',
        'upsstats.html.template',
        'hosts.conf.template'
    ]

    for template in static_files:
        src = os.path.join(script_dir, template)
        dst = os.path.join(script_dir, template[:-9])  # Remove .template extension
        try:
            shutil.copy2(src, dst)
            print(f"Copied {template} to {dst}")
        except FileNotFoundError:
            print(f"Warning: Static template file not found: {src}")
        except Exception as e:
            print(f"Error copying {src} to {dst}: {e}")

def main():
    """Main function to generate all configuration files"""
    try:
        config = load_config()
        
        # Get script directory and template directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(script_dir, 'templates')
        
        # Process template files that need configuration
        template_files = [
            'ups.conf.template',
            'upsd.users.template',
            'upsmon.conf.template'
        ]
        
        # Process each template file
        for template_name in template_files:
            template_path = os.path.join(template_dir, template_name)
            output_path = os.path.join(script_dir, template_name[:-9])  # remove '.template'
            process_template(template_path, output_path, config)
        
        # Copy static files
        copy_static_files(script_dir)
        
    except Exception as e:
        print(f"Error in main function: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 