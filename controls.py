from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QComboBox
)
from icons import get_svg_icon
from style import MODERN_STYLE

class ClickableSlider(QSlider):
    """
    Precision slider allowing direct jump-to-position on mouse click
    and continuous live scrubbing without default pageStep jumps.
    """
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self._pos_to_val(event.position().x())
            self.setValue(val)
            self.sliderPressed.emit()
            self.sliderMoved.emit(val)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            val = self._pos_to_val(event.position().x())
            self.setValue(val)
            self.sliderMoved.emit(val)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.sliderReleased.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _pos_to_val(self, x: float) -> int:
        w = self.width()
        if w <= 0:
            return 0
        ratio = max(0.0, min(1.0, x / w))
        return int(self.minimum() + ratio * (self.maximum() - self.minimum()))

class PlayerControls(QWidget):
    play_toggled = pyqtSignal()
    seek_requested = pyqtSignal(float)
    scrub_started = pyqtSignal()
    scrub_requested = pyqtSignal(float)
    speed_changed = pyqtSignal(float)
    audio_track_changed = pyqtSignal(int)
    skip_requested = pyqtSignal(float)
    prev_requested = pyqtSignal()
    next_requested = pyqtSignal()
    playlist_requested = pyqtSignal()
    fullscreen_toggled = pyqtSignal()
    open_file_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(MODERN_STYLE)

        self.is_seeking = False
        self.total_duration = 0.0

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.dock = QWidget(self)
        self.dock.setObjectName("controlDock")
        self.dock.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer_layout.addWidget(self.dock)

        root = QVBoxLayout(self.dock)
        root.setContentsMargins(18, 10, 18, 12)
        root.setSpacing(6)

        seek_row = QHBoxLayout()
        seek_row.setSpacing(10)

        self.cur_time_lbl = QLabel("00:00", self.dock)
        self.cur_time_lbl.setProperty("role", "timeLabel")
        seek_row.addWidget(self.cur_time_lbl)

        self.slider = ClickableSlider(Qt.Orientation.Horizontal, self.dock)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(self._on_slider_pressed)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.slider.sliderReleased.connect(self._on_slider_released)
        seek_row.addWidget(self.slider, stretch=1)

        self.total_time_lbl = QLabel("00:00", self.dock)
        self.total_time_lbl.setProperty("role", "timeLabel")
        seek_row.addWidget(self.total_time_lbl)

        root.addLayout(seek_row)

        deck_row = QHBoxLayout()
        deck_row.setSpacing(12)

        self.btn_open = QPushButton(self.dock)
        self.btn_open.setProperty("role", "iconBtn")
        self.btn_open.setIcon(get_svg_icon("folder", "#cbd5e1", 18))
        self.btn_open.setIconSize(QSize(18, 18))
        self.btn_open.setToolTip("Open Media File (Ctrl+O)")
        self.btn_open.clicked.connect(self.open_file_requested.emit)
        deck_row.addWidget(self.btn_open)

        self.btn_open_folder = QPushButton(self.dock)
        self.btn_open_folder.setProperty("role", "iconBtn")
        self.btn_open_folder.setIcon(get_svg_icon("folder_open", "#cbd5e1", 18))
        self.btn_open_folder.setIconSize(QSize(18, 18))
        self.btn_open_folder.setToolTip("Open Folder (Ctrl+Shift+O)")
        self.btn_open_folder.clicked.connect(self.open_folder_requested.emit)
        deck_row.addWidget(self.btn_open_folder)

        self.btn_playlist = QPushButton(self.dock)
        self.btn_playlist.setProperty("role", "iconBtn")
        self.btn_playlist.setIcon(get_svg_icon("playlist", "#cbd5e1", 18))
        self.btn_playlist.setIconSize(QSize(18, 18))
        self.btn_playlist.setToolTip("Media Playlist (Ctrl+L)")
        self.btn_playlist.clicked.connect(self.playlist_requested.emit)
        deck_row.addWidget(self.btn_playlist)

        lbl_audio_icon = QLabel(self.dock)
        lbl_audio_icon.setStyleSheet("background: transparent;")
        lbl_audio_icon.setPixmap(get_svg_icon("audio", "#94a3b8", 16).pixmap(16, 16))
        deck_row.addWidget(lbl_audio_icon)

        self.audio_combo = QComboBox(self.dock)
        self.audio_combo.setToolTip("Audio Track (A)")
        self.audio_combo.addItem("No Audio", 1)
        self.audio_combo.currentIndexChanged.connect(self._on_audio_track_changed)
        deck_row.addWidget(self.audio_combo)

        deck_row.addStretch(1)

        self.btn_prev = QPushButton(self.dock)
        self.btn_prev.setProperty("role", "iconBtn")
        self.btn_prev.setIcon(get_svg_icon("prev", "#e2e8f0", 20))
        self.btn_prev.setIconSize(QSize(20, 20))
        self.btn_prev.setToolTip("Previous Track (Ctrl+Left)")
        self.btn_prev.clicked.connect(self.prev_requested.emit)
        deck_row.addWidget(self.btn_prev)

        self.btn_rewind = QPushButton(self.dock)
        self.btn_rewind.setProperty("role", "iconBtn")
        self.btn_rewind.setIcon(get_svg_icon("replay_10", "#e2e8f0", 22))
        self.btn_rewind.setIconSize(QSize(22, 22))
        self.btn_rewind.setToolTip("Rewind 10s (Left Arrow)")
        self.btn_rewind.clicked.connect(lambda: self.skip_requested.emit(-10.0))
        deck_row.addWidget(self.btn_rewind)

        self.btn_play = QPushButton(self.dock)
        self.btn_play.setObjectName("heroPlayBtn")
        self.btn_play.setIcon(get_svg_icon("play", "#090a0f", 20))
        self.btn_play.setIconSize(QSize(20, 20))
        self.btn_play.setToolTip("Play / Pause (Space)")
        self.btn_play.clicked.connect(self.play_toggled.emit)
        deck_row.addWidget(self.btn_play)

        self.btn_forward = QPushButton(self.dock)
        self.btn_forward.setProperty("role", "iconBtn")
        self.btn_forward.setIcon(get_svg_icon("forward_10", "#e2e8f0", 22))
        self.btn_forward.setIconSize(QSize(22, 22))
        self.btn_forward.setToolTip("Skip 10s (Right Arrow)")
        self.btn_forward.clicked.connect(lambda: self.skip_requested.emit(10.0))
        deck_row.addWidget(self.btn_forward)

        self.btn_next = QPushButton(self.dock)
        self.btn_next.setProperty("role", "iconBtn")
        self.btn_next.setIcon(get_svg_icon("next", "#e2e8f0", 20))
        self.btn_next.setIconSize(QSize(20, 20))
        self.btn_next.setToolTip("Next Track (Ctrl+Right)")
        self.btn_next.clicked.connect(self.next_requested.emit)
        deck_row.addWidget(self.btn_next)

        deck_row.addStretch(1)

        lbl_speed_icon = QLabel(self.dock)
        lbl_speed_icon.setStyleSheet("background: transparent;")
        lbl_speed_icon.setPixmap(get_svg_icon("speed", "#94a3b8", 16).pixmap(16, 16))
        deck_row.addWidget(lbl_speed_icon)

        self.speed_combo = QComboBox(self.dock)
        self.speed_combo.setToolTip("Playback Speed ([ and ])")
        self.speed_values = [0.3, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
        for val in self.speed_values:
            self.speed_combo.addItem(f"{val}x", val)
        self.speed_combo.setCurrentIndex(self.speed_values.index(1.0))
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        deck_row.addWidget(self.speed_combo)

        self.btn_fullscreen = QPushButton(self.dock)
        self.btn_fullscreen.setProperty("role", "iconBtn")
        self.btn_fullscreen.setIcon(get_svg_icon("fullscreen", "#cbd5e1", 18))
        self.btn_fullscreen.setIconSize(QSize(18, 18))
        self.btn_fullscreen.setToolTip("Fullscreen (F)")
        self.btn_fullscreen.clicked.connect(self.fullscreen_toggled.emit)
        deck_row.addWidget(self.btn_fullscreen)

        root.addLayout(deck_row)

    def set_playback_state(self, is_playing: bool):
        icon_name = "pause" if is_playing else "play"
        self.btn_play.setIcon(get_svg_icon(icon_name, "#090a0f", 20))

    def set_fullscreen_icon(self, is_fullscreen: bool):
        icon_name = "minimize" if is_fullscreen else "fullscreen"
        self.btn_fullscreen.setIcon(get_svg_icon(icon_name, "#cbd5e1", 18))

    def populate_audio_tracks(self, tracks: list):
        self.audio_combo.blockSignals(True)
        self.audio_combo.clear()
        for t in tracks:
            self.audio_combo.addItem(t["label"], t["id"])
        self.audio_combo.blockSignals(False)

    def set_active_audio_track(self, track_id: int):
        """Syncs the HUD dropdown display to the active MPV audio track ID."""
        self.audio_combo.blockSignals(True)
        for i in range(self.audio_combo.count()):
            if self.audio_combo.itemData(i) == track_id:
                self.audio_combo.setCurrentIndex(i)
                break
        self.audio_combo.blockSignals(False)
        self.audio_combo.update()

    def _on_audio_track_changed(self, idx):
        track_id = self.audio_combo.currentData()
        if track_id is not None:
            self.audio_track_changed.emit(int(track_id))

    def set_duration(self, duration: float):
        self.total_duration = duration
        self.total_time_lbl.setText(self.format_time(duration))

    def update_timestamp(self, current: float):
        if not self.is_seeking and self.total_duration > 0:
            val = int((current / self.total_duration) * 1000)
            self.slider.blockSignals(True)
            self.slider.setValue(val)
            self.slider.blockSignals(False)
        self.cur_time_lbl.setText(self.format_time(current))

    def _on_speed_changed(self, idx):
        self.speed_changed.emit(self.speed_values[idx])

    def change_speed_step(self, delta: int):
        new_idx = max(0, min(self.speed_combo.currentIndex() + delta, len(self.speed_values) - 1))
        self.speed_combo.setCurrentIndex(new_idx)

    def cycle_audio_track(self):
        count = self.audio_combo.count()
        if count > 1:
            next_idx = (self.audio_combo.currentIndex() + 1) % count
            self.audio_combo.setCurrentIndex(next_idx)

    def _on_slider_pressed(self):
        self.is_seeking = True
        self.scrub_started.emit()

    def _on_slider_moved(self, val):
        if self.total_duration > 0:
            preview_sec = (val / 1000.0) * self.total_duration
            self.cur_time_lbl.setText(self.format_time(preview_sec))
            self.scrub_requested.emit(preview_sec)

    def _on_slider_released(self):
        if self.total_duration > 0:
            target_sec = (self.slider.value() / 1000.0) * self.total_duration
            self.seek_requested.emit(target_sec)
        self.is_seeking = False

    @staticmethod
    def format_time(seconds: float) -> str:
        s = int(max(0, seconds))
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
