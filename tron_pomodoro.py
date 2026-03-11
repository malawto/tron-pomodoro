#!/usr/bin/env python3
"""
Tron Bit Pomodoro Timer
A system tray pomodoro timer using the animated Tron bit as the icon.
Includes a floating window for better visibility.
"""

import json
import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import threading
import time
import tempfile
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
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        btn_work = Gtk.Button(label="Work (25 min)")
        btn_work.connect("clicked", lambda w: timer.start_work())
        button_box.pack_start(btn_work, False, False, 0)
        
        btn_short = Gtk.Button(label="Short Break (5 min)")
        btn_short.connect("clicked", lambda w: timer.start_short_break())
        button_box.pack_start(btn_short, False, False, 0)
        
        btn_long = Gtk.Button(label="Long Break (15 min)")
        btn_long.connect("clicked", lambda w: timer.start_long_break())
        button_box.pack_start(btn_long, False, False, 0)
        
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
        
        # Timer durations in seconds
        self.WORK_DURATION = 25 * 60
        self.SHORT_BREAK = 5 * 60
        self.LONG_BREAK = 15 * 60
        
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

        # Config / mute state
        self.config_path = Path.home() / ".config" / "tron-pomodoro" / "settings.json"
        _cfg = self._load_config()
        self.muted = _cfg.get("muted", False)
        self.volume = _cfg.get("volume", 0.5)

        # Create menu items
        self.pause_menu_item = None
        self.stop_menu_item = None
        self.mute_menu_item = None

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

    def _load_config(self):
        try:
            return json.loads(self.config_path.read_text())
        except Exception:
            return {}

    def _save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({"muted": self.muted, "volume": self.volume}))

    def set_volume(self, value):
        self.volume = value
        self._save_config()

    def toggle_mute(self, widget=None):
        self.muted = not self.muted
        self._save_config()
        if self.floating_window:
            self.floating_window.update_mute_button(self.muted)
        if self.mute_menu_item:
            self.mute_menu_item.set_label("Unmute" if self.muted else "Mute")

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
        
        # Update display
        self._update_display()
        
        # Show notification
        self._show_notification("Pomodoro Timer", message)
        
        # Show floating window if hidden
        if self.floating_window and not self.floating_window.get_visible():
            self.floating_window.present()
        
        # After 3 seconds, switch back to normal
        GLib.timeout_add_seconds(3, self._reset_to_normal)
    
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
    
    def _reset_to_normal(self):
        """Reset animation to normal mode."""
        self.animation_mode = "normal"
        self.current_frame = 0
        return False  # Don't repeat timeout
    
    def show_window(self, widget=None):
        """Show the floating window."""
        if self.floating_window:
            self.floating_window.present()
    
    def start_work(self, widget=None):
        """Start a work session."""
        self._start_timer(self.WORK_DURATION, "Work")
    
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
            self._start_timer(minutes * 60, f"Custom ({minutes}m)")
        
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
        self._update_display()
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
        
        # Mute
        self.mute_menu_item = Gtk.MenuItem(label="Unmute" if self.muted else "Mute")
        self.mute_menu_item.connect('activate', self.toggle_mute)
        menu.append(self.mute_menu_item)

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
    icon_path = Path(__file__).parent / "bit.gif"

    if not icon_path.exists():
        print(f"Error: bit.gif not found at {icon_path}")
        return
    
    timer = PomodoroTimer(icon_path)
    timer.run()


if __name__ == "__main__":
    main()
