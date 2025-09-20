#!/usr/bin/env python3
"""
Obliterator Wiping Engine
Purpose: Secure data sanitization following NIST SP 800-88r2 guidelines
Runtime: Python 3.x on Bookworm Puppy Linux with root privileges
Privileges: root required for direct device access
Usage: python3 wiping-engine.py --device /dev/sdX --method purge --confirm TOKEN
"""

import os
import sys
import time
import random
import hashlib
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import threading
import signal

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SanitizationMethod(Enum):
    """NIST SP 800-88r2 Sanitization Methods"""
    CLEAR = "clear"      # Single pass, accessible areas only
    PURGE = "purge"      # Multiple passes, all areas including HPA/DCO
    DESTROY = "destroy"  # Physical destruction (guidance only)

class WipeStatus(Enum):
    """Wipe operation status"""
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WipePass:
    """Individual wipe pass configuration"""
    pass_id: int
    name: str
    pattern_type: str  # 'random', 'zeros', 'ones', 'pattern', 'complement'
    pattern_data: Optional[bytes] = None
    verify: bool = True

@dataclass
class WipeProgress:
    """Wipe progress tracking"""
    device: str
    current_pass: int
    total_passes: int
    pass_name: str
    bytes_written: int
    total_bytes: int
    bytes_per_second: float
    elapsed_time: float
    estimated_remaining: float
    verification_status: str = "pending"
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class WipingEngine:
    """Main wiping engine implementing NIST SP 800-88r2 compliant sanitization"""

    def __init__(self):
        self.current_wipe = None
        self.progress_callback: Optional[Callable[[WipeProgress], None]] = None
        self.status = WipeStatus.READY
        self.stop_requested = False
        self.pause_requested = False

        # NIST-compliant wipe patterns
        self.wipe_patterns = {
            SanitizationMethod.CLEAR: [
                WipePass(1, "Single Random Pass", "random", verify=True)
            ],
            SanitizationMethod.PURGE: [
                WipePass(1, "Random Pass 1", "random", verify=True),
                WipePass(2, "Complement Pass", "complement", verify=True),
                WipePass(3, "Random Pass 2", "random", verify=True),
                WipePass(4, "Pattern Pass (0x55)", "pattern", b'\x55', verify=True),
                WipePass(5, "Final Zero Pass", "zeros", verify=True)
            ]
        }

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.warning(f"Received signal {signum}, requesting stop...")
        self.request_stop()

    def set_progress_callback(self, callback: Callable[[WipeProgress], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    def request_stop(self):
        """Request wipe operation to stop"""
        self.stop_requested = True
        logger.info("Stop requested")

    def request_pause(self):
        """Request wipe operation to pause"""
        self.pause_requested = True
        logger.info("Pause requested")

    def resume(self):
        """Resume paused wipe operation"""
        if self.status == WipeStatus.PAUSED:
            self.pause_requested = False
            self.status = WipeStatus.RUNNING
            logger.info("Wipe resumed")

    def get_device_info(self, device_path: str) -> Dict:
        """Get device information for wiping"""
        try:
            # Get device size
            with open(device_path, 'rb') as device:
                device.seek(0, 2)  # Seek to end
                size = device.tell()

            # Get device details
            info = {
                'path': device_path,
                'size_bytes': size,
                'size_human': self._format_size(size),
                'block_size': 4096,  # Default block size
                'supports_ata_secure_erase': self._check_ata_secure_erase(device_path),
                'supports_nvme_secure_erase': self._check_nvme_secure_erase(device_path),
                'has_hpa': self._check_hpa(device_path),
                'has_dco': self._check_dco(device_path),
                'is_mounted': self._check_mounted(device_path)
            }

            return info

        except Exception as e:
            logger.error(f"Failed to get device info for {device_path}: {e}")
            raise

    def _check_ata_secure_erase(self, device_path: str) -> bool:
        """Check if device supports ATA Secure Erase"""
        try:
            result = subprocess.run(['hdparm', '-I', device_path],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                output = result.stdout.lower()
                return 'security' in output and 'erase' in output
        except:
            pass
        return False

    def _check_nvme_secure_erase(self, device_path: str) -> bool:
        """Check if NVMe device supports secure erase"""
        if 'nvme' not in device_path:
            return False
        try:
            result = subprocess.run(['nvme', 'id-ctrl', device_path],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Check for Format NVM or Sanitize support
                return 'sanitize' in result.stdout.lower() or 'format' in result.stdout.lower()
        except:
            pass
        return False

    def _check_hpa(self, device_path: str) -> bool:
        """Check if device has Host Protected Area enabled"""
        try:
            result = subprocess.run(['hdparm', '-N', device_path],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return '/' in result.stdout  # Indicates current/max sectors differ
        except:
            pass
        return False

    def _check_dco(self, device_path: str) -> bool:
        """Check if device has Device Configuration Overlay"""
        try:
            result = subprocess.run(['hdparm', '--dco-identify', device_path],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return 'enabled' in result.stdout.lower()
        except:
            pass
        return False

    def _check_mounted(self, device_path: str) -> bool:
        """Check if device or its partitions are mounted"""
        try:
            with open('/proc/mounts', 'r') as f:
                mounts = f.read()
            return device_path in mounts
        except:
            return False

    def prepare_device(self, device_path: str) -> bool:
        """Prepare device for wiping (remove HPA/DCO, unmount, etc.)"""
        logger.info(f"Preparing device {device_path} for wiping")

        try:
            # Unmount any mounted filesystems
            self._unmount_device(device_path)

            # Remove HPA if present
            if self._check_hpa(device_path):
                logger.info("Removing Host Protected Area")
                if not self._remove_hpa(device_path):
                    logger.warning("Failed to remove HPA")

            # Remove DCO if present
            if self._check_dco(device_path):
                logger.info("Removing Device Configuration Overlay")
                if not self._remove_dco(device_path):
                    logger.warning("Failed to remove DCO")

            return True

        except Exception as e:
            logger.error(f"Failed to prepare device {device_path}: {e}")
            return False

    def _unmount_device(self, device_path: str):
        """Unmount device and all its partitions"""
        try:
            # Get all partitions for this device
            result = subprocess.run(['lsblk', '-ln', '-o', 'NAME', device_path],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                devices = [f"/dev/{line.strip()}" for line in result.stdout.strip().split('\n') if line.strip()]

                for dev in devices:
                    try:
                        subprocess.run(['umount', dev], capture_output=True, timeout=30)
                    except:
                        pass  # Ignore errors for non-mounted devices

        except Exception as e:
            logger.warning(f"Failed to unmount {device_path}: {e}")

    def _remove_hpa(self, device_path: str) -> bool:
        """Remove Host Protected Area"""
        try:
            # First get the maximum size
            result = subprocess.run(['hdparm', '-N', device_path],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and '/' in result.stdout:
                # Set to maximum size
                result = subprocess.run(['hdparm', '-N', 'pmax', device_path],
                                      capture_output=True, text=True, timeout=30)
                return result.returncode == 0
        except Exception as e:
            logger.error(f"HPA removal failed: {e}")
        return False

    def _remove_dco(self, device_path: str) -> bool:
        """Remove Device Configuration Overlay"""
        try:
            result = subprocess.run(['hdparm', '--dco-restore', device_path],
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"DCO removal failed: {e}")
        return False

    def wipe_device(self, device_path: str, method: SanitizationMethod,
                   confirm_token: str, dry_run: bool = False) -> bool:
        """
        Main device wiping function

        Args:
            device_path: Path to device (e.g., /dev/sda)
            method: Sanitization method (CLEAR, PURGE, DESTROY)
            confirm_token: Confirmation token for safety
            dry_run: If True, show what would be done without doing it
        """

        if method == SanitizationMethod.DESTROY:
            logger.info("DESTROY method requires physical destruction - see documentation")
            return True

        logger.info(f"Starting {method.value} wipe of {device_path}")

        # Validate device exists and is accessible
        if not os.path.exists(device_path):
            raise ValueError(f"Device {device_path} does not exist")

        if not os.access(device_path, os.R_OK | os.W_OK):
            raise PermissionError(f"Insufficient permissions for {device_path}")

        # Get device information
        device_info = self.get_device_info(device_path)

        if dry_run:
            logger.info("DRY RUN MODE - No actual wiping will be performed")
            self._show_wipe_plan(device_path, method, device_info)
            return True

        # Safety checks
        if device_info['is_mounted']:
            raise ValueError(f"Device {device_path} has mounted filesystems")

        # Prepare device for wiping
        if not self.prepare_device(device_path):
            raise RuntimeError(f"Failed to prepare device {device_path}")

        # Initialize progress tracking
        passes = self.wipe_patterns[method]
        progress = WipeProgress(
            device=device_path,
            current_pass=0,
            total_passes=len(passes),
            pass_name="Initializing",
            bytes_written=0,
            total_bytes=device_info['size_bytes'],
            bytes_per_second=0.0,
            elapsed_time=0.0,
            estimated_remaining=0.0
        )

        self.current_wipe = progress
        self.status = WipeStatus.RUNNING
        start_time = time.time()

        try:
            # Check if we can use hardware-accelerated erase
            if (method == SanitizationMethod.PURGE and
                device_info['supports_ata_secure_erase']):
                logger.info("Using ATA Secure Erase")
                success = self._ata_secure_erase(device_path, progress)
            elif (method == SanitizationMethod.PURGE and
                  device_info['supports_nvme_secure_erase']):
                logger.info("Using NVMe Secure Erase")
                success = self._nvme_secure_erase(device_path, progress)
            else:
                # Use multi-pass overwrite
                success = self._multipass_wipe(device_path, passes, progress)

            if success and not self.stop_requested:
                self.status = WipeStatus.COMPLETED
                progress.pass_name = "Completed"
                progress.elapsed_time = time.time() - start_time

                if self.progress_callback:
                    self.progress_callback(progress)

                logger.info(f"Wipe completed successfully in {progress.elapsed_time:.1f} seconds")
                return True
            else:
                self.status = WipeStatus.FAILED if not self.stop_requested else WipeStatus.CANCELLED
                return False

        except Exception as e:
            logger.error(f"Wipe failed: {e}")
            self.status = WipeStatus.FAILED
            progress.errors.append(str(e))

            if self.progress_callback:
                self.progress_callback(progress)

            return False
        finally:
            self.current_wipe = None

    def _show_wipe_plan(self, device_path: str, method: SanitizationMethod, device_info: Dict):
        """Show what would be done in dry-run mode"""
        print(f"\n--- WIPE PLAN FOR {device_path} ---")
        print(f"Device Size: {device_info['size_human']} ({device_info['size_bytes']} bytes)")
        print(f"Method: {method.value.upper()}")

        if device_info['has_hpa']:
            print("- Remove Host Protected Area")
        if device_info['has_dco']:
            print("- Remove Device Configuration Overlay")

        if method in self.wipe_patterns:
            passes = self.wipe_patterns[method]
            print(f"Wipe Passes ({len(passes)}):")
            for pass_info in passes:
                verify_text = " + verify" if pass_info.verify else ""
                print(f"  {pass_info.pass_id}. {pass_info.name} ({pass_info.pattern_type}){verify_text}")

        if device_info['supports_ata_secure_erase'] and method == SanitizationMethod.PURGE:
            print("- Use ATA Secure Erase (hardware accelerated)")
        elif device_info['supports_nvme_secure_erase'] and method == SanitizationMethod.PURGE:
            print("- Use NVMe Secure Erase (hardware accelerated)")

        print("--- END WIPE PLAN ---\n")

    def _multipass_wipe(self, device_path: str, passes: List[WipePass],
                       progress: WipeProgress) -> bool:
        """Perform multi-pass overwrite wipe"""

        for pass_info in passes:
            if self.stop_requested:
                logger.info("Stop requested during wipe")
                return False

            progress.current_pass = pass_info.pass_id
            progress.pass_name = pass_info.name
            progress.bytes_written = 0

            logger.info(f"Starting pass {pass_info.pass_id}: {pass_info.name}")

            # Generate pattern for this pass
            if pass_info.pattern_type == "random":
                pattern = self._generate_random_pattern()
            elif pass_info.pattern_type == "zeros":
                pattern = b'\x00' * 4096
            elif pass_info.pattern_type == "ones":
                pattern = b'\xff' * 4096
            elif pass_info.pattern_type == "pattern":
                pattern = pass_info.pattern_data * (4096 // len(pass_info.pattern_data))
            elif pass_info.pattern_type == "complement":
                # Use complement of previous pass (simplified)
                pattern = self._generate_complement_pattern()
            else:
                logger.error(f"Unknown pattern type: {pass_info.pattern_type}")
                return False

            # Perform the write pass
            if not self._write_pattern(device_path, pattern, progress):
                return False

            # Verify the pass if requested
            if pass_info.verify:
                logger.info(f"Verifying pass {pass_info.pass_id}")
                if not self._verify_pattern(device_path, pattern, progress):
                    logger.warning(f"Verification failed for pass {pass_info.pass_id}")
                    progress.verification_status = "failed"
                else:
                    progress.verification_status = "passed"

        return True

    def _write_pattern(self, device_path: str, pattern: bytes,
                      progress: WipeProgress) -> bool:
        """Write pattern to entire device"""

        try:
            with open(device_path, 'r+b') as device:
                device_size = progress.total_bytes
                bytes_written = 0
                start_time = time.time()
                last_update = start_time

                while bytes_written < device_size and not self.stop_requested:
                    # Handle pause requests
                    while self.pause_requested and not self.stop_requested:
                        self.status = WipeStatus.PAUSED
                        time.sleep(0.1)

                    if self.stop_requested:
                        break

                    self.status = WipeStatus.RUNNING

                    # Calculate chunk size
                    remaining = device_size - bytes_written
                    chunk_size = min(len(pattern), remaining)
                    chunk = pattern[:chunk_size]

                    # Write chunk
                    device.write(chunk)
                    device.flush()
                    os.fsync(device.fileno())  # Force write to disk

                    bytes_written += chunk_size
                    progress.bytes_written = bytes_written

                    # Update progress periodically
                    current_time = time.time()
                    if current_time - last_update >= 1.0:  # Update every second
                        elapsed = current_time - start_time
                        if elapsed > 0:
                            progress.bytes_per_second = bytes_written / elapsed
                            progress.elapsed_time = elapsed

                            if progress.bytes_per_second > 0:
                                remaining_bytes = device_size - bytes_written
                                progress.estimated_remaining = remaining_bytes / progress.bytes_per_second

                        if self.progress_callback:
                            self.progress_callback(progress)

                        last_update = current_time

                # Final progress update
                progress.bytes_written = bytes_written
                progress.elapsed_time = time.time() - start_time
                if self.progress_callback:
                    self.progress_callback(progress)

                return bytes_written >= device_size

        except Exception as e:
            logger.error(f"Write operation failed: {e}")
            progress.errors.append(f"Write failed: {str(e)}")
            return False

    def _verify_pattern(self, device_path: str, expected_pattern: bytes,
                       progress: WipeProgress) -> bool:
        """Verify written pattern (statistical sampling for large devices)"""

        try:
            device_size = progress.total_bytes
            sample_size = min(device_size, 100 * 1024 * 1024)  # Sample up to 100MB
            sample_count = 10  # Number of sample locations

            with open(device_path, 'rb') as device:
                for i in range(sample_count):
                    if self.stop_requested:
                        return False

                    # Calculate sample position
                    if device_size > sample_size:
                        max_offset = device_size - len(expected_pattern)
                        offset = (max_offset // sample_count) * i
                    else:
                        offset = 0

                    device.seek(offset)
                    read_data = device.read(len(expected_pattern))

                    if read_data != expected_pattern:
                        logger.error(f"Verification failed at offset {offset}")
                        return False

            return True

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False

    def _ata_secure_erase(self, device_path: str, progress: WipeProgress) -> bool:
        """Perform ATA Secure Erase"""

        try:
            progress.pass_name = "ATA Secure Erase"
            progress.current_pass = 1
            progress.total_passes = 1

            # Check if security is frozen
            result = subprocess.run(['hdparm', '-I', device_path],
                                  capture_output=True, text=True, timeout=30)

            if 'frozen' in result.stdout.lower():
                logger.error("ATA security is frozen - cannot perform secure erase")
                return False

            # Set user password (temporary)
            temp_password = "obliterator"
            result = subprocess.run(['hdparm', '--user-master', 'u',
                                   '--security-set-pass', temp_password, device_path],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error("Failed to set ATA security password")
                return False

            # Get estimated erase time
            erase_time = self._get_ata_erase_time(device_path)
            progress.estimated_remaining = erase_time

            if self.progress_callback:
                self.progress_callback(progress)

            # Perform secure erase
            logger.info(f"Starting ATA Secure Erase (estimated time: {erase_time} seconds)")
            start_time = time.time()

            result = subprocess.run(['hdparm', '--user-master', 'u',
                                   '--security-erase', temp_password, device_path],
                                  capture_output=True, text=True, timeout=erase_time + 300)

            elapsed = time.time() - start_time
            progress.elapsed_time = elapsed
            progress.bytes_written = progress.total_bytes  # Mark as complete

            if self.progress_callback:
                self.progress_callback(progress)

            if result.returncode == 0:
                logger.info(f"ATA Secure Erase completed in {elapsed:.1f} seconds")
                return True
            else:
                logger.error(f"ATA Secure Erase failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("ATA Secure Erase timed out")
            return False
        except Exception as e:
            logger.error(f"ATA Secure Erase failed: {e}")
            return False

    def _nvme_secure_erase(self, device_path: str, progress: WipeProgress) -> bool:
        """Perform NVMe Secure Erase or Format"""

        try:
            progress.pass_name = "NVMe Secure Erase"
            progress.current_pass = 1
            progress.total_passes = 1

            # First try sanitize command
            logger.info("Attempting NVMe sanitize")
            start_time = time.time()

            result = subprocess.run(['nvme', 'sanitize', device_path, '--sanact=2'],
                                  capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                # Monitor sanitize progress
                while not self.stop_requested:
                    result = subprocess.run(['nvme', 'sanitize-log', device_path],
                                          capture_output=True, text=True, timeout=30)

                    if 'completed successfully' in result.stdout.lower():
                        break
                    elif 'failed' in result.stdout.lower():
                        logger.error("NVMe sanitize failed")
                        return False

                    time.sleep(5)
                    elapsed = time.time() - start_time
                    progress.elapsed_time = elapsed

                    if self.progress_callback:
                        self.progress_callback(progress)

                progress.bytes_written = progress.total_bytes
                logger.info(f"NVMe sanitize completed in {progress.elapsed_time:.1f} seconds")
                return True

            # Fall back to format with secure erase
            logger.info("Sanitize not supported, trying format with secure erase")

            result = subprocess.run(['nvme', 'format', device_path, '--ses=1'],
                                  capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                progress.bytes_written = progress.total_bytes
                progress.elapsed_time = time.time() - start_time
                logger.info(f"NVMe format completed in {progress.elapsed_time:.1f} seconds")
                return True
            else:
                logger.error(f"NVMe format failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("NVMe secure erase timed out")
            return False
        except Exception as e:
            logger.error(f"NVMe secure erase failed: {e}")
            return False

    def _get_ata_erase_time(self, device_path: str) -> float:
        """Get estimated ATA secure erase time"""
        try:
            result = subprocess.run(['hdparm', '-I', device_path],
                                  capture_output=True, text=True, timeout=30)

            for line in result.stdout.split('\n'):
                if 'erase unit' in line.lower():
                    # Parse erase time (usually in minutes)
                    import re
                    match = re.search(r'(\d+)', line)
                    if match:
                        return int(match.group(1)) * 60  # Convert to seconds

            # Default estimate based on size
            device_info = self.get_device_info(device_path)
            size_gb = device_info['size_bytes'] / (1024**3)
            return max(300, size_gb * 2)  # Minimum 5 minutes, ~2 seconds per GB

        except:
            return 1800  # Default 30 minutes

    def _generate_random_pattern(self, size: int = 4096) -> bytes:
        """Generate cryptographically secure random pattern"""
        return os.urandom(size)

    def _generate_complement_pattern(self, size: int = 4096) -> bytes:
        """Generate complement pattern"""
        # For simplicity, use alternating pattern
        pattern = bytearray()
        for i in range(size):
            pattern.append(0xAA if i % 2 == 0 else 0x55)
        return bytes(pattern)

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

    def calculate_hash(self, device_path: str, algorithm: str = 'sha256') -> Optional[str]:
        """Calculate hash of device content (for verification)"""
        try:
            hasher = hashlib.new(algorithm)

            with open(device_path, 'rb') as device:
                # Read in chunks to avoid memory issues
                chunk_size = 1024 * 1024  # 1MB chunks
                while True:
                    chunk = device.read(chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)

                    if self.stop_requested:
                        return None

            return hasher.hexdigest()

        except Exception as e:
            logger.error(f"Hash calculation failed: {e}")
            return None

def main():
    """Main function for standalone testing"""
    import argparse

    parser = argparse.ArgumentParser(description='Obliterator Wiping Engine')
    parser.add_argument('--device', required=True, help='Device to wipe (e.g., /dev/sdb)')
    parser.add_argument('--method', choices=['clear', 'purge', 'destroy'],
                       default='clear', help='Sanitization method')
    parser.add_argument('--confirm', required=True, help='Confirmation token')
    parser.add_argument('--dry-run', action='store_true', help='Show plan without executing')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Safety check - require specific confirmation token
    expected_token = f"OBLITERATE-{os.path.basename(args.device).upper()}"
    if args.confirm != expected_token and not args.dry_run:
        print(f"ERROR: Invalid confirmation token. Expected: {expected_token}")
        sys.exit(1)

    def progress_callback(progress: WipeProgress):
        """Print progress updates"""
        percent = (progress.bytes_written / progress.total_bytes) * 100
        speed_mb = progress.bytes_per_second / (1024 * 1024)

        print(f"\rPass {progress.current_pass}/{progress.total_passes}: {progress.pass_name} "
              f"- {percent:.1f}% ({speed_mb:.1f} MB/s) "
              f"ETA: {progress.estimated_remaining:.0f}s", end='', flush=True)

    # Initialize wiping engine
    engine = WipingEngine()
    engine.set_progress_callback(progress_callback)

    method = SanitizationMethod(args.method)

    try:
        success = engine.wipe_device(args.device, method, args.confirm, args.dry_run)

        if success:
            print(f"\n{'Dry run completed' if args.dry_run else 'Wipe completed successfully'}")
        else:
            print(f"\n{'Dry run failed' if args.dry_run else 'Wipe failed'}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nWipe cancelled by user")
        engine.request_stop()
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

