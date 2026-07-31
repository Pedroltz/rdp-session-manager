#!/bin/bash
# RDP Session Manager startup script

echo "Starting RDP Session Manager..."

# Check dependencies
if ! python3 -c "import gi" 2>/dev/null; then
    echo "Error: PyGObject was not found"
    echo "Instale com: sudo apt install python3-gi"
    exit 1
fi

if ! python3 -c "import psutil" 2>/dev/null; then
    echo "Warning: psutil was not found"
    echo "Instale com: sudo apt install python3-psutil"
fi

# Run the application
python3 src/main.py
