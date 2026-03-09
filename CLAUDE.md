# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Tron Bit Pomodoro Timer — a Linux/GNOME desktop app with an animated system tray icon (Tron bit GIF) and a floating GTK control window.

## Setup

```bash
# --system-site-packages is required: python3-gi (PyGObject) is only available as a system apt package
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install Pillow pystray numpy
```

System packages required: `sudo apt install python3 python3-venv python3-gi gir1.2-appindicator3-0.1`

## Running

```bash
source venv/bin/activate
python tron_pomodoro.py
```

## Architecture

Single-file application (`tron_pomodoro.py`) with two classes:

**`FloatingWindow`** — Draggable, borderless GTK3 window (always on top). Shows the animated Tron bit at 128px, countdown timer, session label, and control buttons (Work, Short Break, Long Break, Custom, Pause, Stop, Hide). Tron-themed dark blue/cyan styling.

**`PomodoroTimer`** — Core logic. Manages:
- AppIndicator3 system tray icon (falls back to `pystray`)
- GIF animation: 43 frames extracted via Pillow. Frame ranges: Normal rotation (0–8, 20–32), "yes" completion animation (9–19), "no" last-minute warning (33–42)
- Timer countdown in a background daemon thread; UI updates marshalled back via `GLib.idle_add()`
- Tray label format: `▶ Work: 25:00` (running) or `⏸ Work: 24:59` (paused)
- Desktop notification on completion

Animation state machine: idle → "normal" looping rotation; last 60 seconds → "no" animation; on completion → "yes" plays once, then loops.

## Sounds

`generate_sounds.py` generates three WAV files using numpy into `sounds/`:
- `bit_start.wav` — played when a session starts
- `bit_no.wav` — played at the 60-second warning (last minute)
- `bit_yes.wav` — played on session completion

`PomodoroTimer._ensure_sounds()` auto-generates them at startup if missing. `_play_sound()` plays them non-blocking via `aplay`. Requires numpy (`pip install numpy`) and system `aplay` (part of `alsa-utils`).
