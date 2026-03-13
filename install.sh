#!/usr/bin/env bash
# install.sh — generates and installs the GNOME autostart entry for Tron Pomodoro
# Run this from anywhere; it resolves the repo location automatically.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$INSTALL_DIR/tron-pomodoro.desktop.template"
AUTOSTART_DIR="$HOME/.config/autostart"
OUTPUT="$AUTOSTART_DIR/tron-pomodoro.desktop"

# Locate the GIF icon (pick the first .gif found in the repo root)
ICON_FILE="$(basename "$(ls "$INSTALL_DIR"/*.gif 2>/dev/null | head -n1)")"

if [[ -z "$ICON_FILE" ]]; then
    echo "ERROR: No .gif file found in $INSTALL_DIR"
    echo "Make sure the icon file is present in the repo root."
    exit 1
fi

if [[ ! -f "$TEMPLATE" ]]; then
    echo "ERROR: Template not found at $TEMPLATE"
    exit 1
fi

if [[ ! -d "$INSTALL_DIR/venv" ]]; then
    echo "WARNING: venv not found at $INSTALL_DIR/venv"
    echo "Run the setup steps in README.md before installing the autostart entry."
    echo "Continuing anyway..."
fi

mkdir -p "$AUTOSTART_DIR"

DESKTOP_CONTENT="$(sed \
    -e "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" \
    -e "s|{{ICON_FILE}}|$ICON_FILE|g" \
    "$TEMPLATE")"

echo "$DESKTOP_CONTENT" > "$OUTPUT"
chmod +x "$OUTPUT"

# Also install to applications dir so GNOME Shell associates windows with our icon
APPLICATIONS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPLICATIONS_DIR"
echo "$DESKTOP_CONTENT" > "$APPLICATIONS_DIR/tron-pomodoro.desktop"

echo "Installed autostart entry to: $OUTPUT"
echo "Installed application entry to: $APPLICATIONS_DIR/tron-pomodoro.desktop"
echo ""
echo "Contents:"
echo "---"
cat "$OUTPUT"
echo "---"
echo ""
echo "The timer will start automatically on next login."
echo "To start it now:"
echo "  $INSTALL_DIR/venv/bin/python $INSTALL_DIR/tron_pomodoro.py &"
