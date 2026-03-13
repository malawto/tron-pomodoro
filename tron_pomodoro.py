#!/usr/bin/env python3
"""
Tron Bit Pomodoro Timer
A system tray pomodoro timer using the animated Tron bit as the icon.
Includes a floating window for better visibility.
"""

import json
import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import subprocess
import threading
import time
import tempfile
from datetime import datetime
from pathlib import Path
from PIL import Image

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('AppIndicator3', '0.1')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gtk, AppIndicator3, GLib, Gdk, GdkPixbuf
    USE_APPINDICATOR = True
except (ImportError, ValueError):
    USE_APPINDICATOR = False
    print("AppIndicator3 not available")


class FloatingWindow(Gtk.Window):
    """Floating timer window with larger animated bit."""

    def __init__(self, timer):
        super().__init__(title="Tron Pomodoro")
        self.timer = timer

        # Window setup
        self.set_decorated(False)  # No title bar
        self.set_keep_above(True)  # Always on top
        self.set_resizable(False)
        self.set_default_size(200, 280)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_wmclass("tron-pomodoro", "tron-pomodoro")

        # Make window draggable
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion)
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Main container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        self.add(vbox)

        # Animated bit display
        self.bit_image = Gtk.Image()
        vbox.pack_start(self.bit_image, False, False, 0)

        # Timer label
        self.timer_label = Gtk.Label()
        self.timer_label.set_markup("<span font='24' weight='bold'>Ready</span>")
        vbox.pack_start(self.timer_label, False, False, 0)

        # Session type label
        self.session_label = Gtk.Label()
        self.session_label.set_text("")
        vbox.pack_start(self.session_label, False, False, 0)

        # Current task label
        self.task_label = Gtk.Label()
        self.task_label.set_text("")
        self.task_label.set_line_wrap(True)
        self.task_label.set_max_width_chars(22)
        vbox.pack_start(self.task_label, False, False, 0)

        # Session counter label
        self.counter_label = Gtk.Label()
        self.counter_label.set_text("")
        vbox.pack_start(self.counter_label, False, False, 0)

        # "Start next session" button — shown after completion, hidden otherwise
        self.btn_next = Gtk.Button()
        self.btn_next.connect("clicked", lambda w: timer.start_next_session())
        self.btn_next.set_no_show_all(True)  # exclude from show_all()
        vbox.pack_start(self.btn_next, False, False, 0)

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.btn_work = Gtk.Button()
        self.btn_work.connect("clicked", lambda w: timer.start_work())
        button_box.pack_start(self.btn_work, False, False, 0)

        self.btn_short = Gtk.Button()
        self.btn_short.connect("clicked", lambda w: timer.start_short_break())
        button_box.pack_start(self.btn_short, False, False, 0)

        self.btn_long = Gtk.Button()
        self.btn_long.connect("clicked", lambda w: timer.start_long_break())
        button_box.pack_start(self.btn_long, False, False, 0)

        btn_custom = Gtk.Button(label="Custom Timer...")
        btn_custom.connect("clicked", lambda w: timer.start_custom_timer())
        button_box.pack_start(btn_custom, False, False, 0)

        # Pause/Stop buttons
        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.btn_pause = Gtk.Button(label="Pause")
        self.btn_pause.connect("clicked", lambda w: timer.toggle_pause())
        self.btn_pause.set_sensitive(False)
        control_box.pack_start(self.btn_pause, True, True, 0)

        self.btn_stop = Gtk.Button(label="Stop")
        self.btn_stop.connect("clicked", lambda w: timer.stop_timer())
        self.btn_stop.set_sensitive(False)
        control_box.pack_start(self.btn_stop, True, True, 0)

        button_box.pack_start(control_box, False, False, 0)
        vbox.pack_start(button_box, False, False, 0)

        # Mute / Hide row
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.btn_mute = Gtk.Button(label="Mute")
        self.btn_mute.connect("clicked", lambda w: timer.toggle_mute())
        bottom_box.pack_start(self.btn_mute, True, True, 0)

        btn_close = Gtk.Button(label="Hide")
        btn_close.connect("clicked", lambda w: self.hide())
        bottom_box.pack_start(btn_close, True, True, 0)

        vbox.pack_start(bottom_box, False, False, 0)

        # Volume slider row
        vol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vol_label = Gtk.Label(label="Vol:")
        vol_box.pack_start(vol_label, False, False, 0)
        self.vol_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05)
        self.vol_slider.set_value(timer.volume)
        self.vol_slider.set_draw_value(False)
        self.vol_slider.connect("value-changed", lambda s: timer.set_volume(s.get_value()))
        vol_box.pack_start(self.vol_slider, True, True, 0)
        vbox.pack_start(vol_box, False, False, 0)

        # Settings button
        btn_settings = Gtk.Button(label="Settings...")
        btn_settings.connect("clicked", lambda w: timer.show_settings_dialog())
        vbox.pack_start(btn_settings, False, False, 0)

        # Style
        css = b"""
        window {
            background-color: rgba(0, 20, 40, 0.95);
            border: 2px solid #00BFFF;
            border-radius: 10px;
        }
        label {
            color: #00BFFF;
        }
        button {
            background: #001a33;
            color: #00BFFF;
            border: 1px solid #00BFFF;
            border-radius: 5px;
            padding: 8px;
        }
        button:hover {
            background: #003366;
        }
        scale trough {
            background: #001a33;
            border: 1px solid #00BFFF;
            border-radius: 3px;
            min-height: 4px;
        }
        scale highlight {
            background: #00BFFF;
            border-radius: 3px;
        }
        scale slider {
            background: #00BFFF;
            border-radius: 50%;
            min-width: 12px;
            min-height: 12px;
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Show all widgets
        self.show_all()
        # But hide the window initially
        self.hide()

    def on_button_press(self, widget, event):
        """Start dragging."""
        if event.button == 1:
            self.dragging = True
            self.drag_offset_x = event.x_root - self.get_position()[0]
            self.drag_offset_y = event.y_root - self.get_position()[1]

    def on_button_release(self, widget, event):
        """Stop dragging."""
        if event.button == 1:
            self.dragging = False

    def on_motion(self, widget, event):
        """Handle dragging."""
        if self.dragging:
            new_x = event.x_root - self.drag_offset_x
            new_y = event.y_root - self.drag_offset_y
            self.move(int(new_x), int(new_y))

    def update_display(self, time_str, session_type, is_paused, is_running):
        """Update the timer display."""
        if is_running:
            status = "⏸ PAUSED" if is_paused else "▶"
            self.timer_label.set_markup(f"<span font='24' weight='bold'>{time_str}</span>")
            self.session_label.set_markup(f"<span font='12'>{status} {session_type}</span>")
        else:
            self.timer_label.set_markup("<span font='24' weight='bold'>Ready</span>")
            self.session_label.set_text("")

        # Update button sensitivity
        self.btn_pause.set_sensitive(is_running)
        self.btn_stop.set_sensitive(is_running)
        if is_paused:
            self.btn_pause.set_label("Resume")
        else:
            self.btn_pause.set_label("Pause")

    def update_mute_button(self, muted):
        self.btn_mute.set_label("Unmute" if muted else "Mute")

    def update_next_button(self, label=None):
        """Show the 'start next' button with the given label, or hide it."""
        if label:
            self.btn_next.set_label(label)
            self.btn_next.show()
        else:
            self.btn_next.hide()

    def update_button_labels(self, work_min, short_min, long_min):
        self.btn_work.set_label(f"Work ({work_min} min)")
        self.btn_short.set_label(f"Short Break ({short_min} min)")
        self.btn_long.set_label(f"Long Break ({long_min} min)")

    def update_task(self, task):
        """Show or hide the current task description."""
        if task:
            self.task_label.set_markup(f"<span font='10' style='italic'>{task}</span>")
        else:
            self.task_label.set_text("")

    def update_counter(self, sessions_completed, sessions_per_cycle, enabled,
                       running=False, blink_on=False):
        """Update the session counter display.

        While a session is running the next dot (in-progress position) blinks.
        blink_on controls whether it's currently showing as filled or empty.
        """
        if not enabled:
            self.counter_label.set_text("")
            return
        pos = sessions_completed % sessions_per_cycle
        dots = []
        for i in range(sessions_per_cycle):
            if i < pos:
                dots.append("●")
            elif i == pos and running:
                dots.append("●" if blink_on else "○")
            else:
                dots.append("○")
        dot_str = " ".join(dots)
        total_text = f"{sessions_completed} session{'s' if sessions_completed != 1 else ''}"
        self.counter_label.set_markup(
            f"<span font='10'>{dot_str}\n{total_text}</span>"
        )


class PomodoroTimer:
    def __init__(self, icon_path):
        self.icon_path = icon_path
        self.indicator = None
        self.floating_window = None
        self.timer_thread = None
        self.running = False
        self.paused = False
        self.remaining_seconds = 0
        self.session_type = None
        self._current_task = None
        self._last_session_was_break = False  # drives "start next" label
        self._blink_state = False   # toggled every 500 ms for in-progress dot
        self._blink_tick = 0

        # Timer durations in seconds (derived from config after loading below)

        # Animation frame ranges
        self.NORMAL_FRAMES = list(range(0, 9)) + list(range(20, 33))  # Idle rotation
        self.YES_FRAMES = list(range(9, 20))  # "Yes" animation
        self.NO_FRAMES = list(range(33, 43))  # "No" animation

        # Load GIF frames (small size for tray icon only; large frames lazy-loaded on demand)
        self.frames = self._load_gif_frames()
        self.large_frame_data = None  # Lazy-loaded as raw RGBA bytes when window is first shown
        self.current_frame = 0
        self.animation_mode = "normal"  # "normal", "yes", or "no"
        self.start_yes_played = False  # Track if start yes animation has played
        self.temp_icon_path = None

        # Sound setup
        self.sounds_dir = Path(__file__).parent / "sounds"
        self._ensure_sounds()
        import pygame
        pygame.mixer.init()
        self._sound_cache = self._preload_sounds()

        # Notification support (initialized once)
        self._notify_module = None
        try:
            import gi as _gi
            _gi.require_version('Notify', '0.7')
            from gi.repository import Notify as _Notify
            _Notify.init("Tron Pomodoro")
            self._notify_module = _Notify
        except Exception:
            pass

        # Config / persistent state
        self.config_path = Path.home() / ".config" / "tron-pomodoro" / "settings.json"
        _cfg = self._load_config()
        self.muted = _cfg.get("muted", False)
        self.volume = _cfg.get("volume", 0.5)
        self.session_counter_enabled = _cfg.get("session_counter_enabled", True)
        self.sessions_completed = _cfg.get("sessions_completed", 0)
        self.sessions_per_cycle = _cfg.get("sessions_per_cycle", 4)
        self.task_logging_enabled = _cfg.get("task_logging_enabled", True)
        self.work_duration_min = _cfg.get("work_duration_min", 25)
        self.short_break_min = _cfg.get("short_break_min", 5)
        self.long_break_min = _cfg.get("long_break_min", 15)
        self._update_durations()

        # Create menu items
        self.pause_menu_item = None
        self.stop_menu_item = None
        self.mute_menu_item = None
        self.task_menu_item = None   # non-interactive current-task display

    def _ensure_sounds(self):
        """Generate sound files into the sounds/ directory if not already present."""
        expected = [
            self.sounds_dir / "bit_yes.wav",
            self.sounds_dir / "bit_no.wav",
            self.sounds_dir / "bit_start.wav",
        ]
        if all(p.exists() for p in expected):
            return
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from generate_sounds import generate_bit_yes, generate_bit_no, generate_bit_work_start
            self.sounds_dir.mkdir(exist_ok=True)
            generate_bit_yes(str(self.sounds_dir / "bit_yes.wav"))
            generate_bit_no(str(self.sounds_dir / "bit_no.wav"))
            generate_bit_work_start(str(self.sounds_dir / "bit_start.wav"))
            print("Sounds generated.")
        except Exception as e:
            print(f"Sound generation failed: {e}")

    def _update_durations(self):
        """Recompute second-based duration constants from config minute values."""
        self.WORK_DURATION = self.work_duration_min * 60
        self.SHORT_BREAK = self.short_break_min * 60
        self.LONG_BREAK = self.long_break_min * 60

    def _init_dialog(self, dialog):
        """Apply common dialog setup: bit icon + suppress taskbar/pager entry."""
        dialog.set_skip_taskbar_hint(True)
        dialog.set_skip_pager_hint(True)
        if self.floating_window:
            dialog.set_transient_for(self.floating_window)
        if getattr(self, '_app_pixbuf', None):
            dialog.set_icon(self._app_pixbuf)

    def _load_config(self):
        try:
            return json.loads(self.config_path.read_text())
        except Exception:
            return {}

    def _save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({
            "muted": self.muted,
            "volume": self.volume,
            "session_counter_enabled": self.session_counter_enabled,
            "sessions_completed": self.sessions_completed,
            "sessions_per_cycle": self.sessions_per_cycle,
            "task_logging_enabled": self.task_logging_enabled,
            "work_duration_min": self.work_duration_min,
            "short_break_min": self.short_break_min,
            "long_break_min": self.long_break_min,
        }))

    def set_volume(self, value):
        self.volume = value
        self._save_config()

    def _apply_mute(self, muted):
        """Set mute state and sync all UI elements."""
        self.muted = muted
        self._save_config()
        if self.floating_window:
            self.floating_window.update_mute_button(self.muted)
        if self.mute_menu_item:
            self.mute_menu_item.set_label("Unmute" if self.muted else "Mute")

    def toggle_mute(self, widget=None):
        self._apply_mute(not self.muted)

    def _preload_sounds(self):
        """Load all WAV files into pygame at startup to avoid per-play disk reads."""
        import pygame
        cache = {}
        for name in ("bit_yes.wav", "bit_no.wav", "bit_start.wav"):
            path = self.sounds_dir / name
            if path.exists():
                cache[name] = pygame.mixer.Sound(str(path))
        return cache

    def _play_sound(self, filename):
        """Play a cached sound non-blocking (pygame.Sound.play is already async)."""
        if self.muted:
            return
        sound = self._sound_cache.get(filename)
        if sound is None:
            return
        sound.set_volume(self.volume)
        sound.play()

    def _load_gif_frames(self, size=32):
        """Load all frames from the animated GIF as PIL Images."""
        frames = []
        img = Image.open(self.icon_path)
        try:
            while True:
                frame = img.copy().convert('RGBA')
                frame.thumbnail((size, size), Image.Resampling.LANCZOS)
                frames.append(frame)
                img.seek(img.tell() + 1)
        except EOFError:
            pass
        return frames

    def _ensure_large_frames(self):
        """Lazy-load large (128px) frames as raw RGBA bytes on first use."""
        if self.large_frame_data is not None:
            return
        self.large_frame_data = []
        img = Image.open(self.icon_path)
        try:
            while True:
                frame = img.copy().convert('RGBA')
                frame.thumbnail((128, 128), Image.Resampling.LANCZOS)
                w, h = frame.size
                self.large_frame_data.append((frame.tobytes(), w, h))
                img.seek(img.tell() + 1)
        except EOFError:
            pass

    def _advance_frame(self):
        """Advance animation state by one tick and return the GIF frame index to display."""
        if self.animation_mode == "yes":
            frame_range = self.YES_FRAMES
        elif self.animation_mode == "no":
            frame_range = self.NO_FRAMES
        else:
            frame_range = self.NORMAL_FRAMES

        frame_index = self.current_frame % len(frame_range)
        actual_frame = frame_range[frame_index]

        self.current_frame += 1

        # One-shot yes animation at session start: switch to normal after one loop
        if self.animation_mode == "yes" and not self.start_yes_played and self.current_frame >= len(frame_range):
            self.start_yes_played = True
            self.animation_mode = "normal"
            self.current_frame = 0
        elif self.current_frame >= len(frame_range):
            self.current_frame = 0

        return actual_frame

    def _update_icon(self):
        """Update the system tray icon and floating window with the next frame."""
        actual_frame = self._advance_frame()

        if USE_APPINDICATOR and self.indicator and self.temp_icon_path:
            frame = self.frames[actual_frame]
            icon_path = self.temp_icon_path.parent / f"tron_bit_icon_{self.current_frame}.png"
            frame.save(icon_path, 'PNG')
            icon_name = f"tron_bit_icon_{self.current_frame}"
            self.indicator.set_property("icon-theme-path", str(self.temp_icon_path.parent))
            self.indicator.set_property("icon-name", icon_name)

        # Update floating window if visible — build Pixbuf directly from raw bytes (no disk I/O)
        if self.floating_window and self.floating_window.get_visible():
            self._ensure_large_frames()
            raw, w, h = self.large_frame_data[actual_frame]
            gbytes = GLib.Bytes.new(raw)
            pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
                gbytes, GdkPixbuf.Colorspace.RGB, True, 8, w, h, w * 4
            )
            self.floating_window.bit_image.set_from_pixbuf(pixbuf)

        # Toggle blink state every 500 ms (5 × 100 ms ticks)
        self._blink_tick += 1
        if self._blink_tick >= 5:
            self._blink_tick = 0
            self._blink_state = not self._blink_state
            self._update_counter_display()

        return True  # Continue the GLib timeout

    def _format_time(self, seconds):
        """Format seconds as MM:SS."""
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    def _timer_countdown(self):
        """Run the timer countdown."""
        while self.remaining_seconds > 0 and self.running:
            if not self.paused:
                # Check if we should switch to "no" animation (last minute)
                if self.remaining_seconds == 60:
                    self.animation_mode = "no"
                    self.current_frame = 0  # Reset frame counter
                    self._play_sound("bit_no.wav")

                time.sleep(1)
                self.remaining_seconds -= 1
                GLib.idle_add(self._update_display)

        if self.running and self.remaining_seconds == 0:
            GLib.idle_add(self._timer_complete)

    def _timer_complete(self):
        """Handle timer completion."""
        self.running = False
        self.animation_mode = "yes"  # Show "yes" animation when complete
        self.start_yes_played = True  # Set to true so it keeps looping (not one-time)
        self.current_frame = 0  # Reset frame counter
        self._play_sound("bit_yes.wav")
        message = f"{self.session_type} complete!"

        # Track work-type session completion
        cycle_complete = False
        self._last_session_was_break = not self._is_countable_session()
        if self._is_countable_session():
            if self.session_counter_enabled:
                self.sessions_completed += 1
                self._save_config()
                self._update_counter_display()
                if self.sessions_completed % self.sessions_per_cycle == 0:
                    cycle_complete = True
            if self.session_type == "Work" and self.task_logging_enabled:
                self._log_task_entry(self._current_task, self.WORK_DURATION // 60, True)

        # Show "start next" button
        if self.floating_window:
            if self._last_session_was_break:
                next_label = f"Start Work ({self.work_duration_min} min) →"
            else:
                next_label = f"Start Short Break ({self.short_break_min} min) →"
            self.floating_window.update_next_button(next_label)

        # Update display
        self._update_display()

        # Show notification
        self._show_notification("Pomodoro Timer", message)

        # Show floating window if hidden
        if self.floating_window and not self.floating_window.get_visible():
            self.floating_window.present()

        # After 3 seconds, switch back to normal (and suggest long break if cycle done)
        GLib.timeout_add_seconds(3, self._reset_to_normal)
        if cycle_complete:
            GLib.timeout_add_seconds(3, self._suggest_long_break)

    def _show_notification(self, title, message):
        """Show a desktop notification."""
        if self._notify_module is None:
            return
        try:
            notification = self._notify_module.Notification.new(title, message, None)
            notification.show()
        except Exception as e:
            print(f"Notification error: {e}")

    def _update_display(self):
        """Update all displays with current timer status."""
        # Update indicator label
        if self.indicator:
            if self.running:
                status = "⏸" if self.paused else "▶"
                time_str = self._format_time(self.remaining_seconds)
                label = f"{status} {self.session_type}: {time_str}"
            else:
                label = "Ready"
            self.indicator.set_label(label, "")

            # Update menu item sensitivity
            if self.pause_menu_item:
                self.pause_menu_item.set_sensitive(self.running)
            if self.stop_menu_item:
                self.stop_menu_item.set_sensitive(self.running)

        # Update floating window
        if self.floating_window:
            time_str = self._format_time(self.remaining_seconds) if self.running else "Ready"
            self.floating_window.update_display(
                time_str,
                self.session_type or "",
                self.paused,
                self.running
            )
            self.floating_window.update_task(self._current_task)
            # Hide "start next" while a session is running
            if self.running:
                self.floating_window.update_next_button(None)

        # Sync task name in tray menu
        if self.task_menu_item:
            if self._current_task and self.running:
                self.task_menu_item.set_label(f"  ↳ {self._current_task}")
                self.task_menu_item.show()
            else:
                self.task_menu_item.hide()

    def _is_countable_session(self):
        """True for work-type sessions (Work, Custom) — not breaks."""
        return bool(self.session_type and "Break" not in self.session_type)

    def _update_counter_display(self):
        """Sync session counter label in the floating window."""
        if self.floating_window:
            self.floating_window.update_counter(
                self.sessions_completed,
                self.sessions_per_cycle,
                self.session_counter_enabled,
                running=self.running and self._is_countable_session(),
                blink_on=self._blink_state,
            )

    def _reset_to_normal(self):
        """Reset animation to normal mode."""
        self.animation_mode = "normal"
        self.current_frame = 0
        return False  # Don't repeat timeout

    def _suggest_long_break(self):
        """Show a dialog suggesting a long break after a full cycle."""
        cycles = self.sessions_completed // self.sessions_per_cycle
        dialog = Gtk.Dialog(
            title="Cycle Complete!",
            parent=self.floating_window,
            modal=True,
        )
        self._init_dialog(dialog)
        dialog.add_buttons(
            f"Long Break ({self.long_break_min} min)", Gtk.ResponseType.ACCEPT,
            f"Short Break ({self.short_break_min} min)", Gtk.ResponseType.REJECT,
            "Skip", Gtk.ResponseType.CANCEL,
        )

        content = dialog.get_content_area()
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        lbl = Gtk.Label()
        cycle_word = "cycle" if cycles == 1 else "cycles"
        lbl.set_markup(
            f"<b>You've completed {self.sessions_per_cycle} sessions "
            f"({cycles} {cycle_word} total).</b>\n\nTime for a long break?"
        )
        lbl.set_line_wrap(True)
        lbl.set_max_width_chars(40)
        content.pack_start(lbl, False, False, 0)

        dialog.show_all()
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            self.start_long_break()
        elif response == Gtk.ResponseType.REJECT:
            self.start_short_break()

        return False  # Don't repeat timeout

    # ── Task logging ────────────────────────────────────────────────────────

    def _prompt_task_name(self):
        """Show a dialog asking what the user is working on.

        Returns (proceed, task):
            proceed=False  — user closed the window (X); cancel the session
            proceed=True   — user clicked Start or Skip; task may be None
        """
        dialog = Gtk.Dialog(
            title="What are you working on?",
            parent=self.floating_window,
            modal=True,
        )
        self._init_dialog(dialog)
        dialog.add_buttons("Skip", Gtk.ResponseType.CANCEL, "Start", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_margin_top(10)
        content.set_margin_bottom(10)
        content.set_margin_start(10)
        content.set_margin_end(10)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Task description (optional)")
        entry.set_activates_default(True)
        content.pack_start(entry, False, False, 0)

        dialog.show_all()
        response = dialog.run()
        text = entry.get_text().strip()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            return True, text or None
        elif response == Gtk.ResponseType.CANCEL:
            return True, None   # Skip — start with no task
        else:
            return False, None  # Window closed (DELETE_EVENT) — cancel

    def _log_task_entry(self, task, duration_min, completed):
        """Append a work session entry to the task log JSON file."""
        log_path = self.config_path.parent / "task_log.json"
        try:
            entries = json.loads(log_path.read_text()) if log_path.exists() else []
        except Exception:
            entries = []
        now = datetime.now()
        entries.append({
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "task": task or "",
            "duration_min": duration_min,
            "completed": completed,
        })
        try:
            log_path.write_text(json.dumps(entries, indent=2))
        except Exception as e:
            print(f"Task log write error: {e}")

    def _open_task_log(self):
        """Open the task log file with the system default viewer."""
        log_path = self.config_path.parent / "task_log.json"
        if not log_path.exists():
            dialog = Gtk.MessageDialog(
                parent=self.floating_window,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="No task log yet. Complete a Work session to create one.",
            )
            self._init_dialog(dialog)
            dialog.run()
            dialog.destroy()
            return
        subprocess.Popen(["xdg-open", str(log_path)])

    # ── Settings dialog ──────────────────────────────────────────────────────

    def show_settings_dialog(self, widget=None):
        """Show the settings dialog."""
        dialog = Gtk.Dialog(
            title="Settings",
            parent=self.floating_window,
            modal=True,
        )
        dialog.add_buttons("Close", Gtk.ResponseType.CLOSE)
        dialog.set_default_size(320, -1)
        self._init_dialog(dialog)

        content = dialog.get_content_area()
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_spacing(6)

        def section_label(text):
            lbl = Gtk.Label()
            lbl.set_markup(f"<b>{text}</b>")
            lbl.set_halign(Gtk.Align.START)
            return lbl

        # ── Session Counter ──────────────────────────────────────────────────
        content.pack_start(section_label("Session Counter"), False, False, 0)

        counter_check = Gtk.CheckButton(label="Enable session counter")
        counter_check.set_active(self.session_counter_enabled)
        def on_counter_toggle(w):
            self.session_counter_enabled = w.get_active()
            self._save_config()
            self._update_counter_display()
        counter_check.connect("toggled", on_counter_toggle)
        content.pack_start(counter_check, False, False, 0)

        cycle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cycle_box.pack_start(Gtk.Label(label="Sessions per cycle:"), False, False, 0)
        adj = Gtk.Adjustment(value=self.sessions_per_cycle, lower=1, upper=12, step_increment=1)
        cycle_spin = Gtk.SpinButton(adjustment=adj)
        cycle_spin.set_digits(0)
        def on_cycle_change(s):
            self.sessions_per_cycle = int(s.get_value())
            self._save_config()
            self._update_counter_display()
        cycle_spin.connect("value-changed", on_cycle_change)
        cycle_box.pack_start(cycle_spin, False, False, 0)
        content.pack_start(cycle_box, False, False, 0)

        count_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        count_lbl = Gtk.Label(label=f"Sessions completed: {self.sessions_completed}")
        count_lbl.set_halign(Gtk.Align.START)
        count_row.pack_start(count_lbl, True, True, 0)
        reset_btn = Gtk.Button(label="Reset")
        def on_reset(_w):
            self.sessions_completed = 0
            self._save_config()
            self._update_counter_display()
            count_lbl.set_text(f"Sessions completed: {self.sessions_completed}")
        reset_btn.connect("clicked", on_reset)
        count_row.pack_start(reset_btn, False, False, 0)
        content.pack_start(count_row, False, False, 0)

        content.pack_start(Gtk.Separator(), False, False, 8)

        # ── Timers ───────────────────────────────────────────────────────────
        content.pack_start(section_label("Timers"), False, False, 0)

        def duration_row(label_text, current_min, lower, upper, on_change):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl = Gtk.Label(label=label_text)
            lbl.set_width_chars(16)
            lbl.set_halign(Gtk.Align.START)
            row.pack_start(lbl, False, False, 0)
            adj = Gtk.Adjustment(value=current_min, lower=lower, upper=upper, step_increment=1)
            spin = Gtk.SpinButton(adjustment=adj)
            spin.set_digits(0)
            spin.set_width_chars(4)
            spin.connect("value-changed", on_change)
            row.pack_start(spin, False, False, 0)
            row.pack_start(Gtk.Label(label="min"), False, False, 0)
            return row

        def on_work_change(s):
            self.work_duration_min = int(s.get_value())
            self._update_durations()
            self._save_config()
            if self.floating_window:
                self.floating_window.update_button_labels(
                    self.work_duration_min, self.short_break_min, self.long_break_min)

        def on_short_change(s):
            self.short_break_min = int(s.get_value())
            self._update_durations()
            self._save_config()
            if self.floating_window:
                self.floating_window.update_button_labels(
                    self.work_duration_min, self.short_break_min, self.long_break_min)

        def on_long_change(s):
            self.long_break_min = int(s.get_value())
            self._update_durations()
            self._save_config()
            if self.floating_window:
                self.floating_window.update_button_labels(
                    self.work_duration_min, self.short_break_min, self.long_break_min)

        content.pack_start(
            duration_row("Work session:", self.work_duration_min, 1, 120, on_work_change),
            False, False, 0)
        content.pack_start(
            duration_row("Short break:", self.short_break_min, 1, 60, on_short_change),
            False, False, 0)
        content.pack_start(
            duration_row("Long break:", self.long_break_min, 1, 120, on_long_change),
            False, False, 0)

        content.pack_start(Gtk.Separator(), False, False, 8)

        # ── Task Logging ─────────────────────────────────────────────────────
        content.pack_start(section_label("Task Logging"), False, False, 0)

        log_check = Gtk.CheckButton(label="Enable task logging (prompts before Work sessions)")
        log_check.set_active(self.task_logging_enabled)
        def on_log_toggle(w):
            self.task_logging_enabled = w.get_active()
            self._save_config()
        log_check.connect("toggled", on_log_toggle)
        content.pack_start(log_check, False, False, 0)

        view_log_btn = Gtk.Button(label="View Log...")
        view_log_btn.connect("clicked", lambda w: self._open_task_log())
        content.pack_start(view_log_btn, False, False, 0)

        content.pack_start(Gtk.Separator(), False, False, 8)

        # ── Audio ────────────────────────────────────────────────────────────
        content.pack_start(section_label("Audio"), False, False, 0)

        mute_check = Gtk.CheckButton(label="Mute")
        mute_check.set_active(self.muted)
        mute_check.connect("toggled", lambda w: self._apply_mute(w.get_active()))
        content.pack_start(mute_check, False, False, 0)

        vol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vol_box.pack_start(Gtk.Label(label="Volume:"), False, False, 0)
        vol_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05)
        vol_slider.set_value(self.volume)
        vol_slider.set_draw_value(False)
        def on_vol_change(s):
            self.volume = s.get_value()
            self._save_config()
            if self.floating_window:
                self.floating_window.vol_slider.set_value(self.volume)
        vol_slider.connect("value-changed", on_vol_change)
        vol_box.pack_start(vol_slider, True, True, 0)
        content.pack_start(vol_box, False, False, 0)

        dialog.show_all()
        dialog.run()
        dialog.destroy()

    # ── Timer control ────────────────────────────────────────────────────────

    def start_next_session(self, widget=None):
        """Start the logical next session after the last one completed."""
        if self._last_session_was_break:
            self.start_work()
        else:
            self.start_short_break()

    def show_window(self, widget=None):
        """Show the floating window."""
        if self.floating_window:
            self.floating_window.present()

    def start_work(self, widget=None):
        """Start a work session, optionally prompting for a task name."""
        if self.task_logging_enabled:
            proceed, task = self._prompt_task_name()
            if not proceed:
                return
        else:
            task = None
        self._start_timer(self.WORK_DURATION, "Work")
        # Set task AFTER _start_timer; stop_timer() inside it would clear it otherwise
        self._current_task = task
        if self.floating_window:
            self.floating_window.update_task(self._current_task)

    def start_short_break(self, widget=None):
        """Start a short break."""
        self._start_timer(self.SHORT_BREAK, "Break")

    def start_long_break(self, widget=None):
        """Start a long break."""
        self._start_timer(self.LONG_BREAK, "Long Break")

    def start_custom_timer(self, widget=None):
        """Show dialog to start a custom timer."""
        dialog = Gtk.Dialog(
            title="Custom Timer",
            parent=self.floating_window if self.floating_window else None,
            modal=True
        )
        self._init_dialog(dialog)
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "OK", Gtk.ResponseType.OK
        )

        content = dialog.get_content_area()
        content.set_margin_top(10)
        content.set_margin_bottom(10)
        content.set_margin_start(10)
        content.set_margin_end(10)

        # Minutes input
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label = Gtk.Label(label="Minutes:")
        hbox.pack_start(label, False, False, 0)

        adjustment = Gtk.Adjustment(value=25, lower=1, upper=180, step_increment=1)
        spinbutton = Gtk.SpinButton(adjustment=adjustment)
        spinbutton.set_digits(0)
        hbox.pack_start(spinbutton, True, True, 0)

        content.pack_start(hbox, False, False, 0)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            minutes = int(spinbutton.get_value())
            dialog.destroy()
            if self.task_logging_enabled:
                proceed, task = self._prompt_task_name()
                if not proceed:
                    return
            else:
                task = None
            self._start_timer(minutes * 60, f"Custom ({minutes}m)")
            # Set task AFTER _start_timer; stop_timer() inside it would clear it otherwise
            self._current_task = task
            if self.floating_window:
                self.floating_window.update_task(self._current_task)
        else:
            dialog.destroy()

    def _start_timer(self, duration, session_type):
        """Start a timer with the given duration."""
        self.stop_timer()
        self.remaining_seconds = duration
        self.session_type = session_type
        self.running = True
        self.paused = False
        self.animation_mode = "yes"  # Start with yes animation
        self.start_yes_played = False  # Reset flag so yes plays once then switches to normal
        self.current_frame = 0  # Reset frame counter
        self._update_display()

        self._play_sound("bit_start.wav")
        self.timer_thread = threading.Thread(target=self._timer_countdown, daemon=True)
        self.timer_thread.start()

    def toggle_pause(self, widget=None):
        """Toggle pause state."""
        if self.running:
            self.paused = not self.paused
            self._update_display()

    def stop_timer(self, widget=None):
        """Stop the current timer."""
        self.running = False
        self.paused = False
        self.remaining_seconds = 0
        self.animation_mode = "normal"  # Reset to normal when stopped
        self.current_frame = 0  # Reset frame counter
        self._current_task = None
        if self.floating_window:
            self.floating_window.update_next_button(None)
        self._update_display()
        self._update_counter_display()
        if self.timer_thread:
            self.timer_thread.join(timeout=1)

    def quit_app(self, widget=None):
        """Quit the application."""
        self.stop_timer()
        Gtk.main_quit()

    def build_menu(self):
        """Build the indicator menu."""
        menu = Gtk.Menu()

        # Show window
        item_show = Gtk.MenuItem(label="Show Timer Window")
        item_show.connect('activate', self.show_window)
        menu.append(item_show)

        # Current task (non-interactive, only visible when a task is set)
        self.task_menu_item = Gtk.MenuItem(label="")
        self.task_menu_item.set_sensitive(False)
        self.task_menu_item.set_no_show_all(True)
        menu.append(self.task_menu_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Work session
        item_work = Gtk.MenuItem(label="Start Work (25 min)")
        item_work.connect('activate', self.start_work)
        menu.append(item_work)

        # Short break
        item_short_break = Gtk.MenuItem(label="Start Short Break (5 min)")
        item_short_break.connect('activate', self.start_short_break)
        menu.append(item_short_break)

        # Long break
        item_long_break = Gtk.MenuItem(label="Start Long Break (15 min)")
        item_long_break.connect('activate', self.start_long_break)
        menu.append(item_long_break)

        # Custom timer
        item_custom = Gtk.MenuItem(label="Custom Timer...")
        item_custom.connect('activate', self.start_custom_timer)
        menu.append(item_custom)

        # Separator
        menu.append(Gtk.SeparatorMenuItem())

        # Pause/Resume
        self.pause_menu_item = Gtk.MenuItem(label="Pause/Resume")
        self.pause_menu_item.connect('activate', self.toggle_pause)
        self.pause_menu_item.set_sensitive(False)
        menu.append(self.pause_menu_item)

        # Stop
        self.stop_menu_item = Gtk.MenuItem(label="Stop Timer")
        self.stop_menu_item.connect('activate', self.stop_timer)
        self.stop_menu_item.set_sensitive(False)
        menu.append(self.stop_menu_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Mute
        self.mute_menu_item = Gtk.MenuItem(label="Unmute" if self.muted else "Mute")
        self.mute_menu_item.connect('activate', self.toggle_mute)
        menu.append(self.mute_menu_item)

        # Settings
        item_settings = Gtk.MenuItem(label="Settings...")
        item_settings.connect('activate', self.show_settings_dialog)
        menu.append(item_settings)

        # Separator
        menu.append(Gtk.SeparatorMenuItem())

        # Quit
        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect('activate', self.quit_app)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def run(self):
        """Run the system tray application."""
        if USE_APPINDICATOR:
            # Create temp file for icon
            temp_dir = tempfile.gettempdir()
            self.temp_icon_path = Path(temp_dir) / "tron_bit_icon.png"

            # Save first frame
            self.frames[self.NORMAL_FRAMES[0]].save(self.temp_icon_path, 'PNG')

            # Create AppIndicator
            self.indicator = AppIndicator3.Indicator.new(
                "tron-pomodoro",
                str(self.temp_icon_path),
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS
            )
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self.indicator.set_label("Ready", "")

            # Create floating window
            self.floating_window = FloatingWindow(self)
            self.floating_window.update_mute_button(self.muted)
            self.floating_window.update_button_labels(
                self.work_duration_min, self.short_break_min, self.long_break_min)
            self._update_counter_display()

            # Load pixbuf and set as default icon for every window in this process
            try:
                self._app_pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(self.temp_icon_path))
                Gtk.Window.set_default_icon(self._app_pixbuf)
            except Exception:
                self._app_pixbuf = None

            # Set menu
            self.indicator.set_menu(self.build_menu())

            # Start animation
            GLib.timeout_add(100, self._update_icon)

            # Run GTK main loop
            Gtk.main()
        else:
            print("AppIndicator3 not available. Install python3-gi and gir1.2-appindicator3-0.1")
            return


def main():
    GLib.set_prgname("tron-pomodoro")
    GLib.set_application_name("Tron Pomodoro")

    icon_path = Path(__file__).parent / "bit.gif"

    if not icon_path.exists():
        print(f"Error: bit.gif not found at {icon_path}")
        return

    timer = PomodoroTimer(icon_path)
    timer.run()


if __name__ == "__main__":
    main()
