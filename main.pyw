import sys
import os
import time
script_dir = os.path.dirname(os.path.abspath(__file__))
if hasattr(os, "add_dll_directory"):
    try:
        os.add_dll_directory(script_dir)
    except Exception:
        pass
os.environ["PATH"] = script_dir + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QAction, QKeySequence, QActionGroup, QCursor, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox
)

from style import MODERN_STYLE
from controls import PlayerControls
from engine import MPVEngine
from indicator import SeekIndicator
from player_info import PlayerInfoDialog
from music_view import MusicOverlay, extract_music_info, BeatScanWorker
from media_list_dialog import MediaListDialog
from app_state import load_app_state, save_app_state

class MainPlayerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vision Player")
        self.logo_path = os.path.join(script_dir, "logo.png")
        if os.path.exists(self.logo_path):
            self.setWindowIcon(QIcon(self.logo_path))
        self.resize(1100, 660)
        self.setStyleSheet(MODERN_STYLE)
        self.setAcceptDrops(True)

        self.video_surface = QWidget(self)
        self.video_surface.setStyleSheet("background-color: #000000;")
        self.video_surface.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)
        self.video_surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setCentralWidget(self.video_surface)

        self.engine = MPVEngine(int(self.video_surface.winId()))

        self.controls = PlayerControls(self)
        self.controls.setFixedHeight(84)

        self._was_playing_before_scrub = False
        self._last_scrub_time = 0.0

        self.rewind_indicator = SeekIndicator(self)
        self.skip_indicator = SeekIndicator(self)

        self.ffmpeg_path = os.path.join(script_dir, "ffmpeg.exe")
        self.AUDIO_EXTENSIONS = {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.alac', '.aiff'}
        self.ALL_MEDIA_EXTENSIONS = {
            '.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.ts',
            '.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.alac', '.aiff'
        }
        self.music_overlay = MusicOverlay(self)
        self.beat_worker = None

        saved_state = load_app_state()
        self.playlist = []
        self.playlist_index = -1
        self.media_list_dialog = None
        self.current_memory_mode = saved_state.get("memory_mode", "medium")
        self.mem_action_group = None
        self.current_ambient_mode = saved_state.get("ambient_mode", "dot")
        self.ambient_action_group = None

        self.resume_where_left = bool(saved_state.get("resume_where_left", False))
        self.open_in_fullscreen = bool(saved_state.get("open_in_fullscreen", False))
        self.autoplay_on_open = bool(saved_state.get("autoplay_on_open", True))
        self.file_positions = saved_state.get("file_positions", {})

        self.audio_menu = None
        self.audio_action_group = None
        self.subtitle_menu = None
        self.subtitle_action_group = None
        self.settings_menu = None
        self.more_menu = None
        self.info_dialog = None
        self._build_menu()

        self.last_cursor_pos = QCursor.pos()
        self.idle_ticks = 0
        self.cursor_hidden = False

        self.mouse_watch_timer = QTimer(self)
        self.mouse_watch_timer.setInterval(150)
        self.mouse_watch_timer.timeout.connect(self._check_mouse_activity)
        self.mouse_watch_timer.start()

        self.engine.signals.time_updated.connect(self.controls.update_timestamp)
        self.engine.signals.time_updated.connect(self.music_overlay.update_playback_time)
        self.engine.signals.duration_changed.connect(self.controls.set_duration)
        self.engine.signals.playback_state_changed.connect(self.controls.set_playback_state)
        self.engine.signals.playback_state_changed.connect(self.music_overlay.set_playback_state)
        self.engine.signals.audio_tracks_found.connect(self.on_audio_tracks_loaded)
        self.engine.signals.audio_track_changed.connect(self.on_active_audio_track_changed)
        self.engine.signals.subtitle_tracks_found.connect(self.on_subtitle_tracks_loaded)
        self.engine.signals.subtitle_track_changed.connect(self.on_active_subtitle_track_changed)
        self.engine.signals.playback_ended.connect(self.on_playback_ended)

        self.controls.play_toggled.connect(self.on_play_toggle)
        self.controls.scrub_started.connect(self.on_scrub_start)
        self.controls.scrub_requested.connect(self.on_scrub_frame)
        self.controls.seek_requested.connect(self.on_seek_finished)
        self.controls.speed_changed.connect(self.engine.set_speed)
        self.controls.speed_changed.connect(self.music_overlay.set_playback_speed)
        self.controls.audio_track_changed.connect(self.engine.set_audio_track)
        self.controls.skip_requested.connect(self.on_skip_relative)
        self.controls.prev_requested.connect(self.play_previous_track)
        self.controls.next_requested.connect(self.play_next_track)
        self.controls.playlist_requested.connect(self.open_media_list_dialog)
        self.controls.fullscreen_toggled.connect(self.toggle_fullscreen)
        self.controls.open_file_requested.connect(self.open_file_dialog)
        self.controls.open_folder_requested.connect(self.open_folder_dialog)

        QTimer.singleShot(150, self._restore_saved_state)

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        open_action = QAction("&Open File...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        open_folder_action = QAction("Open &Folder...", self)
        open_folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_folder_action.triggered.connect(self.open_folder_dialog)
        file_menu.addAction(open_folder_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.audio_menu = menubar.addMenu("&Audio")
        no_track = QAction("No media loaded", self)
        no_track.setEnabled(False)
        self.audio_menu.addAction(no_track)

        self.subtitle_menu = menubar.addMenu("&Subtitles")
        self._setup_empty_subtitle_menu()

        self.settings_menu = menubar.addMenu("&Settings")

        self.resume_action = QAction("Play Where Left Off", self, checkable=True)
        self.resume_action.setChecked(self.resume_where_left)
        self.resume_action.setToolTip("Resume video and music playback from the last watched position")
        self.resume_action.triggered.connect(self._on_toggle_resume_where_left)
        self.settings_menu.addAction(self.resume_action)

        self.fs_action = QAction("Open in Fullscreen", self, checkable=True)
        self.fs_action.setChecked(self.open_in_fullscreen)
        self.fs_action.setToolTip("Launch the player directly into fullscreen mode")
        self.fs_action.triggered.connect(self._on_toggle_open_in_fullscreen)
        self.settings_menu.addAction(self.fs_action)

        self.autoplay_action = QAction("Play on Opening", self, checkable=True)
        self.autoplay_action.setChecked(self.autoplay_on_open)
        self.autoplay_action.setToolTip("Automatically begin playback as soon as media is opened")
        self.autoplay_action.triggered.connect(self._on_toggle_autoplay_on_open)
        self.settings_menu.addAction(self.autoplay_action)

        self.more_menu = menubar.addMenu("&More")

        playlist_action = QAction("&List Media / Playlist...", self)
        playlist_action.setShortcut(QKeySequence("Ctrl+L"))
        playlist_action.triggered.connect(self.open_media_list_dialog)
        self.more_menu.addAction(playlist_action)

        info_action = QAction("&Player Info & Stream Stats", self)
        info_action.setShortcut(QKeySequence("Ctrl+I"))
        info_action.triggered.connect(self.open_player_info)
        self.more_menu.addAction(info_action)

        mem_menu = self.more_menu.addMenu("&Memory Mode")
        self.mem_action_group = QActionGroup(self)
        self.mem_action_group.setExclusive(True)

        mem_options = [
            ("Low (0 – 200 MB)", "low", "Minimal RAM; instant packet cleanup; low buffering"),
            ("Medium (0 – 400 MB)", "medium", "Balanced smooth scrubbing and pre-buffering"),
            ("High (0 – 800 MB)", "high", "Heavy forward & backward caching (Recommended 16GB+ RAM)")
        ]
        for title, key, desc in mem_options:
            act = QAction(title, self, checkable=True)
            act.setData(key)
            act.setToolTip(desc)
            if key == "medium":
                act.setChecked(True)
            act.triggered.connect(lambda checked, m=key: self.set_memory_mode(m))
            self.mem_action_group.addAction(act)
            mem_menu.addAction(act)

        ambient_menu = self.more_menu.addMenu("Audio &Ambient Mode")
        self.ambient_action_group = QActionGroup(self)
        self.ambient_action_group.setExclusive(True)

        amb_options = [
            ("Dot (Radial Ambient)", "dot", "Atmospheric circular ambient aura and radial glow"),
            ("Sticks (Spectrum Bars)", "sticks", "Dynamic rhythm equalizer sticks across the viewport")
        ]
        for title, key, desc in amb_options:
            act = QAction(title, self, checkable=True)
            act.setData(key)
            act.setToolTip(desc)
            if key == "dot":
                act.setChecked(True)
            act.triggered.connect(lambda checked, mode=key: self.set_ambient_mode(mode))
            self.ambient_action_group.addAction(act)
            ambient_menu.addAction(act)

        fs_action = QAction("Toggle &Fullscreen", self)
        fs_action.setShortcut(QKeySequence("F"))
        fs_action.triggered.connect(self.toggle_fullscreen)
        self.more_menu.addAction(fs_action)

    def _setup_empty_subtitle_menu(self):
        self.subtitle_menu.clear()
        no_sub = QAction("No media loaded", self)
        no_sub.setEnabled(False)
        self.subtitle_menu.addAction(no_sub)

        self.subtitle_menu.addSeparator()
        add_ext = QAction("&Add External Subtitle File...", self)
        add_ext.setShortcut(QKeySequence("Ctrl+Shift+S"))
        add_ext.triggered.connect(self.open_subtitle_dialog)
        self.subtitle_menu.addAction(add_ext)

    def sync_dock_geometry(self):
        """Pins the floating control dock neatly to the bottom center of the video viewport."""
        if not self.isVisible():
            return
        surf_global = self.video_surface.mapToGlobal(QPoint(0, 0))
        sw = self.video_surface.width()
        sh = self.video_surface.height()

        dock_w = min(max(int(sw * 0.78), 540), 860)
        dock_h = 84
        dock_x = surf_global.x() + (sw - dock_w) // 2
        dock_y = surf_global.y() + sh - dock_h - 24

        self.controls.setGeometry(dock_x, dock_y, dock_w, dock_h)

        if hasattr(self, 'music_overlay') and self.music_overlay.isVisible():
            self.music_overlay.setGeometry(surf_global.x(), surf_global.y(), sw, sh)
            self.controls.raise_()

        ind_size = 100
        ind_y = surf_global.y() + (sh - ind_size) // 2
        if self.rewind_indicator.isVisible():
            self.rewind_indicator.move(surf_global.x() + int(sw * 0.20) - (ind_size // 2), ind_y)
        if self.skip_indicator.isVisible():
            self.skip_indicator.move(surf_global.x() + int(sw * 0.80) - (ind_size // 2), ind_y)

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_dock_geometry()
        self.controls.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sync_dock_geometry()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.sync_dock_geometry()

    def _check_mouse_activity(self):
        """Detects mouse motion over the Direct3D window and auto-hides after 3 seconds."""
        if not self.isActiveWindow() and not self.controls.isActiveWindow():
            return

        pos = QCursor.pos()
        if pos != self.last_cursor_pos:
            self.last_cursor_pos = pos
            self.idle_ticks = 0
            self.show_hud()
        else:
            if self.controls.underMouse() or self.controls.is_seeking:
                self.idle_ticks = 0
                return

            self.idle_ticks += 1
            if self.idle_ticks >= 20 and self.engine.current_file:
                self.hide_hud()

    def show_hud(self):
        if not self.controls.isVisible():
            self.sync_dock_geometry()
            self.controls.show()
        if not self.isFullScreen():
            self.menuBar().show()
        if self.cursor_hidden:
            QApplication.restoreOverrideCursor()
            self.cursor_hidden = False

    def hide_hud(self):
        if self.controls.isVisible():
            self.controls.hide()
        if self.isFullScreen():
            self.menuBar().hide()
            if not self.cursor_hidden:
                QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
                self.cursor_hidden = True

    def on_audio_tracks_loaded(self, tracks: list):
        self.controls.populate_audio_tracks(tracks)
        self.audio_menu.clear()
        self.audio_action_group = QActionGroup(self)
        self.audio_action_group.setExclusive(True)

        for idx, track in enumerate(tracks):
            track_id = track["id"]
            action = QAction(track["label"], self, checkable=True)
            action.setData(track_id)
            if idx == 0:
                action.setChecked(True)
            action.triggered.connect(lambda checked, tid=track_id: self.engine.set_audio_track(tid))
            self.audio_action_group.addAction(action)
            self.audio_menu.addAction(action)

    def on_active_audio_track_changed(self, track_id: int):
        self.controls.set_active_audio_track(track_id)

        if self.audio_action_group:
            for action in self.audio_action_group.actions():
                if action.data() == track_id:
                    action.setChecked(True)
                    break

    def on_subtitle_tracks_loaded(self, tracks: list):
        self.subtitle_menu.clear()
        self.subtitle_action_group = QActionGroup(self)
        self.subtitle_action_group.setExclusive(True)

        off_action = QAction("Off (Disable Subtitles)", self, checkable=True)
        off_action.setData(None)
        off_action.triggered.connect(lambda: self.engine.set_subtitle_track('no'))
        self.subtitle_action_group.addAction(off_action)
        self.subtitle_menu.addAction(off_action)
        self.subtitle_menu.addSeparator()

        if tracks:
            for track in tracks:
                sub_id = track["id"]
                action = QAction(track["label"], self, checkable=True)
                action.setData(sub_id)
                action.triggered.connect(lambda checked, sid=sub_id: self.engine.set_subtitle_track(sid))
                self.subtitle_action_group.addAction(action)
                self.subtitle_menu.addAction(action)
        else:
            none_avail = QAction("No embedded subtitles", self)
            none_avail.setEnabled(False)
            self.subtitle_menu.addAction(none_avail)

        self.subtitle_menu.addSeparator()
        add_ext = QAction("&Add External Subtitle File...", self)
        add_ext.setShortcut(QKeySequence("Ctrl+Shift+S"))
        add_ext.triggered.connect(self.open_subtitle_dialog)
        self.subtitle_menu.addAction(add_ext)

        self.subtitle_menu.addSeparator()
        sub_delay_minus = QAction("Subtitle Delay -0.1s", self)
        sub_delay_minus.setShortcut(QKeySequence("Z"))
        sub_delay_minus.triggered.connect(lambda: self.engine.adjust_sub_delay(-0.1))
        self.subtitle_menu.addAction(sub_delay_minus)

        sub_delay_plus = QAction("Subtitle Delay +0.1s", self)
        sub_delay_plus.setShortcut(QKeySequence("X"))
        sub_delay_plus.triggered.connect(lambda: self.engine.adjust_sub_delay(0.1))
        self.subtitle_menu.addAction(sub_delay_plus)

        sub_delay_reset = QAction("Reset Subtitle Delay (0.0s)", self)
        sub_delay_reset.triggered.connect(self.engine.reset_sub_delay)
        self.subtitle_menu.addAction(sub_delay_reset)

    def on_active_subtitle_track_changed(self, track_id):
        if not self.subtitle_action_group:
            return
        for action in self.subtitle_action_group.actions():
            if action.data() == track_id:
                action.setChecked(True)
                return
        for action in self.subtitle_action_group.actions():
            if action.data() is None:
                action.setChecked(True)
                break

    def open_subtitle_dialog(self):
        if not self.engine.current_file:
            self.open_file_dialog()
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Subtitle File", "",
            "Subtitle Files (*.srt *.ass *.ssa *.vtt *.sub *.idx);;All Files (*)"
        )
        if path:
            self.engine.add_subtitle_file(path)
            self.show_hud()

    def open_player_info(self):
        if self.info_dialog is None:
            self.info_dialog = PlayerInfoDialog(self.engine, self)
        self.info_dialog.refresh_stats()
        if not self.info_dialog.timer.isActive():
            self.info_dialog.timer.start(500)
        self.info_dialog.show()
        self.info_dialog.raise_()
        self.info_dialog.activateWindow()

    def _on_toggle_resume_where_left(self, checked: bool):
        self.resume_where_left = bool(checked)
        self._save_current_state()

    def _on_toggle_open_in_fullscreen(self, checked: bool):
        self.open_in_fullscreen = bool(checked)
        self._save_current_state()

    def _on_toggle_autoplay_on_open(self, checked: bool):
        self.autoplay_on_open = bool(checked)
        self._save_current_state()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
            self.controls.set_fullscreen_icon(False)
        else:
            self.showFullScreen()
            self.menuBar().hide()
            self.controls.set_fullscreen_icon(True)
        QTimer.singleShot(50, self.sync_dock_geometry)
        self.show_hud()

    def open_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder with Media")
        if folder:
            media_files = []
            for root, dirs, files in os.walk(folder):
                for f in sorted(files):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in self.ALL_MEDIA_EXTENSIONS:
                        media_files.append(os.path.join(root, f))
                break

            if media_files:
                self.playlist = media_files
                self.play_track_at_index(0)
                if self.media_list_dialog and self.media_list_dialog.isVisible():
                    self.media_list_dialog.update_playlist(self.playlist, self.playlist_index)

    def open_media_list_dialog(self):
        if self.media_list_dialog is None:
            self.media_list_dialog = MediaListDialog(self)
            self.media_list_dialog.track_selected.connect(self.play_track_at_index)
        self.media_list_dialog.update_playlist(self.playlist, self.playlist_index)
        self.media_list_dialog.show()
        self.media_list_dialog.raise_()
        self.media_list_dialog.activateWindow()

    def play_track_at_index(self, index: int):
        if not self.playlist:
            return
        if 0 <= index < len(self.playlist):
            self.playlist_index = index
            target_path = self.playlist[index]
            self.load_video(target_path)
            if self.media_list_dialog:
                self.media_list_dialog.set_current_index(index)
            self._save_current_state()

    def play_next_track(self):
        if not self.playlist:
            return
        next_idx = self.playlist_index + 1
        if next_idx < len(self.playlist):
            self.play_track_at_index(next_idx)
        else:
            self.play_track_at_index(0)

    def play_previous_track(self):
        if not self.playlist:
            return
        prev_idx = self.playlist_index - 1
        if prev_idx >= 0:
            self.play_track_at_index(prev_idx)
        else:
            self.play_track_at_index(len(self.playlist) - 1)

    def set_memory_mode(self, mode: str, prompt_warning: bool = True):
        mode = (mode or "medium").lower()
        if mode == "high" and prompt_warning:
            reply = QMessageBox.warning(
                self,
                "High Memory Mode Warning",
                "High Memory Mode pre-renders and caches up to 800 MB in RAM for instantaneous forward and backward seeks.\n\n"
                "⚠️ Recommended System Memory: Minimum 16 GB RAM.\n\n"
                "Enable High Memory Mode?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.sync_memory_mode_ui(self.current_memory_mode)
                return

        self.current_memory_mode = mode
        self.engine.set_memory_mode(mode)
        self.sync_memory_mode_ui(mode)
        self._save_current_state()

    def sync_memory_mode_ui(self, mode: str):
        if self.mem_action_group:
            for act in self.mem_action_group.actions():
                if act.data() == mode:
                    act.setChecked(True)
                    break

    def set_ambient_mode(self, mode: str):
        mode = str(mode or "dot").lower()
        self.current_ambient_mode = mode
        self.music_overlay.set_ambient_mode(mode)
        self.sync_ambient_mode_ui(mode)
        self._save_current_state()

    def sync_ambient_mode_ui(self, mode: str):
        if self.ambient_action_group:
            for act in self.ambient_action_group.actions():
                if act.data() == mode:
                    act.setChecked(True)
                    break

    def on_playback_ended(self):
        self.controls.set_playback_state(False)
        self.music_overlay.set_playback_state(False)
        if self.playlist and len(self.playlist) > 1 and self.playlist_index + 1 < len(self.playlist):
            QTimer.singleShot(500, self.play_next_track)

    def _save_current_state(self):
        if self.resume_where_left:
            cur_file = self.engine.current_file
            cur_time = 0.0
        else:
            cur_file = None
            cur_time = 0.0
        try:
            cur_time = float(getattr(self.engine.player, 'time_pos', 0.0) or 0.0)
        except Exception:
            pass
        if cur_file and cur_time > 1.0:
            self.file_positions[cur_file] = round(cur_time, 2)
        save_app_state(
            cur_file, cur_time, self.playlist, self.playlist_index,
            self.current_memory_mode, self.current_ambient_mode,
            self.resume_where_left, self.open_in_fullscreen, self.autoplay_on_open,
            self.file_positions
        )

    def _restore_saved_state(self):
        state = load_app_state()
        last_file = state.get("last_file")
        last_time = state.get("last_timestamp", 0.0)
        saved_playlist = state.get("playlist", [])
        saved_idx = state.get("playlist_index", 0)
        saved_mem = state.get("memory_mode", "medium")
        saved_amb = state.get("ambient_mode", "dot")

        if self.open_in_fullscreen and not self.isFullScreen():
            QTimer.singleShot(100, self.toggle_fullscreen)

        if saved_mem in ("low", "medium", "high"):
            self.set_memory_mode(saved_mem, prompt_warning=False)

        if saved_amb in ("dot", "sticks"):
            self.set_ambient_mode(saved_amb)

        if saved_playlist:
            valid_list = [p for p in saved_playlist if os.path.exists(p)]
            if valid_list:
                self.playlist = valid_list
                self.playlist_index = min(saved_idx, len(self.playlist) - 1)

        if last_file and os.path.exists(last_file):
            if last_file not in self.playlist:
                self.playlist = [last_file]
                self.playlist_index = 0
            else:
                self.playlist_index = self.playlist.index(last_file)

            self.load_video(last_file)
            if self.resume_where_left and last_time > 1.0:
                QTimer.singleShot(350, lambda: self.engine.seek(last_time, exact=True))

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Media", "",
            "All Media Files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.ts *.mp3 *.flac *.m4a *.aac *.ogg *.opus *.wav *.wma);;Music Files (*.mp3 *.flac *.m4a *.aac *.ogg *.opus *.wav *.wma);;Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.ts);;All Files (*)"
        )
        if path:
            folder = os.path.dirname(os.path.abspath(path))
            sibling_media = []
            try:
                for f in sorted(os.listdir(folder)):
                    full = os.path.join(folder, f)
                    if os.path.isfile(full):
                        ext = os.path.splitext(f)[1].lower()
                        if ext in self.ALL_MEDIA_EXTENSIONS:
                            sibling_media.append(full)
            except Exception:
                sibling_media = [path]

            self.playlist = sibling_media if sibling_media else [path]
            try:
                self.playlist_index = self.playlist.index(path)
            except ValueError:
                self.playlist_index = 0

            self.load_video(path)
            if self.media_list_dialog and self.media_list_dialog.isVisible():
                self.media_list_dialog.update_playlist(self.playlist, self.playlist_index)
            self._save_current_state()

    def load_video(self, path: str, autoplay: bool | None = None):
        auto = self.autoplay_on_open if autoplay is None else autoplay
        self.engine.load_file(path, autoplay=auto)
        self.setWindowTitle(f"Vision Player — {os.path.basename(path)}")

        if self.resume_where_left:
            saved_time = self.file_positions.get(path, 0.0)
            if saved_time > 2.0:
                QTimer.singleShot(350, lambda: self.engine.seek(saved_time, exact=True))

        ext = os.path.splitext(path)[1].lower()
        if ext in self.AUDIO_EXTENSIONS:
            surf_global = self.video_surface.mapToGlobal(QPoint(0, 0))
            self.music_overlay.setGeometry(
                surf_global.x(), surf_global.y(),
                self.video_surface.width(), self.video_surface.height()
            )
            meta = getattr(self.engine.player, 'metadata', None)
            info = extract_music_info(path, meta, self.ffmpeg_path)
            self.music_overlay.set_track_info(info)
            self.music_overlay.show()
            self.controls.raise_()

            if self.beat_worker and self.beat_worker.isRunning():
                self.beat_worker.terminate()
                self.beat_worker.wait()
            self.music_overlay.set_beat_map([])
            self.beat_worker = BeatScanWorker(path, self.ffmpeg_path, self)
            self.beat_worker.beat_map_ready.connect(self.music_overlay.set_beat_map)
            self.beat_worker.start()
        else:
            if self.beat_worker and self.beat_worker.isRunning():
                self.beat_worker.terminate()
                self.beat_worker.wait()
            self.music_overlay.set_beat_map([])
            self.music_overlay.hide()

        self._save_current_state()
        self.show_hud()

    def on_play_toggle(self):
        if not self.engine.current_file:
            self.open_file_dialog()
            return
        self.engine.toggle_play()
        self.show_hud()

    def on_scrub_start(self):
        if self.engine.current_file:
            self._was_playing_before_scrub = not bool(self.engine.player.pause)
            if self._was_playing_before_scrub:
                self.engine.player.pause = True

    def on_scrub_frame(self, target_sec: float):
        if not self.engine.current_file:
            return
        now = time.time()
        if now - self._last_scrub_time >= 0.03:
            self._last_scrub_time = now
            self.engine.seek(target_sec, exact=True)

    def on_seek_finished(self, target_sec: float):
        if not self.engine.current_file:
            return
        self.engine.seek(target_sec, exact=True)
        if self._was_playing_before_scrub:
            self.engine.player.pause = False
            self._was_playing_before_scrub = False

    def on_skip_relative(self, delta: float):
        if not self.engine.current_file:
            return
        self.engine.seek_relative(delta)
        self.show_seek_indicator(delta)
        self.show_hud()

    def show_seek_indicator(self, delta: float):
        if not self.isVisible():
            return
        surf_global = self.video_surface.mapToGlobal(QPoint(0, 0))
        sw = self.video_surface.width()
        sh = self.video_surface.height()

        ind_size = 100
        y = surf_global.y() + (sh - ind_size) // 2

        if delta < 0:
            x = surf_global.x() + int(sw * 0.20) - (ind_size // 2)
            self.rewind_indicator.flash("replay_10", x, y)
        else:
            x = surf_global.x() + int(sw * 0.80) - (ind_size // 2)
            self.skip_indicator.flash("forward_10", x, y)

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key.Key_Space:
            self.on_play_toggle()
        elif key == Qt.Key.Key_Right:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.play_next_track()
            else:
                self.on_skip_relative(10.0)
        elif key == Qt.Key.Key_Left:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.play_previous_track()
            else:
                self.on_skip_relative(-10.0)
        elif key == Qt.Key.Key_N:
            self.play_next_track()
        elif key == Qt.Key.Key_P:
            self.play_previous_track()
        elif key == Qt.Key.Key_L:
            self.open_media_list_dialog()
        elif key == Qt.Key.Key_BracketRight:
            self.controls.change_speed_step(1)
            self.show_hud()
        elif key == Qt.Key.Key_BracketLeft:
            self.controls.change_speed_step(-1)
            self.show_hud()
        elif key == Qt.Key.Key_A:
            self.controls.cycle_audio_track()
            self.show_hud()
        elif key == Qt.Key.Key_S:
            if self.subtitle_action_group:
                actions = self.subtitle_action_group.actions()
                if len(actions) > 1:
                    cur_idx = 0
                    for i, a in enumerate(actions):
                        if a.isChecked():
                            cur_idx = i
                            break
                    next_action = actions[(cur_idx + 1) % len(actions)]
                    next_action.trigger()
                    self.show_hud()
        elif key == Qt.Key.Key_I:
            self.open_player_info()
        elif key == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif key == Qt.Key.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.toggle_fullscreen()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                self.load_video(file_path)
                break

    def closeEvent(self, event):
        self._save_current_state()
        self.mouse_watch_timer.stop()
        if self.beat_worker and self.beat_worker.isRunning():
            self.beat_worker.terminate()
            self.beat_worker.wait()
        if self.media_list_dialog:
            self.media_list_dialog.close()
        self.controls.close()
        self.music_overlay.close()
        self.rewind_indicator.close()
        self.skip_indicator.close()
        if self.info_dialog:
            self.info_dialog.close()
        if self.cursor_hidden:
            QApplication.restoreOverrideCursor()
        self.engine.terminate()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainPlayerWindow()
    window.show()
    sys.exit(app.exec())
