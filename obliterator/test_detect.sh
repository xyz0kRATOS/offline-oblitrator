#!/usr/bin/env bash
# Quick test for the fixed drive detection
# Run this to verify the detection script works

echo "Testing Obliterator Drive Detection Fix"
echo "======================================"

# Test basic lsblk functionality first
echo "1. Testing basic lsblk command..."
if lsblk -J -o NAME,SIZE,TYPE >/dev/null 2>&1; then
    echo "✅ lsblk works"
else
    echo "❌ lsblk failed"
    exit 1
fi

# Test the detection script
echo ""
echo "2. Testing drive detection script..."

# Make script executable
chmod +x detect_drives.sh

# Run detection with debug
echo "Running: sudo ./detect_drives.sh --debug"
sudo DEBUG=true ./detect_drives.sh --debug

# Check results
echo ""
echo "3. Checking output files..."

if [ -f "/tmp/obliterator/detected_drives.json" ]; then
    echo "✅ JSON file created"
    echo "Drive count: $(grep -c '"device":' /tmp/obliterator/detected_drives.json 2>/dev/null || echo "0")"
else
    echo "❌ JSON file not created"
fi

if [ -f "/tmp/obliterator/detected_drives.txt" ]; then
    echo "✅ Human-readable report created"
else
    echo "❌ Human-readable report not created"
fi

# Show summary
echo ""
echo "4. Detection Summary:"
echo "===================="
if [ -f "/tmp/obliterator/detected_drives.txt" ]; then
    head -20 /tmp/obliterator/detected_drives.txt
else
    echo "No summary available"
fi

echo ""
echo "Test completed. If you see ✅ marks above, the detection is working."
echo "You can now run: cd gui && sudo python3 main.py"
