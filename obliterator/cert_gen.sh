Usage: $0 [OPTIONS] WIPE_RESULTS_FILE

Arguments:
  WIPE_RESULTS_FILE    JSON file containing wipe operation results

Options:
  --operator NAME      Operator name (will prompt if not provided)
  --operator-id ID     Operator ID (will prompt if not provided)
  --operator-title TITLE    Operator position/title
  --operator-phone PHONE    Operator phone number
  --operator-email EMAIL    Operator email address
  --organization ORG   Organization name (optional)
  --property-number NUM     Organizational property/asset number
  --pre-classification CLASS    Pre-sanitization confidentiality level
  --post-classification CLASS   Post-sanitization confidentiality level
  --post-destination DEST       Post-sanitization destination
  --location LOCATION      Physical location of operation
  --output FILE        Output JSON certificate file
  --pdf FILE           Output PDF certificate file
  --keys-dir DIR       Directory containing private/public keys
                       (default: $KEYS_DIR)
  --debug              Enable debug output
  --help, -h           Show this help message

Environment Variables:
  OBLITERATOR_OUTPUT_DIR           Output directory for certificates
  OBLITERATOR_KEYS_DIR             Directory containing keys
  OBLITERATOR_PROPERTY_NUMBER      Default property number
  OBLITERATOR_PRE_CLASSIFICATION   Default pre-sanitization classification
  OBLITERATOR_POST_CLASSIFICATION  Default post-sanitization classification
  OBLITERATOR_POST_DESTINATION     Default post-sanitization destination
  OBLITERATOR_LOCATION             Default operation location
  DEBUG                            Enable debug mode (true/false)

Examples:
  sudo $0 /tmp/obliterator/wipe_results_12345.json

  $0 --operator "John Doe" \
     --operator-id "JD001" \
     --operator-title "IT Security Specialist" \
     --operator-phone "+1-555-0123" \
     --operator-email "john.doe@company.com" \
     --organization "SecureData Corp" \
     --property-number "IT-HDD-2024-0157" \
     --pre-classification "CONFIDENTIAL" \
     --post-classification "UNCLASSIFIED" \
     --post-destination "Secure disposal facility" \
     --location "Data Center A, Room 201" \
     results.json

  $0 --output cert.json --pdf cert.pdf results.json

NIST SP 800-88r2 Compliance:
  This tool generates certificates compliant with NIST SP 800-88r2 Initial
  Public Draft requirements, including all mandatory fields:

  • Media identification (manufacturer, model, serial, property number)
  • Media characteristics (type, source, interface)
  • Sanitization details (method, technique, tool, verification)
  • Personnel information (name, title, contact, signature)
  • Classification levels (pre/post sanitization)
  • Timestamps and location information

Certificate Contents:
  - Complete device and operation metadata
  - NIST SP 800-88r2 compliance references
  - Personnel verification information with contact details
  - Media classification and destination tracking
  - Digital signature for tamper detection
  - Verification results and timestamps
  - Operator identification and contact information

Output Files:
  - certificate_ID.json    Machine-readable certificate
  - certificate_ID.pdf     Human-readable certificate
  - certificate_ID.json.sig  Detached signature file

Security Notes:
  - Private key must exist in keys directory
  - Certificate is signed with RSA-SHA256
  - Public key required for verification
  - Keep private key secure and offline

  - All personnel information is included in certificate
#!/usr/bin/env bash
# Obliterator Certificate Generation Script
# Generates tamper-evident digital certificates for wipe operations
# Version: 1.0.0

set -euo pipefail

# Configuration
readonly SCRIPT_NAME="cert_gen.sh"
readonly VERSION="1.0.0"
readonly OUTPUT_DIR="${OBLITERATOR_OUTPUT_DIR:-/tmp/obliterator}"
readonly KEYS_DIR="${OBLITERATOR_KEYS_DIR:-/media/usb/keys}"
readonly CERTS_DIR="${OUTPUT_DIR}/certificates"
readonly LOG_FILE="${OUTPUT_DIR}/cert_gen.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Global variables
WIPE_RESULTS_FILE=""
OPERATOR_NAME=""
OPERATOR_ID=""
OPERATOR_TITLE=""
OPERATOR_PHONE=""
OPERATOR_EMAIL=""
ORGANIZATION=""
CERT_OUTPUT_FILE=""
PDF_OUTPUT_FILE=""

# Logging functions
log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${GREEN}${msg}${NC}"
    echo "$msg" >> "$LOG_FILE"
}

warn() {
    local msg="[WARNING] $1"
    echo -e "${YELLOW}${msg}${NC}" >&2
    echo "$msg" >> "$LOG_FILE"
}

error() {
    local msg="[ERROR] $1"
    echo -e "${RED}${msg}${NC}" >&2
    echo "$msg" >> "$LOG_FILE"
    exit 1
}

debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        local msg="[DEBUG] $1"
        echo -e "${BLUE}${msg}${NC}"
        echo "$msg" >> "$LOG_FILE"
    fi
}

# Initialize certificate generation
init_cert_gen() {
    mkdir -p "$OUTPUT_DIR" "$CERTS_DIR"
    chmod 700 "$OUTPUT_DIR" "$CERTS_DIR"

    # Initialize log
    cat > "$LOG_FILE" << EOF
# Obliterator Certificate Generation Log
# Started: $(date -Iseconds)
# Script: $SCRIPT_NAME v$VERSION
# System: $(uname -a)
# User: $(whoami)
EOF

    log "Certificate generation initialized"
}

# Check if private key exists and is accessible
check_private_key() {
    local private_key="$KEYS_DIR/private.pem"
    local public_key="$KEYS_DIR/public.pem"

    if [[ ! -f "$private_key" ]]; then
        error "Private key not found: $private_key"
    fi

    if [[ ! -r "$private_key" ]]; then
        error "Cannot read private key: $private_key"
    fi

    if [[ ! -f "$public_key" ]]; then
        warn "Public key not found: $public_key"
        log "Generating public key from private key"

        if ! openssl rsa -in "$private_key" -pubout -out "$public_key" 2>/dev/null; then
            error "Failed to generate public key from private key"
        fi

        chmod 644 "$public_key"
        log "Public key generated: $public_key"
    fi

    # Test key validity
    if ! openssl rsa -in "$private_key" -check -noout 2>/dev/null; then
        error "Private key is invalid or corrupted"
    fi

    if ! openssl rsa -pubin -in "$public_key" -check -noout 2>/dev/null; then
        error "Public key is invalid or corrupted"
    fi

    log "Key validation passed"
}

# Get public key fingerprint
get_public_key_id() {
    local public_key="$KEYS_DIR/public.pem"

    if [[ -f "$public_key" ]]; then
        openssl rsa -pubin -in "$public_key" -outform DER 2>/dev/null | \
            openssl dgst -sha256 -binary | \
            base64 -w 0 | \
            sed 's/^/sha256-/'
    else
        echo "unknown"
    fi
}

# Load and validate wipe results
load_wipe_results() {
    local results_file="$1"

    if [[ ! -f "$results_file" ]]; then
        error "Wipe results file not found: $results_file"
    fi

    if ! jq empty "$results_file" 2>/dev/null; then
        error "Wipe results file is not valid JSON: $results_file"
    fi

    log "Loaded wipe results from: $results_file"
    cat "$results_file"
}

# Get operator information
get_operator_info() {
    if [[ -z "$OPERATOR_NAME" ]]; then
        echo -n "Enter operator name: "
        read -r OPERATOR_NAME
    fi

    if [[ -z "$OPERATOR_ID" ]]; then
        echo -n "Enter operator ID: "
        read -r OPERATOR_ID
    fi

    if [[ -z "$ORGANIZATION" ]]; then
        echo -n "Enter organization (optional): "
        read -r ORGANIZATION
    fi

    log "Operator: $OPERATOR_NAME ($OPERATOR_ID)"
    if [[ -n "$ORGANIZATION" ]]; then
        log "Organization: $ORGANIZATION"
    fi
}

# Get system information
get_system_info() {
    local hostname os_info boot_iso_id usb_id

    hostname=$(hostname 2>/dev/null || echo "unknown")
    os_info=$(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2 || uname -s)

    # Try to identify boot ISO/USB
    boot_iso_id="unknown"
    if [[ -f /proc/cmdline ]]; then
        local cmdline
        cmdline=$(cat /proc/cmdline)
        if echo "$cmdline" | grep -q "live"; then
            boot_iso_id="obliterator-live-boot"
        fi
    fi

    # Try to identify USB device
    usb_id="unknown"
    if [[ -d "$KEYS_DIR" ]]; then
        local mount_point
        mount_point=$(df "$KEYS_DIR" 2>/dev/null | tail -1 | awk '{print $1}' || echo "unknown")
        if [[ "$mount_point" != "unknown" ]]; then
            usb_id="usb-$(basename "$mount_point")"
        fi
    fi

    jq -n \
        --arg hostname "$hostname" \
        --arg os "$os_info" \
        --arg boot_iso_id "$boot_iso_id" \
        --arg usb_id "$usb_id" \
        '{
            hostname: $hostname,
            os: $os,
            boot_iso_id: $boot_iso_id,
            usb_id: $usb_id
        }'
}

# Map wipe method to NIST reference
get_nist_reference() {
    local method="$1"
    local device_type="$2"

    case "$method" in
        "ATA_SECURE_ERASE")
            echo "NIST SP 800-88 Rev. 1 - Section 5.2.3 Purge by Block Erase"
            ;;
        "ATA_SECURE_ERASE_ENHANCED")
            echo "NIST SP 800-88 Rev. 1 - Section 5.2.3 Purge by Enhanced Block Erase"
            ;;
        "NVME_CRYPTO_ERASE")
            echo "NIST SP 800-88 Rev. 1 - Section 5.2.1 Purge by Cryptographic Erase"
            ;;
        "MULTI_PASS_OVERWRITE")
            if [[ "$device_type" == "hdd" ]]; then
                echo "NIST SP 800-88 Rev. 1 - Section 5.2.2 Purge by Overwrite"
            else
                echo "NIST SP 800-88 Rev. 1 - Section 5.1.2 Clear by Overwrite (SSD limitations noted)"
            fi
            ;;
        "BLKDISCARD")
            echo "NIST SP 800-88 Rev. 1 - Section 5.1.1 Clear by Logical Techniques (TRIM)"
            ;;
        *)
            echo "NIST SP 800-88 Rev. 1 - Method classification pending"
            ;;
    esac
}

# Generate the main certificate JSON
generate_certificate_json() {
    local wipe_results="$1"
    local cert_id

    # Generate UUID for certificate
    if command -v uuidgen &>/dev/null; then
        cert_id=$(uuidgen)
    else
        # Fallback UUID generation
        cert_id="$(date +%s)-$(shuf -i 10000-99999 -n 1 2>/dev/null || echo $RANDOM)"
    fi

    log "Generating certificate: $cert_id"

    # Extract information from wipe results
    local operation_id device method passes
    operation_id=$(echo "$wipe_results" | jq -r '.operation_id // "unknown"')
    device=$(echo "$wipe_results" | jq -r '.device // "unknown"')
    method=$(echo "$wipe_results" | jq -r '.method // "unknown"')
    passes=$(echo "$wipe_results" | jq -r '.passes // 1')

    # Get device information
    local device_info
    if [[ -f "${OUTPUT_DIR}/detected_drives.json" ]]; then
        device_info=$(jq ".drives[] | select(.device == \"$device\")" "${OUTPUT_DIR}/detected_drives.json" 2>/dev/null || echo '{}')
    else
        device_info='{}'
    fi

    # Extract device details
    local interface model serial size_bytes device_type
    interface=$(echo "$device_info" | jq -r '.interface // "unknown"')
    model=$(echo "$device_info" | jq -r '.model // "unknown"')
    serial=$(echo "$device_info" | jq -r '.serial // "unknown"')
    size_bytes=$(echo "$device_info" | jq -r '.size_bytes // 0')
    device_type=$(echo "$device_info" | jq -r '.type // "disk"')

    # If device info not available, try to get it directly
    if [[ "$model" == "unknown" && -b "$device" ]]; then
        local lsblk_info
        lsblk_info=$(lsblk -J -o MODEL,SERIAL,SIZE "$device" 2>/dev/null | jq '.blockdevices[0]' || echo '{}')
        model=$(echo "$lsblk_info" | jq -r '.model // "unknown"')
        serial=$(echo "$lsblk_info" | jq -r '.serial // "unknown"')

        if [[ $size_bytes -eq 0 ]]; then
            size_bytes=$(blockdev --getsize64 "$device" 2>/dev/null || echo 0)
        fi
    fi

    # Get manufacturer from model string (basic extraction)
    local manufacturer="unknown"
    case "$model" in
        Samsung*) manufacturer="Samsung" ;;
        WDC*|WD*|"Western Digital"*) manufacturer="Western Digital" ;;
        Seagate*|ST*) manufacturer="Seagate" ;;
        Toshiba*) manufacturer="Toshiba" ;;
        Intel*) manufacturer="Intel" ;;
        Kingston*) manufacturer="Kingston" ;;
        SanDisk*) manufacturer="SanDisk" ;;
        Crucial*) manufacturer="Crucial" ;;
        *)
            # Try to extract first word as manufacturer
            manufacturer=$(echo "$model" | awk '{print $1}')
            if [[ -z "$manufacturer" || "$manufacturer" == "unknown" ]]; then
                manufacturer="Unknown"
            fi
            ;;
    esac

    # Determine media type based on device characteristics
    local media_type="unknown"
    case "$device_type" in
        "nvme") media_type="flash memory (NVMe)" ;;
        "ssd") media_type="flash memory (SSD)" ;;
        "hdd") media_type="magnetic (HDD)" ;;
        "usb") media_type="flash memory (USB)" ;;
        *)
            if [[ "$interface" == "nvme" ]]; then
                media_type="flash memory (NVMe)"
            elif [[ "$is_ssd" == "true" ]]; then
                media_type="flash memory (SSD)"
            else
                media_type="magnetic (HDD)"
            fi
            ;;
    esac

    # Determine media source
    local media_source="computer"  # Default assumption
    if [[ "$interface" == "usb" ]]; then
        media_source="user (removable)"
    fi

    # Get property number (if environment variable set)
    local property_number="${OBLITERATOR_PROPERTY_NUMBER:-}"

    # Get confidentiality categorizations (if environment variables set)
    local pre_sanitization_classification="${OBLITERATOR_PRE_CLASSIFICATION:-}"
    local post_sanitization_classification="${OBLITERATOR_POST_CLASSIFICATION:-}"
    local post_sanitization_destination="${OBLITERATOR_POST_DESTINATION:-}"

    # Map method to NIST categories
    local sanitization_category sanitization_technique
    case "$method" in
        "ATA_SECURE_ERASE")
            sanitization_category="purge"
            sanitization_technique="block erase (ATA Secure Erase)"
            ;;
        "ATA_SECURE_ERASE_ENHANCED")
            sanitization_category="purge"
            sanitization_technique="block erase (ATA Enhanced Secure Erase)"
            ;;
        "NVME_CRYPTO_ERASE")
            sanitization_category="purge"
            sanitization_technique="crypto erase (NVMe Format with Secure Erase)"
            ;;
        "MULTI_PASS_OVERWRITE")
            if [[ "$device_type" == "hdd" ]]; then
                sanitization_category="purge"
            else
                sanitization_category="clear"
            fi
            sanitization_technique="overwrite (multi-pass pattern)"
            ;;
        "BLKDISCARD")
            sanitization_category="clear"
            sanitization_technique="logical (TRIM/discard commands)"
            ;;
        *)
            sanitization_category="unknown"
            sanitization_technique="unknown"
            ;;
    esac

    # Get system info
    local system_info
    system_info=$(get_system_info)

    # Get NIST reference
    local nist_ref
    nist_ref=$(get_nist_reference "$method" "$device_type")

    # Get timestamps
    local start_time end_time
    start_time=$(echo "$wipe_results" | jq -r '.start_time // ""')
    end_time=$(echo "$wipe_results" | jq -r '.end_time // ""')

    if [[ -z "$start_time" ]]; then
        start_time=$(date -Iseconds)
    fi
    if [[ -z "$end_time" ]]; then
        end_time=$(date -Iseconds)
    fi

    # Get pass summary
    local pass_summary
    pass_summary=$(echo "$wipe_results" | jq '.pass_summary // []')

    # Get verification results
    local verification
    verification=$(echo "$wipe_results" | jq '.verification // {"verify_method": "none", "result": "UNKNOWN", "notes": ""}')

    # Determine verification method type
    local verification_method_type="unknown"
    local verify_method
    verify_method=$(echo "$verification" | jq -r '.verify_method // "none"')
    case "$verify_method" in
        "readback") verification_method_type="sampling (start and end sectors)" ;;
        "hash") verification_method_type="sampling (hash verification)" ;;
        "device_report") verification_method_type="device self-report" ;;
        "full") verification_method_type="full media verification" ;;
        *) verification_method_type="sampling" ;;
    esac

    # Get public key ID
    local public_key_id
    public_key_id=$(get_public_key_id)

    # Get operator contact information (from environment or prompt)
    get_operator_contact_info

    # Get location information
    local location="${OBLITERATOR_LOCATION:-$(hostname) - $(date +'%Z')}"

    # Build complete certificate following NIST SP 800-88r2 requirements
    local certificate_json
    certificate_json=$(jq -n \
        --arg cert_id "$cert_id" \
        --arg version "$VERSION" \
        --arg operator_name "$OPERATOR_NAME" \
        --arg operator_id "$OPERATOR_ID" \
        --arg organization "$ORGANIZATION" \
        --arg operator_title "$OPERATOR_TITLE" \
        --arg operator_phone "$OPERATOR_PHONE" \
        --arg operator_email "$OPERATOR_EMAIL" \
        --argjson device_info "$system_info" \
        --arg device_node "$device" \
        --arg manufacturer "$manufacturer" \
        --arg model "$model" \
        --arg serial "$serial" \
        --arg property_number "$property_number" \
        --arg media_type "$media_type" \
        --arg media_source "$media_source" \
        --arg pre_classification "$pre_sanitization_classification" \
        --arg post_classification "$post_sanitization_classification" \
        --arg post_destination "$post_sanitization_destination" \
        --arg interface "$interface" \
        --argjson size_bytes "$size_bytes" \
        --arg sanitization_category "$sanitization_category" \
        --arg sanitization_technique "$sanitization_technique" \
        --arg method "$method" \
        --argjson passes "$passes" \
        --argjson pass_summary "$pass_summary" \
        --argjson verification "$verification" \
        --arg verification_method_type "$verification_method_type" \
        --arg tool_name "Obliterator" \
        --arg tool_version "$version" \
        --arg nist_ref "$nist_ref" \
        --arg start_time "$start_time" \
        --arg end_time "$end_time" \
        --arg verification_date "$(date -Iseconds)" \
        --arg location "$location" \
        --arg public_key_id "$public_key_id" \
        '{
            certificate_id: $cert_id,
            nist_compliance: "NIST SP 800-88r2 Initial Public Draft",
            obliterator_version: $version,

            # Operator/Verifier Information (NIST Required)
            verification_personnel: {
                name: $operator_name,
                position_title: $operator_title,
                operator_id: $operator_id,
                organization: (if $organization == "" then null else $organization end),
                contact_phone: $operator_phone,
                contact_email: $operator_email,
                verification_date: $verification_date,
                location: $location,
                digital_signature: "See signature section below"
            },

            # System Information
            system_device: $device_info,

            # Media Information (NIST Required)
            media: {
                device_node: $device_node,
                manufacturer: $manufacturer,
                model: $model,
                serial_number: $serial,
                organizational_property_number: (if $property_number == "" then null else $property_number end),
                media_type: $media_type,
                media_source: $media_source,
                interface_type: $interface,
                capacity_bytes: $size_bytes,
                capacity_formatted: (if $size_bytes > 0 then ($size_bytes | tonumber | . / 1073741824 | floor | tostring + " GB") else "unknown" end)
            },

            # Classification (NIST Optional)
            confidentiality_classification: {
                pre_sanitization: (if $pre_classification == "" then null else $pre_classification end),
                post_sanitization: (if $post_classification == "" then null else $post_classification end),
                post_sanitization_destination: (if $post_destination == "" then null else $post_destination end)
            },

            # Sanitization Information (NIST Required)
            sanitization: {
                sanitization_method: $sanitization_category,
                sanitization_technique: $sanitization_technique,
                detailed_method: $method,
                passes_performed: $passes,
                tool_used: {
                    name: $tool_name,
                    version: $tool_version,
                    nist_reference: $nist_ref
                },
                pass_details: $pass_summary,
                timestamp_start: $start_time,
                timestamp_end: $end_time
            },

            # Verification Information (NIST Required)
            verification: {
                verification_method: $verification_method_type,
                verification_result: ($verification.result // "UNKNOWN"),
                verification_details: $verification,
                verification_notes: ($verification.notes // "")
            },

            # Digital Signature (Integrity Protection)
            digital_signature: {
                algorithm: "RSA-SHA256",
                public_key_id: $public_key_id,
                signature_base64: null,
                certificate_hash: null
            }
        }')

    echo "$certificate_json"
}

# Get operator contact information
get_operator_contact_info() {
    # Get operator title/position
    if [[ -z "${OPERATOR_TITLE:-}" ]]; then
        echo -n "Enter operator title/position: "
        read -r OPERATOR_TITLE
    fi

    # Get operator phone
    if [[ -z "${OPERATOR_PHONE:-}" ]]; then
        echo -n "Enter operator phone number: "
        read -r OPERATOR_PHONE
    fi

    # Get operator email
    if [[ -z "${OPERATOR_EMAIL:-}" ]]; then
        echo -n "Enter operator email: "
        read -r OPERATOR_EMAIL
    fi

    # Export for use in certificate generation
    export OPERATOR_TITLE OPERATOR_PHONE OPERATOR_EMAIL

    log "Contact info - Title: $OPERATOR_TITLE, Phone: $OPERATOR_PHONE, Email: $OPERATOR_EMAIL"
}

# Sign the certificate JSON
sign_certificate() {
    local cert_json="$1"
    local private_key="$KEYS_DIR/private.pem"

    log "Signing certificate with private key"

    # Create temporary file for certificate content
    local temp_cert="/tmp/obliterator_cert_$"
    echo "$cert_json" > "$temp_cert"

    # Sign the certificate
    local signature_file="/tmp/obliterator_sig_$"
    if ! openssl dgst -sha256 -sign "$private_key" -out "$signature_file" "$temp_cert"; then
        rm -f "$temp_cert" "$signature_file"
        error "Failed to sign certificate"
    fi

    # Convert signature to base64
    local signature_base64
    signature_base64=$(base64 -w 0 < "$signature_file")

    # Add signature to certificate
    local signed_cert
    signed_cert=$(echo "$cert_json" | jq --arg sig "$signature_base64" '.signature.signature_base64 = $sig')

    # Cleanup
    rm -f "$temp_cert" "$signature_file"

    log "Certificate signed successfully"
    echo "$signed_cert"
}

# Generate HTML template for PDF conversion
generate_html_template() {
    local cert_json="$1"

    # Extract key information for display
    local cert_id operator_name device_node method start_time
    cert_id=$(echo "$cert_json" | jq -r '.certificate_id')
    operator_name=$(echo "$cert_json" | jq -r '.operator.name')
    device_node=$(echo "$cert_json" | jq -r '.drives[0].device_node')
    method=$(echo "$cert_json" | jq -r '.drives[0].method')
    start_time=$(echo "$cert_json" | jq -r '.timestamp_start')

    local model serial size_bytes nist_ref
    model=$(echo "$cert_json" | jq -r '.drives[0].model')
    serial=$(echo "$cert_json" | jq -r '.drives[0].serial')
    size_bytes=$(echo "$cert_json" | jq -r '.drives[0].size_bytes')
    nist_ref=$(echo "$cert_json" | jq -r '.nist_sp800_88_reference')

    # Format size
    local size_human
    if command -v numfmt &>/dev/null && [[ $size_bytes -gt 0 ]]; then
        size_human=$(numfmt --to=iec-i --suffix=B "$size_bytes")
    else
        size_human="$size_bytes bytes"
    fi

    # Format timestamp
    local formatted_date
    if command -v date &>/dev/null; then
        formatted_date=$(date -d "$start_time" "+%Y-%m-%d %H:%M:%S UTC" 2>/dev/null || echo "$start_time")
    else
        formatted_date="$start_time"
    fi

    # Get verification status
    local verification_result verification_method
    verification_result=$(echo "$cert_json" | jq -r '.drives[0].verification.result // "UNKNOWN"')
    verification_method=$(echo "$cert_json" | jq -r '.drives[0].verification.verify_method // "none"')

    # Create HTML template
    cat << EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Obliterator Data Destruction Certificate</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            color: #333;
            line-height: 1.6;
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #6a0d83;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .title {
            color: #6a0d83;
            font-size: 28px;
            font-weight: bold;
            margin: 0;
        }
        .subtitle {
            color: #666;
            font-size: 16px;
            margin: 5px 0;
        }
        .cert-id {
            font-family: monospace;
            background: #f0f0f0;
            padding: 8px;
            border-radius: 4px;
            margin: 10px 0;
            display: inline-block;
        }
        .section {
            margin: 25px 0;
            padding: 15px;
            border-left: 4px solid #6a0d83;
            background: #f9f9f9;
        }
        .section-title {
            font-weight: bold;
            color: #6a0d83;
            margin-bottom: 10px;
            font-size: 18px;
        }
        .field {
            margin: 8px 0;
        }
        .field-label {
            font-weight: bold;
            display: inline-block;
            width: 150px;
        }
        .field-value {
            color: #555;
        }
        .verification {
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .verification.pass {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .verification.fail {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .verification.unknown {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
            text-align: center;
        }
        .signature-info {
            background: #e9ecef;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
            font-family: monospace;
            font-size: 11px;
            word-break: break-all;
        }
        .nist-compliance {
            background: #e7f3ff;
            border: 1px solid #b3d9ff;
            padding: 15px;
            border-radius: 4px;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">OBLITERATOR</div>
        <div class="subtitle">Data Destruction Certificate</div>
        <div class="cert-id">Certificate ID: $cert_id</div>
    </div>

    <div class="section">
        <div class="section-title">Operator Information</div>
        <div class="field">
            <span class="field-label">Name:</span>
            <span class="field-value">$operator_name</span>
        </div>
        <div class="field">
            <span class="field-label">Date:</span>
            <span class="field-value">$formatted_date</span>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Device Information</div>
        <div class="field">
            <span class="field-label">Device:</span>
            <span class="field-value">$device_node</span>
        </div>
        <div class="field">
            <span class="field-label">Model:</span>
            <span class="field-value">$model</span>
        </div>
        <div class="field">
            <span class="field-label">Serial Number:</span>
            <span class="field-value">$serial</span>
        </div>
        <div class="field">
            <span class="field-label">Capacity:</span>
            <span class="field-value">$size_human</span>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Destruction Method</div>
        <div class="field">
            <span class="field-label">Method:</span>
            <span class="field-value">$method</span>
        </div>
        <div class="nist-compliance">
            <strong>NIST SP 800-88 Rev. 1 Compliance:</strong><br>
            $nist_ref
        </div>
    </div>

    <div class="section">
        <div class="section-title">Verification Results</div>
        <div class="verification $(echo "$verification_result" | tr '[:upper:]' '[:lower:]')">
            <strong>Status:</strong> $verification_result<br>
            <strong>Method:</strong> $verification_method
        </div>
    </div>

    <div class="section">
        <div class="section-title">Digital Signature</div>
        <div class="signature-info">
            This certificate is digitally signed using RSA-SHA256.<br>
            Public Key ID: $(echo "$cert_json" | jq -r '.signature.public_key_id')<br>
            <br>
            To verify this certificate:<br>
            1. Save certificate JSON file<br>
            2. Run: ./verify_cert.sh certificate.json<br>
            3. Check signature against public key
        </div>
    </div>

    <div class="footer">
        Generated by Obliterator v$VERSION | $(date)<br>
        This certificate provides tamper-evident proof of secure data destruction.<br>
        Certificate ID: $cert_id
    </div>
</body>
</html>
EOF
}

# Convert HTML to PDF
generate_pdf_certificate() {
    local cert_json="$1"
    local output_file="$2"

    log "Generating PDF certificate: $output_file"

    # Generate HTML template
    local html_content
    html_content=$(generate_html_template "$cert_json")

    local temp_html="/tmp/obliterator_cert_$.html"
    echo "$html_content" > "$temp_html"

    # Try different PDF generators
    local pdf_success="false"

    # Try wkhtmltopdf first
    if command -v wkhtmltopdf &>/dev/null; then
        log "Using wkhtmltopdf for PDF generation"
        if wkhtmltopdf --page-size A4 --margin-top 20mm --margin-bottom 20mm \
                       --margin-left 15mm --margin-right 15mm \
                       "$temp_html" "$output_file" 2>/dev/null; then
            pdf_success="true"
            log "PDF generated successfully with wkhtmltopdf"
        else
            warn "wkhtmltopdf failed, trying alternatives"
        fi
    fi

    # Try pandoc + weasyprint
    if [[ "$pdf_success" == "false" ]] && command -v pandoc &>/dev/null; then
        log "Using pandoc for PDF generation"
        if pandoc "$temp_html" -o "$output_file" --pdf-engine=weasyprint 2>/dev/null; then
            pdf_success="true"
            log "PDF generated successfully with pandoc"
        elif pandoc "$temp_html" -o "$output_file" 2>/dev/null; then
            pdf_success="true"
            log "PDF generated successfully with pandoc (default engine)"
        else
            warn "pandoc failed"
        fi
    fi

    # Try Python weasyprint directly
    if [[ "$pdf_success" == "false" ]] && command -v python3 &>/dev/null; then
        log "Trying Python weasyprint"
        if python3 -c "
import weasyprint
weasyprint.HTML('$temp_html').write_pdf('$output_file')
" 2>/dev/null; then
            pdf_success="true"
            log "PDF generated successfully with Python weasyprint"
        fi
    fi

    # Cleanup
    rm -f "$temp_html"

    if [[ "$pdf_success" == "true" ]]; then
        log "PDF certificate generated: $output_file"
        return 0
    else
        warn "PDF generation failed - all methods exhausted"
        warn "Certificate available in JSON format only"
        return 1
    fi
}

# Main certificate generation function
generate_certificate() {
    local wipe_results_file="$1"

    log "Starting certificate generation for: $wipe_results_file"

    # Load wipe results
    local wipe_results
    wipe_results=$(load_wipe_results "$wipe_results_file")

    # Get operator information
    get_operator_info

    # Generate certificate JSON
    local cert_json
    cert_json=$(generate_certificate_json "$wipe_results")

    # Sign certificate
    local signed_cert
    signed_cert=$(sign_certificate "$cert_json")

    # Determine output files
    local cert_id
    cert_id=$(echo "$signed_cert" | jq -r '.certificate_id')

    if [[ -z "$CERT_OUTPUT_FILE" ]]; then
        CERT_OUTPUT_FILE="$CERTS_DIR/certificate_${cert_id}.json"
    fi

    if [[ -z "$PDF_OUTPUT_FILE" ]]; then
        PDF_OUTPUT_FILE="$CERTS_DIR/certificate_${cert_id}.pdf"
    fi

    # Save JSON certificate
    echo "$signed_cert" | jq '.' > "$CERT_OUTPUT_FILE"
    chmod 644 "$CERT_OUTPUT_FILE"
    log "JSON certificate saved: $CERT_OUTPUT_FILE"

    # Generate PDF certificate
    if generate_pdf_certificate "$signed_cert" "$PDF_OUTPUT_FILE"; then
        chmod 644 "$PDF_OUTPUT_FILE"
        log "PDF certificate saved: $PDF_OUTPUT_FILE"
    fi

    # Create signature file for separate verification
    local sig_file="${CERT_OUTPUT_FILE}.sig"
    echo "$signed_cert" | jq -r '.signature.signature_base64' | base64 -d > "$sig_file"
    chmod 644 "$sig_file"

    log "Certificate generation completed successfully"

    # Display summary
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                                ║${NC}"
    echo -e "${GREEN}║  ${PURPLE}✅  CERTIFICATE GENERATED SUCCESSFULLY  ✅${GREEN}                               ║${NC}"
    echo -e "${GREEN}║                                                                                ║${NC}"
    echo -e "${GREEN}║  ${YELLOW}Certificate ID: ${BLUE}$cert_id${GREEN}                      ║${NC}"
    echo -e "${GREEN}║                                                                                ║${NC}"
    echo -e "${GREEN}║  ${YELLOW}Files Generated:${GREEN}                                                        ║${NC}"
    echo -e "${GREEN}║  ${BLUE}• JSON: $CERT_OUTPUT_FILE${GREEN}"
    printf "%*s║${NC}\n" $((80 - ${#CERT_OUTPUT_FILE} - 10)) ""
    if [[ -f "$PDF_OUTPUT_FILE" ]]; then
        echo -e "${GREEN}║  ${BLUE}• PDF:  $PDF_OUTPUT_FILE${GREEN}"
        printf "%*s║${NC}\n" $((80 - ${#PDF_OUTPUT_FILE} - 10)) ""
    fi
    echo -e "${GREEN}║                                                                                ║${NC}"
    echo -e "${GREEN}║  ${YELLOW}Next Steps:${GREEN}                                                             ║${NC}"
    echo -e "${GREEN}║  ${BLUE}• Verify: ./verify_cert.sh $CERT_OUTPUT_FILE${GREEN}"
    printf "%*s║${NC}\n" $((80 - ${#CERT_OUTPUT_FILE} - 20)) ""
    echo -e "${GREEN}║  ${BLUE}• Backup: Copy certificate files to secure location${GREEN}                    ║${NC}"
    echo -e "${GREEN}║                                                                                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"

    echo ""
    echo "Certificate Details:"
    echo "  ID: $cert_id"
    echo "  Operator: $OPERATOR_NAME ($OPERATOR_ID)"
    echo "  Device: $(echo "$signed_cert" | jq -r '.drives[0].device_node')"
    echo "  Method: $(echo "$signed_cert" | jq -r '.drives[0].method')"
    echo "  Verification: $(echo "$signed_cert" | jq -r '.drives[0].verification.result')"
}

# Show usage information
show_usage() {
    cat << EOF
Obliterator Certificate Generation Script v$VERSION
Generates tamper-evident digital certificates for wipe operations

Usage: $0 [OPTIONS] WIPE_RESULTS_FILE

Arguments:
  WIPE_RESULTS_FILE    JSON file containing wipe operation results

Options:
  --operator NAME      Operator name (will prompt if not provided)
  --operator-id ID     Operator ID (will prompt if not provided)
  --organization ORG   Organization name (optional)
  --output FILE        Output JSON certificate file
  --pdf FILE           Output PDF certificate file
  --keys-dir DIR       Directory containing private/public keys
                       (default: $KEYS_DIR)
  --debug              Enable debug output
  --help, -h           Show this help message

Environment Variables:
  OBLITERATOR_OUTPUT_DIR    Output directory for certificates
  OBLITERATOR_KEYS_DIR      Directory containing keys
  DEBUG                     Enable debug mode (true/false)

Examples:
  sudo $0 /tmp/obliterator/wipe_results_12345.json
  $0 --operator "John Doe" --operator-id "JD001" results.json
  $0 --output cert.json --pdf cert.pdf results.json

Certificate Contents:
  - Device and operation metadata
  - NIST SP 800-88 Rev. 1 compliance references
  - Digital signature for tamper detection
  - Verification results and timestamps
  - Operator identification

Output Files:
  - certificate_ID.json    Machine-readable certificate
  - certificate_ID.pdf     Human-readable certificate
  - certificate_ID.json.sig  Detached signature file

Security Notes:
  - Private key must exist in keys directory
  - Certificate is signed with RSA-SHA256
  - Public key required for verification
  - Keep private key secure and offline
EOF
}

# Main function
main() {
    log "Starting Obliterator certificate generation v$VERSION"

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --operator)
                OPERATOR_NAME="$2"
                shift 2
                ;;
            --operator-id)
                OPERATOR_ID="$2"
                shift 2
                ;;
            --operator-title)
                OPERATOR_TITLE="$2"
                shift 2
                ;;
            --operator-phone)
                OPERATOR_PHONE="$2"
                shift 2
                ;;
            --operator-email)
                OPERATOR_EMAIL="$2"
                shift 2
                ;;
            --organization)
                ORGANIZATION="$2"
                shift 2
                ;;
            --property-number)
                export OBLITERATOR_PROPERTY_NUMBER="$2"
                shift 2
                ;;
            --pre-classification)
                export OBLITERATOR_PRE_CLASSIFICATION="$2"
                shift 2
                ;;
            --post-classification)
                export OBLITERATOR_POST_CLASSIFICATION="$2"
                shift 2
                ;;
            --post-destination)
                export OBLITERATOR_POST_DESTINATION="$2"
                shift 2
                ;;
            --location)
                export OBLITERATOR_LOCATION="$2"
                shift 2
                ;;
            --output)
                CERT_OUTPUT_FILE="$2"
                shift 2
                ;;
            --pdf)
                PDF_OUTPUT_FILE="$2"
                shift 2
                ;;
            --keys-dir)
                KEYS_DIR="$2"
                shift 2
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            -*)
                error "Unknown option: $1"
                ;;
            *)
                if [[ -z "$WIPE_RESULTS_FILE" ]]; then
                    WIPE_RESULTS_FILE="$1"
                else
                    error "Multiple wipe results files specified"
                fi
                shift
                ;;
        esac
    done

    # Validate arguments
    if [[ -z "$WIPE_RESULTS_FILE" ]]; then
        error "No wipe results file specified. Use --help for usage information."
    fi

    if [[ ! -f "$WIPE_RESULTS_FILE" ]]; then
        error "Wipe results file not found: $WIPE_RESULTS_FILE"
    fi

    # Initialize
    init_cert_gen

    # Check for private key
    check_private_key

    # Generate certificate
    generate_certificate "$WIPE_RESULTS_FILE"

    log "Certificate generation completed successfully"
}

# Error handling
trap 'error "Script interrupted"' INT TERM

# Run main function
main "$@"

