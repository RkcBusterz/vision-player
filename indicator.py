from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
)
from icons import get_svg_icon

class SeekIndicator(QWidget):
    """
    Floating frameless indicator that flashes for 1 second on skip / rewind,
    rendered over the native GPU video surface with clean glassmorphism.
    """
    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(100, 100)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.card = QWidget(self)
        self.card.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 23, 42, 220);
                border: 1.5px solid rgba(255, 255, 255, 50);
                border-radius: 50px;
            }
        """)
        outer_layout.addWidget(self.card)

        inner_layout = QVBoxLayout(self.card)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel(self.card)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        inner_layout.addWidget(self.icon_label)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(1000)
        self.anim.setKeyValueAt(0.0, 1.0)
        self.anim.setKeyValueAt(0.60, 1.0)
        self.anim.setKeyValueAt(1.0, 0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.finished.connect(self.hide)

    def flash(self, icon_name: str, x: int, y: int):
        self.anim.stop()
        self.icon_label.setPixmap(get_svg_icon(icon_name, "#ffffff", 44).pixmap(44, 44))
        self.move(x, y)
        self.opacity_effect.setOpacity(1.0)
        self.show()
        self.anim.start()
