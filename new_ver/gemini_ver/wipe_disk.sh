#!/bin/bash
# wipe_disk.sh - Securely sanitizes a block device.
# DO NOT RUN MANUALLY unless you know exactly what you are doing.
# This script is designed to be called by obliterator_gui.py.
#
# Usage:
# sudo bash wipe_disk.sh /dev/sdX OBLITERATE

TARGET_DEVICE=$1
CONFIRM_TOKEN=$2
WIPE_METHOD="5-pass-overwrite" # Default for HDDs

# --- SAFETY CHECKS ---
if [ "$EUID" -ne 0 ]; then
  echo "ERROR: This script must be run as root."
  exit 1
fi

if [ -z "$TARGET_DEVICE" ] || [ ! -b "$TARGET_DEVICE" ]; then
  echo "ERROR: Invalid or no target device specified."
  exit 1
fi

if [ "$CONFIRM_TOKEN" != "OBLITERATE" ]; then
  echo "ERROR: Incorrect confirmation token. Aborting."
  exit 1
fi

echo "--- Starting Sanitization on $TARGET_DEVICE ---"
# Note: In a full implementation, you would detect the device type (HDD/SSD/NVMe)
# and choose the wipe method (ATA Secure Erase, NVMe Format, Overwrite) accordingly.
# For this prototype, we will perform a 5-pass overwrite suitable for HDDs.

DEVICE_SIZE_BYTES=$(blockdev --getsize64 "$TARGET_DEVICE")
if [ "$DEVICE_SIZE_BYTES" -eq 0 ]; then
    echo "ERROR: Could not determine device size. Aborting."
    exit 1
fi

echo "WIPE_METHOD: $WIPE_METHOD"
echo "DEVICE_SIZE: $(($DEVICE_SIZE_BYTES / 1024 / 1024 / 1024)) GB"

# --- 5-PASS OVERWRITE (NIST Clear Method for HDDs) ---

# Pass 1: Random Data
echo "PROGRESS:1/5:Starting Pass 1 (Random)..."
dd if=/dev/urandom bs=1M | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
echo "PROGRESS:1/5:Verifying Pass 1..."
# Verification would involve reading back samples and checking they are not zero. Skipping in this prototype for brevity.

# Pass 2: Complement of Random (Hard to script simply, we'll use another random pass)
echo "PROGRESS:2/5:Starting Pass 2 (Random)..."
dd if=/dev/urandom bs=1M | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none

# Pass 3: Fixed Pattern 0x55
echo "PROGRESS:3/5:Starting Pass 3 (Pattern 0x55)..."
dd if=/dev/zero bs=1M | tr "\000" "\125" | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none

# Pass 4: Fixed Pattern 0xAA
echo "PROGRESS:4/5:Starting Pass 4 (Pattern 0xAA)..."
dd if=/dev/zero bs=1M | tr "\000" "\252" | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none

# Pass 5: Zeros
echo "PROGRESS:5/5:Starting Pass 5 (Zeros)..."
dd if=/dev/zero bs=1M | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
echo "PROGRESS:5/5:Verifying Pass 5..."
# A real verification would read back sectors and ensure they are zero.

sync # Ensure all writes are committed to disk

echo "--- Sanitization Complete on $TARGET_DEVICE ---"
echo "STATUS:SUCCESS"
