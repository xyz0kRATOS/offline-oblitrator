#!/usr/bin/env bash
# Obliterator Certificate Verification Script
# Verifies tamper-evident digital certificates
# Version: 1.0.0

set -euo pipefail

# Configuration
readonly SCRIPT_NAME="verify_cert.sh"
readonly VERSION="1.0.0"
readonly OUTPUT_DIR="${OBLITERATOR_OUTPUT_DIR:-/tmp/obliterator}"
readonly KEYS_DIR="${OBLITERATOR_KEYS_DIR:-/media/usb/keys}"
readonly LOG_FILE="${OUTPUT_DIR}/verify_cert.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Global variables
CERT_FILE=""
PUBLIC_KEY_FILE=""
VERBOSE=false
CHECK_FIELDS=true
OUTPUT_FORMAT="human"

# Logging functions
log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${GREEN}${msg}${NC}"
    fi
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

warn() {
    local msg="[WARNING] $1"
    echo -e "${YELLOW}${msg}${NC}" >&2
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

error() {
    local msg="[ERROR] $1"
    echo -e "${RED}${msg}${NC}" >&2
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
    exit 1
}

debug() {
    if [[ "${DEBUG:-false}" == "true" || "$VERBOSE" == "true" ]]; then
        local msg="[DEBUG] $1"
        echo -e "${BLUE}${msg}${NC}"
        echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
    fi
}

# Initialize verification
init_verification() {
    mkdir -p "$OUTPUT_DIR" 2>/dev/null || true

    # Initialize log
    cat > "$LOG_FILE" 2>/dev/null << EOF || true
# Obliterator Certificate Verification Log
# Started: $(date -Iseconds)
# Script: $SCRIPT_NAME v$VERSION
# System: $(uname -a)
# User: $(whoami)
# Certificate: $CERT_FILE
EOF

    log "Certificate verification initialized"
}

# Validate certificate file format
validate_certificate_format() {
    local cert_file="$1"

    debug "Validating certificate format: $cert_file"

    if [[ ! -f "$cert_file" ]]; then
        error "Certificate file not found: $cert_file"
    fi

    if [[ ! -r "$cert_file" ]]; then
        error "Cannot read certificate file: $cert_file"
    fi

    # Check if it's valid JSON
    if ! jq empty "$cert_file" 2>/dev/null; then
        error "Certificate file is not valid JSON"
    fi

    # Check for required fields
    local required_fields=(
        ".certificate_id"
        ".obliterator_version"
        ".operator"
        ".device"
        ".drives"
        ".nist_sp800_88_reference"
        ".timestamp_start"
        ".timestamp_end"
        ".signature"
        ".signature.algorithm"
        ".signature.public_key_id"
        ".signature.signature_base64"
    )

    for field in "${required_fields[@]}"; do
        if ! jq -e "$field" "$cert_file" >/dev/null 2>&1; then
            error "Missing required field in certificate: $field"
        fi
    done

    log "Certificate format validation passed"
}

# Find public key file
find_public_key() {
    local cert_file="$1"

    # If public key file explicitly provided, use it
    if [[ -n "$PUBLIC_KEY_FILE" ]]; then
        if [[ ! -f "$PUBLIC_KEY_FILE" ]]; then
            error "Specified public key file not found: $PUBLIC_KEY_FILE"
        fi
        echo "$PUBLIC_KEY_FILE"
        return
    fi

    # Try to find public key based on certificate's key ID
    local public_key_id
    public_key_id=$(jq -r '.signature.public_key_id // "unknown"' "$cert_file")

    debug "Looking for public key with ID: $public_key_id"

    # Check default keys directory
    local default_public_key="$KEYS_DIR/public.pem"
    if [[ -f "$default_public_key" ]]; then
        # Verify this is the correct key
        local file_key_id
        if file_key_id=$(openssl rsa -pubin -in "$default_public_key" -outform DER 2>/dev/null | \
                        openssl dgst -sha256 -binary | \
                        base64 -w 0 | \
                        sed 's/^/sha256-/'); then

            if [[ "$file_key_id" == "$public_key_id" ]]; then
                debug "Found matching public key: $default_public_key"
                echo "$default_public_key"
                return
            else
                warn "Public key ID mismatch - certificate: $public_key_id, file: $file_key_id"
            fi
        fi
    fi

    # Look for public key in same directory as certificate
    local cert_dir
    cert_dir=$(dirname "$cert_file")
    local cert_public_key="$cert_dir/public.pem"

    if [[ -f "$cert_public_key" ]]; then
        debug "Found public key in certificate directory: $cert_public_key"
        echo "$cert_public_key"
        return
    fi

    # Look for public key with same name as certificate
    local cert_basename
    cert_basename=$(basename "$cert_file" .json)
    local named_public_key="$cert_dir/${cert_basename}_public.pem"

    if [[ -f "$named_public_key" ]]; then
        debug "Found named public key: $named_public_key"
        echo "$named_public_key"
        return
    fi

    error "Public key not found. Please specify with --public-key option."
}

# Verify digital signature
verify_signature() {
    local cert_file="$1"
    local public_key_file="$2"

    debug "Verifying digital signature"
    log "Certificate: $cert_file"
    log "Public key: $public_key_file"

    # Extract signature
    local signature_base64
    signature_base64=$(jq -r '.signature.signature_base64' "$cert_file")

    if [[ "$signature_base64" == "null" || -z "$signature_base64" ]]; then
        error "No signature found in certificate"
    fi

    # Create temporary files
    local temp_cert="/tmp/obliterator_verify_cert_$$"
    local temp_sig="/tmp/obliterator_verify_sig_$$"
    local temp_cert_nosig="/tmp/obliterator_verify_nosig_$$"

    # Remove signature from certificate for verification
    jq 'del(.signature.signature_base64) | .signature.signature_base64 = null' "$cert_file" > "$temp_cert_nosig"

    # Decode signature
    echo "$signature_base64" | base64 -d > "$temp_sig"

    # Verify signature
    local verification_result="false"
    if openssl dgst -sha256 -verify "$public_key_file" -signature "$temp_sig" "$temp_cert_nosig" >/dev/null 2>&1; then
        verification_result="true"
        log "Digital signature verification: PASSED"
    else
        log "Digital signature verification: FAILED"
    fi

    # Cleanup
    rm -f "$temp_cert" "$temp_sig" "$temp_cert_nosig"

    echo "$verification_result"
}

# Validate certificate fields
validate_certificate_fields() {
    local cert_file="$1"

    if [[ "$CHECK_FIELDS" != "true" ]]; then
        return 0
    fi

    debug "Validating certificate fields"

    local validation_errors=()

    # Check certificate ID format (should be UUID-like)
    local cert_id
    cert_id=$(jq -r '.certificate_id' "$cert_file")
    if [[ ! "$cert_id" =~ ^[0-9a-f-]{8,}$ ]]; then
        validation_errors+=("Invalid certificate ID format: $cert_id")
    fi

    # Check version format
    local version
    version=$(jq -r '.obliterator_version' "$cert_file")
    if [[ ! "$version" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        validation_errors+=("Invalid version format: $version")
    fi

    # Check operator fields
    local operator_name operator_id
    operator_name=$(jq -r '.operator.name' "$cert_file")
    operator_id=$(jq -r '.operator.operator_id' "$cert_file")

    if [[ -z "$operator_name" || "$operator_name" == "null" ]]; then
        validation_errors+=("Missing operator name")
    fi

    if [[ -z "$operator_id" || "$operator_id" == "null" ]]; then
        validation_errors+=("Missing operator ID")
    fi

    # Check device information
    local hostname
    hostname=$(jq -r '.device.hostname' "$cert_file")
    if [[ -z "$hostname" || "$hostname" == "null" ]]; then
        validation_errors+=("Missing device hostname")
    fi

    # Check drives array
    local drives_count
    drives_count=$(jq '.drives | length' "$cert_file")
    if [[ $drives_count -eq 0 ]]; then
        validation_errors+=("No drives found in certificate")
    fi

    # Validate each drive
    for ((i=0; i<drives_count; i++)); do
        local device_node method
        device_node=$(jq -r ".drives[$i].device_node" "$cert_file")
        method=$(jq -r ".drives[$i].method" "$cert_file")

        if [[ ! "$device_node" =~ ^/dev/ ]]; then
            validation_errors+=("Invalid device node format: $device_node")
        fi

        # Check if method is recognized
        case "$method" in
            "MULTI_PASS_OVERWRITE"|"ATA_SECURE_ERASE"|"ATA_SECURE_ERASE_ENHANCED"|"NVME_CRYPTO_ERASE"|"BLKDISCARD")
                # Valid methods
                ;;
            *)
                validation_errors+=("Unknown wipe method: $method")
                ;;
        esac

        # Check pass summary
        local pass_summary
        pass_summary=$(jq ".drives[$i].pass_summary" "$cert_file")
        if [[ "$pass_summary" == "null" || "$pass_summary" == "[]" ]]; then
            validation_errors+=("Missing pass summary for drive $device_node")
        fi
    done

    # Check timestamps
    local start_time end_time
    start_time=$(jq -r '.timestamp_start' "$cert_file")
    end_time=$(jq -r '.timestamp_end' "$cert_file")

    # Basic ISO8601 format check
    if [[ ! "$start_time" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
        validation_errors+=("Invalid start timestamp format: $start_time")
    fi

    if [[ ! "$end_time" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
        validation_errors+=("Invalid end timestamp format: $end_time")
    fi

    # Check if end time is after start time
    if command -v date >/dev/null 2>&1; then
        local start_epoch end_epoch
        start_epoch=$(date -d "$start_time" +%s 2>/dev/null || echo 0)
        end_epoch=$(date -d "$end_time" +%s 2>/dev/null || echo 0)

        if [[ $start_epoch -gt 0 && $end_epoch -gt 0 && $end_epoch -lt $start_epoch ]]; then
            validation_errors+=("End time is before start time")
        fi
    fi

    # Check NIST reference
    local nist_ref
    nist_ref=$(jq -r '.nist_sp800_88_reference' "$cert_file")
    if [[ ! "$nist_ref" =~ "NIST SP 800-88" ]]; then
        validation_errors+=("Invalid NIST reference: $nist_ref")
    fi

    # Check signature algorithm
    local sig_algorithm
    sig_algorithm=$(jq -r '.signature.algorithm' "$cert_file")
    if [[ "$sig_algorithm" != "RSA-SHA256" ]]; then
        validation_errors+=("Unsupported signature algorithm: $sig_algorithm")
    fi

    # Report validation results
    if [[ ${#validation_errors[@]} -eq 0 ]]; then
        log "Certificate field validation: PASSED"
        return 0
    else
        log "Certificate field validation: FAILED"
        for error in "${validation_errors[@]}"; do
            warn "Validation error: $error"
        done
        return 1
    fi
}

# Extract and display certificate information
display_certificate_info() {
    local cert_file="$1"

    # Extract key information
    local cert_id version operator_name operator_id organization
    cert_id=$(jq -r '.certificate_id' "$cert_file")
    version=$(jq -r '.obliterator_version' "$cert_file")
    operator_name=$(jq -r '.operator.name' "$cert_file")
    operator_id=$(jq -r '.operator.operator_id' "$cert_file")
    organization=$(jq -r '.operator.organization // "N/A"' "$cert_file")

    local hostname start_time end_time
    hostname=$(jq -r '.device.hostname' "$cert_file")
    start_time=$(jq -r '.timestamp_start' "$cert_file")
    end_time=$(jq -r '.timestamp_end' "$cert_file")

    # Format timestamps if possible
    local formatted_start formatted_end
    if command -v date >/dev/null 2>&1; then
        formatted_start=$(date -d "$start_time" "+%Y-%m-%d %H:%M:%S UTC" 2>/dev/null || echo "$start_time")
        formatted_end=$(date -d "$end_time" "+%Y-%m-%d %H:%M:%S UTC" 2>/dev/null || echo "$end_time")
    else
        formatted_start="$start_time"
        formatted_end="$end_time"
    fi

    case "$OUTPUT_FORMAT" in
        "json")
            # JSON output for machine processing
            jq -n \
                --arg cert_id "$cert_id" \
                --arg version "$version" \
                --arg operator_name "$operator_name" \
                --arg operator_id "$operator_id" \
                --arg organization "$organization" \
                --arg hostname "$hostname" \
                --arg start_time "$start_time" \
                --arg end_time "$end_time" \
                '{
                    certificate_id: $cert_id,
                    version: $version,
                    operator: {
                        name: $operator_name,
                        id: $operator_id,
                        organization: $organization
                    },
                    device: {
                        hostname: $hostname
                    },
                    timestamps: {
                        start: $start_time,
                        end: $end_time
                    }
                }'
            ;;
        "brief")
            # Brief output
            echo "Certificate: $cert_id"
            echo "Operator: $operator_name ($operator_id)"
            echo "Date: $formatted_start"
            ;;
        "human"|*)
            # Human-readable detailed output
            cat << EOF

Certificate Information:
  ID: $cert_id
  Version: $version

Operator:
  Name: $operator_name
  ID: $operator_id
  Organization: $organization

Device:
  Hostname: $hostname

Timestamps:
  Start: $formatted_start
  End: $formatted_end

EOF

            # Display drive information
            local drives_count
            drives_count=$(jq '.drives | length' "$cert_file")

            echo "Drives Processed: $drives_count"
            echo ""

            for ((i=0; i<drives_count; i++)); do
                local device_node interface model serial size_bytes method passes
                device_node=$(jq -r ".drives[$i].device_node" "$cert_file")
                interface=$(jq -r ".drives[$i].interface" "$cert_file")
                model=$(jq -r ".drives[$i].model" "$cert_file")
                serial=$(jq -r ".drives[$i].serial" "$cert_file")
                size_bytes=$(jq -r ".drives[$i].size_bytes" "$cert_file")
                method=$(jq -r ".drives[$i].method" "$cert_file")
                passes=$(jq -r ".drives[$i].passes" "$cert_file")

                # Format size
                local size_human
                if command -v numfmt >/dev/null 2>&1 && [[ $size_bytes -gt 0 ]]; then
                    size_human=$(numfmt --to=iec-i --suffix=B "$size_bytes" 2>/dev/null || echo "$size_bytes bytes")
                else
                    size_human="$size_bytes bytes"
                fi

                echo "Drive $((i+1)): $device_node"
                echo "  Model: $model"
                echo "  Serial: $serial"
                echo "  Size: $size_human"
                echo "  Interface: $interface"
                echo "  Method: $method"
                echo "  Passes: $passes"

                # Verification status
                local verification_result verification_method
                verification_result=$(jq -r ".drives[$i].verification.result // \"UNKNOWN\"" "$cert_file")
                verification_method=$(jq -r ".drives[$i].verification.verify_method // \"none\"" "$cert_file")

                echo "  Verification: $verification_result ($verification_method)"
                echo ""
            done

            # NIST compliance
            local nist_ref
            nist_ref=$(jq -r '.nist_sp800_88_reference' "$cert_file")
            echo "NIST Compliance: $nist_ref"
            echo ""
            ;;
    esac
}

# Main verification function
verify_certificate() {
    local cert_file="$1"

    log "Starting certificate verification: $cert_file"

    # Step 1: Validate certificate format
    validate_certificate_format "$cert_file"

    # Step 2: Find public key
    local public_key_file
    public_key_file=$(find_public_key "$cert_file")

    # Step 3: Verify digital signature
    local signature_valid
    signature_valid=$(verify_signature "$cert_file" "$public_key_file")

    # Step 4: Validate certificate fields
    local fields_valid="true"
    if ! validate_certificate_fields "$cert_file"; then
        fields_valid="false"
    fi

    # Determine overall result
    local overall_result="VALID"
    if [[ "$signature_valid" != "true" ]]; then
        overall_result="INVALID_SIGNATURE"
    elif [[ "$fields_valid" != "true" ]]; then
        overall_result="INVALID_FIELDS"
    fi

    # Display results
    case "$OUTPUT_FORMAT" in
        "json")
            jq -n \
                --arg result "$overall_result" \
                --argjson signature_valid "$signature_valid" \
                --argjson fields_valid "$fields_valid" \
                --arg public_key "$public_key_file" \
                '{
                    verification_result: $result,
                    signature_valid: $signature_valid,
                    fields_valid: $fields_valid,
                    public_key_used: $public_key
                }'
            ;;
        "brief")
            echo "Verification: $overall_result"
            ;;
        "human"|*)
            echo ""
            echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${PURPLE}║                                                                                ║${NC}"

            if [[ "$overall_result" == "VALID" ]]; then
                echo -e "${PURPLE}║  ${GREEN}✅  CERTIFICATE VERIFICATION: PASSED  ✅${PURPLE}                               ║${NC}"
                echo -e "${PURPLE}║                                                                                ║${NC}"
                echo -e "${PURPLE}║  ${WHITE}This certificate is authentic and has not been tampered with.${PURPLE}          ║${NC}"
            else
                echo -e "${PURPLE}║  ${RED}❌  CERTIFICATE VERIFICATION: FAILED  ❌${PURPLE}                               ║${NC}"
                echo -e "${PURPLE}║                                                                                ║${NC}"
                echo -e "${PURPLE}║  ${WHITE}This certificate may be invalid or tampered with.${PURPLE}                     ║${NC}"
            fi

            echo -e "${PURPLE}║                                                                                ║${NC}"
            echo -e "${PURPLE}║  ${YELLOW}Verification Details:${PURPLE}                                                   ║${NC}"

            if [[ "$signature_valid" == "true" ]]; then
                echo -e "${PURPLE}║  ${GREEN}• Digital Signature: VALID${PURPLE}                                            ║${NC}"
            else
                echo -e "${PURPLE}║  ${RED}• Digital Signature: INVALID${PURPLE}                                          ║${NC}"
            fi

            if [[ "$fields_valid" == "true" ]]; then
                echo -e "${PURPLE}║  ${GREEN}• Certificate Fields: VALID${PURPLE}                                           ║${NC}"
            else
                echo -e "${PURPLE}║  ${RED}• Certificate Fields: INVALID${PURPLE}                                         ║${NC}"
            fi

            echo -e "${PURPLE}║                                                                                ║${NC}"
            echo -e "${PURPLE}║  ${BLUE}Public Key: $(basename "$public_key_file")${PURPLE}"
            printf "%*s║${NC}\n" $((80 - ${#public_key_file} - 25)) ""
            echo -e "${PURPLE}║                                                                                ║${NC}"
            echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"

            # Display certificate information
            display_certificate_info "$cert_file"
            ;;
    esac

    # Return appropriate exit code
    case "$overall_result" in
        "VALID")
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Show usage information
show_usage() {
    cat << EOF
Obliterator Certificate Verification Script v$VERSION
Verifies tamper-evident digital certificates

Usage: $0 [OPTIONS] CERTIFICATE_FILE

Arguments:
  CERTIFICATE_FILE     JSON certificate file to verify

Options:
  --public-key FILE    Public key file for verification
                       (auto-detected if not specified)
  --keys-dir DIR       Directory containing keys
                       (default: $KEYS_DIR)
  --format FORMAT      Output format: human, brief, json
                       (default: human)
  --no-field-check     Skip certificate field validation
  --verbose, -v        Verbose output
  --debug              Enable debug output
  --help, -h           Show this help message

Environment Variables:
  OBLITERATOR_KEYS_DIR      Directory containing keys
  DEBUG                     Enable debug mode (true/false)

Examples:
  $0 certificate.json
  $0 --public-key public.pem certificate.json
  $0 --format json certificate.json
  $0 --verbose certificate.json

Verification Process:
  1. Validate JSON format and required fields
  2. Locate appropriate public key
  3. Verify RSA-SHA256 digital signature
  4. Validate certificate field contents
  5. Report overall verification result

Exit Codes:
  0  Certificate is valid
  1  Certificate is invalid or verification failed

Public Key Location:
  The script searches for public keys in this order:
  1. Explicitly specified with --public-key
  2. Keys directory: $KEYS_DIR/public.pem
  3. Same directory as certificate: ./public.pem
  4. Named key: certificate_name_public.pem
EOF
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --public-key)
                PUBLIC_KEY_FILE="$2"
                shift 2
                ;;
            --keys-dir)
                KEYS_DIR="$2"
                shift 2
                ;;
            --format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            --no-field-check)
                CHECK_FIELDS=false
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --debug)
                DEBUG=true
                VERBOSE=true
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
                if [[ -z "$CERT_FILE" ]]; then
                    CERT_FILE="$1"
                else
                    error "Multiple certificate files specified"
                fi
                shift
                ;;
        esac
    done

    # Validate arguments
    if [[ -z "$CERT_FILE" ]]; then
        error "No certificate file specified. Use --help for usage information."
    fi

    # Validate output format
    case "$OUTPUT_FORMAT" in
        "human"|"brief"|"json")
            ;;
        *)
            error "Invalid output format: $OUTPUT_FORMAT (use human, brief, or json)"
            ;;
    esac

    # Initialize
    init_verification

    # Verify certificate
    if verify_certificate "$CERT_FILE"; then
        log "Certificate verification completed: VALID"
        exit 0
    else
        log "Certificate verification completed: INVALID"
        exit 1
    fi
}

# Error handling
trap 'error "Script interrupted"' INT TERM

# Run main function
main "$@"

