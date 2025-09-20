#!/bin/bash
# Obliterator Installation Script for Bookworm Puppy Linux
# Purpose: Install all required packages and setup environment for secure data wiping
# Runtime: Bookworm Puppy Linux
# Privileges: root required
# Usage: sudo ./installer-bash.sh [--offline]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/obliterator-install.log"
OFFLINE_MODE=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --offline)
            OFFLINE_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--offline] [--help]"
            echo "  --offline  Use offline package installation (requires .deb files)"
            echo "  --help     Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root. Use: sudo $0"
fi

log "Starting Obliterator installation on Bookworm Puppy Linux"

# Create necessary directories
log "Creating directory structure..."
mkdir -p /opt/obliterator/{bin,lib,gui,certs,wipes,keys}
mkdir -p /opt/obliterator/certificates
mkdir -p /var/log/obliterator
mkdir -p /tmp/obliterator

# Set up USB mount point for certificates
USB_MOUNT="/mnt/obliterator-usb"
mkdir -p "$USB_MOUNT"

# Required packages
REQUIRED_PACKAGES=(
    "hdparm"
    "nvme-cli"
    "sgutils2"
    "parted"
    "smartmontools"
    "cryptsetup"
    "python3"
    "python3-pip"
    "python3-tk"
    "python3-json"
    "python3-cryptography"
    "dbus"
    "udev"
    "util-linux"
    "coreutils"
    "pciutils"
    "usbutils"
)

PYTHON_PACKAGES=(
    "customtkinter"
    "cryptography"
    "reportlab"
    "PyJWT"
    "psutil"
)

# Function to install packages online
install_online() {
    log "Updating package lists..."
    apt-get update || warning "Package update failed, continuing with cached lists"

    log "Installing required system packages..."
    for package in "${REQUIRED_PACKAGES[@]}"; do
        log "Installing $package..."
        if apt-get install -y "$package"; then
            success "$package installed successfully"
        else
            warning "Failed to install $package, may need manual installation"
        fi
    done

    log "Installing Python packages..."
    for package in "${PYTHON_PACKAGES[@]}"; do
        log "Installing Python package $package..."
        if pip3 install "$package"; then
            success "Python package $package installed successfully"
        else
            warning "Failed to install Python package $package"
        fi
    done
}

# Function to install packages offline
install_offline() {
    log "Installing packages in offline mode..."
    DEB_DIR="$SCRIPT_DIR/debs"

    if [[ ! -d "$DEB_DIR" ]]; then
        error "Offline mode requires $DEB_DIR directory with .deb files"
    fi

    log "Installing .deb packages from $DEB_DIR..."
    if ls "$DEB_DIR"/*.deb 1> /dev/null 2>&1; then
        dpkg -i "$DEB_DIR"/*.deb || true
        apt-get install -f -y # Fix any dependency issues
    else
        warning "No .deb files found in $DEB_DIR"
    fi

    # Install Python packages from wheels if available
    WHEEL_DIR="$SCRIPT_DIR/wheels"
    if [[ -d "$WHEEL_DIR" ]]; then
        log "Installing Python wheels from $WHEEL_DIR..."
        pip3 install --no-index --find-links "$WHEEL_DIR" "${PYTHON_PACKAGES[@]}" || warning "Some Python packages failed to install offline"
    fi
}

# Install packages based on mode
if [[ "$OFFLINE_MODE" == true ]]; then
    install_offline
else
    install_online
fi

# Create udev rules for device access
log "Setting up udev rules..."
cat > /etc/udev/rules.d/99-obliterator.rules << 'EOF'
# Obliterator udev rules for secure device access
KERNEL=="sd*", GROUP="disk", MODE="0664"
KERNEL=="nvme*", GROUP="disk", MODE="0664"
SUBSYSTEM=="block", GROUP="disk", MODE="0664"
ACTION=="add", SUBSYSTEM=="block", RUN+="/bin/chmod 664 %N"
EOF

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

# Create obliterator user and group
log "Setting up obliterator user and permissions..."
if ! getent group obliterator > /dev/null; then
    groupadd obliterator
fi
if ! getent passwd obliterator > /dev/null; then
    useradd -g obliterator -d /opt/obliterator -s /bin/bash obliterator
fi

# Add obliterator user to necessary groups
usermod -a -G disk,storage,plugdev obliterator

# Set permissions
chown -R obliterator:obliterator /opt/obliterator
chmod -R 755 /opt/obliterator
chmod 700 /opt/obliterator/keys
chmod 755 /opt/obliterator/certificates

# Create systemd mount service for USB persistence
log "Setting up USB persistence mount service..."
cat > /etc/systemd/system/obliterator-usb.service << 'EOF'
[Unit]
Description=Mount Obliterator USB for certificate storage
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'USB_DEV=$(blkid -L OBLITERATOR 2>/dev/null || echo ""); if [ -n "$USB_DEV" ]; then mkdir -p /mnt/obliterator-usb && mount "$USB_DEV" /mnt/obliterator-usb && chmod 755 /mnt/obliterator-usb && chown obliterator:obliterator /mnt/obliterator-usb; fi'
ExecStop=/bin/umount /mnt/obliterator-usb

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable obliterator-usb.service

# Test installed tools
log "Testing installed tools..."

test_tool() {
    local tool=$1
    local test_cmd=$2

    if command -v "$tool" > /dev/null; then
        if eval "$test_cmd" > /dev/null 2>&1; then
            success "$tool is working correctly"
        else
            warning "$tool is installed but test command failed"
        fi
    else
        error "$tool is not available"
    fi
}

test_tool "hdparm" "hdparm --version"
test_tool "nvme" "nvme version"
test_tool "sginfo" "sginfo --version"
test_tool "smartctl" "smartctl --version"
test_tool "cryptsetup" "cryptsetup --version"
test_tool "python3" "python3 --version"

# Test Python packages
log "Testing Python packages..."
python3 -c "import customtkinter; print('CustomTkinter:', customtkinter.__version__)" || warning "CustomTkinter test failed"
python3 -c "import cryptography; print('Cryptography version OK')" || warning "Cryptography test failed"
python3 -c "import reportlab; print('ReportLab version OK')" || warning "ReportLab test failed"

# Create launch script
log "Creating launch script..."
cat > /opt/obliterator/bin/obliterator << 'EOF'
#!/bin/bash
# Obliterator Launch Script
export PYTHONPATH="/opt/obliterator/lib:$PYTHONPATH"
cd /opt/obliterator/gui
exec python3 obliterator-gui.py "$@"
EOF

chmod +x /opt/obliterator/bin/obliterator

# Add to system PATH
if ! grep -q "/opt/obliterator/bin" /etc/environment; then
    echo 'PATH="/opt/obliterator/bin:$PATH"' >> /etc/environment
fi

# Create desktop entry for GUI mode
log "Creating desktop entry..."
cat > /usr/share/applications/obliterator.desktop << 'EOF'
[Desktop Entry]
Name=Obliterator
Comment=Secure Data Wiping Tool
Exec=/opt/obliterator/bin/obliterator
Icon=/opt/obliterator/gui/obliterator-icon.png
Terminal=false
Type=Application
Categories=System;Security;
EOF

# Generate initial key pair if not exists
log "Setting up cryptographic keys..."
KEY_DIR="/opt/obliterator/keys"
PRIVATE_KEY="$KEY_DIR/obliterator-private.pem"
PUBLIC_KEY="$KEY_DIR/obliterator-public.pem"

if [[ ! -f "$PRIVATE_KEY" ]]; then
    log "Generating RSA-4096 key pair for certificate signing..."
    openssl genpkey -algorithm RSA -pkcs8 -out "$PRIVATE_KEY" -aes256 -pass pass:obliterator2025
    openssl pkey -in "$PRIVATE_KEY" -pubout -out "$PUBLIC_KEY" -passin pass:obliterator2025

    chmod 600 "$PRIVATE_KEY"
    chmod 644 "$PUBLIC_KEY"
    chown obliterator:obliterator "$PRIVATE_KEY" "$PUBLIC_KEY"
    success "Cryptographic keys generated successfully"
else
    log "Cryptographic keys already exist, skipping generation"
fi

# Create configuration file
log "Creating configuration file..."
cat > /opt/obliterator/obliterator.conf << 'EOF'
# Obliterator Configuration
[general]
version=1.0.0
debug=false
log_level=INFO

[security]
private_key=/opt/obliterator/keys/obliterator-private.pem
public_key=/opt/obliterator/keys/obliterator-public.pem
key_passphrase=obliterator2025
signature_algorithm=RS256

[storage]
certificate_dir=/mnt/obliterator-usb/certificates
local_backup_dir=/opt/obliterator/certificates
usb_label=OBLITERATOR

[wiping]
default_passes=5
verify_after_wipe=true
enable_ata_secure_erase=true
enable_nvme_secure_erase=true
remove_hpa_dco=true

[gui]
theme=dark
window_size=1024x768
show_advanced_options=false
EOF

chown obliterator:obliterator /opt/obliterator/obliterator.conf

# Final system configuration
log "Finalizing system configuration..."

# Ensure proper permissions for block device access
echo 'obliterator ALL=(ALL) NOPASSWD: /bin/dd, /usr/bin/hdparm, /usr/bin/nvme, /usr/bin/smartctl, /sbin/cryptsetup' >> /etc/sudoers.d/obliterator

# Create log rotation configuration
cat > /etc/logrotate.d/obliterator << 'EOF'
/var/log/obliterator/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 obliterator obliterator
}
EOF

success "Obliterator installation completed successfully!"

log "Installation Summary:"
log "- Installation directory: /opt/obliterator"
log "- Launch command: obliterator"
log "- Configuration file: /opt/obliterator/obliterator.conf"
log "- Certificate storage: /mnt/obliterator-usb/certificates"
log "- Log files: /var/log/obliterator/"
log "- USB mount point: /mnt/obliterator-usb"

echo ""
echo -e "${GREEN}Installation Complete!${NC}"
echo "To run Obliterator:"
echo "  1. Graphical mode: obliterator"
echo "  2. Command line: cd /opt/obliterator && python3 gui/obliterator-gui.py"
echo "  3. Test installation: obliterator --test"
echo ""
echo "Note: Ensure your USB drive is labeled 'OBLITERATOR' for automatic certificate storage"
echo "To label USB: sudo e2label /dev/sdX1 OBLITERATOR"

