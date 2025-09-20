#!/usr/bin/env python3
"""
Obliterator Device Detection Module
Purpose: Detect and enumerate storage devices with detailed information
Runtime: Python 3.x on Bookworm Puppy Linux
Privileges: root required for hardware access
Usage: python3 device-detection.py [--json] [--verbose]
"""

import json
import subprocess
import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeviceDetector:
    """Comprehensive storage device detection and information gathering"""

    def __init__(self):
        self.devices = []
        self.verbose = False

    def run_command(self, cmd: List[str], timeout: int = 30) -> Tuple[str, str, int]:
        """Execute system command safely with timeout"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(cmd)}")
            return "", "Timeout", 1
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return "", str(e), 1

    def detect_block_devices_json(self) -> List[Dict]:
        """Primary detection method using lsblk JSON output"""
        devices = []

        try:
            # Use lsblk with JSON output for comprehensive device info
            stdout, stderr, returncode = self.run_command([
                'lsblk', '-J', '-o',
                'NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL,VENDOR,REV,STATE,ROTA,DISC-MAX'
            ])

            if returncode == 0 and stdout:
                data = json.loads(stdout)
                for device in data.get('blockdevices', []):
                    if device.get('type') == 'disk':
                        device_info = self._parse_lsblk_device(device)
                        if device_info:
                            devices.append(device_info)
            else:
                logger.warning("lsblk JSON method failed, falling back to proc method")
                return self.detect_block_devices_proc()

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return self.detect_block_devices_proc()
        except Exception as e:
            logger.error(f"Device detection failed: {e}")
            return self.detect_block_devices_proc()

        return devices

    def detect_block_devices_proc(self) -> List[Dict]:
        """Fallback detection method using /proc/partitions"""
        devices = []

        try:
            # Read from /proc/partitions
            with open('/proc/partitions', 'r') as f:
                lines = f.readlines()

            for line in lines[2:]:  # Skip header lines
                parts = line.strip().split()
                if len(parts) >= 4:
                    major, minor, blocks, name = parts[:4]

                    # Filter for whole disks (not partitions)
                    if self._is_whole_disk(name):
                        device_path = f"/dev/{name}"
                        device_info = self._get_device_details(device_path, name, int(blocks))
                        if device_info:
                            devices.append(device_info)

        except Exception as e:
            logger.error(f"Proc detection failed: {e}")

        return devices

    def _is_whole_disk(self, name: str) -> bool:
        """Determine if device name represents a whole disk"""
        # Skip partitions (sd[a-z][0-9]+ or nvme[0-9]+n[0-9]+p[0-9]+)
        if re.match(r'^sd[a-z]\d+$', name):
            return False
        if re.match(r'^nvme\d+n\d+p\d+$', name):
            return False
        if re.match(r'^mmcblk\d+p\d+$', name):
            return False

        # Accept whole disks
        if re.match(r'^sd[a-z]$', name):
            return True
        if re.match(r'^nvme\d+n\d+$', name):
            return True
        if re.match(r'^mmcblk\d+$', name):
            return True
        if re.match(r'^hd[a-z]$', name):
            return True

        return False

    def _parse_lsblk_device(self, device: Dict) -> Optional[Dict]:
        """Parse device information from lsblk JSON output"""
        try:
            name = device.get('name', '')
            device_path = f"/dev/{name}"

            # Basic device information
            device_info = {
                'device': device_path,
                'name': name,
                'size_bytes': self._parse_size(device.get('size', '0')),
                'size_human': device.get('size', 'Unknown'),
                'model': device.get('model', '').strip() or 'Unknown',
                'serial': device.get('serial', '').strip() or 'Unknown',
                'vendor': device.get('vendor', '').strip() or 'Unknown',
                'revision': device.get('rev', '').strip() or 'Unknown',
                'rotational': device.get('rota', '0') == '1',
                'removable': self._is_removable(device_path),
                'media_type': self._determine_media_type(device, device_path),
                'mount_points': self._get_mount_points(device),
                'filesystem': device.get('fstype', ''),
                'state': device.get('state', 'running'),
                'transport': self._get_transport_type(device_path),
                'smart_capable': False,
                'smart_health': 'Unknown',
                'temperature': None,
                'power_on_hours': None,
                'hpa_enabled': False,
                'hpa_size': 0,
                'dco_enabled': False,
                'ata_security': 'Unknown',
                'wipe_status': 'Ready'
            }

            # Enhance with additional details
            self._enhance_device_info(device_info)

            return device_info

        except Exception as e:
            logger.error(f"Failed to parse device {device}: {e}")
            return None

    def _get_device_details(self, device_path: str, name: str, blocks: int) -> Optional[Dict]:
        """Get detailed device information for proc fallback method"""
        try:
            device_info = {
                'device': device_path,
                'name': name,
                'size_bytes': blocks * 1024,  # /proc/partitions shows 1K blocks
                'size_human': self._format_size(blocks * 1024),
                'model': 'Unknown',
                'serial': 'Unknown',
                'vendor': 'Unknown',
                'revision': 'Unknown',
                'rotational': True,  # Default assumption
                'removable': self._is_removable(device_path),
                'media_type': 'Unknown',
                'mount_points': [],
                'filesystem': '',
                'state': 'running',
                'transport': self._get_transport_type(device_path),
                'smart_capable': False,
                'smart_health': 'Unknown',
                'temperature': None,
                'power_on_hours': None,
                'hpa_enabled': False,
                'hpa_size': 0,
                'dco_enabled': False,
                'ata_security': 'Unknown',
                'wipe_status': 'Ready'
            }

            # Enhance with additional details
            self._enhance_device_info(device_info)

            return device_info

        except Exception as e:
            logger.error(f"Failed to get details for {device_path}: {e}")
            return None

    def _enhance_device_info(self, device_info: Dict) -> None:
        """Enhance device information with additional data sources"""
        device_path = device_info['device']

        # Get SMART information
        self._add_smart_info(device_info)

        # Get HPA/DCO information for ATA devices
        if device_info['transport'] in ['ata', 'sata']:
            self._add_hpa_dco_info(device_info)

        # Get NVMe specific information
        if 'nvme' in device_path:
            self._add_nvme_info(device_info)

        # Get USB device information
        if device_info['removable']:
            self._add_usb_info(device_info)

        # Determine accurate media type
        device_info['media_type'] = self._determine_final_media_type(device_info)

    def _add_smart_info(self, device_info: Dict) -> None:
        """Add SMART information to device"""
        device_path = device_info['device']

        try:
            stdout, stderr, returncode = self.run_command(['smartctl', '-i', device_path])

            if returncode in [0, 4]:  # 0 = success, 4 = SMART available but device failing
                device_info['smart_capable'] = True

                # Parse SMART info
                for line in stdout.split('\n'):
                    line = line.strip()
                    if 'Device Model:' in line:
                        model = line.split(':', 1)[1].strip()
                        if model and model != 'Unknown':
                            device_info['model'] = model
                    elif 'Serial Number:' in line:
                        serial = line.split(':', 1)[1].strip()
                        if serial and serial != 'Unknown':
                            device_info['serial'] = serial
                    elif 'Firmware Version:' in line:
                        revision = line.split(':', 1)[1].strip()
                        if revision and revision != 'Unknown':
                            device_info['revision'] = revision
                    elif 'Rotation Rate:' in line:
                        rate = line.split(':', 1)[1].strip().lower()
                        device_info['rotational'] = 'solid state' not in rate and 'rpm' in rate

                # Get health status
                stdout, stderr, returncode = self.run_command(['smartctl', '-H', device_path])
                if returncode in [0, 4]:
                    if 'PASSED' in stdout:
                        device_info['smart_health'] = 'PASSED'
                    elif 'FAILED' in stdout:
                        device_info['smart_health'] = 'FAILED'
                    else:
                        device_info['smart_health'] = 'Unknown'

                # Get temperature and power-on hours
                stdout, stderr, returncode = self.run_command(['smartctl', '-A', device_path])
                if returncode in [0, 4]:
                    for line in stdout.split('\n'):
                        if 'Temperature_Celsius' in line or 'Airflow_Temperature_Cel' in line:
                            parts = line.split()
                            if len(parts) >= 10:
                                try:
                                    device_info['temperature'] = int(parts[9])
                                except (ValueError, IndexError):
                                    pass
                        elif 'Power_On_Hours' in line:
                            parts = line.split()
                            if len(parts) >= 10:
                                try:
                                    device_info['power_on_hours'] = int(parts[9])
                                except (ValueError, IndexError):
                                    pass

        except Exception as e:
            logger.error(f"SMART info failed for {device_path}: {e}")

    def _add_hpa_dco_info(self, device_info: Dict) -> None:
        """Add HPA/DCO information for ATA devices"""
        device_path = device_info['device']

        try:
            # Check HPA status
            stdout, stderr, returncode = self.run_command(['hdparm', '-N', device_path])
            if returncode == 0:
                for line in stdout.split('\n'):
                    if 'max sectors' in line.lower():
                        if '/' in line:
                            current, maximum = line.split('/')[-2:]
                            try:
                                current_sectors = int(current.strip().split()[-1])
                                max_sectors = int(maximum.strip().split()[0])
                                if max_sectors > current_sectors:
                                    device_info['hpa_enabled'] = True
                                    device_info['hpa_size'] = (max_sectors - current_sectors) * 512
                            except (ValueError, IndexError):
                                pass

            # Check DCO status
            stdout, stderr, returncode = self.run_command(['hdparm', '--dco-identify', device_path])
            if returncode == 0:
                if 'enabled' in stdout.lower():
                    device_info['dco_enabled'] = True

            # Check ATA security status
            stdout, stderr, returncode = self.run_command(['hdparm', '-I', device_path])
            if returncode == 0:
                security_section = False
                for line in stdout.split('\n'):
                    line = line.strip().lower()
                    if 'security:' in line:
                        security_section = True
                    elif security_section and line:
                        if 'not' in line and ('enabled' in line or 'supported' in line):
                            device_info['ata_security'] = 'Not supported'
                        elif 'supported' in line:
                            device_info['ata_security'] = 'Supported'
                        elif 'enabled' in line:
                            device_info['ata_security'] = 'Enabled'
                        elif 'frozen' in line:
                            device_info['ata_security'] = 'Frozen'
                        break

        except Exception as e:
            logger.error(f"HPA/DCO info failed for {device_path}: {e}")

    def _add_nvme_info(self, device_info: Dict) -> None:
        """Add NVMe specific information"""
        device_path = device_info['device']

        try:
            # Get NVMe device information
            stdout, stderr, returncode = self.run_command(['nvme', 'id-ctrl', device_path])
            if returncode == 0:
                for line in stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('mn '):
                        model = line.split(':', 1)[1].strip() if ':' in line else line[3:].strip()
                        if model and model != 'Unknown':
                            device_info['model'] = model
                    elif line.startswith('sn '):
                        serial = line.split(':', 1)[1].strip() if ':' in line else line[3:].strip()
                        if serial and serial != 'Unknown':
                            device_info['serial'] = serial
                    elif line.startswith('fr '):
                        revision = line.split(':', 1)[1].strip() if ':' in line else line[3:].strip()
                        if revision and revision != 'Unknown':
                            device_info['revision'] = revision

            # Check NVMe SMART/health
            stdout, stderr, returncode = self.run_command(['nvme', 'smart-log', device_path])
            if returncode == 0:
                device_info['smart_capable'] = True
                for line in stdout.split('\n'):
                    line = line.strip().lower()
                    if 'critical_warning' in line:
                        if '0x00' in line:
                            device_info['smart_health'] = 'PASSED'
                        else:
                            device_info['smart_health'] = 'WARNING'
                    elif 'temperature' in line:
                        temp_match = re.search(r'(\d+)', line)
                        if temp_match:
                            # NVMe temperature is in Kelvin, convert to Celsius
                            temp_k = int(temp_match.group(1))
                            device_info['temperature'] = temp_k - 273
                    elif 'power_on_hours' in line:
                        hours_match = re.search(r'(\d+)', line)
                        if hours_match:
                            device_info['power_on_hours'] = int(hours_match.group(1))

        except Exception as e:
            logger.error(f"NVMe info failed for {device_path}: {e}")

    def _add_usb_info(self, device_info: Dict) -> None:
        """Add USB device specific information"""
        device_path = device_info['device']
        device_name = device_info['name']

        try:
            # Get USB device information from lsusb and sysfs
            if device_name.startswith('sd'):
                # Find corresponding USB device
                usb_path = f"/sys/block/{device_name}/device"
                if os.path.exists(usb_path):
                    # Read vendor and product info
                    vendor_file = f"{usb_path}/vendor"
                    model_file = f"{usb_path}/model"

                    if os.path.exists(vendor_file):
                        with open(vendor_file, 'r') as f:
                            vendor = f.read().strip()
                            if vendor:
                                device_info['vendor'] = vendor

                    if os.path.exists(model_file):
                        with open(model_file, 'r') as f:
                            model = f.read().strip()
                            if model:
                                device_info['model'] = model

        except Exception as e:
            logger.error(f"USB info failed for {device_path}: {e}")

    def _determine_media_type(self, device: Dict, device_path: str) -> str:
        """Determine media type from lsblk data"""
        if 'nvme' in device_path:
            return 'NVMe SSD'
        elif device.get('rota', '0') == '0':
            return 'SSD'
        elif device.get('rota', '1') == '1':
            return 'HDD'
        else:
            return 'Unknown'

    def _determine_final_media_type(self, device_info: Dict) -> str:
        """Determine final media type based on all available information"""
        device_path = device_info['device']

        if 'nvme' in device_path:
            return 'NVMe SSD'
        elif 'mmc' in device_path:
            return 'eMMC/SD'
        elif device_info['removable'] and device_info['vendor'] != 'Unknown':
            return 'USB Flash'
        elif not device_info['rotational']:
            return 'SATA SSD'
        elif device_info['rotational']:
            return 'SATA HDD'
        else:
            return 'Unknown'

    def _get_transport_type(self, device_path: str) -> str:
        """Determine device transport type"""
        if 'nvme' in device_path:
            return 'nvme'
        elif 'mmc' in device_path:
            return 'mmc'
        else:
            # Check if it's SATA or ATA
            try:
                stdout, stderr, returncode = self.run_command(['smartctl', '-i', device_path])
                if 'ATA' in stdout or 'SATA' in stdout:
                    return 'sata'
                elif 'USB' in stdout:
                    return 'usb'
                else:
                    return 'ata'
            except:
                return 'unknown'

    def _is_removable(self, device_path: str) -> bool:
        """Check if device is removable"""
        device_name = os.path.basename(device_path)
        removable_file = f"/sys/block/{device_name}/removable"

        try:
            if os.path.exists(removable_file):
                with open(removable_file, 'r') as f:
                    return f.read().strip() == '1'
        except:
            pass
        return False

    def _get_mount_points(self, device: Dict) -> List[str]:
        """Extract mount points from lsblk device data"""
        mount_points = []

        # Check main device
        if device.get('mountpoint'):
            mount_points.append(device['mountpoint'])

        # Check children (partitions)
        for child in device.get('children', []):
            if child.get('mountpoint'):
                mount_points.append(child['mountpoint'])

        return mount_points

    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        if not size_str or size_str == '0':
            return 0

        size_str = size_str.upper().strip()

        # Handle different size formats
        multipliers = {
            'B': 1,
            'K': 1024, 'KB': 1024, 'KIB': 1024,
            'M': 1024**2, 'MB': 1024**2, 'MIB': 1024**2,
            'G': 1024**3, 'GB': 1024**3, 'GIB': 1024**3,
            'T': 1024**4, 'TB': 1024**4, 'TIB': 1024**4,
            'P': 1024**5, 'PB': 1024**5, 'PIB': 1024**5
        }

        # Extract number and unit
        match = re.match(r'([0-9.]+)\s*([A-Z]*)', size_str)
        if match:
            number_str, unit = match.groups()
            try:
                number = float(number_str)
                multiplier = multipliers.get(unit, 1)
                return int(number * multiplier)
            except ValueError:
                pass

        return 0

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"

        units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"

    def detect_all_devices(self) -> List[Dict]:
        """Main device detection method"""
        logger.info("Starting device detection...")

        # Try JSON method first, fall back to proc method
        devices = self.detect_block_devices_json()

        if not devices:
            logger.warning("JSON detection failed, using proc method")
            devices = self.detect_block_devices_proc()

        # Filter out obviously unsuitable devices
        filtered_devices = []
        for device in devices:
            # Skip very small devices (< 1MB)
            if device['size_bytes'] < 1024 * 1024:
                continue

            # Skip loop devices, ram disks, etc.
            if any(skip in device['name'] for skip in ['loop', 'ram', 'dm-', 'sr']):
                continue

            # Skip mounted root filesystem by default
            if any(mount in ['/'] for mount in device['mount_points']):
                device['wipe_status'] = 'Protected (Root FS)'

            filtered_devices.append(device)

        logger.info(f"Detected {len(filtered_devices)} storage devices")
        return filtered_devices

    def get_device_summary(self, device: Dict) -> str:
        """Generate a human-readable device summary"""
        summary_parts = [
            f"{device['device']}",
            f"{device['model'][:20]}..." if len(device['model']) > 20 else device['model'],
            f"{device['size_human']}",
            f"{device['media_type']}"
        ]

        if device['serial'] != 'Unknown':
            summary_parts.append(f"S/N: {device['serial'][:10]}...")

        if device['hpa_enabled']:
            summary_parts.append("HPA")

        if device['dco_enabled']:
            summary_parts.append("DCO")

        if device['mount_points']:
            summary_parts.append(f"Mounted: {', '.join(device['mount_points'])}")

        return " | ".join(summary_parts)

def main():
    """Main function for standalone execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Obliterator Device Detection')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--device', help='Get info for specific device')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    detector = DeviceDetector()
    detector.verbose = args.verbose

    if args.device:
        # Get info for specific device
        devices = detector.detect_all_devices()
        target_device = None

        for device in devices:
            if device['device'] == args.device or device['name'] == args.device:
                target_device = device
                break

        if target_device:
            if args.json:
                print(json.dumps(target_device, indent=2))
            else:
                print(f"Device Information for {target_device['device']}:")
                for key, value in target_device.items():
                    print(f"  {key}: {value}")
        else:
            print(f"Device {args.device} not found")
            sys.exit(1)
    else:
        # Get all devices
        devices = detector.detect_all_devices()

        if args.json:
            print(json.dumps(devices, indent=2))
        else:
            print(f"Found {len(devices)} storage devices:")
            print("-" * 80)

            for device in devices:
                print(detector.get_device_summary(device))

                if args.verbose:
                    print(f"  Serial: {device['serial']}")
                    print(f"  Vendor: {device['vendor']}")
                    print(f"  Transport: {device['transport']}")
                    print(f"  SMART: {device['smart_health']}")
                    print(f"  Status: {device['wipe_status']}")

                    if device['temperature']:
                        print(f"  Temperature: {device['temperature']}°C")
                    if device['power_on_hours']:
                        print(f"  Power-on Hours: {device['power_on_hours']}")
                    if device['hpa_enabled']:
                        print(f"  HPA Size: {detector._format_size(device['hpa_size'])}")

                    print()

if __name__ == "__main__":
    main()

