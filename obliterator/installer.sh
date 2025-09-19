#!/usr/bin/env bash
# Obliterator Dependencies Installer
# For Bookworm Puppy Linux / Debian Bookworm
# Version: 1.0.0

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Detect package manager
detect_package_manager() {
    if command -v apt-get &> /dev/null; then
        echo "apt"
    elif command -v petget &> /dev/null; then
        echo "petget"  # Puppy Linux package manager
    elif command -v apk &> /dev/null; then
        echo "apk"     # Alpine Linux
    else
        echo "unknown"
    fi
}

# Install packages using appropriate package manager
install_packages() {
    local pkg_mgr="$1"
    shift
    local packages=("$@")

    case "$pkg_mgr" in
        "apt")
            log "Updating package lists..."
            apt-get update -qq
            log "Installing packages: ${packages[*]}"
            apt-get install -y "${packages[@]}" || {
                warn "Some packages failed to install via apt, will try manual installation"
                return 1
            }
            ;;
        "petget")
            log "Using Puppy Linux petget package manager"
            for pkg in "${packages[@]}"; do
                log "Installing $pkg..."
                petget install "$pkg" || warn "Failed to install $pkg via petget"
            done
            ;;
        "apk")
            log "Using Alpine apk package manager"
            apk update
            apk add "${packages[@]}" || {
                warn "Some packages failed to install via apk"
                return 1
            }
            ;;
        *)
            error "Unknown package manager - manual installation required"
            return 1
            ;;
    esac
}

# Manual installation fallback
install_manual() {
    local tool="$1"
    local url="$2"
    local install_cmd="$3"

    log "Attempting manual installation of $tool"

    if ! command -v wget &> /dev/null && ! command -v curl &> /dev/null; then
        error "Neither wget nor curl available for manual downloads"
        return 1
    fi

    local temp_dir
    temp_dir=$(mktemp -d)
    cd "$temp_dir" || return 1

    if command -v wget &> /dev/null; then
        wget -q "$url" || return 1
    else
        curl -sL "$url" -o "$(basename "$url")" || return 1
    fi

    eval "$install_cmd" || {
        error "Manual installation of $tool failed"
        rm -rf "$temp_dir"
        return 1
    }

    rm -rf "$temp_dir"
    log "Manual installation of $tool completed"
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Verify installation
verify_tool() {
    local tool="$1"
    local version_flag="${2:---version}"

    if command_exists "$tool"; then
        log "✓ $tool is installed"
        if [[ "$tool" != "python3-tk" ]]; then  # Skip version check for python3-tk
            $tool $version_flag &> /dev/null || true
        fi
        return 0
    else
        error "✗ $tool is NOT installed"
        return 1
    fi
}

# Install Python packages via pip
install_python_packages() {
    log "Installing Python packages..."

    # Ensure pip is available
    if ! command_exists pip3; then
        if command_exists python3; then
            python3 -m ensurepip --default-pip || {
                warn "Could not install pip via ensurepip"
            }
        fi
    fi

    if command_exists pip3; then
        # Install essential Python packages for GUI
        pip3 install --user --no-warn-script-location \
            tkinter-tooltip \
            pillow \
            requests \
            supabase || warn "Some Python packages failed to install"
    else
        warn "pip3 not available - Python packages not installed"
    fi
}

# Test tkinter availability
test_tkinter() {
    log "Testing tkinter availability..."
    python3 -c "
import tkinter as tk
import tkinter.ttk as ttk
root = tk.Tk()
root.withdraw()
print('tkinter test: OK')
root.destroy()
" 2>/dev/null && log "✓ tkinter is working" || warn "✗ tkinter test failed"
}

# Create virtual environment for GUI
setup_venv() {
    log "Setting up Python virtual environment..."

    if command_exists python3; then
        python3 -m venv /opt/obliterator-venv || {
            warn "Could not create virtual environment"
            return 1
        }

        # Activate and install packages
        source /opt/obliterator-venv/bin/activate
        pip install --no-warn-script-location \
            pillow \
            requests \
            customtkinter || warn "Some packages failed in venv"
        deactivate

        log "Virtual environment created at /opt/obliterator-venv"
    else
        error "Python3 not available"
        return 1
    fi
}

main() {
    log "Starting Obliterator dependencies installation..."

    check_root

    # Detect system
    local pkg_mgr
    pkg_mgr=$(detect_package_manager)
    log "Detected package manager: $pkg_mgr"

    # Core system packages
    local core_packages=(
        "hdparm"           # ATA drive utilities
        "nvme-cli"         # NVMe utilities
        "parted"           # Disk partitioning
        "gdisk"            # GPT partitioning
        "util-linux"       # lsblk, etc.
        "lsscsi"           # SCSI utilities
        "smartmontools"    # SMART utilities
        "pv"               # Progress viewer
        "coreutils"        # dd, shred, etc.
        "openssl"          # Cryptographic operations
        "jq"               # JSON processing
        "sqlite3"          # Local database
        "cryptsetup"       # LUKS operations
        "dbus"             # System bus
        "udev"             # Device management
    )

    # Python and GUI packages
    local python_packages=(
        "python3"
        "python3-dev"
        "python3-pip"
        "python3-venv"
        "python3-tk"       # Tkinter GUI
        "python3-pil"      # Pillow imaging
    )

    # PDF generation tools
    local pdf_packages=(
        "wkhtmltopdf"      # HTML to PDF
        "pandoc"           # Document converter
        "weasyprint"       # Alternative PDF generator
    )

    # Network tools (for optional cloud sync)
    local network_packages=(
        "curl"
        "wget"
        "ca-certificates"
    )

    # Combine all packages
    local all_packages=()
    all_packages+=("${core_packages[@]}")
    all_packages+=("${python_packages[@]}")
    all_packages+=("${pdf_packages[@]}")
    all_packages+=("${network_packages[@]}")

    # Attempt package installation
    if [[ "$pkg_mgr" != "unknown" ]]; then
        install_packages "$pkg_mgr" "${all_packages[@]}" || {
            warn "Package installation had issues, will verify individually"
        }
    else
        warn "No supported package manager found"
        log "Please install packages manually:"
        printf '%s\n' "${all_packages[@]}"
    fi

    # Install Python packages
    install_python_packages

    # Setup virtual environment
    setup_venv || warn "Virtual environment setup failed"

    # Test tkinter
    test_tkinter

    # Verification phase
    log "Verifying installed tools..."

    local failed_tools=()

    # Verify core tools
    verify_tool "hdparm" "--version" || failed_tools+=("hdparm")
    verify_tool "nvme" "version" || failed_tools+=("nvme")
    verify_tool "lsblk" "--version" || failed_tools+=("lsblk")
    verify_tool "parted" "--version" || failed_tools+=("parted")
    verify_tool "sgdisk" "--version" || failed_tools+=("sgdisk")
    verify_tool "pv" "--version" || failed_tools+=("pv")
    verify_tool "dd" "--version" || failed_tools+=("dd")
    verify_tool "shred" "--version" || failed_tools+=("shred")
    verify_tool "openssl" "version" || failed_tools+=("openssl")
    verify_tool "jq" "--version" || failed_tools+=("jq")
    verify_tool "sqlite3" "--version" || failed_tools+=("sqlite3")
    verify_tool "cryptsetup" "--version" || failed_tools+=("cryptsetup")
    verify_tool "python3" "--version" || failed_tools+=("python3")

    # Verify PDF tools (at least one should work)
    local pdf_available=false
    if verify_tool "wkhtmltopdf" "--version"; then
        pdf_available=true
    elif verify_tool "pandoc" "--version"; then
        pdf_available=true
    elif command_exists python3 && python3 -c "import weasyprint" 2>/dev/null; then
        log "✓ weasyprint (Python) is available"
        pdf_available=true
    fi

    if [[ "$pdf_available" == false ]]; then
        failed_tools+=("pdf-generator")
        error "No PDF generation tool available (wkhtmltopdf, pandoc, or weasyprint)"
    fi

    # Report results
    if [[ ${#failed_tools[@]} -eq 0 ]]; then
        log "🎉 All dependencies installed successfully!"
        log "Next steps:"
        log "  1. Run ./setup_key_storage.sh to setup private keys"
        log "  2. Test with ./examples/test_loopback.sh"
        log "  3. Launch GUI with: cd gui && python3 main.py"
    else
        error "❌ Some tools failed to install:"
        printf '%s\n' "${failed_tools[@]}"
        log "Manual installation may be required for missing tools"
        exit 1
    fi

    # Create basic directories
    mkdir -p /opt/obliterator/{logs,certificates,temp}
    chmod 700 /opt/obliterator

    log "Installation completed! Check above for any warnings."
}

# Handle script arguments
case "${1:-}" in
    "--help"|"-h")
        echo "Obliterator Dependencies Installer"
        echo "Usage: sudo $0 [--help|--list-packages|--verify-only]"
        echo ""
        echo "Options:"
        echo "  --help          Show this help"
        echo "  --list-packages List packages that will be installed"
        echo "  --verify-only   Only verify existing installations"
        exit 0
        ;;
    "--list-packages")
        echo "Core packages: hdparm nvme-cli parted gdisk util-linux lsscsi"
        echo "               smartmontools pv coreutils openssl jq sqlite3"
        echo "               cryptsetup dbus udev"
        echo "Python packages: python3 python3-dev python3-pip python3-venv"
        echo "                python3-tk python3-pil"
        echo "PDF packages: wkhtmltopdf pandoc weasyprint"
        echo "Network packages: curl wget ca-certificates"
        exit 0
        ;;
    "--verify-only")
        log "Verification mode - checking existing installations only"
        # Set a flag to skip installation
        VERIFY_ONLY=true
        ;;
    "")
        # Normal installation
        VERIFY_ONLY=false
        ;;
    *)
        error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Run main installation unless verify-only mode
if [[ "${VERIFY_ONLY:-false}" == "true" ]]; then
    log "Verifying existing installations..."
    # Run only verification parts
    verify_tool "hdparm" "--version"
    verify_tool "nvme" "version"
    verify_tool "python3" "--version"
    test_tkinter
    log "Verification complete"
else
    main "$@"
fi

