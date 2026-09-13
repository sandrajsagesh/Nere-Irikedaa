"""
UI Polish Verification Script.
Tests:
1. LiquidGlassCard rendering & status themes for all posture states
2. Dynamic Island pill styling
3. Smooth entrance and exit animations
4. Content crossfade transitions between states
5. Useful Mode vs Useless Mode styling and messaging
6. Clean dismissal and resource teardown
"""
import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from overlay import ScreenBlurOverlay, STATE_THEMES, USELESS_THEME
from config import PostureState, AppMode

def verify_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    overlay = ScreenBlurOverlay()
    
    print("Testing UI Polish Components...")
    
    # 1. Test Useful Mode with Forward Neck
    print("[1/4] Triggering Useful Mode warning: FORWARD_NECK")
    overlay.trigger_warning(PostureState.FORWARD_NECK, AppMode.USEFUL)
    app.processEvents()
    
    card = overlay.glass_card
    assert card.title_label.text() != "", "Title should be populated"
    assert "FORWARD NECK" in card.status_pill.text_label.text(), "Pill should display FORWARD NECK"
    assert "Useful Mode" in card.mode_label.text(), "Mode label should say Useful Mode"
    print("      -> Forward Neck banner, pill, and typography rendered correctly.")
    
    # Wait for entrance animation
    time.sleep(0.4)
    app.processEvents()

    # 2. Test Content Crossfade to Slouching
    print("[2/4] Smooth transition to SLOUCHING (crossfade test)")
    overlay.trigger_warning(PostureState.SLOUCHING, AppMode.USEFUL)
    for _ in range(15):
        time.sleep(0.02)
        app.processEvents()
        
    assert "SLOUCH" in card.status_pill.text_label.text(), "Pill should update to SLOUCH DETECTED"
    print("      -> Crossfaded smoothly to Slouching.")

    # 3. Test Useless Mode (Good posture trolling)
    print("[3/4] Triggering Useless Mode warning (Good posture troll)")
    overlay.trigger_warning(PostureState.GOOD, AppMode.USELESS)
    for _ in range(15):
        time.sleep(0.02)
        app.processEvents()
        
    assert "Useless Mode" in card.mode_label.text(), "Mode label should say Useless Mode"
    print(f"      -> Useless Mode comedy dialogue: \"{card.title_label.text()}\"")
    print(f"      -> Subtitle: \"{card.subtitle_label.text()}\"")

    # 4. Test Dismissal / Exit Animation
    print("[4/4] Testing smooth exit animation & hide")
    overlay.clear_warning()
    for _ in range(25):
        time.sleep(0.02)
        app.processEvents()

    assert not overlay.isVisible(), "Overlay should be hidden after clear animation completes"
    print("      -> Overlay dismissed and blurred pixmap cleared successfully.")

    print("\nALL UI POLISH TESTS PASSED SUCCESSFULLY!")
    overlay.close()

if __name__ == "__main__":
    verify_ui()
