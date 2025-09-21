#!/bin-bash
# wipe_disk.sh - (v5 - With Test Mode)

# --- Strict Mode ---
set -euo pipefail

# --- Dependency Check ---
for cmd in dd pv blockdev tr; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Critical command '$cmd' is not found." >&2; exit 1;
  fi
done

# --- Parameters and Safety Checks ---
TARGET_DEVICE="${1:-}"
CONFIRM_TOKEN="${2:-}"
TEST_MODE="${3:-}" # Optional parameter for test mode

if [ "$EUID" -ne 0 ]; then
  echo "ERROR: This script must be run as root." >&2; exit 1;
fi
if [ -z "$TARGET_DEVICE" ] || [ ! -b "$TARGET_DEVICE" ]; then
  echo "ERROR: Invalid target device." >&2; exit 1;
fi
if [ "$CONFIRM_TOKEN" != "OBLITERATE" ]; then
  echo "ERROR: Incorrect confirmation token." >&2; exit 1;
fi

# --- [NEW] Test Mode Logic ---
if [ "$TEST_MODE" == "--test" ]; then
  echo "--- Starting TEST MODE Simulation on $TARGET_DEVICE ---"
  echo "WIPE_METHOD: 5-pass-simulation"
  
  echo "PROGRESS:1/5:Simulating Pass 1..." && sleep 2
  echo "PROGRESS:2/5:Simulating Pass 2..." && sleep 2
  echo "PROGRESS:3/5:Simulating Pass 3..." && sleep 2
  echo "PROGRESS:4/5:Simulating Pass 4..." && sleep 2
  echo "PROGRESS:5/5:Simulating Pass 5..." && sleep 2
  
  echo "VERIFICATION:PASSED - Simulation complete."
  echo "--- Sanitization Simulation Complete ---"
  echo "STATUS:SUCCESS"
  exit 0
fi

# --- Real Wiping Logic (Unchanged) ---
echo "--- Starting 5-Pass Sanitization on $TARGET_DEVICE ---"
DEVICE_SIZE_BYTES=$(blockdev --getsize64 "$TARGET_DEVICE")
echo "WIPE_METHOD: 5-pass-dd-robust"; sync

# Pass 1: Random
echo "PROGRESS:1/5:Starting Pass 1 (Random Data)..."
dd if=/dev/urandom bs=1M | pv -p -t -e -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
sync; echo "PROGRESS:1/5:Pass 1 Complete."

# Pass 2: Pattern 0x55
echo "PROGRESS:2/5:Starting Pass 2 (Pattern 0x55)..."
dd if=/dev/zero bs=1M | tr "\000" "\125" | pv -p -t -e -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
sync; echo "PROGRESS:2/5:Pass 2 Complete."

# Pass 3: Pattern 0xAA
echo "PROGRESS:3/5:Starting Pass 3 (Pattern 0xAA)..."
dd if=/dev/zero bs=1M | tr "\000" "\252" | pv -p -t -e -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
sync; echo "PROGRESS:3/5:Pass 3 Complete."

# Pass 4: Random
echo "PROGRESS:4/5:Starting Pass 4 (Random Data)..."
dd if=/dev/urandom bs=1M | pv -p -t -e -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
sync; echo "PROGRESS:4/5:Pass 4 Complete."

# Pass 5: Zeros
echo "PROGRESS:5/5:Starting Pass 5 (Zeros)..."
dd if=/dev/zero bs=1M | pv -p -t -e -s "$DEVICE_SIZE_BYTES" | dd of="$TARGET_DEVICE" bs=1M oflag=direct status=none
sync; echo "PROGRESS:5/5:Pass 5 Complete."

echo "VERIFICATION:Starting final verification..."
FIRST_MB_NON_ZERO=$(dd if="$TARGET_DEVICE" bs=1M count=1 2>/dev/null | tr -d '\0')
if [ -n "$FIRST_MB_NON_ZERO" ]; then
    echo "VERIFICATION:FAILED - First megabyte contains non-zero data." >&2; exit 1;
else
    echo "VERIFICATION:PASSED - The first megabyte is all zeros as expected."
fi

echo "--- Sanitization Complete on $TARGET_DEVICE ---"
echo "STATUS:SUCCESS"
exit 0
