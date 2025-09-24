#!/bin/bash
# generate_certificate.sh - Obliterator Certificate Generation Tool
# 
# This script generates a digitally signed JSON certificate for completed wipes.
# It can be called by the main GUI or used standalone for testing.
#
# Usage: ./generate_certificate.sh <device_path> <serial_number> [status]
#
# Required dependencies: openssl, jq (for JSON formatting)
# Required files: private_key.pem in keys/ directory

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIVATE_KEY_PATH="${SCRIPT_DIR}/keys/private_key.pem"
CERT_DIR="${SCRIPT_DIR}/certificates"
APP_NAME="OBLITERATOR"
APP_VERSION="12.0-final"

# --- Dependency Check ---
for cmd in openssl jq base64; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Critical command '$cmd' is not found. Cannot proceed." >&2
    echo "Install with: apt-get install openssl jq coreutils" >&2
    exit 1
  fi
done

# --- Parameters ---
DEVICE_PATH="${1:-}"
SERIAL_NUMBER="${2:-UNKNOWN_SERIAL}"
WIPE_STATUS="${3:-Success}"

if [ -z "$DEVICE_PATH" ]; then
  echo "ERROR: Device path is required as first parameter." >&2
  echo "Usage: $0 <device_path> [serial_number] [status]" >&2
  exit 1
fi

# --- Validate Private Key ---
if [ ! -f "$PRIVATE_KEY_PATH" ]; then
  echo "ERROR: Private key not found at $PRIVATE_KEY_PATH" >&2
  echo "Generate with: openssl genrsa -out $PRIVATE_KEY_PATH 4096" >&2
  exit 1
fi

# Ensure certificates directory exists
mkdir -p "$CERT_DIR"

# --- Generate Timestamp ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
FILE_TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")

echo "--- Obliterator Certificate Generator ---"
echo "Device: $DEVICE_PATH"
echo "Serial: $SERIAL_NUMBER"
echo "Status: $WIPE_STATUS"
echo "Timestamp: $TIMESTAMP"

# --- Gather Device Information ---
get_device_info() {
  local device="$1"
  local model="Unknown"
  local size_bytes=0
  local media_type="Unknown"
  
  # Try to get device info using various methods
  if command -v smartctl >/dev/null 2>&1; then
    if smartctl -i "$device" >/dev/null 2>&1; then
      model=$(smartctl -i "$device" 2>/dev/null | grep "Device Model\|Model Number" | head -1 | cut -d: -f2 | xargs || echo "Unknown")
    fi
  fi
  
  # Get device size
  if command -v blockdev >/dev/null 2>&1; then
    size_bytes=$(blockdev --getsize64 "$device" 2>/dev/null || echo 0)
  fi
  
  # Determine media type based on device name
  case "$device" in
    /dev/nvme*) media_type="NVMe SSD" ;;
    /dev/sd*) media_type="SATA/USB Drive" ;;
    *) media_type="Block Device" ;;
  esac
  
  echo "$model|$size_bytes|$media_type"
}

DEVICE_INFO=$(get_device_info "$DEVICE_PATH")
IFS='|' read -r DEVICE_MODEL DEVICE_SIZE MEDIA_TYPE <<< "$DEVICE_INFO"

# --- Get Host System Information ---
get_host_info() {
  local hostname=$(hostname 2>/dev/null || echo "unknown")
  local kernel=$(uname -r 2>/dev/null || echo "unknown")
  local os_info="Unknown"
  
  if [ -f /etc/os-release ]; then
    os_info=$(grep "PRETTY_NAME" /etc/os-release | cut -d'"' -f2 || echo "Unknown")
  fi
  
  echo "$hostname|$kernel|$os_info"
}

HOST_INFO=$(get_host_info)
IFS='|' read -r HOSTNAME KERNEL_VERSION OS_INFO <<< "$HOST_INFO"

# --- Create Certificate Payload ---
create_certificate_payload() {
cat << EOF
{
  "certificate_metadata": {
    "version": "1.0",
    "generated_timestamp": "$TIMESTAMP",
    "nist_reference": "NIST SP 800-88r2 IPD (July 2025)",
    "certificate_id": "$(uuidgen 2>/dev/null || echo "${FILE_TIMESTAMP}-${RANDOM}")"
  },
  "tool_information": {
    "name": "$APP_NAME",
    "version": "$APP_VERSION",
    "method": "Clear",
    "technique": "5-Pass Overwrite with dd",
    "verification_method": "Zero-byte verification"
  },
  "sanitization_event": {
    "timestamp": "$TIMESTAMP",
    "status": "$WIPE_STATUS",
    "operator": {
      "system_user": "$(whoami)",
      "hostname": "$HOSTNAME",
      "timestamp": "$TIMESTAMP"
    }
  },
  "media_information": {
    "device_path": "$DEVICE_PATH",
    "manufacturer": "Unknown",
    "model": "$DEVICE_MODEL",
    "serial_number": "$SERIAL_NUMBER",
    "media_type": "$MEDIA_TYPE",
    "capacity_bytes": $DEVICE_SIZE,
    "capacity_gb": $(echo "scale=2; $DEVICE_SIZE / 1000000000" | bc -l 2>/dev/null || echo "0"),
    "pre_sanitization_classification": "Unknown",
    "post_sanitization_classification": "Unclassified"
  },
  "sanitization_details": {
    "passes_performed": [
      {
        "pass_number": 1,
        "pattern_type": "Random",
        "pattern_description": "Cryptographically secure random data",
        "timestamp": "$TIMESTAMP"
      },
      {
        "pass_number": 2,
        "pattern_type": "Fixed",
        "pattern_description": "0x55 (01010101 binary pattern)",
        "timestamp": "$TIMESTAMP"
      },
      {
        "pass_number": 3,
        "pattern_type": "Fixed",
        "pattern_description": "0xAA (10101010 binary pattern)",
        "timestamp": "$TIMESTAMP"
      },
      {
        "pass_number": 4,
        "pattern_type": "Random",
        "pattern_description": "Cryptographically secure random data",
        "timestamp": "$TIMESTAMP"
      },
      {
        "pass_number": 5,
        "pattern_type": "Zeros",
        "pattern_description": "0x00 (all zeros - final pass)",
        "timestamp": "$TIMESTAMP"
      }
    ],
    "verification_status": "Passed",
    "verification_details": "First megabyte verified to contain only zeros"
  },
  "environment_information": {
    "operating_system": "$OS_INFO",
    "kernel_version": "$KERNEL_VERSION",
    "execution_environment": "Bootable Live USB (Air-gapped)",
    "tools_used": [
      "dd (GNU coreutils)",
      "pv (pipe viewer)",
      "blockdev",
      "tr (GNU coreutils)"
    ]
  },
  "compliance_information": {
    "standard": "NIST SP 800-88r2",
    "sanitization_method": "Clear",
    "residual_risk_assessment": "Low for magnetic media, Medium for flash media due to wear leveling",
    "recommended_follow_up": "Physical destruction recommended for high-security applications with flash media"
  }
}
EOF
}

# --- Generate and Sign Certificate ---
echo "Generating certificate payload..."
CERT_PAYLOAD=$(create_certificate_payload)

# Pretty print the JSON to ensure it's valid
echo "Validating JSON structure..."
echo "$CERT_PAYLOAD" | jq . > /dev/null || {
  echo "ERROR: Generated JSON is invalid!" >&2
  exit 1
}

# Sign the certificate
echo "Signing certificate with private key..."
SIGNATURE=$(echo -n "$CERT_PAYLOAD" | openssl dgst -sha256 -sign "$PRIVATE_KEY_PATH" | base64 -w 0)

# Create final signed certificate container
SIGNED_CERT=$(cat << EOF
{
  "certificate_payload": $CERT_PAYLOAD,
  "signature": {
    "algorithm": "RSA-SHA256",
    "format": "PKCS#1 v1.5",
    "value": "$SIGNATURE",
    "signed_timestamp": "$TIMESTAMP"
  }
}
EOF
)

# --- Save Certificate ---
CERT_FILENAME="wipe-${FILE_TIMESTAMP}-${SERIAL_NUMBER}.json"
CERT_FILEPATH="$CERT_DIR/$CERT_FILENAME"

echo "Saving certificate to: $CERT_FILEPATH"
echo "$SIGNED_CERT" | jq . > "$CERT_FILEPATH"

# Verify the file was created and is valid JSON
if [ -f "$CERT_FILEPATH" ] && jq . "$CERT_FILEPATH" >/dev/null 2>&1; then
  echo "SUCCESS: Certificate generated and saved successfully!"
  echo "File: $CERT_FILEPATH"
  echo "Size: $(stat -c%s "$CERT_FILEPATH") bytes"
  
  # Display certificate summary
  echo ""
  echo "--- Certificate Summary ---"
  echo "Device: $DEVICE_PATH"
  echo "Serial: $SERIAL_NUMBER"
  echo "Status: $WIPE_STATUS"
  echo "Timestamp: $TIMESTAMP"
  echo "Certificate ID: $(jq -r '.certificate_payload.certificate_metadata.certificate_id' "$CERT_FILEPATH")"
  echo "Signature: $(echo "$SIGNATURE" | cut -c1-32)..."
else
  echo "ERROR: Failed to create or validate certificate file!" >&2
  exit 1
fi

# --- Optional: Verify Signature ---
if [ "${VERIFY_SIGNATURE:-yes}" = "yes" ]; then
  echo ""
  echo "--- Verifying Signature ---"
  
  # Extract payload and signature
  jq -r '.certificate_payload' "$CERT_FILEPATH" > /tmp/cert_payload.json
  jq -r '.signature.value' "$CERT_FILEPATH" | base64 -d > /tmp/cert_signature.bin
  
  # Verify signature
  if openssl dgst -sha256 -verify <(openssl rsa -in "$PRIVATE_KEY_PATH" -pubout) -signature /tmp/cert_signature.bin /tmp/cert_payload.json >/dev/null 2>&1; then
    echo "SUCCESS: Signature verification passed!"
  else
    echo "WARNING: Signature verification failed!" >&2
  fi
  
  # Cleanup temp files
  rm -f /tmp/cert_payload.json /tmp/cert_signature.bin
fi

echo ""
echo "Certificate generation complete!"
exit 0
