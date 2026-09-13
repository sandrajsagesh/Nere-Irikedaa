"""
System tray and global emergency exit hotkey for Useless 3.0 — Posture Glass.
Supports switching between Useful/Useless mode, pausing/resuming, opening debug HUD, and Ctrl+Shift+Q exit.
"""
from typing import Callable
from PIL import Image, ImageDraw
import pystray
import keyboard
from config import AppMode, Sensitivity

def create_tray_image(color: str = "#00e6ff") -> Image.Image:
    """Generates a clean glass icon programmatically."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw two round glass lenses
    draw.ellipse([8, 18, 28, 38], outline=color, width=4)
    draw.ellipse([36, 18, 56, 38], outline=color, width=4)
    # Bridge
    draw.line([28, 28, 36, 28], fill=color, width=3)
    # Temples
    draw.line([8, 26, 2, 22], fill=color, width=3)
    draw.line([56, 26, 62, 22], fill=color, width=3)
    return img

class SystemTrayManager:
    def __init__(
        self,
        on_toggle_mode: Callable[[AppMode], None],
        on_toggle_monitoring: Callable[[bool], None],
        on_toggle_debug: Callable[[], None],
        on_change_sensitivity: Callable[[Sensitivity], None],
        on_exit: Callable[[], None],
        on_show_window: Optional[Callable[[], None]] = None,
    ):
        self.on_toggle_mode = on_toggle_mode
        self.on_toggle_monitoring = on_toggle_monitoring
        self.on_toggle_debug = on_toggle_debug
        self.on_change_sensitivity = on_change_sensitivity
        self.on_exit = on_exit
        self.on_show_window = on_show_window

        self.current_mode = AppMode.USEFUL
        self.is_monitoring = True
        self.current_sensitivity = Sensitivity.NORMAL
        self.tray_icon: Optional[pystray.Icon] = None

        # Setup emergency exit hotkey: Ctrl + Shift + Q
        try:
            keyboard.add_hotkey("ctrl+shift+q", self._emergency_exit)
            print("[SystemTray] Emergency hotkey registered: Ctrl + Shift + Q")
        except Exception as e:
            print(f"[SystemTray] Warning: Could not register global hotkey: {e}")

    def _emergency_exit(self):
        print("\n[EMERGENCY EXIT] Ctrl + Shift + Q triggered! Stopping immediately...")
        self.stop()
        self.on_exit()

    def _handle_show_window(self, icon=None, item=None):
        if self.on_show_window:
            self.on_show_window()

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                "Useless 3.0 — Posture Glass",
                None,
                enabled=False,
            ),
            pystray.MenuItem(
                "Open Window",
                self._handle_show_window,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: "Pause Monitoring" if self.is_monitoring else "Resume Monitoring",
                self._handle_toggle_monitoring,
            ),
            pystray.MenuItem(
                lambda item: "Mode: Useful (Helping Posture)" if self.current_mode == AppMode.USEFUL else "Mode: Useless (Trolling Good Posture)",
                self._handle_toggle_mode,
            ),
            pystray.MenuItem(
                "Toggle Debug HUD",
                self._handle_toggle_debug,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Sensitivity",
                pystray.Menu(
                    pystray.MenuItem(
                        "Low",
                        lambda: self._set_sensitivity(Sensitivity.LOW),
                        checked=lambda item: self.current_sensitivity == Sensitivity.LOW,
                    ),
                    pystray.MenuItem(
                        "Normal",
                        lambda: self._set_sensitivity(Sensitivity.NORMAL),
                        checked=lambda item: self.current_sensitivity == Sensitivity.NORMAL,
                    ),
                    pystray.MenuItem(
                        "High",
                        lambda: self._set_sensitivity(Sensitivity.HIGH),
                        checked=lambda item: self.current_sensitivity == Sensitivity.HIGH,
                    ),
                ),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Stop & Exit (Ctrl+Shift+Q)",
                self._handle_exit,
            ),
        )

    def _handle_toggle_monitoring(self, icon, item):
        self.is_monitoring = not self.is_monitoring
        self.on_toggle_monitoring(self.is_monitoring)
        self.tray_icon.update_menu()

    def _handle_toggle_mode(self, icon, item):
        if self.current_mode == AppMode.USEFUL:
            self.current_mode = AppMode.USELESS
        else:
            self.current_mode = AppMode.USEFUL
        self.on_toggle_mode(self.current_mode)
        self.tray_icon.icon = create_tray_image("#ff6b6b" if self.current_mode == AppMode.USEFUL else "#00e6ff")
        self.tray_icon.update_menu()

    def _handle_toggle_debug(self, icon, item):
        self.on_toggle_debug()

    def _set_sensitivity(self, sens: Sensitivity):
        self.current_sensitivity = sens
        self.on_change_sensitivity(sens)
        self.tray_icon.update_menu()

    def _handle_exit(self, icon, item):
        self.stop()
        self.on_exit()

    def start(self):
        icon_img = create_tray_image("#ff6b6b")
        self.tray_icon = pystray.Icon(
            "PostureGlass",
            icon_img,
            "Useless 3.0 — Posture Glass",
            menu=self._build_menu()
        )
        self.tray_icon.run_detached()
        print("[SystemTray] System tray icon running in background.")

    def stop(self):
        try:
            keyboard.remove_hotkey("ctrl+shift+q")
        except Exception:
            pass
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
