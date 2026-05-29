#!/usr/bin/env bash
# Onepager — Dependency installation helper
# Installs Playwright (Python) and Chromium browser for HTML-to-PNG capture.

set -e

echo "=== Onepager: Installing dependencies ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not found."
    exit 1
fi

# Check Python version >= 3.8
python3 -c "
import sys
if sys.version_info < (3, 8):
    print('ERROR: Python 3.8+ is required. Current version:', sys.version)
    sys.exit(1)
" || exit 1

if python3 -c "import playwright" &> /dev/null; then
    echo "Playwright is already installed, skipping installation."
    exit 0
fi

echo "[1/2] Installing Playwright Python package..."
pip3 install "playwright>=1.40,<2.0"

echo "[2/2] Installing Chromium browser for Playwright..."
python3 -m playwright install chromium

echo ""
echo "=== Installation complete ==="
echo "You can now run: python3 scripts/capture.py <input.html> --output <output.png> --width 800"
