MODERN_STYLE = """
QMainWindow {
    background-color: #000000;
}

/* Top Menu Bar */
QMenuBar {
    background-color: #0b0e14;
    color: #94a3b8;
    font-family: "Segoe UI", -apple-system, sans-serif;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 10px;
    border-bottom: 1px solid #161b26;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 5px;
}

QMenuBar::item:selected {
    background-color: #1e2536;
    color: #ffffff;
}

QMenu {
    background-color: #0f131d;
    color: #e2e8f0;
    font-size: 12px;
    border: 1px solid #222b3d;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 22px 6px 12px;
    border-radius: 5px;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

/* Floating Glass Control Dock */
QWidget#controlDock {
    background-color: rgba(13, 17, 26, 225);
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 18px;
}

/* Center Play/Pause Hero Button */
QPushButton#heroPlayBtn {
    background-color: #ffffff;
    border: none;
    border-radius: 21px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
}

QPushButton#heroPlayBtn:hover {
    background-color: #dbeafe;
}

QPushButton#heroPlayBtn:pressed {
    background-color: #93c5fd;
}

/* Circular SVG Icon Buttons */
QPushButton[role="iconBtn"] {
    background-color: transparent;
    border: none;
    border-radius: 17px;
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
}

QPushButton[role="iconBtn"]:hover {
    background-color: rgba(255, 255, 255, 28);
}

QPushButton[role="iconBtn"]:pressed {
    background-color: rgba(255, 255, 255, 15);
}

/* Sleek Capsule Dropdowns */
QComboBox {
    background-color: rgba(255, 255, 255, 16);
    color: #e2e8f0;
    font-family: "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 12px;
    padding: 4px 12px;
    min-width: 68px;
}

QComboBox:hover {
    background-color: rgba(255, 255, 255, 28);
    border-color: rgba(255, 255, 255, 55);
    color: #ffffff;
}

QComboBox::drop-down {
    border: none;
    width: 0px;
}

QComboBox QAbstractItemView {
    background-color: #0f131d;
    color: #e2e8f0;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    border: 1px solid #28324a;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}

/* Timestamp Labels */
QLabel[role="timeLabel"] {
    color: #94a3b8;
    font-family: "Consolas", "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}

/* Precision Scrub Bar */
QSlider {
    background: transparent;
}

QSlider::groove:horizontal {
    height: 4px;
    background: rgba(255, 255, 255, 40);
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}

QSlider::handle:horizontal:hover {
    background: #60a5fa;
}
"""
