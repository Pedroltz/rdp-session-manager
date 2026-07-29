#!/bin/bash
# RDP Session Manager initialization script

echo "Starting RDP Session Manager..."

# Check dependencies
if ! python3 -c "import gi" 2>/dev/null; then
    echo "Error: PyGObject not found"
    echo "Install with: sudo apt install python3-gi"
    exit 1
fi

if ! python3 -c "import psutil" 2>/dev/null; then
    echo "Warning: psutil not found"
    echo "Install with: sudo apt install python3-psutil"
fi

# Run application
python3 src/main.py
