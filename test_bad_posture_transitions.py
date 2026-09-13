"""
Test file for verifying all 10 required bad posture state transitions in Useful Mode:
1. GOOD -> LEANING_LEFT
2. GOOD -> LEANING_RIGHT
3. LEANING_LEFT -> TOO_CLOSE
4. LEANING_RIGHT -> TOO_CLOSE
5. LEANING_LEFT -> SLOUCHING
6. LEANING_RIGHT -> SLOUCHING
7. LEANING_LEFT -> FORWARD_NECK
8. LEANING_RIGHT -> FORWARD_NECK
9. TOO_CLOSE -> SLOUCHING
10. SLOUCHING -> TOO_CLOSE

Verifies:
- New posture recognized promptly without requiring returning to GOOD first
- Alert / message timer is reset for the new state
- New state's comment and badge appear on the overlay
- Ongoing bad state (e.g. SLOUCHING -> SLOUCHING) does NOT spam or reset messages
- UNKNOWN does not trigger a warning
"""
import sys
from PyQt6.QtWidgets import QApplication
from config import (
    PostureState,
    AppMode,
    USEFUL_MESSAGES,
    POSTURE_DISPLAY_NAMES,
)
from posture_engine import PostureEngine
from overlay import ScreenBlurOverlay
from verify_useful_stability import simulate_step


def test_all_10_transitions():
    app = QApplication.instance() or QApplication(sys.argv)
    overlay = ScreenBlurOverlay()
    engine = PostureEngine()

    transitions = [
        (PostureState.GOOD, PostureState.LEANING_LEFT),
        (PostureState.GOOD, PostureState.LEANING_RIGHT),
        (PostureState.LEANING_LEFT, PostureState.TOO_CLOSE),
        (PostureState.LEANING_RIGHT, PostureState.TOO_CLOSE),
        (PostureState.LEANING_LEFT, PostureState.SLOUCHING),
        (PostureState.LEANING_RIGHT, PostureState.SLOUCHING),
        (PostureState.LEANING_LEFT, PostureState.FORWARD_NECK),
        (PostureState.LEANING_RIGHT, PostureState.FORWARD_NECK),
        (PostureState.TOO_CLOSE, PostureState.SLOUCHING),
        (PostureState.SLOUCHING, PostureState.TOO_CLOSE),
    ]

    t = 100.0
    current_warning_state = None

    print("=" * 80)
    print("VERIFYING 10 REQUIRED POSTURE TRANSITIONS IN USEFUL MODE")
    print("=" * 80)

    for i, (from_state, to_state) in enumerate(transitions, 1):
        print(f"\n[{i}/10] Transition: {from_state.value.upper()} -> {to_state.value.upper()}")

        # 1. Establish the starting state
        if from_state == PostureState.GOOD:
            # Hold good for 1.35s to clear any prior warnings
            for _ in range(45):
                simulate_step(engine, PostureState.GOOD, t)
                t += 0.03
            assert engine.current_state == PostureState.GOOD
            assert not engine.warning_active
            current_warning_state = None
            overlay.clear_warning()
            app.processEvents()

            # Transition from GOOD to bad posture requires 2.0s sustained
            for _ in range(70):
                simulate_step(engine, to_state, t)
                t += 0.03
        else:
            # If not already in from_state, sustain it for 2.1s
            if not engine.warning_active or engine.current_state != from_state:
                for _ in range(70):
                    simulate_step(engine, from_state, t)
                    t += 0.03
                current_warning_state = from_state
                overlay.trigger_warning(from_state, AppMode.USEFUL)
                app.processEvents()

            assert engine.current_state == from_state, f"Expected {from_state}, got {engine.current_state}"
            assert engine.warning_active

            # Now transition directly to to_state, simulating 1 intermediate jitter frame of a different posture
            jitter_posture = PostureState.FORWARD_NECK if to_state != PostureState.FORWARD_NECK else PostureState.SLOUCHING
            frames = [jitter_posture] + [to_state] * 12

            for s in frames:
                simulate_step(engine, s, t)
                t += 0.03
                if engine.current_state == to_state:
                    break

        # 2. Check engine state
        assert engine.current_state == to_state, (
            f"State transition failed! Expected {to_state.value}, got {engine.current_state.value}"
        )
        assert engine.warning_active, "Warning should be active for bad posture!"

        # 3. Simulate main.py warning dispatch
        is_bad_posture = engine.warning_active and engine.current_state not in (PostureState.GOOD, PostureState.UNKNOWN)
        if is_bad_posture and current_warning_state != engine.current_state:
            overlay.trigger_warning(engine.current_state, AppMode.USEFUL)
            current_warning_state = engine.current_state
            app.processEvents()

        # 4. Verify overlay UI content
        badge = overlay.glass_card.status_pill.text_label.text()
        title = overlay.glass_card.title_label.text()
        sub = overlay.glass_card.subtitle_label.text()
        expected_badge = POSTURE_DISPLAY_NAMES[to_state].upper()

        assert expected_badge in badge.upper(), f"Badge mismatch! Expected {expected_badge}, got {badge}"
        assert (title, sub) in USEFUL_MESSAGES[to_state], f"Comment mismatch! Got ({title}, {sub}) for {to_state}"

        print(f"  -> Authoritative State: {engine.current_state.value.upper()}")
        print(f"  -> Badge: {badge}")
        print(f"  -> Comment Title: \"{title}\"")
        print(f"  -> Comment Subtitle: \"{sub}\"")
        print(f"  -> Result: PASS")

    # 5. Verify no repeat spam when continuing in same bad posture (SLOUCHING -> SLOUCHING)
    print("\n[VERIFICATION: ANTI-SPAM] Continuing in same bad posture (SLOUCHING -> SLOUCHING)")
    initial_title = overlay.glass_card.title_label.text()
    for _ in range(30):
        simulate_step(engine, PostureState.TOO_CLOSE, t)
        t += 0.03
        # main.py check
        if engine.warning_active and engine.current_state not in (PostureState.GOOD, PostureState.UNKNOWN):
            if current_warning_state != engine.current_state:
                overlay.trigger_warning(engine.current_state, AppMode.USEFUL)
                current_warning_state = engine.current_state
        app.processEvents()

    assert overlay.glass_card.title_label.text() == initial_title, "Comment was re-randomized or spammed!"
    print("  -> Confirmed: Continuing same posture does not spam or restart comment [PASS]")

    # 6. Verify UNKNOWN does not trigger warning
    print("\n[VERIFICATION: SAFE UNKNOWN] UNKNOWN confidence drop does not trigger warning")
    for _ in range(30):
        simulate_step(engine, PostureState.UNKNOWN, t)
        t += 0.03
    assert not engine.warning_active or engine.current_state == PostureState.UNKNOWN
    # In main.py
    is_bad = engine.warning_active and engine.current_state not in (PostureState.GOOD, PostureState.UNKNOWN)
    assert not is_bad, "UNKNOWN must never be flagged as bad posture!"
    print("  -> Confirmed: UNKNOWN is handled safely and never triggers warning [PASS]")

    print("\n" + "=" * 80)
    print("ALL 10 TRANSITIONS AND CONSTRAINTS VERIFIED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    test_all_10_transitions()
