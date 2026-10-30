from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtCore import QByteArray, Qt

SVG_DEFS = {
    "play": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 5.14v13.72a1 1 0 001.53.85l11-6.86a1 1 0 000-1.7l-11-6.86A1 1 0 008 5.14z" fill="{color}"/>
    </svg>
    """,
    "pause": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="6" y="5" width="4" height="14" rx="1.5" fill="{color}"/>
        <rect x="14" y="5" width="4" height="14" rx="1.5" fill="{color}"/>
    </svg>
    """,
    "replay_10": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 8l-4 4 4 4" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M11 8l-4 4 4 4" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <text x="17.5" y="15" fill="{color}" font-size="8.5" font-weight="800" font-family="'Segoe UI', sans-serif" text-anchor="middle">10</text>
    </svg>
    """,
    "forward_10": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <text x="6.5" y="15" fill="{color}" font-size="8.5" font-weight="800" font-family="'Segoe UI', sans-serif" text-anchor="middle">10</text>
        <path d="M13 8l4 4-4 4" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M18 8l4 4-4 4" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "folder": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "audio": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M11 5L6 9H3v6h3l5 4V5z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M15.5 8.5a5 5 0 010 7M18.5 6a8.5 8.5 0 010 12" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
    </svg>
    """,
    "speed": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="9" stroke="{color}" stroke-width="2"/>
        <path d="M12 12l3.5-3.5" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        <circle cx="12" cy="12" r="1.5" fill="{color}"/>
    </svg>
    """,
    "fullscreen": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "minimize": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 10h6V4m10 6h-6V4m0 16v-6h6M10 20v-6H4" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "music_note": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M9 18V5l12-2v13" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="6" cy="18" r="3" stroke="{color}" stroke-width="2"/>
        <circle cx="18" cy="16" r="3" stroke="{color}" stroke-width="2"/>
    </svg>
    """,
    "prev": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 6v12M18 6L8 12l10 6V6z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "next": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M18 6v12M6 6l10 6-10 6V6z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "folder_open": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 6a2 2 0 012-2h4l2 2h10a2 2 0 012 2v2H2V6z" stroke="{color}" stroke-width="2"/>
        <path d="M2 12h20l-2 8H4l-2-8z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "playlist": """
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 6h16M4 12h10M4 18h7m6-4v6l5-3-5-3z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """
}

def get_svg_icon(name: str, color: str = "#CBD5E1", size: int = 24) -> QIcon:
    raw_svg = SVG_DEFS.get(name, "").replace("{color}", color)
    if not raw_svg:
        return QIcon()

    renderer = QSvgRenderer(QByteArray(raw_svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
