import os
import time
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QScrollArea, QGridLayout, QApplication
)

class PlayerInfoDialog(QDialog):
    """
    Real-time Player & Media Information Dialog displaying video stream,
    audio stream, rendering/frame stats, memory usage, and container details.
    Auto-refreshes continuously while visible, with responsive text wrapping
    and smart middle-ellipsis for long filenames/paths.
    """
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._last_update_ts = 0.0
        self._pulse_state = False

        self.setWindowTitle("Vision Player — Media & Engine Stats")
        self.setFixedWidth(530)
        self.resize(530, 640)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0e17;
                color: #e2e8f0;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QWidget#scrollContent {
                background: transparent;
            }
            QWidget.card {
                background-color: #121826;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
            QLabel.sectionHeader {
                color: #38bdf8;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
                background: transparent;
            }
            QLabel.keyLabel {
                color: #94a3b8;
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }
            QLabel.valLabel {
                color: #f8fafc;
                font-size: 11px;
                font-weight: 600;
                font-family: 'Consolas', 'Segoe UI', monospace;
                background: transparent;
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

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 16)
        main_layout.setSpacing(12)

        title_row = QHBoxLayout()
        header_lbl = QLabel("Player & Stream Diagnostics")
        header_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        title_row.addWidget(header_lbl)
        title_row.addStretch(1)

        self.live_badge = QLabel("● LIVE STATS")
        self.live_badge.setStyleSheet("""
            color: #10b981;
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            background-color: rgba(16, 185, 129, 20);
            border: 1px solid rgba(16, 185, 129, 50);
            border-radius: 6px;
        """)
        title_row.addWidget(self.live_badge)
        main_layout.addLayout(title_row)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_widget = QWidget()
        content_widget.setObjectName("scrollContent")
        content_widget.setMaximumWidth(490)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(12)

        self.val_labels = {}

        v_card, v_grid = self._create_card("VIDEO STREAM")
        self._add_row(v_card, v_grid, 0, "Resolution", "resolution")
        self._add_row(v_card, v_grid, 1, "Codec", "video_codec")
        self._add_row(v_card, v_grid, 2, "Framerate", "fps")
        self._add_row(v_card, v_grid, 3, "Hardware Decoding", "hwdec")
        self._add_row(v_card, v_grid, 4, "Pixel Format", "pixel_format")
        self._add_row(v_card, v_grid, 5, "Video Bitrate", "video_bitrate")
        content_layout.addWidget(v_card)

        a_card, a_grid = self._create_card("AUDIO STREAM")
        self._add_row(a_card, a_grid, 0, "Audio Codec", "audio_codec")
        self._add_row(a_card, a_grid, 1, "Channels", "channels")
        self._add_row(a_card, a_grid, 2, "Sample Rate", "sample_rate")
        self._add_row(a_card, a_grid, 3, "Audio Bitrate", "audio_bitrate")
        content_layout.addWidget(a_card)

        f_card, f_grid = self._create_card("PLAYBACK & RENDERING")
        self._add_row(f_card, f_grid, 0, "Rendered / Total Frames", "frames")
        self._add_row(f_card, f_grid, 1, "Dropped Frames", "dropped_frames")
        self._add_row(f_card, f_grid, 2, "Playback Speed", "speed")
        content_layout.addWidget(f_card)

        p_card, p_grid = self._create_card("SYSTEM & CACHE")
        self._add_row(p_card, p_grid, 0, "Process Memory (RAM)", "process_ram")
        self._add_row(p_card, p_grid, 1, "Demuxer Cache Buffer", "cache_buffer")
        content_layout.addWidget(p_card)

        d_card, d_grid = self._create_card("MEDIA FILE")
        self._add_row(d_card, d_grid, 0, "File Name", "file_name")
        self._add_row(d_card, d_grid, 1, "File Size", "file_size")
        self._add_row(d_card, d_grid, 2, "Container Format", "container")
        self._add_row(d_card, d_grid, 3, "Full File Path", "file_path")
        content_layout.addWidget(d_card)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, stretch=1)

        btn_row = QHBoxLayout()

        btn_refresh = QPushButton("⟳ Refresh", self)
        btn_refresh.setProperty("class", "actionBtn")
        btn_refresh.setToolTip("Force refresh statistics")
        btn_refresh.clicked.connect(self.refresh_stats)
        btn_row.addWidget(btn_refresh)

        btn_copy = QPushButton("Copy Stats", self)
        btn_copy.setProperty("class", "actionBtn")
        btn_copy.setToolTip("Copy all statistics to clipboard")
        btn_copy.clicked.connect(self.copy_stats)
        btn_row.addWidget(btn_copy)

        btn_row.addStretch(1)

        btn_close = QPushButton("Close", self)
        btn_close.setProperty("class", "closeBtn")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        main_layout.addLayout(btn_row)

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.refresh_stats)
        self.timer.start()

        if hasattr(self.engine, 'signals') and hasattr(self.engine.signals, 'time_updated'):
            self.engine.signals.time_updated.connect(self._on_time_tick)

    def _create_card(self, title: str):
        card = QWidget(self)
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QLabel(title, card)
        header.setProperty("class", "sectionHeader")
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setContentsMargins(0, 2, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        return card, grid

    def _add_row(self, card: QWidget, grid: QGridLayout, row: int, label_text: str, key: str):
        lbl = QLabel(label_text, card)
        lbl.setProperty("class", "keyLabel")
        grid.addWidget(lbl, row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        val = QLabel("—", card)
        val.setProperty("class", "valLabel")
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val.setWordWrap(True)
        val.setMaximumWidth(310)
        grid.addWidget(val, row, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.val_labels[key] = val

    @staticmethod
    def _format_display_val(key: str, s: str) -> tuple[str, str]:
        """
        Formats long filenames/paths with middle-ellipsis to keep layout clean and responsive,
        while preserving the complete string for tooltips and clipboard.
        """
        if key == "file_name":
            if len(s) > 38:
                return f"{s[:20]}...{s[-15:]}", s
        elif key == "file_path":
            if len(s) > 36:
                return f"{s[:16]}...{s[-17:]}", s
        return s, s

    def _on_time_tick(self, _pos: float):
        now = time.time()
        if self.isVisible() and (now - self._last_update_ts >= 0.4):
            self._last_update_ts = now
            self.refresh_stats()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_stats()
        if not self.timer.isActive():
            self.timer.start(500)

    def refresh_stats(self):
        if not self.isVisible():
            return
        try:
            stats = self.engine.get_stats()
            if not stats:
                self.live_badge.setText("○ NO MEDIA LOADED")
                self.live_badge.setStyleSheet("""
                    color: #94a3b8;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 3px 8px;
                    background-color: rgba(148, 163, 184, 20);
                    border: 1px solid rgba(148, 163, 184, 40);
                    border-radius: 6px;
                """)
                for lbl in self.val_labels.values():
                    lbl.setText("—")
                    lbl.setToolTip("")
                return

            self._pulse_state = not self._pulse_state
            dot = "●" if self._pulse_state else "◉"
            self.live_badge.setText(f"{dot} LIVE STATS")
            self.live_badge.setStyleSheet("""
                color: #10b981;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 8px;
                background-color: rgba(16, 185, 129, 20);
                border: 1px solid rgba(16, 185, 129, 50);
                border-radius: 6px;
            """)

            for key, val in stats.items():
                if key in self.val_labels:
                    lbl = self.val_labels[key]
                    disp_str, full_str = self._format_display_val(key, str(val))
                    if lbl.text() != disp_str:
                        lbl.setText(disp_str)
                    if full_str != disp_str:
                        lbl.setToolTip(full_str)
                    else:
                        lbl.setToolTip("")
                    lbl.update()
        except Exception:
            pass

    def copy_stats(self):
        stats = self.engine.get_stats()
        if not stats:
            return
        lines = ["=== Vision Player Statistics ==="]
        for k, v in stats.items():
            lines.append(f"{k.replace('_', ' ').title()}: {v}")
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(lines))
