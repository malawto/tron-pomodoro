#!/usr/bin/env bash
# build_deb.sh — build a self-contained .deb package via fpm
#
# Prerequisites:
#   gem install fpm          (or: sudo apt install ruby-fpm)
#   pip3 install hatchling   (only needed if you want to build the wheel too)
#
# System deps declared in the package (installed automatically by apt):
#   python3, python3-gi, gir1.2-appindicator3-0.1, gir1.2-notify-0.7
#
# pip deps (Pillow, numpy, pygame, pystray) are bundled inside the .deb
# so no internet access is needed at install time.

set -euo pipefail

VERSION="1.0.0"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGING="$REPO_DIR/dist/staging"
LIB_DIR="$STAGING/usr/lib/tron-pomodoro"
BIN_DIR="$STAGING/usr/bin"
APP_DIR="$STAGING/usr/share/applications"

echo "==> Cleaning dist/"
rm -rf "$REPO_DIR/dist"
mkdir -p "$LIB_DIR" "$BIN_DIR" "$APP_DIR"

echo "==> Installing pip dependencies into bundle"
pip3 install --quiet --target "$LIB_DIR/deps" \
    "Pillow>=9.0" "numpy>=1.20" "pygame>=2.0" "pystray>=0.19"

echo "==> Copying app files"
cp "$REPO_DIR/tron_pomodoro.py" \
   "$REPO_DIR/generate_sounds.py" \
   "$REPO_DIR/bit.gif" \
   "$LIB_DIR/"

echo "==> Pre-generating sounds"
mkdir -p "$LIB_DIR/sounds"
PYTHONPATH="$LIB_DIR/deps" python3 - <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else '.')
import os, sys
repo = os.environ.get('LIB_DIR', '.')
sys.path.insert(0, repo)
from generate_sounds import generate_bit_yes, generate_bit_no, generate_bit_work_start
sounds = os.path.join(os.environ['LIB_DIR'], 'sounds')
generate_bit_yes(os.path.join(sounds, 'bit_yes.wav'))
generate_bit_no(os.path.join(sounds, 'bit_no.wav'))
generate_bit_work_start(os.path.join(sounds, 'bit_start.wav'))
print("  sounds generated")
PYEOF

echo "==> Writing launcher script"
cat > "$BIN_DIR/tron-pomodoro" << 'EOF'
#!/bin/bash
PYTHONPATH=/usr/lib/tron-pomodoro/deps exec python3 /usr/lib/tron-pomodoro/tron_pomodoro.py "$@"
EOF
chmod +x "$BIN_DIR/tron-pomodoro"

echo "==> Writing .desktop entry"
cat > "$APP_DIR/tron-pomodoro.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=Tron Pomodoro
Comment=Pomodoro timer with animated Tron bit
Exec=tron-pomodoro
Icon=/usr/lib/tron-pomodoro/bit.gif
Terminal=false
Categories=Utility;
StartupNotify=false
EOF

echo "==> Building .deb with fpm"
fpm \
    --input-type dir \
    --output-type deb \
    --name tron-pomodoro \
    --version "$VERSION" \
    --architecture amd64 \
    --description "Tron Bit Pomodoro Timer — animated system tray Pomodoro timer for Linux/GNOME" \
    --url "https://github.com/malawto/tron-pomodoro" \
    --depends python3 \
    --depends python3-gi \
    --depends "gir1.2-appindicator3-0.1" \
    --depends "gir1.2-notify-0.7" \
    --chdir "$STAGING" \
    --package "$REPO_DIR/dist/" \
    .

echo ""
echo "Done: $(ls "$REPO_DIR"/dist/*.deb)"
echo ""
echo "Install with:"
echo "  sudo dpkg -i $(ls "$REPO_DIR"/dist/*.deb)"
