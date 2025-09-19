#!/usr/bin/env bash
# Simple Drive Detection Script
# Based on /proc/partitions approach - no jq dependencies
# Version: 1.0.0

set -euo pipefail

# Configuration
OUTPUT_DIR="${OBLITERATOR_OUTPUT_DIR:-/tmp/obliterator}"
DRIVES_JSON="$OUTPUT_DIR/detected_drives.json"
DRIVES_TXT="$OUTPUT_DIR/detected_drives.txt"
LOG_FILE="$OUTPUT_DIR/detection.log"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Logging
log_msg() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null || true
}

warn_msg() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
    echo "[WARN] $1" >> "$LOG_FILE" 2>/dev/null || true
}

error_msg() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    echo "[ERROR] $1" >> "$LOG_FILE" 2>/dev/null || true
}

# Format bytes to human readable
format_size() {
    local bytes=$1
    if [[ $bytes -ge 1073741824 ]]; then
        echo "$((bytes / 1073741824)) GB"
    elif [[ $bytes -ge 1048576 ]]; then
        echo "$((bytes / 1048576)) MB"
    else
        echo "$((bytes / 1024)) KB"
    fi
}

# Check if device is OS drive
is_os_drive() {
    local device_path="$1"
    [[ -f /proc/mounts ]] || return 1
    
    while read -r line; do
        set -- $line
        local mounted_device="$1"
        local mount_point="$2"
        
        if [[ "$mounted_device" == "${device_path}"* && "$mount_point" == "/" ]]; then
            return 0
        fi
    done < /proc/mounts
    
    return 1
}

# Check if device is mounted
is_mounted() {
    local device_path="$1"
    [[ -f /proc/mounts ]] || return 1
    grep -q "^$device_path" /proc/mounts
}

# Get device details
get_device_info() {
    local device_name="$1"
    local blocks="$2"
    local device_path="/dev/$device_name"
    
    # Check if device exists
    [[ -e "$device_path" ]] || return 1
    
    # Calculate size
    local size_bytes=$((blocks * 512))
    local size_human
    size_human=$(format_size $size_bytes)
    
    # Default values
    local device_type="Unknown"
    local model="Unknown"
    local serial="Unknown"
    local interface="unknown"
    local removable="false"
    local is_ssd="false"
    local os_drive="false"
    local mounted="false"
    
    # Get info from /sys
    local sys_path="/sys/block/$device_name"
    
    # Check if removable
    if [[ -f "$sys_path/removable" ]]; then
        local removable_flag
        removable_flag=$(cat "$sys_path/removable" 2>/dev/null || echo "0")
        if [[ "$removable_flag" == "1" ]]; then
            removable="true"
            device_type="USB/Removable"
            interface="usb"
        fi
    fi
    
    # Check if SSD (non-rotational)
    if [[ -f "$sys_path/queue/rotational" ]]; then
        local rotational
        rotational=$(cat "$sys_path/queue/rotational" 2>/dev/null || echo "1")
        if [[ "$rotational" == "0" ]]; then
            is_ssd="true"
            device_type="SSD"
            interface="sata"
        else
            device_type="HDD"
            interface="sata"
        fi
    fi
    
    # Check for NVMe
    if [[ "$device_name" =~ nvme ]]; then
        device_type="NVMe SSD"
        interface="nvme"
        is_ssd="true"
    fi
    
    # Get model
    if [[ -f "$sys_path/device/model" ]]; then
        model=$(cat "$sys_path/device/model" 2>/dev/null | tr -d '\0' | xargs)
        [[ -n "$model" ]] || model="Unknown"
    fi
    
    # Get serial (try different locations)
    for serial_file in "$sys_path/device/serial" "$sys_path/serial"; do
        if [[ -f "$serial_file" ]]; then
            serial=$(cat "$serial_file" 2>/dev/null | tr -d '\0' | xargs)
            [[ -n "$serial" ]] && break
        fi
    done
    
    # Check OS drive status
    if is_os_drive "$device_path"; then
        os_drive="true"
    fi
    
    # Check mount status
    if is_mounted "$device_path"; then
        mounted="true"
    fi
    
    # Determine recommended method
    local method="MULTI_PASS_OVERWRITE"
    local confidence="medium"
    local reason="Standard overwrite method"
    
    case "$interface" in
        "nvme")
            method="NVME_CRYPTO_ERASE"
            confidence="high"
            reason="NVMe cryptographic erase"
            ;;
        "sata")
            if [[ "$is_ssd" == "true" ]]; then
                method="ATA_SECURE_ERASE_ENHANCED"
                confidence="high"
                reason="SSD enhanced secure erase"
            else
                method="ATA_SECURE_ERASE"
                confidence="high"
                reason="HDD secure erase"
            fi
            ;;
        "usb")
            method="MULTI_PASS_OVERWRITE"
            confidence="medium"
            reason="USB device overwrite"
            ;;
    esac
    
    # Output device info (one line per call)
    echo "DEVICE_START"
    echo "device=$device_path"
    echo "name=$device_name"
    echo "size=$size_human"
    echo "size_bytes=$size_bytes"
    echo "type=$device_type"
    echo "interface=$interface"
    echo "model=$model"
    echo "serial=$serial"
    echo "is_ssd=$is_ssd"
    echo "removable=$removable"
    echo "os_drive=$os_drive"
    echo "mounted=$mounted"
    echo "method=$method"
    echo "confidence=$confidence"
    echo "reason=$reason"
    echo "DEVICE_END"
}

# Main detection function
detect_devices() {
    log_msg "Starting device detection..."
    
    # Check /proc/partitions
    if [[ ! -f /proc/partitions ]]; then
        error_msg "/proc/partitions not found"
        return 1
    fi
    
    local devices_found=0
    local temp_file="/tmp/devices_$$"
    
    # Process /proc/partitions
    tail -n +3 /proc/partitions | while read -r line; do
        set -- $line
        [[ $# -ge 4 ]] || continue
        
        local major="$1"
        local minor="$2" 
        local blocks="$3"
        local name="$4"
        
        # Skip partitions (devices ending with numbers)
        [[ ! "$name" =~ [0-9]$ ]] || continue
        
        # Skip very small devices (< 1GB)
        [[ $blocks -gt 2097152 ]] || continue
        
        log_msg "Processing device: $name"
        
        # Get device info
        if device_info=$(get_device_info "$name" "$blocks"); then
            echo "$device_info" >> "$temp_file"
            ((devices_found++))
        fi
    done
    
    # Build JSON output
    create_json_output "$temp_file" $devices_found
    create_text_output "$temp_file" $devices_found
    
    rm -f "$temp_file"
    
    log_msg "Detection complete: $devices_found devices found"
    return 0
}

# Create JSON output
create_json_output() {
    local temp_file="$1"
    local device_count="$2"
    
    log_msg "Creating JSON output..."
    
    # Start JSON
    cat > "$DRIVES_JSON" << EOF
{
    "drives": [
EOF
    
    local first_device=true
    local current_device=""
    
    # Process each device block
    if [[ -f "$temp_file" ]]; then
        while read -r line; do
            if [[ "$line" == "DEVICE_START" ]]; then
                if [[ "$first_device" == "false" ]]; then
                    echo "        }," >> "$DRIVES_JSON"
                fi
                echo "        {" >> "$DRIVES_JSON"
                first_device=false
            elif [[ "$line" == "DEVICE_END" ]]; then
                continue
            elif [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
                local key="${BASH_REMATCH[1]}"
                local value="${BASH_REMATCH[2]}"
                
                # Format JSON field
                case "$key" in
                    "size_bytes"|"is_ssd"|"removable"|"os_drive"|"mounted")
                        echo "            \"$key\": $value," >> "$DRIVES_JSON"
                        ;;
                    "reason")
                        echo "            \"recommended_method\": {" >> "$DRIVES_JSON"
                        echo "                \"method\": \"$(grep "method=" "$temp_file" | tail -1 | cut -d= -f2)\"," >> "$DRIVES_JSON"
                        echo "                \"confidence\": \"$(grep "confidence=" "$temp_file" | tail -1 | cut -d= -f2)\"," >> "$DRIVES_JSON"
                        echo "                \"reason\": \"$value\"" >> "$DRIVES_JSON"
                        echo "            }" >> "$DRIVES_JSON"
                        ;;
                    "method"|"confidence")
                        # Skip - handled with reason
                        ;;
                    *)
                        echo "            \"$key\": \"$value\"," >> "$DRIVES_JSON"
                        ;;
                esac
            fi
        done < "$temp_file"
    fi
    
    # Close last device if any
    if [[ "$first_device" == "false" ]]; then
        echo "        }" >> "$DRIVES_JSON"
    fi
    
    # Finish JSON
    cat >> "$DRIVES_JSON" << EOF
    ],
    "timestamp": "$(date -Iseconds)",
    "version": "1.0.0",
    "system_info": {
        "hostname": "$(hostname)",
        "system": "$(uname -a)"
    },
    "device_count": $device_count
}
EOF
    
    log_msg "JSON output created: $DRIVES_JSON"
}

# Create text output
create_text_output() {
    local temp_file="$1"
    local device_count="$2"
    
    log_msg "Creating text output..."
    
    cat > "$DRIVES_TXT" << EOF
# Obliterator Drive Detection Report
# Generated: $(date)
# System: $(uname -a)

Detected $device_count storage device(s):

EOF
    
    local counter=1
    local in_device=false
    
    if [[ -f "$temp_file" ]]; then
        while read -r line; do
            if [[ "$line" == "DEVICE_START" ]]; then
                echo "Device $counter:" >> "$DRIVES_TXT"
                in_device=true
                ((counter++))
            elif [[ "$line" == "DEVICE_END" ]]; then
                echo "" >> "$DRIVES_TXT"
                in_device=false
            elif [[ "$in_device" == "true" && "$line" =~ ^([^=]+)=(.*)$ ]]; then
                local key="${BASH_REMATCH[1]}"
                local value="${BASH_REMATCH[2]}"
                
                case "$key" in
                    "device") echo "  Path: $value" >> "$DRIVES_TXT" ;;
                    "model") echo "  Model: $value" >> "$DRIVES_TXT" ;;
                    "size") echo "  Size: $value" >> "$DRIVES_TXT" ;;
                    "type") echo "  Type: $value" >> "$DRIVES_TXT" ;;
                    "method") echo "  Recommended: $value" >> "$DRIVES_TXT" ;;
                    "mounted") 
                        if [[ "$value" == "true" ]]; then
                            echo "  ⚠️  WARNING: Device is mounted!" >> "$DRIVES_TXT"
                        fi
                        ;;
                    "os_drive")
                        if [[ "$value" == "true" ]]; then
                            echo "  ⚠️  WARNING: This appears to be the OS drive!" >> "$DRIVES_TXT"
                        fi
                        ;;
                esac
            fi
        done < "$temp_file"
    fi
    
    cat >> "$DRIVES_TXT" << EOF

# Safety Notes:
# - Always verify target devices before wiping
# - Unmount any mounted filesystems first
# - Be extra careful with OS drives
# - Test with loopback devices first

# Usage:
# - JSON data: $DRIVES_JSON
# - GUI: cd gui && sudo python3 main.py
# - CLI: sudo ./wipe.sh /dev/sdX
EOF
    
    log_msg "Text output created: $DRIVES_TXT"
}

# Initialize
init() {
    mkdir -p "$OUTPUT_DIR" 2>/dev/null || true
    chmod 700 "$OUTPUT_DIR" 2>/dev/null || true
    
    # Clear log
    echo "# Detection started: $(date)" > "$LOG_FILE" 2>/dev/null || true
}

# Main execution
main() {
    init
    
    log_msg "Obliterator Simple Drive Detection v1.0.0"
    
    if [[ $EUID -ne 0 ]]; then
        warn_msg "Not running as root - some info may be limited"
    fi
    
    if detect_devices; then
        local count
        count=$(grep -c '"device":' "$DRIVES_JSON" 2>/dev/null || echo "0")
        
        echo ""
        echo "=== DETECTION SUMMARY ==="
        echo "Devices found: $count"
        echo "JSON file: $DRIVES_JSON"
        echo "Text file: $DRIVES_TXT"
        echo "Log file: $LOG_FILE"
        
        if [[ $count -gt 0 ]]; then
            echo ""
            echo "Detected devices:"
            grep "Path:" "$DRIVES_TXT" 2>/dev/null | sed 's/  Path: /  /' || true
        fi
        
        echo ""
        echo "Next steps:"
        echo "  GUI: cd gui && sudo python3 main.py"
        echo "  CLI: sudo ./wipe.sh /dev/sdX"
    else
        error_msg "Detection failed"
        exit 1
    fi
}

# Handle arguments
case "${1:-}" in
    "--help"|"-h")
        echo "Simple Drive Detection Script"
        echo "Usage: $0 [--help]"
        echo ""
        echo "Detects storage devices using /proc/partitions"
        echo "Creates JSON and text output files"
        echo "Run as root for complete information"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        error_msg "Unknown option: $1"
        echo "Use --help for usage"
        exit 1
        ;;
esac
