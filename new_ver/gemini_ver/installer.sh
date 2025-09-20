#!/bin/bash
# installer.sh - Installs dependencies for Obliterator
# Run with: sudo bash installer.sh

echo "--- Starting Obliterator Dependency Installation ---"

# Update package lists
apt-get update

# Install core sanitization and hardware tools
# hdparm: For ATA commands like Secure Erase and HPA/DCO handling
# nvme-cli: For NVMe format and sanitize commands
# smartmontools: For reading device serial numbers and health (smartctl)
# pv: For monitoring progress of data streams (dd)
echo "Installing hardware tools..."
apt-get install -y hdparm nvme-cli smartmontools pv

# Install Python environment and GUI toolkit
# python3-pip: To install Python packages
# python3-tk: Required for tkinter
echo "Installing Python and GUI tools..."
apt-get install -y python3 python3-pip python3-tk

# Install required Python libraries
# customtkinter: For the modern GUI theme
# pycryptodome: For signing the certificates
echo "Installing Python libraries..."
pip3 install customtkinter pycryptodome

echo "--- Installation Complete ---"
echo "You can now run the GUI using: python3 /mnt/home/obliterator/obliterator_gui.py"

