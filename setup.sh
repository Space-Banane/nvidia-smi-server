#!/bin/bash

set -e

echo "======================================"
echo "NVIDIA-SMI Server Setup Script"
echo "======================================"
echo ""

# 1. Check if main.py starts with the correct comment
echo "[1/7] Checking main.py header..."
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found in current directory!"
    exit 1
fi

FIRST_LINE=$(head -n 1 main.py)
if [ "$FIRST_LINE" != "#nvidia-smi-server/main.py" ]; then
    echo "ERROR: main.py does not start with '#nvidia-smi-server/main.py'"
    echo "Found: $FIRST_LINE"
    exit 1
fi
echo "✓ main.py header is correct"
echo ""

# 2. Check if we are on Ubuntu
echo "[2/7] Checking if running on Ubuntu..."
if [ ! -f /etc/os-release ]; then
    echo "ERROR: /etc/os-release not found. Cannot determine OS."
    exit 1
fi

source /etc/os-release
if [[ ! "$ID" =~ ^ubuntu$ ]] && [[ ! "$ID_LIKE" =~ ubuntu ]]; then
    echo "ERROR: This script is designed for Ubuntu-based distributions."
    echo "Detected: $ID ($PRETTY_NAME)"
    exit 1
fi
echo "✓ Running on $PRETTY_NAME"
echo ""

# 2.1. Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# 3. Copy files to /opt and service file to systemd
echo "[3/7] Installing service files..."
INSTALL_DIR="/opt/nvidia-smi-server"
mkdir -p "$INSTALL_DIR"
cp main.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/main.py"

if [ ! -f "nvidia-smi-server.service" ]; then
    echo "ERROR: nvidia-smi-server.service not found!"
    exit 1
fi

cp nvidia-smi-server.service /etc/systemd/system/
echo "✓ Files installed to $INSTALL_DIR"
echo "✓ Service file installed to /etc/systemd/system/"
echo ""

# 4. Reload systemd daemon
echo "[4/7] Reloading systemd daemon..."
systemctl daemon-reload
echo "✓ Systemd daemon reloaded"
echo ""

# 5. Enable and start the service
echo "[5/7] Enabling and starting nvidia-smi-server service..."
systemctl enable nvidia-smi-server.service
systemctl start nvidia-smi-server.service
echo "✓ Service enabled and started"
echo ""

# 6. Check service status
echo "[6/7] Checking service status..."
sleep 2  # Give the service a moment to start
if systemctl is-active --quiet nvidia-smi-server.service; then
    echo "✓ Service is running"
    systemctl status nvidia-smi-server.service --no-pager | head -n 10
else
    echo "ERROR: Service failed to start!"
    systemctl status nvidia-smi-server.service --no-pager
    exit 1
fi
echo ""

# 7. Send test request
echo "[7/7] Sending test request to http://localhost:8000..."
sleep 1  # Give the server a moment to bind to the port

if command -v curl &> /dev/null; then
    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/ 2>&1)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✓ Test request successful (HTTP $HTTP_CODE)"
        echo ""
        echo "Response preview:"
        echo "$BODY" | python3 -m json.tool 2>/dev/null | head -n 20
        if [ $(echo "$BODY" | python3 -m json.tool 2>/dev/null | wc -l) -gt 20 ]; then
            echo "... (truncated)"
        fi
    else
        echo "ERROR: Test request failed (HTTP $HTTP_CODE)"
        echo "Response:"
        echo "$BODY"
        exit 1
    fi
else
    echo "WARNING: curl not found, skipping test request"
    echo "You can manually test with: curl http://localhost:8000/"
fi

echo ""
echo "======================================"
echo "✓ Setup completed successfully!"
echo "======================================"
echo ""
echo "Service is now running on http://localhost:8000/"
echo ""
echo "Useful commands:"
echo "  - Check status:    sudo systemctl status nvidia-smi-server"
echo "  - Stop service:    sudo systemctl stop nvidia-smi-server"
echo "  - Start service:   sudo systemctl start nvidia-smi-server"
echo "  - Restart service: sudo systemctl restart nvidia-smi-server"
echo "  - View logs:       sudo journalctl -u nvidia-smi-server -f"
echo "  - Disable service: sudo systemctl disable nvidia-smi-server"
echo ""
