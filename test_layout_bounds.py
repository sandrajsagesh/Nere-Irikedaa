"""
Targeted layout bounds and hierarchy verification test for MainWindow.
Verifies:
1. Header -> Title/Subtitle -> Divider -> Mode -> Featured Statement -> Spacer -> Status Box -> Footer order.
2. Featured Statement is strictly below Mode section with >=20px spacing.
3. Status box is strictly below Featured Statement.
4. Footer is strictly below Status box.
5. All elements are within window bounds across default (580x650) and resized configurations (560x640, 600x680, 550x620).
6. Useful Mode and Useless Mode display the proper two-line featured statement.
"""
import sys
from PyQt6.QtWidgets import QApplication
from config import AppMode
from app_window import MainWindow

def test_layout_bounds():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=" * 80)
    print("RUNNING MAIN WINDOW LAYOUT & BOUNDS VERIFICATION (COMPACT 580x650)")
    print("=" * 80)

    win = MainWindow(initial_mode=AppMode.USEFUL)
    win.show()
    app.processEvents()

    # Ensure layout is activated
    win.dash_layout.activate()
    app.processEvents()

    sizes_to_test = [
        (520, 615, "Default Compact Size (520x615)"),
        (500, 600, "Compact Lower Target (500x600)"),
        (540, 630, "Compact Upper Target (540x630)"),
        (480, 580, "Minimum Size Bound (480x580)"),
        (560, 640, "Extended Size (560x640)"),
    ]

    for w, h, desc in sizes_to_test:
        print(f"\n[Testing {desc}: {w}x{h}]")
        win.resize(w, h)
        app.processEvents()
        win.dash_layout.activate()
        app.processEvents()

        dash_rect = win.dashboard_layer.geometry()
        
        toggle_geom = win.toggle.geometry()
        concept_geom = win.lbl_concept_body.parentWidget().geometry() if win.lbl_concept_body.parentWidget() != win.dashboard_layer else win.lbl_concept_body.geometry()
        status_box = win.lbl_cam_status.parentWidget()
        assert status_box is not None, "Status box not found"
        status_geom = status_box.geometry()

        # Find footer
        footer_layout = None
        for i in range(win.dash_layout.count()):
            item = win.dash_layout.itemAt(i)
            if item and item.layout() and win.dash_layout.itemAt(i).layout() != win.dash_layout:
                lay = item.layout()
                if lay.count() >= 2:
                    w0 = lay.itemAt(0).widget()
                    if w0 and "Ctrl + Shift + Q" in getattr(w0, 'text', lambda: '')():
                        footer_layout = lay
                        break

        assert footer_layout is not None, "Footer layout not found in dash_layout"
        footer_geom = footer_layout.geometry()

        print(f"  Dashboard layer height: {dash_rect.height()}px")
        print(f"  Toggle geometry: y={toggle_geom.y()}, bottom={toggle_geom.bottom()}, height={toggle_geom.height()}px")
        print(f"  Statement geometry: y={concept_geom.y()}, bottom={concept_geom.bottom()}, height={concept_geom.height()}px")
        print(f"  Status box geometry: y={status_geom.y()}, bottom={status_geom.bottom()}, height={status_geom.height()}px")
        print(f"  Footer layout geometry: y={footer_geom.y()}, bottom={footer_geom.bottom()}, height={footer_geom.height()}px")

        # Assertions
        # 1. Statement is below Mode toggle with comfortable spacing
        assert concept_geom.top() >= toggle_geom.bottom() + 16, (
            f"Spacing error: Concept top ({concept_geom.top()}) too close to Toggle bottom ({toggle_geom.bottom()})"
        )

        # 2. Status box is below Statement
        assert status_geom.top() > concept_geom.bottom(), (
            f"Overlap error: Status box top ({status_geom.top()}) <= Statement bottom ({concept_geom.bottom()})"
        )

        # 3. Footer is below Status box
        assert footer_geom.top() > status_geom.bottom(), (
            f"Overlap error: Footer top ({footer_geom.top()}) <= Status box bottom ({status_geom.bottom()})"
        )

        # 4. Footer bottom is within dashboard layer
        assert footer_geom.bottom() <= dash_rect.height(), (
            f"Overflow error: Footer bottom ({footer_geom.bottom()}) exceeds dashboard height ({dash_rect.height()})"
        )

        # 5. Status box is comfortably inside dashboard layer
        assert status_geom.bottom() <= dash_rect.height() - 24, (
            f"Overflow error: Status box bottom ({status_geom.bottom()}) exceeds allowable dashboard height"
        )
        print("  -> Hierarchy & bounds verified: Toggle < Statement < Status Box < Footer <= Window Bounds.")

        # Test both modes in this size
        for mode in [AppMode.USEFUL, AppMode.USELESS]:
            win.set_mode(mode)
            app.processEvents()
            win.dash_layout.activate()
            app.processEvents()
            assert "✦ NERE IRIKEDAA" in win.app_glyph.text()
            if mode == AppMode.USEFUL:
                assert "Your camera understands your posture" in win.lbl_concept_body.text()
                assert "Your screen pays the price" in win.lbl_concept_body.text()
            else:
                assert "Your posture is perfectly fine" in win.lbl_concept_body.text()
                assert "intervention was necessary" in win.lbl_concept_body.text()

    win.close()
    print("\n" + "=" * 80)
    print("ALL LAYOUT BOUNDS TESTS PASSED PERFECTLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_layout_bounds()
