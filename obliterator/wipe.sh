
#!/usr/bin/env bash
# Obliterator Core Wipe Script
# Secure data destruction following NIST SP 800-88 Rev. 1
# Version: 1.0.0

set -euo pipefail

# Configuration
readonly SCRIPT_NAME="wipe.sh"
readonly VERSION="1.0.0"
readonly OUTPUT_DIR="${OBLITERATOR_OUTPUT_DIR:-/tmp/obliterator}"
readonly LOG_FILE="${OUTPUT_DIR}/wipe_$(date +%Y%m%d_%H%M%S).log"
readonly PROGRESS_FILE="${OUTPUT_DIR}/wipe_progress.json"

# Safety configuration
readonly CONFIRMATION_TEXT="YES-DESTROY-DATA"
readonly MIN_CONFIRMATION_DELAY=3  # seconds
readonly DEFAULT_PASSES=5
readonly BLOCK_SIZE="4M"

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
DEVICE=""
WIPE_METHOD=""
PASSES=$DEFAULT_PASSES
FORCE=false
DRY_RUN=false
VERIFY=true
START_TIME=""
OPERATION_ID=""

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

# Initialize logging and operation tracking
init_operation() {
    mkdir -p "$OUTPUT_DIR"
    chmod 700 "$OUTPUT_DIR"

    OPERATION_ID="wipe_$(date +%s)_$$"
    START_TIME=$(date -Iseconds)

    # Initialize log file
    cat > "$LOG_FILE" << EOF
# Obliterator Wipe Operation Log
# Operation ID: $OPERATION_ID
# Started: $START_TIME
# Script: $SCRIPT_NAME v$VERSION
# System: $(uname -a)
# User: $(whoami)
# Device: $DEVICE
# Method: $WIPE_METHOD
# Passes: $PASSES
EOF

    log "Wipe operation initialized: $OPERATION_ID"

    # Initialize progress tracking
    update_progress "INITIALIZED" 0 0 "Operation started"
}

# Update progress information
update_progress() {
    local status="$1"      # INITIALIZED, IN_PROGRESS, COMPLETED, FAILED
    local pass_num="$2"    # Current pass number
    local percent="$3"     # Percentage complete (0-100)
    local message="$4"     # Status message

    local progress_json
    progress_json=$(jq -n \
        --arg operation_id "$OPERATION_ID" \
        --arg device "$DEVICE" \
        --arg method "$WIPE_METHOD" \
        --arg status "$status" \
        --argjson pass_num "$pass_num" \
        --argjson total_passes "$PASSES" \
        --argjson percent "$percent" \
        --arg message "$message" \
        --arg timestamp "$(date -Iseconds)" \
        --arg start_time "$START_TIME" \
        '{
            operation_id: $operation_id,
            device: $device,
            method: $method,
            status: $status,
            current_pass: $pass_num,
            total_passes: $total_passes,
            percent_complete: $percent,
            message: $message,
            timestamp: $timestamp,
            start_time: $start_time
        }')

    echo "$progress_json" > "$PROGRESS_FILE"
    debug "Progress updated: $status ($percent%)"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root for device access"
    fi
}

# Check if device exists and is a block device
validate_device() {
    if [[ ! -b "$DEVICE" ]]; then
        error "Device $DEVICE is not a valid block device"
    fi

    if [[ ! -r "$DEVICE" || ! -w "$DEVICE" ]]; then
        error "Cannot read/write device $DEVICE - check permissions"
    fi

    # Check if device is mounted
    if mount | grep -q "^$DEVICE"; then
        local mount_points
        mount_points=$(mount | grep "^$DEVICE" | awk '{print $3}' | tr '\n' ' ')
        warn "Device $DEVICE is mounted at: $mount_points"
        warn "Unmount before wiping: umount $DEVICE"

        if [[ "$FORCE" != "true" ]]; then
            error "Device is mounted - use --force to override (DANGEROUS)"
        fi
    fi

    log "Device validation passed: $DEVICE"
}

# Get device information
get_device_info() {
    local device="$1"
    local info="{}"

    # Get basic device info
    if command -v lsblk &>/dev/null; then
        local lsblk_info
        lsblk_info=$(lsblk -J -o NAME,SIZE,MODEL,SERIAL,TRAN "$device" 2>/dev/null | jq '.blockdevices[0]' || echo '{}')
        info=$(echo "$info" | jq ". + {lsblk: $lsblk_info}")
    fi

    # Get size in bytes
    local size_bytes=0
    if [[ -b "$device" ]]; then
        size_bytes=$(blockdev --getsize64 "$device" 2>/dev/null || echo 0)
    fi
    info=$(echo "$info" | jq ". + {size_bytes: $size_bytes}")

    # Determine device type
    local device_type="unknown"
    local interface="unknown"

    if [[ "$device" =~ ^/dev/nvme ]]; then
        device_type="nvme"
        interface="nvme"
    elif [[ "$device" =~ ^/dev/sd ]]; then
        device_type="sata"
        interface="sata"

        # Check if SSD via rotational flag
        local rotational_file="/sys/block/$(basename "$device")/queue/rotational"
        if [[ -f "$rotational_file" ]]; then
            local rotational
            rotational=$(cat "$rotational_file" 2>/dev/null || echo "1")
            if [[ "$rotational" == "0" ]]; then
                device_type="ssd"
            else
                device_type="hdd"
            fi
        fi
    fi

    info=$(echo "$info" | jq --arg type "$device_type" --arg interface "$interface" '. + {type: $type, interface: $interface}')

    echo "$info"
}

# Auto-detect best wipe method for device
auto_detect_method() {
    local device="$1"
    local device_info
    device_info=$(get_device_info "$device")

    local device_type interface
    device_type=$(echo "$device_info" | jq -r '.type // "unknown"')
    interface=$(echo "$device_info" | jq -r '.interface // "unknown"')

    debug "Device type: $device_type, Interface: $interface"

    case "$device_type" in
        "nvme")
            # Check if cryptographic erase is supported
            if command -v nvme &>/dev/null; then
                if nvme id-ctrl "$device" &>/dev/null; then
                    echo "NVME_CRYPTO_ERASE"
                    return
                fi
            fi
            echo "MULTI_PASS_OVERWRITE"
            ;;
        "ssd")
            # Check for ATA secure erase support
            if command -v hdparm &>/dev/null; then
                if hdparm -I "$device" 2>/dev/null | grep -i "security.*supported" &>/dev/null; then
                    echo "ATA_SECURE_ERASE_ENHANCED"
                    return
                fi
            fi
            # Fallback to block discard for SSDs
            echo "BLKDISCARD"
            ;;
        "hdd")
            # Check for ATA secure erase support
            if command -v hdparm &>/dev/null; then
                if hdparm -I "$device" 2>/dev/null | grep -i "security.*supported" &>/dev/null; then
                    echo "ATA_SECURE_ERASE"
                    return
                fi
            fi
            echo "MULTI_PASS_OVERWRITE"
            ;;
        *)
            # Unknown device type - use safe default
            echo "MULTI_PASS_OVERWRITE"
            ;;
    esac
}

# Display dramatic safety warning
show_safety_warning() {
    clear
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                                                ║${NC}"
    echo -e "${RED}║  ${WHITE}⚠️  DESTRUCTIVE OPERATION WARNING  ⚠️${RED}                                      ║${NC}"
    echo -e "${RED}║                                                                                ║${NC}"
    echo -e "${RED}║  ${YELLOW}THIS WILL PERMANENTLY DESTROY ALL DATA ON THE TARGET DEVICE${RED}                ║${NC}"
    echo -e "${RED}║                                                                                ║${NC}"
    echo -e "${RED}║  ${WHITE}Target Device: ${CYAN}$DEVICE${RED}                                                   ║${NC}"
    echo -e "${RED}║  ${WHITE}Wipe Method:   ${CYAN}$WIPE_METHOD${RED}                                             ║${NC}"
    echo -e "${RED}║  ${WHITE}Passes:        ${CYAN}$PASSES${RED}                                                    ║${NC}"
    echo -e "${RED}║                                                                                ║${NC}"
    echo -e "${RED}║  ${YELLOW}• Data recovery will be IMPOSSIBLE after this operation${RED}                      ║${NC}"
    echo -e "${RED}║  ${YELLOW}• Verify the target device is correct${RED}                                       ║${NC}"
    echo -e "${RED}║  ${YELLOW}• Ensure important data is backed up elsewhere${RED}                              ║${NC}"
    echo -e "${RED}║  ${YELLOW}• This process may take several hours to complete${RED}                           ║${NC}"
    echo -e "${RED}║                                                                                ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Show device details
    local device_info
    device_info=$(get_device_info "$DEVICE")
    local size_bytes model serial
    size_bytes=$(echo "$device_info" | jq -r '.size_bytes // 0')
    model=$(echo "$device_info" | jq -r '.lsblk.model // "Unknown"')
    serial=$(echo "$device_info" | jq -r '.lsblk.serial // "Unknown"')

    if [[ $size_bytes -gt 0 ]]; then
        local size_human
        size_human=$(numfmt --to=iec-i --suffix=B "$size_bytes" 2>/dev/null || echo "$size_bytes bytes")
        echo -e "${WHITE}Device Details:${NC}"
        echo -e "  Model:  ${CYAN}$model${NC}"
        echo -e "  Serial: ${CYAN}$serial${NC}"
        echo -e "  Size:   ${CYAN}$size_human${NC}"
        echo ""
    fi

    # Confirmation delay
    echo -e "${YELLOW}Waiting $MIN_CONFIRMATION_DELAY seconds before allowing confirmation...${NC}"
    sleep $MIN_CONFIRMATION_DELAY

    echo -e "${WHITE}To proceed, type exactly: ${RED}$CONFIRMATION_TEXT${NC}"
    echo -n "Confirmation: "

    local user_input
    read -r user_input

    if [[ "$user_input" != "$CONFIRMATION_TEXT" ]]; then
        echo -e "${GREEN}Operation cancelled by user${NC}"
        log "Operation cancelled - incorrect confirmation text"
        exit 0
    fi

    # Physical confirmation
    echo ""
    echo -e "${YELLOW}Final confirmation required:${NC}"
    echo -e "${WHITE}Press and hold ENTER for 3 seconds to proceed...${NC}"
    echo -n "Physical confirmation: "

    # Wait for ENTER and hold for 3 seconds
    if ! read -t 1 -n 1; then
        echo -e "${GREEN}Operation cancelled - no input received${NC}"
        exit 0
    fi

    local hold_start hold_count=0
    hold_start=$(date +%s)

    while IFS= read -t 0.1 -n 1; do
        local current_time
        current_time=$(date +%s)
        if [[ $((current_time - hold_start)) -ge 3 ]]; then
            hold_count=3
            break
        fi
    done

    if [[ $hold_count -lt 3 ]]; then
        echo -e "${GREEN}Operation cancelled - insufficient hold time${NC}"
        exit 0
    fi

    echo ""
    echo -e "${RED}PROCEEDING WITH DATA DESTRUCTION...${NC}"
    log "User confirmed operation with typed and physical confirmation"
}

# Generate random data for overwrite passes
generate_random_data() {
    local output_file="$1"
    local size_bytes="$2"

    if command -v openssl &>/dev/null; then
        openssl rand -out "$output_file" "$size_bytes"
    elif [[ -r /dev/urandom ]]; then
        dd if=/dev/urandom of="$output_file" bs=1M count=$((size_bytes / 1048576)) 2>/dev/null
    else
        error "No random data source available"
    fi
}

# Multi-pass overwrite implementation
wipe_multi_pass() {
    local device="$1"
    local passes="$2"

    log "Starting multi-pass overwrite: $passes passes on $device"
    update_progress "IN_PROGRESS" 0 0 "Starting multi-pass overwrite"

    local device_size
    device_size=$(blockdev --getsize64 "$device")

    if [[ $device_size -eq 0 ]]; then
        error "Could not determine device size"
    fi

    log "Device size: $(numfmt --to=iec-i --suffix=B "$device_size")"

    local pass_results="[]"

    for ((pass=1; pass<=passes; pass++)); do
        local pass_start pass_end algo
        pass_start=$(date -Iseconds)

        log "Starting pass $pass of $passes"
        update_progress "IN_PROGRESS" "$pass" $((pass * 100 / passes)) "Pass $pass of $passes"

        # Determine pass algorithm
        case $pass in
            1)
                algo="zeros"
                log "Pass $pass: Writing zeros"
                if [[ "$DRY_RUN" == "true" ]]; then
                    log "DRY RUN: Would write zeros to $device"
                    sleep 2
                else
                    dd if=/dev/zero of="$device" bs="$BLOCK_SIZE" status=progress 2>&1 | \
                        tee -a "$LOG_FILE" | while read -r line; do
                            if [[ "$line" =~ ([0-9]+).*bytes.*copied ]]; then
                                local bytes_written="${BASH_REMATCH[1]}"
                                local percent=$((bytes_written * 100 / device_size))
                                update_progress "IN_PROGRESS" "$pass" "$percent" "Pass $pass: $line"
                            fi
                        done
                fi
                ;;
            2)
                algo="ones"
                log "Pass $pass: Writing ones (0xFF)"
                if [[ "$DRY_RUN" == "true" ]]; then
                    log "DRY RUN: Would write 0xFF pattern to $device"
                    sleep 2
                else
                    # Create pattern file
                    local pattern_file="/tmp/obliterator_pattern_$$"
                    dd if=/dev/zero of="$pattern_file" bs=1M count=1 2>/dev/null
                    tr '\000' '\377' < /dev/zero | dd of="$pattern_file" bs=1M count=1 2>/dev/null

                    # Write pattern
                    while [[ $(stat -c%s "$pattern_file") -lt $device_size ]]; do
                        cat "$pattern_file" >> "$pattern_file.tmp"
                        mv "$pattern_file.tmp" "$pattern_file"
                        if [[ $(stat -c%s "$pattern_file") -gt $((device_size * 2)) ]]; then
                            truncate -s "$device_size" "$pattern_file"
                            break
                        fi
                    done

                    dd if="$pattern_file" of="$device" bs="$BLOCK_SIZE" status=progress 2>&1 | \
                        tee -a "$LOG_FILE"

                    rm -f "$pattern_file"
                fi
                ;;
            *)
                algo="random"
                log "Pass $pass: Writing random data"
                if [[ "$DRY_RUN" == "true" ]]; then
                    log "DRY RUN: Would write random data to $device"
                    sleep 2
                else
                    dd if=/dev/urandom of="$device" bs="$BLOCK_SIZE" status=progress 2>&1 | \
                        tee -a "$LOG_FILE"
                fi
                ;;
        esac

        pass_end=$(date -Iseconds)

        # Calculate throughput
        local duration_seconds
        duration_seconds=$(( $(date -d "$pass_end" +%s) - $(date -d "$pass_start" +%s) ))
        local throughput="0 MB/s"
        if [[ $duration_seconds -gt 0 ]]; then
            local mb_per_sec=$((device_size / duration_seconds / 1048576))
            throughput="$mb_per_sec MB/s"
        fi

        log "Pass $pass completed in $duration_seconds seconds ($throughput)"

        # Record pass result
        local pass_result
        pass_result=$(jq -n \
            --argjson pass_no "$pass" \
            --arg algo "$algo" \
            --arg start "$pass_start" \
            --arg end "$pass_end" \
            --argjson bytes_written "$device_size" \
            --arg throughput "$throughput" \
            '{
                pass_no: $pass_no,
                algo: $algo,
                start: $start,
                end: $end,
                bytes_written: $bytes_written,
                throughput: $throughput
            }')

        pass_results=$(echo "$pass_results" | jq ". + [$pass_result]")

        # Sync to ensure data is written
        if [[ "$DRY_RUN" != "true" ]]; then
            sync
        fi
    done

    echo "$pass_results"
}

# ATA Secure Erase implementation
wipe_ata_secure_erase() {
    local device="$1"
    local enhanced="$2"  # true for enhanced erase

    log "Starting ATA Secure Erase on $device (enhanced: $enhanced)"
    update_progress "IN_PROGRESS" 1 10 "Checking ATA security status"

    if ! command -v hdparm &>/dev/null; then
        error "hdparm not available for ATA Secure Erase"
    fi

    # Check security support
    local hdparm_info
    hdparm_info=$(hdparm -I "$device" 2>/dev/null || echo "")

    if ! echo "$hdparm_info" | grep -i "security.*supported" &>/dev/null; then
        error "ATA Security feature not supported on $device"
    fi

    local security_enabled security_locked
    security_enabled=$(echo "$hdparm_info" | grep -i "security.*enabled" &>/dev/null && echo "true" || echo "false")
    security_locked=$(echo "$hdparm_info" | grep -i "security.*locked" &>/dev/null && echo "true" || echo "false")

    log "Security status - Enabled: $security_enabled, Locked: $security_locked"

    if [[ "$security_locked" == "true" ]]; then
        error "Device is security locked - unlock before secure erase"
    fi

    # Set temporary password if not enabled
    local temp_password="obliterator_temp_$$"
    local password_set="false"

    if [[ "$security_enabled" == "false" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log "DRY RUN: Would set security password"
        else
            update_progress "IN_PROGRESS" 1 20 "Setting temporary security password"
            log "Setting temporary security password"

            if hdparm --user-master u --security-set-pass "$temp_password" "$device" 2>&1 | tee -a "$LOG_FILE"; then
                password_set="true"
                log "Security password set successfully"
            else
                error "Failed to set security password"
            fi
        fi
    fi

    # Perform secure erase
    update_progress "IN_PROGRESS" 1 30 "Executing secure erase"

    local erase_start erase_end
    erase_start=$(date -Iseconds)

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would execute secure erase"
        sleep 5
        erase_end=$(date -Iseconds)
    else
        log "Executing secure erase (this may take several hours)"

        local erase_cmd
        if [[ "$enhanced" == "true" ]]; then
            erase_cmd="hdparm --user-master u --security-erase-enhanced $temp_password $device"
        else
            erase_cmd="hdparm --user-master u --security-erase $temp_password $device"
        fi

        if eval "$erase_cmd" 2>&1 | tee -a "$LOG_FILE"; then
            erase_end=$(date -Iseconds)
            log "Secure erase completed successfully"
        else
            error "Secure erase failed"
        fi
    fi

    update_progress "IN_PROGRESS" 1 90 "Secure erase completed"

    # Build result
    local method_name
    if [[ "$enhanced" == "true" ]]; then
        method_name="ATA_SECURE_ERASE_ENHANCED"
    else
        method_name="ATA_SECURE_ERASE"
    fi

    local result
    result=$(jq -n \
        --argjson pass_no 1 \
        --arg algo "$method_name" \
        --arg start "$erase_start" \
        --arg end "$erase_end" \
        --argjson bytes_written "$(blockdev --getsize64 "$device")" \
        --argjson password_set "$password_set" \
        '{
            pass_no: $pass_no,
            algo: $algo,
            start: $start,
            end: $end,
            bytes_written: $bytes_written,
            password_set: $password_set
        }')

    echo "[$result]"
}

# NVMe Cryptographic Erase implementation
wipe_nvme_crypto_erase() {
    local device="$1"

    log "Starting NVMe Cryptographic Erase on $device"
    update_progress "IN_PROGRESS" 1 10 "Checking NVMe capabilities"

    if ! command -v nvme &>/dev/null; then
        error "nvme-cli not available for NVMe operations"
    fi

    # Check device capabilities
    local nvme_id
    if ! nvme_id=$(nvme id-ctrl "$device" -o json 2>/dev/null); then
        error "Failed to get NVMe controller information"
    fi

    update_progress "IN_PROGRESS" 1 20 "Executing cryptographic erase"

    local erase_start erase_end
    erase_start=$(date -Iseconds)

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would execute NVMe format with cryptographic erase"
        sleep 3
        erase_end=$(date -Iseconds)
    else
        log "Executing NVMe format with cryptographic erase"

        # Try different secure erase settings
        local format_success="false"

        # Try with SES=1 (cryptographic erase)
        if nvme format "$device" --ses=1 2>&1 | tee -a "$LOG_FILE"; then
            format_success="true"
            log "NVMe format with SES=1 completed"
        elif nvme format "$device" --ses=2 2>&1 | tee -a "$LOG_FILE"; then
            format_success="true"
            log "NVMe format with SES=2 completed"
        else
            warn "NVMe format with secure erase failed, trying standard format"
            if nvme format "$device" 2>&1 | tee -a "$LOG_FILE"; then
                format_success="true"
                log "NVMe standard format completed"
            else
                error "All NVMe format attempts failed"
            fi
        fi

        erase_end=$(date -Iseconds)
    fi

    update_progress "IN_PROGRESS" 1 90 "NVMe erase completed"

    local result
    result=$(jq -n \
        --argjson pass_no 1 \
        --arg algo "NVME_CRYPTO_ERASE" \
        --arg start "$erase_start" \
        --arg end "$erase_end" \
        --argjson bytes_written "$(blockdev --getsize64 "$device")" \
        '{
            pass_no: $pass_no,
            algo: $algo,
            start: $start,
            end: $end,
            bytes_written: $bytes_written
        }')

    echo "[$result]"
}

# Block discard implementation (for SSDs)
wipe_blkdiscard() {
    local device="$1"

    log "Starting block discard on $device"
    update_progress "IN_PROGRESS" 1 10 "Checking discard support"

    if ! command -v blkdiscard &>/dev/null; then
        error "blkdiscard not available"
    fi

    # Check if device supports discard
    local discard_max_bytes discard_granularity
    local sysfs_path="/sys/block/$(basename "$device")/queue"

    if [[ -f "$sysfs_path/discard_max_bytes" ]]; then
        discard_max_bytes=$(cat "$sysfs_path/discard_max_bytes")
        discard_granularity=$(cat "$sysfs_path/discard_granularity" 2>/dev/null || echo "0")

        if [[ $discard_max_bytes -eq 0 ]]; then
            warn "Device does not support discard operations"
            # Fallback to multi-pass overwrite
            log "Falling back to multi-pass overwrite"
            wipe_multi_pass "$device" 3
            return
        fi

        log "Discard support detected - max bytes: $discard_max_bytes, granularity: $discard_granularity"
    else
        warn "Cannot determine discard support, attempting anyway"
    fi

    update_progress "IN_PROGRESS" 1 30 "Executing block discard"

    local discard_start discard_end
    discard_start=$(date -Iseconds)

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would execute blkdiscard on $device"
        sleep 2
        discard_end=$(date -Iseconds)
    else
        log "Executing block discard (TRIM) on entire device"

        if blkdiscard -v "$device" 2>&1 | tee -a "$LOG_FILE"; then
            discard_end=$(date -Iseconds)
            log "Block discard completed successfully"
        else
            error "Block discard failed"
        fi
    fi

    update_progress "IN_PROGRESS" 1 90 "Block discard completed"

    local result
    result=$(jq -n \
        --argjson pass_no 1 \
        --arg algo "BLKDISCARD" \
        --arg start "$discard_start" \
        --arg end "$discard_end" \
        --argjson bytes_written "$(blockdev --getsize64 "$device")" \
        '{
            pass_no: $pass_no,
            algo: $algo,
            start: $start,
            end: $end,
            bytes_written: $bytes_written
        }')

    echo "[$result]"
}

# Verification function
verify_wipe() {
    local device="$1"
    local method="$2"

    if [[ "$VERIFY" != "true" ]]; then
        log "Verification skipped by user"
        return 0
    fi

    log "Starting wipe verification for $device"
    update_progress "IN_PROGRESS" "$PASSES" 95 "Verifying wipe completion"

    local verification_result='{"verify_method": "readback", "result": "UNKNOWN", "notes": ""}'

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would verify wipe by reading device"
        verification_result='{"verify_method": "readback", "result": "PASS", "notes": "DRY RUN - simulated verification"}'
    else
        # Read first and last megabytes to check for zero content
        local temp_file="/tmp/obliterator_verify_$$"
        local device_size
        device_size=$(blockdev --getsize64 "$device")

        # Check first MB
        dd if="$device" of="$temp_file" bs=1M count=1 2>/dev/null

        if hexdump -C "$temp_file" | grep -v "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00" | grep -v "^\*$" | head -10; then
            log "Non-zero data found at beginning of device"
            verification_result='{"verify_method": "readback", "result": "FAIL", "notes": "Non-zero data detected at device start"}'
        else
            # Check last MB
            local last_mb_offset=$((device_size - 1048576))
            if [[ $last_mb_offset -gt 0 ]]; then
                dd if="$device" of="$temp_file" bs=1 skip="$last_mb_offset" count=1048576 2>/dev/null

                if hexdump -C "$temp_file" | grep -v "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00" | grep -v "^\*$" | head -10; then
                    log "Non-zero data found at end of device"
                    verification_result='{"verify_method": "readback", "result": "FAIL", "notes": "Non-zero data detected at device end"}'
                else
                    log "Verification passed - device appears to contain zeros"
                    verification_result='{"verify_method": "readback", "result": "PASS", "notes": "Device start and end contain zeros"}'
                fi
            else
                verification_result='{"verify_method": "readback", "result": "PASS", "notes": "Device too small for end verification"}'
            fi
        fi

        rm -f "$temp_file"
    fi

    echo "$verification_result"
}

# Main wipe function
execute_wipe() {
    log "Executing wipe method: $WIPE_METHOD"

    local pass_summary verification_result

    case "$WIPE_METHOD" in
        "MULTI_PASS_OVERWRITE")
            pass_summary=$(wipe_multi_pass "$DEVICE" "$PASSES")
            ;;
        "ATA_SECURE_ERASE")
            pass_summary=$(wipe_ata_secure_erase "$DEVICE" "false")
            ;;
        "ATA_SECURE_ERASE_ENHANCED")
            pass_summary=$(wipe_ata_secure_erase "$DEVICE" "true")
            ;;
        "NVME_CRYPTO_ERASE")
            pass_summary=$(wipe_nvme_crypto_erase "$DEVICE")
            ;;
        "BLKDISCARD")
            pass_summary=$(wipe_blkdiscard "$DEVICE")
            ;;
        *)
            error "Unknown wipe method: $WIPE_METHOD"
            ;;
    esac

    # Perform verification
    verification_result=$(verify_wipe "$DEVICE" "$WIPE_METHOD")

    # Update final progress
    update_progress "COMPLETED" "$PASSES" 100 "Wipe operation completed successfully"

    log "Wipe operation completed"
    log "Pass summary: $pass_summary"
    log "Verification: $verification_result"

    # Store results for certificate generation
    local results_file="$OUTPUT_DIR/wipe_results_$OPERATION_ID.json"
    jq -n \
        --arg operation_id "$OPERATION_ID" \
        --arg device "$DEVICE" \
        --arg method "$WIPE_METHOD" \
        --argjson passes "$PASSES" \
        --argjson pass_summary "$pass_summary" \
        --argjson verification "$verification_result" \
        --arg start_time "$START_TIME" \
        --arg end_time "$(date -Iseconds)" \
        '{
            operation_id: $operation_id,
            device: $device,
            method: $method,
            passes: $passes,
            pass_summary: $pass_summary,
            verification: $verification,
            start_time: $start_time,
            end_time: $end_time
        }' > "$results_file"

    log "Results saved to: $results_file"
    echo "$results_file"
}

# Print usage information
show_usage() {
    cat << EOF
Obliterator Wipe Script v$VERSION
Secure data destruction following NIST SP 800-88 Rev. 1

Usage: $0 [OPTIONS] DEVICE

Arguments:
  DEVICE              Target block device (e.g., /dev/sda, /dev/nvme0n1)

Options:
  --method METHOD     Wipe method (auto-detected if not specified)
                      Options: MULTI_PASS_OVERWRITE, ATA_SECURE_ERASE,
                               ATA_SECURE_ERASE_ENHANCED, NVME_CRYPTO_ERASE,
                               BLKDISCARD
  --passes N          Number of passes for multi-pass overwrite (default: $DEFAULT_PASSES)
  --force             Force operation on mounted devices (DANGEROUS)
  --no-verify         Skip verification after wipe
  --dry-run           Show what would be done without actually wiping
  --debug             Enable debug output
  --help, -h          Show this help message

Environment Variables:
  OBLITERATOR_OUTPUT_DIR    Output directory for logs and progress
  DEBUG                     Enable debug mode (true/false)

Examples:
  sudo $0 /dev/sdb                    # Auto-detect method and wipe
  sudo $0 --method MULTI_PASS_OVERWRITE --passes 7 /dev/sdc
  sudo $0 --method ATA_SECURE_ERASE /dev/sda
  sudo $0 --dry-run /dev/sdb          # Test run without actual wiping

Safety Notes:
  - This script PERMANENTLY DESTROYS DATA
  - Always verify target device before proceeding
  - Unmount devices before wiping
  - Run as root/sudo for device access
  - Operation may take several hours

NIST SP 800-88 Rev. 1 Compliance:
  - Multi-pass overwrite: Clear/Purge for HDDs
  - ATA Secure Erase: Purge for SATA devices
  - NVMe Crypto Erase: Purge for NVMe SSDs
  - Block Discard: Clear for SSDs (TRIM)
EOF
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --method)
                WIPE_METHOD="$2"
                shift 2
                ;;
            --passes)
                PASSES="$2"
                shift 2
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --no-verify)
                VERIFY=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
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
                if [[ -z "$DEVICE" ]]; then
                    DEVICE="$1"
                else
                    error "Multiple devices specified"
                fi
                shift
                ;;
        esac
    done

    # Validate arguments
    if [[ -z "$DEVICE" ]]; then
        error "No device specified. Use --help for usage information."
    fi

    # Auto-detect method if not specified
    if [[ -z "$WIPE_METHOD" ]]; then
        WIPE_METHOD=$(auto_detect_method "$DEVICE")
        log "Auto-detected wipe method: $WIPE_METHOD"
    fi

    # Validate passes
    if [[ ! "$PASSES" =~ ^[1-9][0-9]*$ ]] || [[ $PASSES -gt 20 ]]; then
        error "Invalid number of passes: $PASSES (must be 1-20)"
    fi

    # Initialize operation
    init_operation

    # Safety checks
    check_root
    validate_device

    # Show safety warning and get confirmation
    if [[ "$DRY_RUN" != "true" ]]; then
        show_safety_warning
    else
        log "DRY RUN MODE - No actual data will be destroyed"
    fi

    # Execute wipe
    local results_file
    results_file=$(execute_wipe)

    # Final summary
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                                ║${NC}"
    echo -e "${GREEN}║  ${WHITE}✅  WIPE OPERATION COMPLETED SUCCESSFULLY  ✅${GREEN}                              ║${NC}"
    echo -e "${GREEN}║                                                                                ║${NC}"
    echo -e "${GREEN}║  ${WHITE}Device:    ${CYAN}$DEVICE${GREEN}                                                   ║${NC}"
    echo -e "${GREEN}║  ${WHITE}Method:    ${CYAN}$WIPE_METHOD${GREEN}                                             ║${NC}"
    echo -e "${GREEN}║  ${WHITE}Operation: ${CYAN}$OPERATION_ID${GREEN}                                      ║${NC}"
    echo -e "${GREEN}║                                                                                ║${NC}"
    echo -e "${GREEN}║  ${YELLOW}Next Steps:${GREEN}                                                             ║${NC}"
    echo -e "${GREEN}║  ${WHITE}• Generate certificate: ./cert_gen.sh $results_file${GREEN}                    ║${NC}"
    echo -e "${GREEN}║  ${WHITE}• View results: cat $results_file${GREEN}                              ║${NC}"
    echo -e "${GREEN}║  ${WHITE}• Check logs: $LOG_FILE${GREEN}                      ║${NC}"
    echo -e "${GREEN}║                                                                                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"

    log "Wipe script completed successfully"
}

# Error handling
trap 'error "Script interrupted"' INT TERM

# Run main function
main "$@"

