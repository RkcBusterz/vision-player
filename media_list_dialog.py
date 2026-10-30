import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem
)

class MediaListDialog(QDialog):
    """
    Glassmorphism Media Playlist Dialog showing loaded folder/queue tracks.
    Highlights currently playing media and allows double-clicking/clicking to jump to track.
    """
    track_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Media Playlist & Queue")
        self.resize(520, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0e17;
                color: #e2e8f0;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QListWidget {
                background-color: #121826;
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 6px;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border-radius: 6px;
                padding: 8px 12px;
                margin-bottom: 2px;
                color: #cbd5e1;
                font-size: 12px;
                font-weight: 500;
            }
            QListWidget::item:hover {
                background-color: rgba(56, 189, 248, 0.10);
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: rgba(37, 99, 235, 0.28);
                border: 1px solid rgba(56, 189, 248, 0.45);
                color: #38bdf8;
                font-weight: 700;
            }
            QPushButton.actionBtn {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton.actionBtn:hover {
                background-color: #2563eb;
                border-color: #3b82f6;
                color: #ffffff;
            }
            QPushButton.closeBtn {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 18px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton.closeBtn:hover {
                background-color: #3b82f6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        header_lbl = QLabel("Loaded Media List")
        header_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        title_row.addWidget(header_lbl)
        title_row.addStretch(1)

        self.count_badge = QLabel("0 Items")
        self.count_badge.setStyleSheet("""
            color: #38bdf8;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            background-color: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.35);
            border-radius: 6px;
        """)
        title_row.addWidget(self.count_badge)
        layout.addLayout(title_row)

        self.list_widget = QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self._on_item_activated)
        layout.addWidget(self.list_widget, stretch=1)

        btn_row = QHBoxLayout()
        hint_lbl = QLabel("Double-click to play item")
        hint_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        btn_row.addWidget(hint_lbl)
        btn_row.addStretch(1)

        btn_play = QPushButton("Play Selected", self)
        btn_play.setProperty("class", "actionBtn")
        btn_play.clicked.connect(self._on_play_clicked)
        btn_row.addWidget(btn_play)

        btn_close = QPushButton("Close", self)
        btn_close.setProperty("class", "closeBtn")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

        self.playlist = []
        self.current_index = -1

    def update_playlist(self, playlist: list[str], current_index: int):
        self.playlist = playlist
        self.current_index = current_index
        self.list_widget.clear()

        self.count_badge.setText(f"{len(playlist)} Items")

        for idx, path in enumerate(playlist):
            filename = os.path.basename(path)
            prefix = "▶ " if idx == current_index else f"{idx + 1:2d}. "
            item = QListWidgetItem(f"{prefix} {filename}")
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setToolTip(path)
            self.list_widget.addItem(item)

        if 0 <= current_index < len(playlist):
            self.list_widget.setCurrentRow(current_index)
            self.list_widget.scrollToItem(self.list_widget.item(current_index))

    def set_current_index(self, index: int):
        self.current_index = index
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if row < len(self.playlist):
                filename = os.path.basename(self.playlist[row])
                prefix = "▶ " if row == index else f"{row + 1:2d}. "
                item.setText(f"{prefix} {filename}")
        if 0 <= index < self.list_widget.count():
            self.list_widget.setCurrentRow(index)

    def _on_item_activated(self, item: QListWidgetItem):
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None:
            self.track_selected.emit(int(idx))

    def _on_play_clicked(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.playlist):
            self.track_selected.emit(row)

