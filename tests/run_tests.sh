#!/bin/bash
# Run all tests

echo "Running RDP Session Manager Tests..."
echo "===================================="

python3 -m pytest tests/ -v --tb=short

echo ""
echo "Tests completed!"
