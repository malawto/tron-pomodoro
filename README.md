# Tron Bit Pomodoro Timer

A system tray Pomodoro timer for GNOME on Linux, using an animated Tron bit GIF as the tray icon.

**Features:**
- Animated system tray icon (43-frame Tron bit GIF via AppIndicator3)
- Floating GTK control window (draggable, always-on-top)
- Preset timers: 25 min work / 5 min short break / 15 min long break / custom
- Sound effects at session start, last-minute warning, and completion
- Mute toggle and volume control, persisted across sessions
- Desktop notifications on completion

---

## Installation

### Option A: .deb package (recommended for Ubuntu/Debian)

The `.deb` bundles all pip dependencies — no internet access needed at install time.
Only system packages are required as prerequisites.

```bash
# Prerequisites (GTK + AppIndicator)
sudo apt install python3 python3-gi gir1.2-appindicator3-0.1 gir1.2-notify-0.7

# Download and install
sudo dpkg -i tron-pomodoro_1.0.0_amd64.deb
```

After install, `tron-pomodoro` is available on your `$PATH` and appears in the
application launcher.

**To autostart on login:**
```bash
cp /usr/share/applications/tron-pomodoro.desktop ~/.config/autostart/
```

**To uninstall:**
```bash
sudo dpkg -r tron-pomodoro
rm -f ~/.config/autostart/tron-pomodoro.desktop
```

---

### Option B: pipx

Installs into an isolated environment. Requires the system packages below first
because `python3-gi` (PyGObject) cannot be pip-installed.

```bash
# Prerequisites
sudo apt install python3-gi gir1.2-appindicator3-0.1 gir1.2-notify-0.7 pipx

# Install from GitHub
pipx install git+https://github.com/malawto/tron-pomodoro --system-site-packages
```

`tron-pomodoro` will be available in `~/.local/bin/` (ensure that's on your `$PATH`).

**To autostart on login**, create `~/.config/autostart/tron-pomodoro.desktop`:
```ini
[Desktop Entry]
Type=Application
Name=Tron Pomodoro
Exec=tron-pomodoro
Terminal=false
X-GNOME-Autostart-enabled=true
```

**To uninstall:**
```bash
pipx uninstall tron-pomodoro
```

---

### Option C: From source

```bash
# Prerequisites
sudo apt install python3 python3-venv python3-gi gir1.2-appindicator3-0.1 gir1.2-notify-0.7

# Clone and set up
git clone https://github.com/malawto/tron-pomodoro ~/src/tron-pomodoro
cd ~/src/tron-pomodoro

# --system-site-packages gives the venv access to python3-gi
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install Pillow numpy pygame pystray

# Run
python tron_pomodoro.py
```

**To autostart on login:**
```bash
bash install.sh
```

This generates `~/.config/autostart/tron-pomodoro.desktop` pointing to the repo directory.

---

## Building the .deb

Requires `fpm` (`gem install fpm`) and Python 3.

```bash
bash build_deb.sh
# outputs dist/tron-pomodoro_1.0.0_amd64.deb
```

---

## Files

| File | Description |
|------|-------------|
| `tron_pomodoro.py` | Main application |
| `generate_sounds.py` | Generates WAV sound effects via numpy |
| `bit.gif` | Animated Tron bit icon (43 frames) |
| `pyproject.toml` | Package metadata for pipx / pip |
| `build_deb.sh` | Builds a self-contained `.deb` via fpm |
| `install.sh` | Installs GNOME autostart entry (from-source only) |
| `tron-pomodoro.desktop.template` | Autostart `.desktop` template used by `install.sh` |
