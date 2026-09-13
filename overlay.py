"""
Liquid Glass UI overlay with smooth screen blur and micro-animations for Useless 3.0 — Posture Glass.
Built with PyQt6, featuring floating liquid glass material aesthetics, Dynamic Island inspired status pills,
time-based smooth blur/dim interpolation (0 -> target over 500ms), and 100% crisp, unblurred text.
"""
import random
from typing import Optional, Tuple
import cv2
import numpy as np

from PyQt6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    pyqtSignal,
    pyqtProperty,
    QObject,
    QRect,
    QRectF,
    QTimer,
)
from PyQt6.QtGui import (
    QImage,
    QPixmap,
    QFont,
    QColor,
    QPainter,
    QPainterPath,
    QLinearGradient,
    QPen,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QFrame,
)

from config import (
    PostureState,
    AppMode,
    POSTURE_DISPLAY_NAMES,
    USEFUL_MESSAGES,
    USELESS_MESSAGES,
)

# ---------------------------------------------------------------------------
# Visual Themes by Posture State (Muted, sophisticated, luxury tones)
# ---------------------------------------------------------------------------
STATE_THEMES = {
    PostureState.GOOD.value: {
        "badge": "PERFECT POSTURE",
        "icon": "●",
        "dot_color": "#00E676",  # Vibrant Emerald
        "accent_bg": "rgba(0, 230, 118, 0.12)",
        "accent_border": "rgba(0, 230, 118, 0.32)",
        "text_color": "#00E676",
    },
    PostureState.FORWARD_NECK.value: {
        "badge": "FORWARD NECK",
        "icon": "⤸",
        "dot_color": "#FF6B81",  # Soft Coral Rose
        "accent_bg": "rgba(255, 107, 129, 0.13)",
        "accent_border": "rgba(255, 107, 129, 0.35)",
        "text_color": "#FF758F",
    },
    PostureState.SLOUCHING.value: {
        "badge": "SLOUCH DETECTED",
        "icon": "↓",
        "dot_color": "#F6A854",  # Warm Sunset Amber
        "accent_bg": "rgba(246, 168, 84, 0.13)",
        "accent_border": "rgba(246, 168, 84, 0.35)",
        "text_color": "#F6B26B",
    },
    PostureState.LEANING_LEFT.value: {
        "badge": "LEANING LEFT",
        "icon": "←",
        "dot_color": "#A78BFA",  # Periwinkle Lavender
        "accent_bg": "rgba(167, 139, 250, 0.13)",
        "accent_border": "rgba(167, 139, 250, 0.35)",
        "text_color": "#C4B5FD",
    },
    PostureState.LEANING_RIGHT.value: {
        "badge": "LEANING RIGHT",
        "icon": "→",
        "dot_color": "#A78BFA",  # Periwinkle Lavender
        "accent_bg": "rgba(167, 139, 250, 0.13)",
        "accent_border": "rgba(167, 139, 250, 0.35)",
        "text_color": "#C4B5FD",
    },
    PostureState.HEAD_TILT.value: {
        "badge": "HEAD TILT",
        "icon": "↻",
        "dot_color": "#C084FC",  # Soft Orchid
        "accent_bg": "rgba(192, 132, 252, 0.13)",
        "accent_border": "rgba(192, 132, 252, 0.35)",
        "text_color": "#D8B4FE",
    },
    PostureState.RECLINED_BENT_NECK.value: {
        "badge": "RECLINED & BENT NECK",
        "icon": "⟲",
        "dot_color": "#FB7185",  # Rose Quartz
        "accent_bg": "rgba(251, 113, 133, 0.13)",
        "accent_border": "rgba(251, 113, 133, 0.35)",
        "text_color": "#FDA4AF",
    },
    PostureState.TOO_CLOSE.value: {
        "badge": "TOO CLOSE TO SCREEN",
        "icon": "🔍",
        "dot_color": "#F87171",  # Soft Crimson
        "accent_bg": "rgba(248, 113, 113, 0.13)",
        "accent_border": "rgba(248, 113, 113, 0.35)",
        "text_color": "#FCA5A5",
    },
    PostureState.UNKNOWN.value: {
        "badge": "SEARCHING...",
        "icon": "○",
        "dot_color": "#94A3B8",  # Muted Slate
        "accent_bg": "rgba(148, 163, 184, 0.12)",
        "accent_border": "rgba(148, 163, 184, 0.30)",
        "text_color": "#CBD5E1",
    },
}

USELESS_THEME = {
    "badge": "POSTURE PERFECT",
    "icon": "✦",
    "dot_color": "#38BDF8",  # Sky Cyan
    "accent_bg": "rgba(56, 189, 248, 0.14)",
    "accent_border": "rgba(56, 189, 248, 0.38)",
    "text_color": "#7DD3FC",
}

FONT_FAMILY = '"Segoe UI Variable Text", "Segoe UI", -apple-system, system-ui, sans-serif'
DISPLAY_FONT_FAMILY = '"Segoe UI Variable Display", "Segoe UI", -apple-system, system-ui, sans-serif'


class OverlaySignals(QObject):
    show_warning = pyqtSignal(str, str, str, str, bool)  # state_key, badge, title, subtitle, is_useless
    hide_warning = pyqtSignal()
    toggle_mode_requested = pyqtSignal()


class StatusPill(QFrame):
    """
    Dynamic-Island styled compact status pill capsule.
    Renders an indicator glyph/dot + clean uppercase state text.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 12, 4)
        layout.setSpacing(7)

        self.dot_label = QLabel("●")
        self.dot_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.dot_label)

        self.text_label = QLabel("POSTURE CHECK")
        self.text_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 1.1px;
        """)
        layout.addWidget(self.text_label)

    def set_theme(self, theme: dict, badge_override: Optional[str] = None):
        dot_col = theme.get("dot_color", "#38BDF8")
        txt_col = theme.get("text_color", "#38BDF8")
        bg_col = theme.get("accent_bg", "rgba(56, 189, 248, 0.14)")
        border_col = theme.get("accent_border", "rgba(56, 189, 248, 0.38)")
        badge_text = badge_override or theme.get("badge", "POSTURE")

        self.dot_label.setText(theme.get("icon", "●"))
        self.dot_label.setStyleSheet(f"color: {dot_col}; font-size: 10px; font-weight: 700;")
        self.text_label.setText(badge_text.upper())
        self.text_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            color: {txt_col};
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 1.1px;
        """)

        self.setStyleSheet(f"""
            StatusPill {{
                background: {bg_col};
                border: 1px solid {border_col};
                border-radius: 12px;
            }}
        """)


class LiquidGlassCard(QFrame):
    """
    Liquid Glass panel with physical frosted-glass characteristics:
    - Translucent acrylic base material allowing subtle background visibility (~70-76% opacity)
    - Specular top-light reflection gradient
    - Delicate 1px perimeter glass bevel with highlighted upper edge
    - Soft diffused elevation shadow
    - Razor-sharp, vector-rendered unblurred typography with smooth state crossfade transitions
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LiquidGlassCard")
        self.setFixedSize(500, 230)

        # Soft diffused drop shadow for floating elevation
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 115))
        shadow.setOffset(0, 14)
        self.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 22, 30, 20)
        main_layout.setSpacing(10)

        # 1. Header Bar: Pill Indicator + Mode Label
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_pill = StatusPill(self)
        header_layout.addWidget(self.status_pill)
        header_layout.addStretch()

        self.mode_label = QLabel("Useful Mode • 3.0")
        self.mode_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            color: rgba(255, 255, 255, 0.40);
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.4px;
        """)
        header_layout.addWidget(self.mode_label)
        main_layout.addLayout(header_layout)

        # 2. Hero Content Container (with smooth crossfade support)
        self.content_widget = QWidget(self)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.setSpacing(6)

        # Posture Category Title
        self.posture_label = QLabel("FORWARD NECK")
        self.posture_label.setStyleSheet(f"""
            font-family: {DISPLAY_FONT_FAMILY};
            color: #FFFFFF;
            font-size: 18px;
            font-weight: 600;
            letter-spacing: -0.2px;
        """)
        content_layout.addWidget(self.posture_label)

        # Primary Punchline (Funny Message Title)
        self.title_label = QLabel("Your neck is trying to join the laptop.")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            color: rgba(255, 255, 255, 0.90);
            font-size: 15px;
            font-weight: 400;
            line-height: 1.45;
        """)
        content_layout.addWidget(self.title_label)

        # Secondary Witty Observation (Subtitle)
        self.subtitle_label = QLabel("The screen is not going anywhere. You can stay back.")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            color: rgba(255, 255, 255, 0.60);
            font-size: 13px;
            font-weight: 400;
            line-height: 1.4;
        """)
        content_layout.addWidget(self.subtitle_label)

        main_layout.addWidget(self.content_widget)
        main_layout.addStretch()

        # 3. Footer Row: Subtle Hint
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.footer_label = QLabel("Sit upright to clear • Esc to dismiss")
        self.footer_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            color: rgba(255, 255, 255, 0.32);
            font-size: 11px;
            font-weight: 400;
            letter-spacing: 0.2px;
        """)
        footer_layout.addWidget(self.footer_label)
        footer_layout.addStretch()
        main_layout.addLayout(footer_layout)

        # Content crossfade opacity effect
        self._content_opacity = QGraphicsOpacityEffect(self.content_widget)
        self._content_opacity.setOpacity(1.0)
        self.content_widget.setGraphicsEffect(self._content_opacity)

        self.anim_content_fade = QPropertyAnimation(self._content_opacity, b"opacity")
        self.anim_content_fade.setDuration(160)
        self.anim_content_fade.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._current_state_key: Optional[str] = None

    def paintEvent(self, event):
        """
        Custom physical glass rendering with translucent acrylic fill,
        specular top-light sheen, and light-catching bevel edge highlight.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        radius = 24.0

        # 1. Glass Body: Semi-transparent dark mica gradient (~70-76% opacity)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect).adjusted(0.6, 0.6, -0.6, -0.6), radius, radius)

        body_grad = QLinearGradient(0, 0, 0, rect.height())
        body_grad.setColorAt(0.0, QColor(24, 30, 44, 175))
        body_grad.setColorAt(0.45, QColor(16, 21, 32, 185))
        body_grad.setColorAt(1.0, QColor(12, 16, 25, 195))
        painter.fillPath(path, body_grad)

        # 2. Specular Top-Light Reflection Sheen
        sheen_grad = QLinearGradient(0, 0, 0, rect.height() * 0.45)
        sheen_grad.setColorAt(0.0, QColor(255, 255, 255, 26))
        sheen_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(path, sheen_grad)

        # 3. Outer Glass Rim Bevel Border (light-catching top highlight)
        border_pen = QPen()
        border_grad = QLinearGradient(0, 0, 0, rect.height())
        border_grad.setColorAt(0.0, QColor(255, 255, 255, 78))   # Specular top rim
        border_grad.setColorAt(0.25, QColor(255, 255, 255, 34))  # Side rim
        border_grad.setColorAt(1.0, QColor(255, 255, 255, 14))   # Bottom rim
        border_pen.setBrush(border_grad)
        border_pen.setWidthF(1.2)
        painter.strokePath(path, border_pen)

    def update_content(self, state_key: str, badge: str, title: str, subtitle: str, is_useless: bool):
        """
        Updates content with a silky smooth crossfade if state changes while already visible.
        """
        theme = USELESS_THEME if is_useless else STATE_THEMES.get(state_key, STATE_THEMES[PostureState.GOOD.value])

        def apply_texts():
            self.status_pill.set_theme(theme, badge)
            self.posture_label.setText(badge.upper())
            self.title_label.setText(title)
            self.subtitle_label.setText(subtitle)

            if is_useless:
                self.mode_label.setText("Useless Mode • 3.0")
                self.mode_label.setStyleSheet(f"""
                    font-family: {FONT_FAMILY};
                    color: #38BDF8;
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: 0.4px;
                """)
                self.footer_label.setText("Slouch to clear screen • Useless Mode Active")
            else:
                self.mode_label.setText("Useful Mode • 3.0")
                self.mode_label.setStyleSheet(f"""
                    font-family: {FONT_FAMILY};
                    color: rgba(255, 255, 255, 0.40);
                    font-size: 11px;
                    font-weight: 500;
                    letter-spacing: 0.4px;
                """)
                self.footer_label.setText("Sit upright to clear • Esc to dismiss")

        # Apply text and theme synchronously
        apply_texts()

        # If card is already visible and transitioning between bad states, perform smooth crossfade pulse
        if self.isVisible() and self._current_state_key is not None and self._current_state_key != state_key:
            self._current_state_key = state_key
            self.anim_content_fade.stop()
            self.anim_content_fade.setStartValue(0.35)
            self.anim_content_fade.setEndValue(1.0)
            self.anim_content_fade.start()
        else:
            self._current_state_key = state_key
            self._content_opacity.setOpacity(1.0)


class ScreenBlurOverlay(QWidget):
    """
    Fullscreen frameless transparent window coordinating:
    1. Background Layer: Clean desktop smoothly cross-dissolving into frosted Gaussian blurred + dimmed backdrop
       over 500ms time-based interpolation.
    2. Glass Panel Layer: Center-floating LiquidGlassCard smoothly fading in and scaling (96% -> 100%)
       over 500ms with OutCubic easing.
    3. Content Layer: 100% vector-rendered, unblurred, razor-sharp typography.
    """
    def __init__(self):
        super().__init__()
        self.signals = OverlaySignals()
        self.signals.show_warning.connect(self._on_show_warning)
        self.signals.hide_warning.connect(self._on_hide_warning)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.clean_pixmap: Optional[QPixmap] = None
        self.blurred_pixmap: Optional[QPixmap] = None
        self._is_visible = False
        self._blur_progress = 0.0

        # Stable alert state and message tracking (deterministic random-on-entry)
        self._current_alert_state: Optional[PostureState] = None
        self._current_alert_mode: Optional[AppMode] = None
        self._current_message: Optional[Tuple[str, str]] = None

        # Central Liquid Glass Card
        self.glass_card = LiquidGlassCard(self)

        # Smooth blur progress animation (0.0 -> 1.0 over 500ms)
        self._is_capturing = False
        self.anim_blur = QPropertyAnimation(self, b"blur_progress")
        self.anim_blur.setDuration(500)
        self.anim_blur.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_blur.finished.connect(self._on_blur_anim_finished)

        # Card opacity animation
        self.card_opacity = QGraphicsOpacityEffect(self.glass_card)
        self.card_opacity.setOpacity(0.0)
        self.glass_card.setGraphicsEffect(self.card_opacity)

        self.anim_card_fade = QPropertyAnimation(self.card_opacity, b"opacity")
        self.anim_card_fade.setDuration(460)
        self.anim_card_fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Card scale animation (96% scale + 12px vertical float -> 100% centered over 500ms)
        self.anim_card_scale = QPropertyAnimation(self.glass_card, b"geometry")
        self.anim_card_scale.setDuration(500)
        self.anim_card_scale.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def blur_progress(self) -> float:
        return self._blur_progress

    @blur_progress.setter
    def blur_progress(self, val: float):
        self._blur_progress = max(0.0, min(1.0, val))
        self.update()

    def _get_target_card_rect(self) -> QRect:
        """Computes responsive card dimensions and centered position respecting screen size."""
        screen = QGuiApplication.primaryScreen()
        sw = self.width() or (screen.geometry().width() if screen else 1920)
        sh = self.height() or (screen.geometry().height() if screen else 1080)

        card_w = min(540, max(460, int(sw * 0.32)))
        card_h = min(250, max(215, int(sh * 0.20)))

        card_x = (sw - card_w) // 2
        card_y = (sh - card_h) // 2
        return QRect(card_x, card_y, card_w, card_h)

    def _capture_and_blur_screen(self):
        """
        Captures clean primary screen and computes high-quality blurred backdrop.
        Guarded against re-entrant calls and robust against arbitrary display resolutions.
        """
        if self._is_capturing:
            return
        self._is_capturing = True

        try:
            screen = QGuiApplication.primaryScreen()
            if not screen:
                return

            geometry = screen.geometry()
            self.setGeometry(geometry)

            # Grab clean screenshot of the desktop
            screenshot = screen.grabWindow(0)
            self.clean_pixmap = screenshot

            qimg = screenshot.toImage().convertToFormat(QImage.Format.Format_RGB888)
            ptr = qimg.bits()
            ptr.setsize(qimg.sizeInBytes())
            h = qimg.height()
            w = qimg.width()
            bpl = qimg.bytesPerLine()

            # Robust stride handling for scanline padding on any resolution
            raw = np.frombuffer(ptr, np.uint8)
            if bpl != w * 3:
                arr = raw.reshape((h, bpl))[:, :w * 3].reshape((h, w, 3))
            else:
                arr = raw.reshape((h, w, 3))

            # 1/3 scale for high performance (< 4ms blur) without pixelation artifacts
            small_w = max(1, w // 3)
            small_h = max(1, h // 3)
            small = cv2.resize(arr, (small_w, small_h), interpolation=cv2.INTER_LINEAR)

            # High-radius Gaussian blur for frosted acrylic effect
            blurred_small = cv2.GaussianBlur(small, (41, 41), 16.0)
            blurred = cv2.resize(blurred_small, (w, h), interpolation=cv2.INTER_LINEAR)

            # Blend with deep obsidian tint (12, 16, 24) at 34% weight
            obsidian = np.full_like(blurred, (12, 16, 24))
            blended = cv2.addWeighted(blurred, 0.66, obsidian, 0.34, 0)

            blurred_qimg = QImage(blended.data, w, h, w * 3, QImage.Format.Format_RGB888)
            self.blurred_pixmap = QPixmap.fromImage(blurred_qimg)
        finally:
            self._is_capturing = False

    def paintEvent(self, event):
        """
        Paints background layer with smooth frame-based interpolation between clean desktop and blurred desktop,
        plus an atmospheric ambient dim layer.
        The LiquidGlassCard and its text are child widgets drawn ON TOP and are NEVER blurred.
        """
        painter = QPainter(self)
        # 1. Base clean desktop
        if self.clean_pixmap:
            painter.drawPixmap(0, 0, self.clean_pixmap)
            
        # 2. Smoothly blended blur layer
        if self.blurred_pixmap and self._blur_progress > 0.0:
            painter.setOpacity(self._blur_progress)
            painter.drawPixmap(0, 0, self.blurred_pixmap)
            painter.setOpacity(1.0)
            
            # 3. Synchronous atmospheric ambient dimming
            dim_alpha = int(75 * self._blur_progress)
            painter.fillRect(self.rect(), QColor(8, 12, 20, dim_alpha))
        elif not self.clean_pixmap:
            # Fallback backdrop if capture unavailable
            painter.fillRect(self.rect(), QColor(10, 14, 22, int(220 * self._blur_progress)))

    def _on_show_warning(self, state_key: str, badge: str, title: str, subtitle: str, is_useless: bool):
        target_rect = self._get_target_card_rect()
        self.glass_card.update_content(state_key, badge, title, subtitle, is_useless)

        if not self._is_visible:
            if not is_useless:
                print(f"[UsefulDebug] overlay requested: {state_key}")
            # Capture backdrop only if not already cached from current session
            if self.clean_pixmap is None:
                if self.isVisible():
                    self.hide()
                self._capture_and_blur_screen()

            self._is_visible = True

            # Start rect: slight scale-down (96%) and shifted down by 12px for subtle upward float
            scale_w = int(target_rect.width() * 0.96)
            scale_h = int(target_rect.height() * 0.96)
            scale_x = target_rect.x() + (target_rect.width() - scale_w) // 2
            scale_y = target_rect.y() + (target_rect.height() - scale_h) // 2 + 12
            start_rect = QRect(scale_x, scale_y, scale_w, scale_h)

            self.glass_card.setGeometry(start_rect)
            self.card_opacity.setOpacity(0.0)

            self.show()

            # Smooth Blur & Dim Interpolation (current -> 1.0)
            self.anim_blur.stop()
            self.anim_blur.setDuration(450)
            self.anim_blur.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim_blur.setStartValue(self._blur_progress)
            self.anim_blur.setEndValue(1.0)
            self.anim_blur.start()

            # Card Fade In
            self.anim_card_fade.stop()
            self.anim_card_fade.setDuration(420)
            self.anim_card_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim_card_fade.setStartValue(self.card_opacity.opacity())
            self.anim_card_fade.setEndValue(1.0)
            self.anim_card_fade.start()

            # Card Subtle Scale-Up and Float-In
            self.anim_card_scale.stop()
            self.anim_card_scale.setDuration(450)
            self.anim_card_scale.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim_card_scale.setStartValue(start_rect)
            self.anim_card_scale.setEndValue(target_rect)
            self.anim_card_scale.start()

        self.update()

    def _on_hide_warning(self):
        if self._is_visible:
            self._is_visible = False

            # Exit rect: slight scale-down (96%) and downward drift (+8px)
            cur_geo = self.glass_card.geometry()
            exit_w = int(cur_geo.width() * 0.96)
            exit_h = int(cur_geo.height() * 0.96)
            exit_x = cur_geo.x() + (cur_geo.width() - exit_w) // 2
            exit_y = cur_geo.y() + (cur_geo.height() - exit_h) // 2 + 8
            exit_rect = QRect(exit_x, exit_y, exit_w, exit_h)

            # Smooth Blur & Dim Fade Out (current -> 0.0 over 380ms)
            self.anim_blur.stop()
            self.anim_blur.setDuration(380)
            self.anim_blur.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self.anim_blur.setStartValue(self._blur_progress)
            self.anim_blur.setEndValue(0.0)
            self.anim_blur.start()

            # Card Fade Out
            self.anim_card_fade.stop()
            self.anim_card_fade.setDuration(320)
            self.anim_card_fade.setEasingCurve(QEasingCurve.Type.InCubic)
            self.anim_card_fade.setStartValue(self.card_opacity.opacity())
            self.anim_card_fade.setEndValue(0.0)
            self.anim_card_fade.start()

            # Card Slight Scale-Down
            self.anim_card_scale.stop()
            self.anim_card_scale.setDuration(350)
            self.anim_card_scale.setEasingCurve(QEasingCurve.Type.InCubic)
            self.anim_card_scale.setStartValue(cur_geo)
            self.anim_card_scale.setEndValue(exit_rect)
            self.anim_card_scale.start()

    def _on_blur_anim_finished(self):
        """Connected once in __init__; cleans up when hide animation completes."""
        if not self._is_visible and self._blur_progress <= 0.01:
            self.hide()
            self.clean_pixmap = None
            self.blurred_pixmap = None

    def trigger_warning(self, state: PostureState, mode: AppMode):
        """
        Thread-safe trigger invoked by posture classification engine.
        Ensures deterministic random-on-entry message selection:
        The message is selected once per alert/state and remains rock-solid stable across frames.
        """
        # Ensure state is PostureState enum
        if isinstance(state, str):
            try:
                state = PostureState(state)
            except ValueError:
                state = PostureState.GOOD

        # Stable on-entry selection: only re-pick if state or mode changes, or on alert entry
        if self._current_alert_state != state or self._current_alert_mode != mode or self._current_message is None:
            self._current_alert_state = state
            self._current_alert_mode = mode
            if mode == AppMode.USELESS:
                self._current_message = random.choice(USELESS_MESSAGES)
            else:
                msg_list = USEFUL_MESSAGES.get(state)
                if msg_list and isinstance(msg_list, list):
                    self._current_message = random.choice(msg_list)
                elif msg_list and isinstance(msg_list, tuple):
                    self._current_message = msg_list
                else:
                    self._current_message = ("Posture Check", "Please sit up straight and align your head.")
                print(f"[UsefulDebug] message selected: \"{self._current_message[0]}\" | \"{self._current_message[1]}\"")

        title, subtitle = self._current_message

        if mode == AppMode.USELESS:
            badge = "POSTURE PERFECT"
            self.signals.show_warning.emit(
                PostureState.GOOD.value,
                badge,
                title,
                subtitle,
                True,
            )
        else:
            badge = POSTURE_DISPLAY_NAMES.get(state, "POSTURE CHECK").upper()
            self.signals.show_warning.emit(
                state.value,
                badge,
                title,
                subtitle,
                False,
            )

    def clear_warning(self):
        """Thread-safe signal to dismiss the warning overlay."""
        self._current_alert_state = None
        self._current_alert_mode = None
        self._current_message = None
        self.signals.hide_warning.emit()

    def keyPressEvent(self, event: QKeyEvent):
        """Allows user to press Escape to dismiss the warning."""
        if event.key() == Qt.Key.Key_Escape:
            self.clear_warning()
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """Clicking outside the glass card dismisses the warning."""
        if not self.glass_card.geometry().contains(event.pos()):
            self.clear_warning()
        super().mousePressEvent(event)
