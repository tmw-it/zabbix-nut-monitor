# NUT / Zabbix Monitor

Requirements:
- Network UPS Tools (NUT) installed and configured
- Zabbix agent installed
- Zabbix server 6.4 or later
- Python 3.x with PyYAML and bcrypt modules

This template will automatically discover any UPS devices monitored by NUT and begin collecting data including:
- Battery charge level
- Load percentage
- Runtime remaining
- Battery voltage
- UPS status

Alerts will be triggered for various conditions including:
- Battery charge below 40% (Disaster)
- Battery charge below 90% (High)
- UPS on battery power
- UPS overload
- Other critical status changes

## Installation

Clone this repo & cd into the new directory

`git clone https://github.com/tmw-it/zabbix-nut-monitor && cd zabbix-nut-monitor/`

### Zabbix Configuration
Copy configuration files into /etc/zabbix/

```bash
sudo cp -r zabbix/* /etc/zabbix/
```

Change ownership and add execute privileges for your zabbix agent

```bash
sudo chown zabbix:zabbix /etc/zabbix/sh/ups-keys.sh
sudo chmod a+x /etc/zabbix/sh/ups-keys.sh
sudo chown zabbix:zabbix /etc/zabbix/zabbix_agentd.d/userparameter_nut.conf
```

Restart Zabbix agent to apply changes:

```bash
sudo systemctl restart zabbix-agent
```

### Import Zabbix Template

1. Log into your Zabbix web interface
2. Navigate to Configuration > Templates
3. Click "Import" in the top right
4. Upload the `zabbix_nut_template.yaml` file from this repository
5. Click "Import"

### Link Template to Host

1. Go to Configuration > Hosts
2. Click on your host
3. Go to the Templates tab
4. Click "Link new templates"
5. Search for "Template UPS"
6. Select it and click "Add"
7. Click "Update" to save changes

### Verify Setup

1. Wait a few minutes for discovery to occur
2. Check Configuration > Hosts > your host > Latest data
3. Search for "UPS" to see your monitoring data


