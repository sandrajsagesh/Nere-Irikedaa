"""
Main application window and animated shell for Nere Irikedaa (Useless 3.0 — Posture Glass).
Features:
- Spacious, responsive desktop utility layout (620 x 780 default)
- Natural vertical hierarchy with clean rhythm and breathing room:
  Header -> Title/Subtitle -> Divider -> Mode toggle -> Flexible space -> Status card -> Fun/Info card -> Footer
- 1.2–1.8s "Nere Irikedaa" startup animation sequence transitioning continuously into the dashboard
- Tactile, smoothly sliding segmented pill mode toggle (Useful vs Useless) over 300ms
- Subtle crossfade feedback on mode descriptions
- Solid, high-contrast luxury dark card surface (no translucency regressions)
- Real-time camera & monitoring health indicators with retry support
- Windows system typography and responsive scaling
"""
import sys
from typing import Optional
from PyQt6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    pyqtSignal,
    pyqtProperty,
    QRect,
    QRectF,
    QPoint,
    QTimer,
)
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QLinearGradient,
    QPen,
    QFont,
    QGuiApplication,
    QMouseEvent,
    QKeySequence,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGraphicsOpacityEffect,
)

from config import AppMode, PostureState

FONT_FAMILY = '"Segoe UI Variable Text", "Segoe UI", -apple-system, system-ui, sans-serif'
DISPLAY_FONT = '"Segoe UI Variable Display", "Segoe UI", -apple-system, system-ui, sans-serif'

DEFAULT_WIDTH = 520
DEFAULT_HEIGHT = 615
MIN_WIDTH = 480
MIN_HEIGHT = 580


class AnimatedModeToggle(QFrame):
    """
    Segmented interactive toggle switch with a tactile sliding pill thumb
    between USEFUL and USELESS modes with time-based cubic easing (300ms).
    Clicking anywhere on the left half selects USEFUL; clicking right selects USELESS.
    """
    mode_changed = pyqtSignal(object)  # emits AppMode

    def __init__(self, initial_mode: AppMode = AppMode.USEFUL, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode = initial_mode
        self._thumb_progress = 0.0 if initial_mode == AppMode.USEFUL else 1.0

        # Thumb slide animation (0.0 = Useful, 1.0 = Useless) over 300ms with OutCubic
        self.anim_thumb = QPropertyAnimation(self, b"thumb_progress")
        self.anim_thumb.setDuration(300)
        self.anim_thumb.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def thumb_progress(self) -> float:
        return self._thumb_progress

    @thumb_progress.setter
    def thumb_progress(self, val: float):
        self._thumb_progress = max(0.0, min(1.0, val))
        self.update()

    def set_mode(self, mode: AppMode, emit_signal: bool = True):
        target = 0.0 if mode == AppMode.USEFUL else 1.0

        # Prevent re-entrancy from restarting or aborting an ongoing glide
        if self._mode == mode:
            if self.anim_thumb.state() == QPropertyAnimation.State.Running and self.anim_thumb.endValue() == target:
                return
            if abs(self._thumb_progress - target) < 0.001:
                return

        self._mode = mode
        self.anim_thumb.stop()
        self.anim_thumb.setDuration(300)
        self.anim_thumb.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_thumb.setStartValue(self._thumb_progress)
        self.anim_thumb.setEndValue(target)
        self.anim_thumb.start()

        if emit_signal:
            self.mode_changed.emit(mode)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            w = self.width()
            if event.pos().x() < w / 2:
                self.set_mode(AppMode.USEFUL, emit_signal=True)
            else:
                self.set_mode(AppMode.USELESS, emit_signal=True)
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = self.rect()
        radius = rect.height() / 2.0

        # 1. Base capsule container background (recessed dark track)
        base_path = QPainterPath()
        base_path.addRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        painter.fillPath(base_path, QColor(9, 12, 19, 235))

        # Track border
        track_pen = QPen(QColor(255, 255, 255, 24), 1.0)
        painter.strokePath(base_path, track_pen)

        # 2. Animated Sliding Tactile Thumb Pill
        pad = 4.0
        track_w = rect.width() - pad * 2.0
        half_w = track_w / 2.0
        thumb_h = rect.height() - pad * 2.0
        thumb_x = pad + self._thumb_progress * half_w
        thumb_y = pad
        thumb_rect = QRectF(thumb_x, thumb_y, half_w, thumb_h)
        thumb_radius = thumb_h / 2.0

        thumb_path = QPainterPath()
        thumb_path.addRoundedRect(thumb_rect, thumb_radius, thumb_radius)

        # Interpolate accent colors:
        # Useful (0.0): Emerald (#00E676 -> 0, 230, 118)
        # Useless (1.0): Sky Cyan (#38BDF8 -> 56, 189, 248)
        p = self._thumb_progress
        r = int((1.0 - p) * 0 + p * 56)
        g = int((1.0 - p) * 230 + p * 189)
        b = int((1.0 - p) * 118 + p * 248)

        base_r = int((1.0 - p) * 16 + p * 14)
        base_g = int((1.0 - p) * 32 + p * 26)
        base_b = int((1.0 - p) * 24 + p * 42)

        # Solid dark backing under thumb
        painter.fillPath(thumb_path, QColor(base_r, base_g, base_b, 245))

        # Glowing accent gradient
        pill_grad = QLinearGradient(thumb_x, thumb_y, thumb_x, thumb_y + thumb_h)
        pill_grad.setColorAt(0.0, QColor(r, g, b, 85))
        pill_grad.setColorAt(1.0, QColor(r, g, b, 35))
        painter.fillPath(thumb_path, pill_grad)

        # Crisp glowing pill border
        thumb_pen = QPen(QColor(r, g, b, 210), 1.5)
        painter.strokePath(thumb_path, thumb_pen)

        # 3. Stable Text Labels ("USEFUL" on left, "USELESS" on right)
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        painter.setFont(font)

        left_rect = QRectF(pad, pad, half_w, thumb_h)
        right_rect = QRectF(pad + half_w, pad, half_w, thumb_h)

        # Smooth color interpolation for text
        useful_alpha = int((1.0 - p) * 255 + p * 100)
        useful_color = QColor(0, 230, 118) if p < 0.25 else QColor(255, 255, 255, useful_alpha)

        useless_alpha = int(p * 255 + (1.0 - p) * 100)
        useless_color = QColor(56, 189, 248) if p > 0.75 else QColor(255, 255, 255, useless_alpha)

        painter.setPen(useful_color)
        painter.drawText(left_rect, Qt.AlignmentFlag.AlignCenter, "USEFUL")

        painter.setPen(useless_color)
        painter.drawText(right_rect, Qt.AlignmentFlag.AlignCenter, "USELESS")


class MainWindow(QWidget):
    """
    Main desktop window for Nere Irikedaa (Useless 3.0 — Posture Glass).
    Presents:
    - Spacious 620 x 780 layout with clean breathing room
    - Proper Qt layout hierarchy:
        Header -> Title/Subtitle -> Divider -> Mode section -> Flexible space -> Status card -> Fun/Info card -> Footer
    - 1.2-1.8s "Nere Irikedaa" startup animation sequence
    - Smooth continuous transition into the main dashboard
    - Tactile 300ms animated mode toggle
    - Mode change crossfade feedback
    - Solid, high-contrast luxury dark finish
    """
    mode_changed = pyqtSignal(object)  # emits AppMode
    retry_camera_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, initial_mode: AppMode = AppMode.USEFUL):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Responsive dimensions with compact default size
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self._center_on_screen()

        self._drag_pos = QPoint()
        self._hero_offset = 14
        self.current_mode = initial_mode

        # Window-level shortcut for Ctrl+Shift+Q
        self.shortcut_quit = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        self.shortcut_quit.activated.connect(self.quit_requested.emit)

        self._init_ui()

    def _center_on_screen(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - DEFAULT_WIDTH) // 2
            y = geo.y() + (geo.height() - DEFAULT_HEIGHT) // 2
            self.move(x, y)

    @pyqtProperty(int)
    def hero_offset(self) -> int:
        return self._hero_offset

    @hero_offset.setter
    def hero_offset(self, val: int):
        self._hero_offset = val
        if hasattr(self, 'lbl_splash_hero'):
            self.lbl_splash_hero.setContentsMargins(0, val, 0, 0)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 14, 14, 14)

        # Outer card container: solid, high-contrast, fully opaque luxury dark finish
        self.card = QFrame(self)
        self.card.setObjectName("AppCard")
        self.card.setStyleSheet(f"""
            #AppCard {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #161B29,
                    stop:0.4 #121520,
                    stop:1 #0D0F17
                );
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-top: 1.5px solid rgba(255, 255, 255, 0.28);
                border-radius: 24px;
            }}
        """)
        root_layout.addWidget(self.card)

        # Layer 1: Dashboard View (Main app control center)
        self.dashboard_layer = QFrame(self.card)
        self.dash_layout = QVBoxLayout(self.dashboard_layer)
        self.dash_layout.setContentsMargins(28, 22, 28, 20)
        self.dash_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. Header: Drag Handle + Minimize / Close Buttons
        # -------------------------------------------------------------
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)

        self.app_glyph = QLabel("✦ NERE IRIKEDAA • USEFUL")
        self.app_glyph.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1.2px;
            color: #00E676;
        """)
        title_bar.addWidget(self.app_glyph)
        title_bar.addStretch()

        btn_min = QPushButton("—")
        btn_min.setFixedSize(28, 28)
        btn_min.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_min.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
                color: rgba(255, 255, 255, 0.70);
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.18);
                color: #ffffff;
            }}
        """)
        btn_min.clicked.connect(self.showMinimized)
        title_bar.addWidget(btn_min)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
                color: rgba(255, 255, 255, 0.70);
                font-size: 10px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: rgba(239, 68, 68, 0.40);
                color: #ffffff;
                border-color: rgba(239, 68, 68, 0.70);
            }}
        """)
        btn_close.clicked.connect(self.hide)
        title_bar.addWidget(btn_close)

        self.dash_layout.addLayout(title_bar)

        # -------------------------------------------------------------
        # 2. Header: App Name & Tagline
        # -------------------------------------------------------------
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 2, 0, 0)
        header_layout.setSpacing(3)

        self.lbl_title = QLabel("Nere Irikedaa")
        self.lbl_title.setStyleSheet(f"""
            font-family: {DISPLAY_FONT};
            font-size: 26px;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: -0.3px;
        """)
        header_layout.addWidget(self.lbl_title)

        self.lbl_tagline = QLabel("An unnecessarily sophisticated posture assistant.")
        self.lbl_tagline.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 13px;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.60);
        """)
        header_layout.addWidget(self.lbl_tagline)

        self.dash_layout.addLayout(header_layout)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        self.dash_layout.addWidget(divider)

        # -------------------------------------------------------------
        # 3. Interactive Mode Section
        # -------------------------------------------------------------
        mode_section = QVBoxLayout()
        mode_section.setContentsMargins(0, 2, 0, 0)
        mode_section.setSpacing(6)

        lbl_mode_hdr = QLabel("MODE")
        lbl_mode_hdr.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 10.5px;
            font-weight: 800;
            letter-spacing: 1.4px;
            color: rgba(255, 255, 255, 0.40);
        """)
        mode_section.addWidget(lbl_mode_hdr)

        self.toggle = AnimatedModeToggle(initial_mode=self.current_mode, parent=self.dashboard_layer)
        self.toggle.mode_changed.connect(self._on_toggle_changed)
        mode_section.addWidget(self.toggle)

        self.dash_layout.addLayout(mode_section)

        # -------------------------------------------------------------
        # 4. Featured Statement Widget (Central Product Tagline)
        # -------------------------------------------------------------
        self.dash_layout.addSpacing(6)

        statement_widget = QWidget()
        statement_layout = QVBoxLayout(statement_widget)
        statement_layout.setContentsMargins(0, 0, 0, 0)
        statement_layout.setSpacing(0)

        self.lbl_statement = QLabel(
            "Your camera understands your posture.\n"
            "Your screen pays the price."
        )
        self.lbl_statement.setWordWrap(True)
        self.lbl_statement.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_statement.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 17px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.90);
            line-height: 1.48;
            letter-spacing: -0.2px;
        """)
        statement_layout.addWidget(self.lbl_statement)
        self.lbl_concept_body = self.lbl_statement

        self.dash_layout.addWidget(statement_widget)

        # -------------------------------------------------------------
        # Clear Empty Gap / Breathing Room (Stretch between statement & status)
        # -------------------------------------------------------------
        self.dash_layout.addStretch(1)

        # -------------------------------------------------------------
        # 5. Status / Health Panel (Compact: 84px height)
        # -------------------------------------------------------------
        status_box = QFrame()
        status_box.setObjectName("StatusBox")
        status_box.setFixedHeight(84)
        status_box.setStyleSheet("""
            #StatusBox {
                background: rgba(0, 0, 0, 0.28);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        s_layout = QVBoxLayout(status_box)
        s_layout.setContentsMargins(18, 12, 18, 12)
        s_layout.setSpacing(8)

        cam_row = QHBoxLayout()
        self.lbl_cam_dot = QLabel("●")
        self.lbl_cam_dot.setStyleSheet("color: #00E676; font-size: 12px;")
        cam_row.addWidget(self.lbl_cam_dot)

        self.lbl_cam_status = QLabel("Camera Active")
        self.lbl_cam_status.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 12.5px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.90);
        """)
        cam_row.addWidget(self.lbl_cam_status)
        cam_row.addStretch()

        self.btn_retry_cam = QPushButton("Retry")
        self.btn_retry_cam.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry_cam.setVisible(False)
        self.btn_retry_cam.setStyleSheet(f"""
            QPushButton {{
                background: rgba(245, 158, 11, 0.20);
                border: 1px solid rgba(245, 158, 11, 0.40);
                border-radius: 10px;
                color: #FBBF24;
                font-family: {FONT_FAMILY};
                font-size: 11px;
                font-weight: 600;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background: rgba(245, 158, 11, 0.35);
            }}
        """)
        self.btn_retry_cam.clicked.connect(self._on_retry_clicked)
        cam_row.addWidget(self.btn_retry_cam)

        s_layout.addLayout(cam_row)

        mon_row = QHBoxLayout()
        self.lbl_mon_dot = QLabel("●")
        self.lbl_mon_dot.setStyleSheet("color: #38BDF8; font-size: 12px;")
        mon_row.addWidget(self.lbl_mon_dot)

        self.lbl_mon_status = QLabel("Posture Monitoring Active")
        self.lbl_mon_status.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 12.5px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.90);
        """)
        mon_row.addWidget(self.lbl_mon_status)
        mon_row.addStretch()

        s_layout.addLayout(mon_row)
        self.dash_layout.addWidget(status_box)

        # Internal compatibility properties for mode descriptions
        self.mode_info_box = QFrame()
        self.lbl_mode_title = QLabel()
        self.lbl_mode_desc = QLabel()
        self.desc_opacity = QGraphicsOpacityEffect(self.mode_info_box)
        self.anim_desc_fade = QPropertyAnimation(self.desc_opacity, b"opacity")

        self._apply_mode_description_texts(self.current_mode)

        # -------------------------------------------------------------
        # 7. Footer: Quit Shortcut & Build Version
        # -------------------------------------------------------------
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(4, 4, 4, 0)

        lbl_quit_hint = QLabel("Ctrl + Shift + Q to quit")
        lbl_quit_hint.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 11.5px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.38);
            letter-spacing: 0.2px;
        """)
        footer_layout.addWidget(lbl_quit_hint)
        footer_layout.addStretch()

        lbl_version = QLabel("v3.0.5 • Windows Native")
        lbl_version.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 11px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.28);
        """)
        footer_layout.addWidget(lbl_version)

        self.dash_layout.addLayout(footer_layout)

        # Dashboard Opacity Effect for smooth transition
        self.dash_opacity = QGraphicsOpacityEffect(self.dashboard_layer)
        self.dash_opacity.setOpacity(1.0)
        self.dashboard_layer.setGraphicsEffect(self.dash_opacity)

        # -------------------------------------------------------------
        # Layer 2: Startup Splash Layer ("Nere Irikedaa")
        # -------------------------------------------------------------
        self.splash_layer = QFrame(self.card)
        self.splash_layer.setObjectName("SplashLayer")
        self.splash_layer.setStyleSheet("""
            #SplashLayer {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #161B29,
                    stop:0.4 #121520,
                    stop:1 #0D0F17
                );
                border-radius: 24px;
            }
        """)
        splash_layout = QVBoxLayout(self.splash_layer)
        splash_layout.setContentsMargins(40, 50, 40, 50)
        splash_layout.setSpacing(10)

        splash_layout.addStretch(3)

        # Subtle brand badge
        self.lbl_splash_badge = QLabel("✦ USELESS 3.0")
        self.lbl_splash_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_splash_badge.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 11.5px;
            font-weight: 800;
            letter-spacing: 2.2px;
            color: #38BDF8;
        """)
        splash_layout.addWidget(self.lbl_splash_badge)

        # Hero Title: "Nere Irikedaa"
        self.lbl_splash_hero = QLabel("Nere Irikedaa")
        self.lbl_splash_hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_splash_hero.setStyleSheet(f"""
            font-family: {DISPLAY_FONT};
            font-size: 34px;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: 1.8px;
        """)
        splash_layout.addWidget(self.lbl_splash_hero)

        # Secondary subtitle
        self.lbl_splash_sub = QLabel("An unnecessarily sophisticated posture assistant.")
        self.lbl_splash_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_splash_sub.setWordWrap(True)
        self.lbl_splash_sub.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 13px;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.58);
            letter-spacing: 0.4px;
        """)
        splash_layout.addWidget(self.lbl_splash_sub)

        splash_layout.addStretch(4)

        # Splash Opacity Effects
        self.splash_opacity = QGraphicsOpacityEffect(self.splash_layer)
        self.splash_opacity.setOpacity(1.0)
        self.splash_layer.setGraphicsEffect(self.splash_opacity)

        self.hero_opacity = QGraphicsOpacityEffect(self.lbl_splash_hero)
        self.hero_opacity.setOpacity(0.0)
        self.lbl_splash_hero.setGraphicsEffect(self.hero_opacity)

        self.sub_opacity = QGraphicsOpacityEffect(self.lbl_splash_sub)
        self.sub_opacity.setOpacity(0.0)
        self.lbl_splash_sub.setGraphicsEffect(self.sub_opacity)

        self.badge_opacity = QGraphicsOpacityEffect(self.lbl_splash_badge)
        self.badge_opacity.setOpacity(0.0)
        self.lbl_splash_badge.setGraphicsEffect(self.badge_opacity)

        # By default start with splash layer hidden until play_startup_sequence is called
        self.splash_layer.setVisible(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep both layers perfectly filling the card container
        card_rect = self.card.rect()
        self.dashboard_layer.setGeometry(card_rect)
        self.splash_layer.setGeometry(card_rect)

    def _apply_mode_description_texts(self, mode: AppMode):
        """Sets text and color styling synchronously."""
        if mode == AppMode.USEFUL:
            self.app_glyph.setText("✦ NERE IRIKEDAA • USEFUL")
            self.app_glyph.setStyleSheet(f"""
                font-family: {FONT_FAMILY};
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1.2px;
                color: #00E676;
            """)
            if hasattr(self, 'lbl_statement'):
                self.lbl_statement.setText(
                    "Your camera understands your posture.\n"
                    "Your screen pays the price."
                )
            self.lbl_mode_title.setText("Actually trying to help.")
            self.lbl_mode_title.setStyleSheet(f"""
                font-family: {FONT_FAMILY};
                font-size: 13.5px;
                font-weight: 600;
                color: #00E676;
            """)
            self.lbl_mode_desc.setText(
                "Only warns when your posture degrades. "
                "Blurs screen and tells you to sit straight."
            )
        else:
            self.app_glyph.setText("✦ NERE IRIKEDAA • USELESS")
            self.app_glyph.setStyleSheet(f"""
                font-family: {FONT_FAMILY};
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1.2px;
                color: #38BDF8;
            """)
            if hasattr(self, 'lbl_statement'):
                self.lbl_statement.setText(
                    "Your posture is perfectly fine.\n"
                    "Unfortunately, we still felt intervention was necessary."
                )
            self.lbl_mode_title.setText("Helping was never the objective.")
            self.lbl_mode_title.setStyleSheet(f"""
                font-family: {FONT_FAMILY};
                font-size: 13.5px;
                font-weight: 600;
                color: #38BDF8;
            """)
            self.lbl_mode_desc.setText(
                "Bans you from seeing your work when posture is too perfect. "
                "Slouching clears the screen."
            )

    def _update_mode_description(self, mode: AppMode, animated: bool = True):
        """Updates the mode description and featured statement on mode change."""
        self._apply_mode_description_texts(mode)

    def _on_toggle_changed(self, mode: AppMode):
        self.current_mode = mode
        self._update_mode_description(mode, animated=True)
        self.mode_changed.emit(mode)

    def _on_retry_clicked(self):
        self.lbl_cam_status.setText("Connecting...")
        self.lbl_cam_dot.setStyleSheet("color: #FBBF24; font-size: 12px;")
        self.btn_retry_cam.setEnabled(False)
        self.retry_camera_requested.emit()

    def set_camera_status(self, is_active: bool, error_msg: Optional[str] = None):
        """Updates camera indicator and retry button dynamically."""
        if is_active:
            self.lbl_cam_dot.setText("●")
            self.lbl_cam_dot.setStyleSheet("color: #00E676; font-size: 12px;")
            self.lbl_cam_status.setText("Camera Active")
            self.lbl_cam_status.setStyleSheet(f"""
                font-family: {FONT_FAMILY};
                font-size: 12.5px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.90);
            """)
            self.btn_retry_cam.setVisible(False)
        else:
            self.lbl_cam_dot.setText("○")
            self.lbl_cam_dot.setStyleSheet("color: #EF4444; font-size: 12px;")
            self.lbl_cam_status.setText("Camera Unavailable" if not error_msg else error_msg)
            self.lbl_cam_status.setStyleSheet(f"""
                font-family: {FONT_FAMILY};
                font-size: 12.5px;
                font-weight: 500;
                color: #FCA5A5;
            """)
            self.btn_retry_cam.setVisible(True)
            self.btn_retry_cam.setEnabled(True)

    def set_mode(self, mode: AppMode):
        """Allows external updates (e.g. from system tray or config load) to update the toggle."""
        self.current_mode = mode
        self.toggle.set_mode(mode, emit_signal=False)
        self._update_mode_description(mode, animated=False)

    def play_opening_animation(self):
        """Default entrance animation: runs the Nere Irikedaa startup sequence."""
        self.play_startup_sequence()

    def play_startup_sequence(self):
        """
        Executes a 1.2–1.6s startup intro sequence:
        Step 1 (0ms): Clean nearly-black dark background. Dashboard is hidden.
        Step 2 (60-500ms): Brand 'Nere Irikedaa' smoothly fades in (0 -> 100%)
               with subtle upward drift (+14px -> 0px) over 440ms with OutCubic.
        Step 3 (360-680ms): Subtitle 'An unnecessarily sophisticated posture assistant.'
               fades in over 320ms.
        Step 4 (680-1050ms): Brief hold of completed intro (~370ms).
        Step 5 (1050-1450ms): Fluid continuous transition into the main dashboard.
        """
        screen = QGuiApplication.primaryScreen()
        sw = screen.geometry().width() if screen else 1920
        sh = screen.geometry().height() if screen else 1080

        w = self.width()
        h = self.height()
        target_x = (sw - w) // 2
        target_y = (sh - h) // 2

        self.move(target_x, target_y)
        self.setWindowOpacity(1.0)

        # Prepare layers
        self.resizeEvent(None)
        self._hero_offset = 14
        if hasattr(self, 'lbl_splash_hero'):
            self.lbl_splash_hero.setContentsMargins(0, 14, 0, 0)

        self.splash_layer.setVisible(True)
        self.splash_layer.raise_()
        self.splash_opacity.setOpacity(1.0)
        self.badge_opacity.setOpacity(0.0)
        self.hero_opacity.setOpacity(0.0)
        self.sub_opacity.setOpacity(0.0)

        self.dashboard_layer.setVisible(False)
        self.dash_opacity.setOpacity(0.0)

        self.show()

        # Step 2 (60ms): Brand appears with subtle upward drift
        self.anim_badge_fade = QPropertyAnimation(self.badge_opacity, b"opacity")
        self.anim_badge_fade.setDuration(320)
        self.anim_badge_fade.setStartValue(0.0)
        self.anim_badge_fade.setEndValue(1.0)

        self.anim_hero_fade = QPropertyAnimation(self.hero_opacity, b"opacity")
        self.anim_hero_fade.setDuration(440)
        self.anim_hero_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_hero_fade.setStartValue(0.0)
        self.anim_hero_fade.setEndValue(1.0)

        self.anim_hero_slide = QPropertyAnimation(self, b"hero_offset")
        self.anim_hero_slide.setDuration(440)
        self.anim_hero_slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_hero_slide.setStartValue(14)
        self.anim_hero_slide.setEndValue(0)

        QTimer.singleShot(60, lambda: (
            self.anim_badge_fade.start(),
            self.anim_hero_fade.start(),
            self.anim_hero_slide.start()
        ))

        # Step 3 (360ms): Secondary subtitle fades in smoothly
        self.anim_sub_fade = QPropertyAnimation(self.sub_opacity, b"opacity")
        self.anim_sub_fade.setDuration(320)
        self.anim_sub_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_sub_fade.setStartValue(0.0)
        self.anim_sub_fade.setEndValue(1.0)

        QTimer.singleShot(360, self.anim_sub_fade.start)

        # Step 5 (1050ms): Fluid continuous transition into the main dashboard
        self.anim_splash_fade = QPropertyAnimation(self.splash_opacity, b"opacity")
        self.anim_splash_fade.setDuration(380)
        self.anim_splash_fade.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.anim_splash_fade.setStartValue(1.0)
        self.anim_splash_fade.setEndValue(0.0)

        self.anim_dash_fade = QPropertyAnimation(self.dash_opacity, b"opacity")
        self.anim_dash_fade.setDuration(400)
        self.anim_dash_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_dash_fade.setStartValue(0.0)
        self.anim_dash_fade.setEndValue(1.0)

        def start_transition():
            self.dashboard_layer.setVisible(True)
            self.dashboard_layer.raise_()
            self.anim_splash_fade.start()
            self.anim_dash_fade.start()

        QTimer.singleShot(1050, start_transition)

        # Step 6 (1450ms): Complete transition and hide splash layer
        def finish_sequence():
            self.splash_layer.setVisible(False)
            self.dash_opacity.setOpacity(1.0)

        QTimer.singleShot(1450, finish_sequence)

    # Smooth Window Dragging
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = QPoint()
        event.accept()
