# Tron Bit Pomodoro Timer

A system tray Pomodoro timer for GNOME on Linux, using an animated Tron bit GIF as the tray icon.

## Features

- Animated system tray icon (Tron bit GIF, frame-by-frame via AppIndicator)
- Floating GTK control window
- Preset timers: 25 min work / 5 min short break / 15 min long break
- Custom timer option
- GNOME autostart support

## Requirements

### System packages

```bash
sudo apt install python3 python3-venv python3-gi gir1.2-appindicator3-0.1
```

### Python packages (installed into virtualenv)

- `Pillow`
- `pystray`

## Setup

```bash
# Clone the repo
git clone <repo-url> ~/src/tron-pomodoro
cd ~/src/tron-pomodoro

# Create and activate a virtualenv
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install Pillow pystray
```

## Running

```bash
cd ~/src/tron-pomodoro
source venv/bin/activate
python tron_pomodoro.py
```

Or run it directly using the venv interpreter without activating:

```bash
~/src/tron-pomodoro/venv/bin/python ~/src/tron-pomodoro/tron_pomodoro.py
```

## Autostart (GNOME)

An install script is provided to generate and install the `.desktop` autostart entry. It detects the repo location automatically and writes the correct paths.

```bash
bash install.sh
```

This creates `~/.config/autostart/tron-pomodoro.desktop` pointing to the current repo directory.

To remove the autostart entry:

```bash
rm ~/.config/autostart/tron-pomodoro.desktop
```

## Files

| File | Description |
|------|-------------|
| `tron_pomodoro.py` | Main application |
| `*.gif` | Animated Tron bit icon |
| `tron-pomodoro.desktop.template` | Autostart entry template |
| `install.sh` | Generates and installs the `.desktop` entry |

## Notes

- The app uses AppIndicator3 when available (GNOME with the AppIndicator extension), falling back to `pystray`.
- The venv is excluded from version control. Run the setup steps above after any fresh clone.
