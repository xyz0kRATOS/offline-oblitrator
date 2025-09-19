#!/usr/bin/env bash
# Obliterator Drive Detection Script
# Detects attached storage devices and collects metadata
# Version: 1.0.0

set -euo pipefail

# Configuration
readonly SCRIPT_NAME="detect_drives.sh"
readonly VERSION="1.0.0"
readonly OUTPUT_DIR="${OBLITERATOR_OUTPUT_DIR:-/tmp/obliterator}"
readonly LOG_FILE="${OUTPUT_DIR}/detect_drives.log"
readonly DRIVES_JSON="${OUTPUT_DIR}/detected_drives.json"
readonly DRIVES_HUMAN="${OUTPUT_DIR}/detected_drives.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
}

debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        local msg="[DEBUG] $1"
        echo -e "${BLUE}${msg}${NC}"
        echo "$msg" >> "$LOG_FILE"
    fi
}

# Initialize output directory
init_output() {
    mkdir -p "$OUTPUT_DIR"
    chmod 700 "$OUTPUT_DIR"
    
    # Initialize log file
    cat > "$LOG_FILE" << EOF
# Obliterator Drive Detection Log
# Started: $(date -Iseconds)
# Script: $SCRIPT_NAME v$VERSION
# System: $(uname -a)
# User: $(whoami)
EOF
}

# Check if running as root/sudo
check_privileges() {
    if [[ $EUID -ne 0 ]]; then
        warn "Not running as root - some information may be limited"
        warn "Run with 'sudo $0' for complete drive information"
    fi
}

# Test if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Safe command execution with error handling
safe_exec() {
    local cmd="$1"
    local description="$2"
    local output
    
    debug "Executing: $cmd"
    
    if output=$(eval "$cmd" 2>&1); then
        debug "$description: Success"
        echo "$output"
        return 0
    else
        warn "$description failed: $output"
        echo ""
        return 1
    fi
}

# Get basic block device information
get_block_devices() {
    log "Detecting block devices..."
    
    local lsblk_output
    if command_exists lsblk; then
        # Get comprehensive device information in JSON format
        lsblk_output=$(safe_exec \
            "lsblk -J -o NAME,MAJ:MIN,RM,SIZE,RO,TYPE,MOUNTPOINT,MODEL,SERIAL,TRAN,SUBSYSTEMS,FSTYPE,LABEL,UUID,PARTUUID" \
            "lsblk JSON output")
        
        echo "$lsblk_output"
    else
        error "lsblk command not available"
        return 1
    fi
}

# Get detailed ATA/SATA drive information
get_ata_info() {
    local device="$1"
    local info_json="{}"
    
    debug "Getting ATA info for $device"
    
    if command_exists hdparm && [[ -b "$device" ]]; then
        local hdparm_output
        hdparm_output=$(safe_exec "hdparm -I $device" "hdparm identify for $device")
        
        if [[ -n "$hdparm_output" ]]; then
            # Parse hdparm output for key information
            local model serial firmware
            model=$(echo "$hdparm_output" | grep -i "Model Number" | cut -d':' -f2 | xargs || echo "unknown")
            serial=$(echo "$hdparm_output" | grep -i "Serial Number" | cut -d':' -f2 | xargs || echo "unknown")
            firmware=$(echo "$hdparm_output" | grep -i "Firmware Revision" | cut -d':' -f2 | xargs || echo "unknown")
            
            # Check security features
            local security_supported security_enabled security_locked
            security_supported=$(echo "$hdparm_output" | grep -i "Security.*supported" &>/dev/null && echo "true" || echo "false")
            security_enabled=$(echo "$hdparm_output" | grep -i "Security.*enabled" &>/dev/null && echo "true" || echo "false")
            security_locked=$(echo "$hdparm_output" | grep -i "Security.*locked" &>/dev/null && echo "true" || echo "false")
            
            # Check for enhanced security erase
            local enhanced_erase_supported
            enhanced_erase_supported=$(echo "$hdparm_output" | grep -i "enhanced.*erase.*supported" &>/dev/null && echo "true" || echo "false")
            
            # Build JSON
            info_json=$(jq -n \
                --arg model "$model" \
                --arg serial "$serial" \
                --arg firmware "$firmware" \
                --argjson security_supported "$security_supported" \
                --argjson security_enabled "$security_enabled" \
                --argjson security_locked "$security_locked" \
                --argjson enhanced_erase "$enhanced_erase_supported" \
                '{
                    model: $model,
                    serial: $serial,
                    firmware: $firmware,
                    security: {
                        supported: $security_supported,
                        enabled: $security_enabled,
                        locked: $security_locked,
                        enhanced_erase_supported: $enhanced_erase
                    }
                }')
        fi
    fi
    
    echo "$info_json"
}

# Get NVMe drive information
get_nvme_info() {
    local device="$1"
    local info_json="{}"
    
    debug "Getting NVMe info for $device"
    
    if command_exists nvme && [[ -c "$device" ]]; then
        # Get controller identification
        local nvme_id
        nvme_id=$(safe_exec "nvme id-ctrl $device -o json" "NVMe controller info for $device")
        
        if [[ -n "$nvme_id" && "$nvme_id" != "{}" ]]; then
            # Parse NVMe JSON output
            local model serial firmware
            model=$(echo "$nvme_id" | jq -r '.mn // "unknown"' 2>/dev/null || echo "unknown")
            serial=$(echo "$nvme_id" | jq -r '.sn // "unknown"' 2>/dev/null || echo "unknown")
            firmware=$(echo "$nvme_id" | jq -r '.fr // "unknown"' 2>/dev/null || echo "unknown")
            
            # Check format capabilities
            local format_output crypto_erase_supported="false"
            if format_output=$(safe_exec "nvme id-ns $device -o json" "NVMe namespace info"); then
                # Check if cryptographic erase is supported
                if echo "$format_output" | jq -e '.lbaf[].ms' &>/dev/null; then
                    crypto_erase_supported="true"
                fi
            fi
            
            info_json=$(jq -n \
                --arg model "$model" \
                --arg serial "$serial" \
                --arg firmware "$firmware" \
                --argjson crypto_erase "$crypto_erase_supported" \
                '{
                    model: $model,
                    serial: $serial,
                    firmware: $firmware,
                    crypto_erase_supported: $crypto_erase
                }')
        fi
    fi
    
    echo "$info_json"
}

# Get SMART information
get_smart_info() {
    local device="$1"
    local smart_json="{}"
    
    debug "Getting SMART info for $device"
    
    if command_exists smartctl; then
        local smart_output
        smart_output=$(safe_exec "smartctl -i -A $device" "SMART info for $device")
        
        if [[ -n "$smart_output" ]]; then
            # Parse SMART output
            local device_model device_serial capacity health
            device_model=$(echo "$smart_output" | grep "Device Model" | cut -d':' -f2 | xargs || echo "unknown")
            device_serial=$(echo "$smart_output" | grep "Serial Number" | cut -d':' -f2 | xargs || echo "unknown")
            capacity=$(echo "$smart_output" | grep "User Capacity" | cut -d':' -f2 | xargs || echo "unknown")
            
            # Check overall health
            local health_status
            if echo "$smart_output" | grep -i "overall.*health.*self.*assessment.*test.*result.*passed" &>/dev/null; then
                health_status="PASSED"
            elif echo "$smart_output" | grep -i "overall.*health.*self.*assessment.*test.*result.*failed" &>/dev/null; then
                health_status="FAILED"
            else
                health_status="UNKNOWN"
            fi
            
            smart_json=$(jq -n \
                --arg model "$device_model" \
                --arg serial "$device_serial" \
                --arg capacity "$capacity" \
                --arg health "$health_status" \
                '{
                    model: $model,
                    serial: $serial,
                    capacity: $capacity,
                    health_status: $health
                }')
        fi
    fi
    
    echo "$smart_json"
}

# Get device udev properties
get_udev_info() {
    local device="$1"
    local udev_json="{}"
    
    debug "Getting udev info for $device"
    
    if command_exists udevadm; then
        local udev_output
        udev_output=$(safe_exec "udevadm info --query=all --name=$device" "udev info for $device")
        
        if [[ -n "$udev_output" ]]; then
            # Parse key udev properties
            local id_bus id_model id_serial id_type id_fs_type
            id_bus=$(echo "$udev_output" | grep "ID_BUS=" | cut -d'=' -f2 || echo "unknown")
            id_model=$(echo "$udev_output" | grep "ID_MODEL=" | cut -d'=' -f2 || echo "unknown")
            id_serial=$(echo "$udev_output" | grep "ID_SERIAL_SHORT=" | cut -d'=' -f2 || echo "unknown")
            id_type=$(echo "$udev_output" | grep "ID_TYPE=" | cut -d'=' -f2 || echo "unknown")
            id_fs_type=$(echo "$udev_output" | grep "ID_FS_TYPE=" | cut -d'=' -f2 || echo "unknown")
            
            # Check if removable
            local removable="false"
            if echo "$udev_output" | grep "ID_DRIVE_FLASH_SD=1\|ID_DRIVE_FLASH_CF=1\|ID_DRIVE_FLOPPY=1" &>/dev/null; then
                removable="true"
            fi
            
            udev_json=$(jq -n \
                --arg bus "$id_bus" \
                --arg model "$id_model" \
                --arg serial "$id_serial" \
                --arg type "$id_type" \
                --arg fs_type "$id_fs_type" \
                --argjson removable "$removable" \
                '{
                    bus: $bus,
                    model: $model,
                    serial: $serial,
                    type: $type,
                    filesystem: $fs_type,
                    removable: $removable
                }')
        fi
    fi
    
    echo "$udev_json"
}

# Determine recommended wipe method based on device characteristics
get_recommended_wipe_method() {
    local device="$1"
    local device_type="$2"
    local is_ssd="$3"
    local has_secure_erase="$4"
    local has_crypto_erase="$5"
    
    local method="MULTI_PASS_OVERWRITE"  # Safe default
    local confidence="medium"
    local reason=""
    
    # NVMe SSDs - prefer crypto erase
    if [[ "$device_type" == "nvme" && "$has_crypto_erase" == "true" ]]; then
        method="NVME_CRYPTO_ERASE"
        confidence="high"
        reason="NVMe SSD with cryptographic erase support"
    
    # SATA SSDs with secure erase
    elif [[ "$is_ssd" == "true" && "$has_secure_erase" == "true" ]]; then
        method="ATA_SECURE_ERASE_ENHANCED"
        confidence="high"
        reason="SATA SSD with enhanced secure erase"
    
    # SATA HDDs with secure erase
    elif [[ "$is_ssd" == "false" && "$has_secure_erase" == "true" ]]; then
        method="ATA_SECURE_ERASE"
        confidence="high"
        reason="SATA HDD with secure erase support"
    
    # SSDs without hardware erase (warn about limitations)
    elif [[ "$is_ssd" == "true" ]]; then
        method="MULTI_PASS_OVERWRITE"
        confidence="low"
        reason="SSD without secure erase - multi-pass has limitations"
    
    # Regular HDDs
    else
        method="MULTI_PASS_OVERWRITE"
        confidence="high"
        reason="Standard multi-pass overwrite for HDD"
    fi
    
    jq -n \
        --arg method "$method" \
        --arg confidence "$confidence" \
        --arg reason "$reason" \
        '{
            method: $method,
            confidence: $confidence,
            reason: $reason
        }'
}

# Check if device appears to be an SSD
is_ssd_device() {
    local device="$1"
    
    # Check rotational characteristic
    local rotational_file="/sys/block/$(basename "$device")/queue/rotational"
    if [[ -f "$rotational_file" ]]; then
        local rotational
        rotational=$(cat "$rotational_file" 2>/dev/null || echo "1")
        if [[ "$rotational" == "0" ]]; then
            echo "true"
            return
        fi
    fi
    
    # Check device name patterns
    if [[ "$device" =~ nvme|ssd ]]; then
        echo "true"
        return
    fi
    
    # Default to HDD
    echo "false"
}

# Process a single drive and collect all information
process_drive() {
    local device="$1"
    local device_info="$2"  # JSON from lsblk
    
    log "Processing drive: $device"
    
    # Extract basic info from lsblk JSON
    local name size type model serial tran mountpoint
    name=$(echo "$device_info" | jq -r '.name // "unknown"')
    size=$(echo "$device_info" | jq -r '.size // "unknown"')
    type=$(echo "$device_info" | jq -r '.type // "unknown"')
    model=$(echo "$device_info" | jq -r '.model // "unknown"')
    serial=$(echo "$device_info" | jq -r '.serial // "unknown"')
    tran=$(echo "$device_info" | jq -r '.tran // "unknown"')
    mountpoint=$(echo "$device_info" | jq -r '.mountpoint // null')
    
    # Determine device type and interface
    local interface="unknown"
    local device_type="disk"
    
    if [[ "$device" =~ ^/dev/nvme ]]; then
        interface="nvme"
        device_type="nvme"
    elif [[ "$tran" == "sata" ]] || [[ "$device" =~ ^/dev/sd ]]; then
        interface="sata"
        device_type="sata"
    elif [[ "$tran" == "usb" ]] || echo "$device_info" | jq -e '.rm == true' &>/dev/null; then
        interface="usb"
        device_type="removable"
    else
        interface="unknown"
    fi
    
    # Check if SSD
    local is_ssd
    is_ssd=$(is_ssd_device "$device")
    
    # Get detailed information based on interface
    local ata_info nvme_info smart_info udev_info
    ata_info="{}"
    nvme_info="{}"
    
    if [[ "$interface" == "sata" ]]; then
        ata_info=$(get_ata_info "$device")
    elif [[ "$interface" == "nvme" ]]; then
        nvme_info=$(get_nvme_info "$device")
    fi
    
    smart_info=$(get_smart_info "$device")
    udev_info=$(get_udev_info "$device")
    
    # Determine capabilities
    local has_secure_erase="false"
    local has_crypto_erase="false"
    
    if [[ "$interface" == "sata" ]]; then
        has_secure_erase=$(echo "$ata_info" | jq -r '.security.supported // false')
    elif [[ "$interface" == "nvme" ]]; then
        has_crypto_erase=$(echo "$nvme_info" | jq -r '.crypto_erase_supported // false')
    fi
    
    # Get recommended wipe method
    local recommended_method
    recommended_method=$(get_recommended_wipe_method "$device" "$device_type" "$is_ssd" "$has_secure_erase" "$has_crypto_erase")
    
    # Check if mounted (security warning)
    local mounted="false"
    local mount_warning=""
    if [[ "$mountpoint" != "null" && -n "$mountpoint" ]]; then
        mounted="true"
        mount_warning="WARNING: Device is currently mounted at $mountpoint"
    fi
    
    # Build complete drive information JSON
    local drive_json
    drive_json=$(jq -n \
        --arg device "$device" \
        --arg name "$name" \
        --arg size "$size" \
        --arg type "$type" \
        --arg interface "$interface" \
        --arg model "$model" \
        --arg serial "$serial" \
        --argjson is_ssd "$is_ssd" \
        --argjson mounted "$mounted" \
        --arg mount_warning "$mount_warning" \
        --argjson ata_info "$ata_info" \
        --argjson nvme_info "$nvme_info" \
        --argjson smart_info "$smart_info" \
        --argjson udev_info "$udev_info" \
        --argjson recommended "$recommended_method" \
        '{
            device: $device,
            name: $name,
            size: $size,
            type: $type,
            interface: $interface,
            model: $model,
            serial: $serial,
            is_ssd: $is_ssd,
            mounted: $mounted,
            mount_warning: $mount_warning,
            ata_info: $ata_info,
            nvme_info: $nvme_info,
            smart_info: $smart_info,
            udev_info: $udev_info,
            recommended_method: $recommended
        }')
    
    echo "$drive_json"
}

# Generate human-readable report
generate_human_report() {
    local drives_json="$1"
    
    cat > "$DRIVES_HUMAN" << EOF
# Obliterator Drive Detection Report
# Generated: $(date -Iseconds)
# System: $(uname -a)

EOF
    
    local drive_count
    drive_count=$(echo "$drives_json" | jq '.drives | length')
    
    echo "Detected $drive_count storage device(s):" >> "$DRIVES_HUMAN"
    echo "" >> "$DRIVES_HUMAN"
    
    # Process each drive for human report
    local i=0
    while [[ $i -lt $drive_count ]]; do
        local drive
        drive=$(echo "$drives_json" | jq ".drives[$i]")
        
        local device name size interface model recommended_method
        device=$(echo "$drive" | jq -r '.device')
        name=$(echo "$drive" | jq -r '.name')
        size=$(echo "$drive" | jq -r '.size')
        interface=$(echo "$drive" | jq -r '.interface')
        model=$(echo "$drive" | jq -r '.model')
        recommended_method=$(echo "$drive" | jq -r '.recommended_method.method')
        
        cat >> "$DRIVES_HUMAN" << EOF
Device $((i+1)): $device
  Name: $name
  Size: $size
  Interface: $interface
  Model: $model
  Recommended Method: $recommended_method
  
EOF
        
        # Add warnings if mounted
        local mounted mount_warning
        mounted=$(echo "$drive" | jq -r '.mounted')
        if [[ "$mounted" == "true" ]]; then
            mount_warning=$(echo "$drive" | jq -r '.mount_warning')
            echo "  ⚠️  $mount_warning" >> "$DRIVES_HUMAN"
            echo "" >> "$DRIVES_HUMAN"
        fi
        
        ((i++))
    done
    
    cat >> "$DRIVES_HUMAN" << EOF

# Safety Notes:
# - Verify target devices carefully before wiping
# - Unmount any mounted filesystems before wiping
# - Some methods may require unlocking security features
# - SSD wiping effectiveness varies by method and device

# Next Steps:
# 1. Review detected devices above
# 2. Unmount any mounted devices: umount /dev/sdX
# 3. Run wipe script: ./wipe.sh /dev/sdX
# 4. Or use GUI: cd gui && python3 main.py
EOF
}

# Main detection function
main() {
    log "Starting Obliterator drive detection v$VERSION"
    
    # Initialize
    init_output
    check_privileges
    
    # Get block devices
    local lsblk_output
    if ! lsblk_output=$(get_block_devices); then
        error "Failed to get block device information"
        exit 1
    fi
    
    # Parse block devices and filter for disks
    local devices
    devices=$(echo "$lsblk_output" | jq -r '.blockdevices[] | select(.type == "disk") | .name')
    
    if [[ -z "$devices" ]]; then
        warn "No disk devices found"
        echo '{"drives": [], "timestamp": "'$(date -Iseconds)'", "version": "'$VERSION'"}' > "$DRIVES_JSON"
        exit 0
    fi
    
    log "Found disk devices: $(echo "$devices" | tr '\n' ' ')"
    
    # Process each device
    local all_drives="[]"
    
    while IFS= read -r device_name; do
        if [[ -z "$device_name" ]]; then continue; fi
        
        local full_device="/dev/$device_name"
        local device_info
        device_info=$(echo "$lsblk_output" | jq ".blockdevices[] | select(.name == \"$device_name\")")
        
        if [[ -n "$device_info" && "$device_info" != "null" ]]; then
            local drive_result
            if drive_result=$(process_drive "$full_device" "$device_info"); then
                all_drives=$(echo "$all_drives" | jq ". + [$drive_result]")
            else
                warn "Failed to process device: $full_device"
            fi
        fi
    done <<< "$devices"
    
    # Build final JSON output
    local final_json
    final_json=$(jq -n \
        --argjson drives "$all_drives" \
        --arg timestamp "$(date -Iseconds)" \
        --arg version "$VERSION" \
        --arg hostname "$(hostname)" \
        --arg system "$(uname -a)" \
        '{
            drives: $drives,
            timestamp: $timestamp,
            version: $version,
            system_info: {
                hostname: $hostname,
                system: $system
            }
        }')
    
    # Write outputs
    echo "$final_json" | jq '.' > "$DRIVES_JSON"
    generate_human_report "$final_json"
    
    local drive_count
    drive_count=$(echo "$final_json" | jq '.drives | length')
    
    log "Detection complete - found $drive_count drive(s)"
    log "JSON output: $DRIVES_JSON"
    log "Human report: $DRIVES_HUMAN"
    log "Log file: $LOG_FILE"
    
    # Display summary
    if [[ "${QUIET:-false}" != "true" ]]; then
        echo ""
        echo "=== DRIVE DETECTION SUMMARY ==="
        echo "Drives found: $drive_count"
        
        if [[ $drive_count -gt 0 ]]; then
            echo ""
            echo "Devices:"
            echo "$final_json" | jq -r '.drives[] | "  \(.device) - \(.size) \(.interface) \(.model)"'
            
            echo ""
            echo "Warnings:"
            local mounted_count
            mounted_count=$(echo "$final_json" | jq '[.drives[] | select(.mounted == true)] | length')
            if [[ $mounted_count -gt 0 ]]; then
                echo "  - $mounted_count device(s) currently mounted"
                echo "  - Unmount before wiping: umount /dev/sdX"
            else
                echo "  - No mounted devices detected"
            fi
        fi
        
        echo ""
        echo "Output files:"
        echo "  JSON: $DRIVES_JSON"
        echo "  Report: $DRIVES_HUMAN"
    fi
}

# Handle command line arguments
case "${1:-}" in
    "--help"|"-h")
        cat << EOF
Obliterator Drive Detection Script v$VERSION

Usage: $0 [OPTIONS]

Options:
  --help, -h          Show this help message
  --quiet, -q         Suppress output summary
  --debug             Enable debug output
  --output-dir DIR    Set output directory (default: $OUTPUT_DIR)
  --json-only         Only output JSON, no human report

Environment Variables:
  OBLITERATOR_OUTPUT_DIR    Output directory for files
  DEBUG                     Enable debug mode (true/false)

Examples:
  sudo $0                    # Detect all drives
  sudo $0 --quiet           # Silent detection
  DEBUG=true sudo $0        # Debug mode

Output Files:
  detected_drives.json      # Machine-readable drive information
  detected_drives.txt       # Human-readable report
  detect_drives.log         # Operation log

Note: Run as root/sudo for complete device access
EOF
        exit 0
        ;;
    "--quiet"|"-q")
        QUIET=true
        ;;
    "--debug")
        DEBUG=true
        ;;
    "--json-only")
        JSON_ONLY=true
        ;;
    "--output-dir")
        if [[ -z "${2:-}" ]]; then
            error "Output directory not specified"
            exit 1
        fi
        OUTPUT_DIR="$2"
        shift
        ;;
    "")
        # Default - no arguments
        ;;
    *)
        error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Run main function
main "$@"
