#!/bin/bash
# generate_cert.sh - Creates and signs a NIST-compliant wipe certificate.

set -euo pipefail

# --- Configuration ---
BASE_DIR="/my-applications/obliterator"
CERT_DIR="${BASE_DIR}/certificates"
PRIVATE_KEY_PATH="${BASE_DIR}/keys/private_key.pem"
APP_NAME="OBLITERATOR"

# --- Script Arguments ---
# This script expects data to be passed in from the GUI.
DEVICE_MODEL="${1:-Unknown Model}"
DEVICE_SERIAL="${2:-Unknown Serial}"
DEVICE_MEDIA_TYPE="${3:-Unknown Type}"
APP_VERSION="${4:-Unknown Version}"

# --- Create Certificate Payload ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
PLACEHOLDER="Not Provided (Input Disabled)"

# Use jq to safely construct the JSON payload
CERT_PAYLOAD=$(jq -n \
    --arg nist_ref "NIST SP 800-88r2" \
    --arg tool_name "$APP_NAME" \
    --arg tool_ver "$APP_VERSION" \
    --arg timestamp "$TIMESTAMP" \
    --arg technique "5-Pass Overwrite" \
    --arg model "$DEVICE_MODEL" \
    --arg serial "$DEVICE_SERIAL" \
    --arg property_num "$PLACEHOLDER" \
    --arg media_type "$DEVICE_MEDIA_TYPE" \
    --arg media_source "$PLACEHOLDER" \
    --arg pre_cat "$PLACEHOLDER" \
    --arg sanitization_method "Clear" \
    --arg verification "Sampling (First 1MB)" \
    --arg post_cat "$PLACEHOLDER" \
    --arg destination "$PLACEHOLDER" \
    '{
        "nist_reference": $nist_ref,
        "media_information": {
            "model": $model,
            "serial_number": $serial,
            "property_number": $property_num,
            "media_type": $media_type,
            "media_source": $media_source
        },
        "sanitization_plan": {
            "pre_sanitization_confidentiality": $pre_cat,
            "sanitization_method": $sanitization_method,
            "sanitization_technique": $technique,
            "tool_used": "\($tool_name) v\($tool_ver)",
            "verification_method": $verification,
            "post_sanitization_confidentiality": $post_cat,
            "post_sanitization_destination": $destination
        },
        "sanitization_event": {
            "timestamp": $timestamp,
            "status": "Success"
        }
    }')

# --- Sign the Payload ---
# 1. Create a temporary file for the payload to be hashed
PAYLOAD_FILE=$(mktemp)
echo "$CERT_PAYLOAD" > "$PAYLOAD_FILE"

# 2. Create the SHA256 hash of the payload
HASH_FILE=$(mktemp)
openssl dgst -sha256 -binary "$PAYLOAD_FILE" > "$HASH_FILE"

# 3. Sign the hash with the private key and Base64 encode the signature
SIGNATURE=$(openssl pkeyutl -sign -inkey "$PRIVATE_KEY_PATH" -pkeyopt digest:sha256 -in "$HASH_FILE" | base64 -w 0)

# --- Assemble Final Signed Certificate ---
# Use jq to combine the payload and the signature into the final file
FINAL_CERT=$(jq -n \
    --argjson payload "$CERT_PAYLOAD" \
    --arg sig "$SIGNATURE" \
    '{
        "certificate_payload": $payload,
        "signature": $sig
    }')

# --- Save the Final Certificate ---
mkdir -p "$CERT_DIR"
FILENAME="wipe-$(date +'%Y%m%d-%H%M%S')-${DEVICE_SERIAL}.json"
FILEPATH="${CERT_DIR}/${FILENAME}"

echo "$FINAL_CERT" > "$FILEPATH"

# Clean up temporary files
rm -f "$PAYLOAD_FILE" "$HASH_FILE"

echo "Certificate successfully generated at ${FILEPATH}"
exit 0
