# SMART Drive Monitoring Setup

This document explains how to configure SMART drive monitoring for Infrastructor across your infrastructure devices.

## Overview

Infrastructor collects SMART (Self-Monitoring, Analysis and Reporting Technology) data from storage devices to monitor drive health, temperature, and other critical metrics. This requires limited sudo access to the `smartctl` command.

## Security Model

The configuration follows the principle of least privilege:
- **Read-only access**: Only information gathering commands are allowed
- **No write operations**: Cannot modify drive settings or run tests
- **Specific binary**: Only the exact `smartctl` binary is permitted
- **Limited scope**: Only `/dev/*` devices are accessible
- **No password required**: Uses NOPASSWD for automated monitoring

## Setup Instructions

### 1. Install smartmontools

On each device you want to monitor:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install smartmontools
```

**CentOS/RHEL/Rocky:**
```bash
sudo yum install smartmontools
# or for newer versions:
sudo dnf install smartmontools
```

**Arch Linux:**
```bash
sudo pacman -S smartmontools
```

### 2. Configure Sudoers

1. **Copy the sudoers file:**
   ```bash
   sudo cp docs/deployment/sudoers.d-smartctl /etc/sudoers.d/smartctl
   ```

2. **Edit the username:**
   Replace `infrastructor` with your actual SSH username:
   ```bash
   sudo sed -i 's/infrastructor/YOUR_SSH_USERNAME/g' /etc/sudoers.d/smartctl
   ```

3. **Set proper permissions:**
   ```bash
   sudo chmod 440 /etc/sudoers.d/smartctl
   sudo chown root:root /etc/sudoers.d/smartctl
   ```

4. **Validate configuration:**
   ```bash
   sudo visudo -c -f /etc/sudoers.d/smartctl
   ```

### 3. Test Configuration

Test that the configuration works:

```bash
# Should work without password prompt:
sudo smartctl -i /dev/sda
sudo smartctl -H /dev/sda  
sudo smartctl -A /dev/sda

# Should fail (not permitted):
sudo smartctl -t short /dev/sda
```

### 4. Configure Infrastructor

Set the SMART monitoring configuration in your Infrastructor deployment:

**Environment Variables:**
```bash
# Enable SMART data collection (default: true)
SMART_MONITORING_ENABLED=true

# Timeout for SMART commands in seconds (default: 15)
SMART_COMMAND_TIMEOUT=15

# Graceful fallback when sudo not available (default: true)  
SMART_GRACEFUL_FALLBACK=true
```

**Or via configuration file:**
```yaml
monitoring:
  smart:
    enabled: true
    command_timeout: 15
    graceful_fallback: true
    require_sudo: false  # Set to true to enforce sudo availability
```

## Supported Devices

The configuration supports all common storage device types:

- **SATA/IDE drives**: `/dev/sda`, `/dev/sdb`, etc.
- **NVMe drives**: `/dev/nvme0n1`, `/dev/nvme1n1`, etc.  
- **eMMC/SD cards**: `/dev/mmcblk0`, etc.
- **RAID controllers**: Device-specific paths

## Monitoring Data Collected

When properly configured, Infrastructor collects:

- **Drive Health Status**: Overall SMART health assessment
- **Temperature**: Current drive temperature in Celsius
- **Power-On Hours**: Total runtime of the drive
- **Wear Leveling**: SSD wear indicators (when available)
- **Error Counts**: Read/write error statistics
- **Data Units Written**: Total data written (NVMe)

## Troubleshooting

### Common Issues

1. **"Permission denied" errors:**
   - Verify sudoers file exists: `ls -la /etc/sudoers.d/smartctl`
   - Check file permissions: should be `440` with `root:root` ownership
   - Validate syntax: `sudo visudo -c -f /etc/sudoers.d/smartctl`

2. **"smartctl: command not found":**
   - Install smartmontools package
   - Check binary location: `which smartctl`
   - Update sudoers file with correct path if needed

3. **SMART data not appearing:**
   - Check device analysis logs: `docker logs infrastructor-api`
   - Verify drives support SMART: `sudo smartctl -i /dev/sda | grep SMART`
   - Test manually: `sudo smartctl -H /dev/sda`

4. **Timeout errors:**
   - Increase `SMART_COMMAND_TIMEOUT` value
   - Check drive responsiveness: some drives are slow to respond

### Fallback Behavior

When sudo access is not available:
- SMART data collection is gracefully skipped
- Device analysis continues with other metrics
- Warning is logged but monitoring doesn't fail
- Basic drive information from `/proc/diskstats` is still collected

### Security Considerations

- **Principle of least privilege**: Only read operations are allowed
- **No password storage**: Uses SSH key authentication + NOPASSWD sudo
- **Limited command scope**: Cannot run drive tests or modify settings
- **Audit trail**: All sudo commands are logged via syslog
- **Regular review**: Periodically audit sudoers configurations

## Alternative Approaches

If sudo access is not feasible:

1. **User groups**: Add SSH user to `disk` group (less secure)
2. **SMART daemon**: Run smartd and read from its output files
3. **Agent deployment**: Run a dedicated monitoring agent with higher privileges
4. **Remote monitoring**: Use hardware-level monitoring (IPMI, iDRAC, iLO)

## Configuration Examples

### Minimal Setup (Single User)
```bash
# /etc/sudoers.d/smartctl
monitoruser ALL=(root) NOPASSWD: /usr/sbin/smartctl -[iHAa] /dev/*
```

### Multi-User Setup
```bash
# /etc/sudoers.d/smartctl
%monitoring ALL=(root) NOPASSWD: /usr/sbin/smartctl -[iHAa] /dev/*
```

### Restrictive Setup (Specific Drives Only)
```bash
# /etc/sudoers.d/smartctl
infrastructor ALL=(root) NOPASSWD: /usr/sbin/smartctl -[iHAa] /dev/sd[a-z], \
                                   /usr/sbin/smartctl -[iHAa] /dev/nvme[0-9]n[0-9]
```

## Automation Scripts

For large deployments, consider automation:

```bash
#!/bin/bash
# deploy-smart-monitoring.sh

HOSTS_FILE="infrastructure-hosts.txt"
SSH_USER="infrastructor"

while read -r host; do
    echo "Configuring SMART monitoring on $host..."
    
    # Copy sudoers file
    scp docs/deployment/sudoers.d-smartctl $SSH_USER@$host:/tmp/
    
    # Install and configure
    ssh $SSH_USER@$host "
        sudo apt update && sudo apt install -y smartmontools
        sudo sed \"s/infrastructor/\$SSH_USER/g\" /tmp/sudoers.d-smartctl > /tmp/smartctl-configured
        sudo mv /tmp/smartctl-configured /etc/sudoers.d/smartctl
        sudo chmod 440 /etc/sudoers.d/smartctl
        sudo chown root:root /etc/sudoers.d/smartctl
        sudo visudo -c -f /etc/sudoers.d/smartctl
        rm /tmp/sudoers.d-smartctl
    "
    
    echo "✓ $host configured"
done < "$HOSTS_FILE"
```

---

For questions or issues with SMART monitoring setup, please refer to the [troubleshooting section](#troubleshooting) or create an issue in the project repository.