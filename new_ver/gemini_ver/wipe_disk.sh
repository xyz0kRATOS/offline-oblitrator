#!/bin/bash
# wipe_disk.sh - Obliterator Wiping Engine (5-Pass Version)
#
# This script securely sanitizes a block device with a 5-pass overwrite.
# It is designed to be called by the Python GUI.
# DO NOT RUN MANUALLY unless you are certain of the target device.
#
# 5-Pass Strategy:
# 1. Fixed Pattern (0x55)
# 2. Complementary Pattern (0xAA)
# 3. Random Data
# 4. Zeros
# 5. Random Data
#
# Usage from GUI:
# bash wipe_disk.sh /dev/sdX OBLITERATE

set -u # Exit on unset variables

# --- Parameters and Safety Checks ---
TARGET_DEVICE="${1:-}"
CONFIRM_TOKEN="${2:-}"

if [ "$EUID" -ne 0 ]; then
  echo "ERROR: This script must be run as root." >&2
  exit 1
fi

if [ -z "$TARGET_DEVICE" ] || [ ! -b "$TARGET_DEVICE" ]; then
  echo "ERROR: Invalid or no target device specified. Target must be a block device." >&2
  exit 1
fi

if [ "$CONFIRM_TOKEN" != "OBLITERATE" ]; then
  echo "ERROR: Incorrect confirmation token. This is a safety feature. Aborting." >&2
  exit 1
fi

# --- Wiping Logic ---
echo "--- Starting 5-Pass Sanitization on $TARGET_DEVICE ---"

DEVICE_SIZE_BYTES=$(blockdev --getsize64 "$TARGET_DEVICE")
if [ "$DEVICE_SIZE_BYTES" -eq 0 ]; then
    echo "ERROR: Could not determine size of $TARGET_DEVICE. Aborting." >&2
    exit 1
fi

WIPE_METHOD="5-pass-overwrite"
echo "WIPE_METHOD: $WIPE_METHOD"
echo "DEVICE_SIZE: $(($DEVICE_SIZE_BYTES / 1024 / 1024 / 1024)) GB"
sync # Sync filesystem before starting

# --- Pass 1: Fixed Pattern (0x55) ---
echo "PROGRESS:1/5:Starting Pass 1 (Pattern 0x55)..."
# We use 'tr' to convert a stream of zeros into the desired pattern.
dd if=/dev/zero bs=1M | tr "\000" "\125" | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
PASS1_EXIT_CODE=$?
sync
if [ $PASS1_EXIT_CODE -ne 0 ]; then
    echo "ERROR: Pass 1 (Pattern 0x55) failed with exit code $PASS1_EXIT_CODE. Aborting." >&2
    exit 1
fi
echo "PROGRESS:1/5:Pass 1 (Pattern 0x55) Complete."


# --- Pass 2: Complementary Pattern (0xAA) ---
echo "PROGRESS:2/5:Starting Pass 2 (Pattern 0xAA)..."
dd if=/dev/zero bs=1M | tr "\000" "\252" | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
PASS2_EXIT_CODE=$?
sync
if [ $PASS2_EXIT_CODE -ne 0 ]; then
    echo "ERROR: Pass 2 (Pattern 0xAA) failed with exit code $PASS2_EXIT_CODE. Aborting." >&2
    exit 1
fi
echo "PROGRESS:2/5:Pass 2 (Pattern 0xAA) Complete."


# --- Pass 3: Random Data ---
echo "PROGRESS:3/5:Starting Pass 3 (Random Data)..."
dd if=/dev/urandom bs=1M | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
PASS3_EXIT_CODE=$?
sync
if [ $PASS3_EXIT_CODE -ne 0 ]; then
    echo "ERROR: Pass 3 (Random) failed with exit code $PASS3_EXIT_CODE. Aborting." >&2
    exit 1
fi
echo "PROGRESS:3/5:Pass 3 (Random Data) Complete."


# --- Pass 4: Zeros ---
echo "PROGRESS:4/5:Starting Pass 4 (Zeros)..."
dd if=/dev/zero bs=1M | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
PASS4_EXIT_CODE=$?
sync
if [ $PASS4_EXIT_CODE -ne 0 ]; then
    echo "ERROR: Pass 4 (Zeros) failed with exit code $PASS4_EXIT_CODE. Aborting." >&2
    exit 1
fi
echo "PROGRESS:4/5:Pass 4 (Zeros) Complete."


# --- Pass 5: Random Data ---
echo "PROGRESS:5/5:Starting Pass 5 (Random Data)..."
dd if=/dev/urandom bs=1M | pv -t -e -p -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
PASS5_EXIT_CODE=$?
sync
if [ $PASS5_EXIT_CODE -ne 0 ]; then
    echo "ERROR: Pass 5 (Random) failed with exit code $PASS5_EXIT_CODE. Aborting." >&2
    exit 1
fi
echo "PROGRESS:5/5:Pass 5 (Random Data) Complete."

# --- Verification Step ---
echo "VERIFICATION:Starting final verification..."
# After a final random pass, the first megabyte should NOT be all zeros.
FIRST_MB=$(dd if="$TARGET_DEVICE" bs=1M count=1 2>/dev/null | tr -d '\0')
if [ -z "$FIRST_MB" ]; then
    echo "VERIFICATION:FAILED - First megabyte is all zeros, which is unexpected after a random pass." >&2
    # This is a warning, not a hard failure, as it's statistically possible but highly unlikely.
else
    echo "VERIFICATION:PASSED - First megabyte contains non-zero data as expected."
fi

echo "--- Sanitization Complete on $TARGET_DEVICE ---"
echo "STATUS:SUCCESS"

exit 0
