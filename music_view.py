import os
import subprocess
import math
import time
import struct
import random
from PyQt6.QtCore import Qt, QRect, QRectF, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QImage, QPixmap, QRadialGradient,
    QPainterPath, QFont, QFontMetrics
)
from PyQt6.QtWidgets import QWidget
from icons import get_svg_icon

def analyze_beat_map(file_path: str, ffmpeg_path: str) -> list[tuple[float, float, float]]:
    """
    Scans the audio file using local ffmpeg to extract 3 dedicated functional channels:
      Channel 1: Sub-bass & Kicks (<=150Hz) -> BEATS & BASS PUNCH (Task 1)
      Channel 2: Mid-range instruments (160Hz-1200Hz) -> MUSIC, CHORDS & TEMPO (Task 2)
      Channel 3: Vocal presence (1.2kHz-3.5kHz) -> LYRICS & VOCALS (Task 3)
    Returns array of (beat_energy, music_energy, vocal_energy) sampled every 50ms.
    """
    if not os.path.exists(ffmpeg_path) or not os.path.exists(file_path):
        return []

    filter_spec = (
        "[0:a]asplit=3[in1][in2][in3];"
        "[in1]lowpass=f=150,aformat=channel_layouts=mono[beat];"
        "[in2]bandpass=f=600:width_type=h:w=900,aformat=channel_layouts=mono[music];"
        "[in3]bandpass=f=2350:width_type=h:w=2100,aformat=channel_layouts=mono[vocal];"
        "[beat][music][vocal]amerge=inputs=3,aresample=1000"
    )

    cmd = [
        ffmpeg_path,
        "-nostdin",
        "-y",
        "-i", file_path,
        "-vn",
        "-filter_complex", filter_spec,
        "-f", "s16le",
        "-"
    ]
    creation_flags = 0x08000000 if os.name == "nt" else 0
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
            timeout=12.0
        )
        raw_pcm = proc.stdout
        if not raw_pcm:
            return []

        chunk_size = 300
        total_len = len(raw_pcm)
        beat_rms = []
        music_rms = []
        vocal_rms = []

        for i in range(0, total_len, chunk_size):
            chunk = raw_pcm[i:i + chunk_size]
            sample_count = len(chunk) // 2
            if sample_count < 3:
                continue
            samples = struct.unpack(f"<{sample_count}h", chunk[:sample_count * 2])
            
            b_s = samples[0::3]
            m_s = samples[1::3]
            v_s = samples[2::3]

            b_energy = math.sqrt(sum(s * s for s in b_s) / max(1, len(b_s)))
            m_energy = math.sqrt(sum(s * s for s in m_s) / max(1, len(m_s)))
            v_energy = math.sqrt(sum(s * s for s in v_s) / max(1, len(v_s)))

            beat_rms.append(b_energy)
            music_rms.append(m_energy)
            vocal_rms.append(v_energy)

        if not beat_rms:
            return []

        max_b = max(beat_rms) or 1.0
        max_m = max(music_rms) or 1.0
        max_v = max(vocal_rms) or 1.0

        normalized = []
        for b, m, v in zip(beat_rms, music_rms, vocal_rms):
            beat_val = math.pow(b / max_b, 1.45)
            music_val = math.pow(m / max_m, 1.15)
            vocal_val = math.pow(v / max_v, 1.25)
            normalized.append((
                min(1.0, max(0.0, beat_val)),
                min(1.0, max(0.0, music_val)),
                min(1.0, max(0.0, vocal_val))
            ))

        return normalized
    except Exception:
        return []

class BeatScanWorker(QThread):
    beat_map_ready = pyqtSignal(list)

    def __init__(self, file_path: str, ffmpeg_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.ffmpeg_path = ffmpeg_path

    def run(self):
        beat_map = analyze_beat_map(self.file_path, self.ffmpeg_path)
        self.beat_map_ready.emit(beat_map)

def get_heartbeat_scale(phase: float) -> float:
    """
    Returns an expansion factor (0.0 to ~0.16) based on normalized phase [0, 1].
    Simulates the physiological 'lub-dub' dual-pulse curve of a heartbeat.
    """
    if phase < 0.14:
        return math.sin((phase / 0.14) * math.pi) * 0.16
    elif 0.18 < phase < 0.34:
        sub = (phase - 0.18) / 0.16
        return math.sin(sub * math.pi) * 0.08
    return 0.0

def extract_ambient_color(qimage: QImage | None) -> QColor:
    """
    Extracts a dominant vibrant ambient color from a cover image.
    Uses HSV boosting so even dark or desaturated covers produce
    a rich, atmospheric ambient glow.
    """
    if not qimage or qimage.isNull():
        return QColor(59, 130, 246)

    thumb = qimage.scaled(
        16, 16,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    r_tot, g_tot, b_tot = 0, 0, 0
    w, h = thumb.width(), thumb.height()
    for y in range(h):
        for x in range(w):
            c = thumb.pixelColor(x, y)
            r_tot += c.red()
            g_tot += c.green()
            b_tot += c.blue()

    count = max(1, w * h)
    avg_r = int(r_tot / count)
    avg_g = int(g_tot / count)
    avg_b = int(b_tot / count)

    base = QColor(avg_r, avg_g, avg_b)
    h_val, s_val, v_val, _ = base.getHsv()
    if h_val < 0:
        h_val = 215

    s_boosted = max(130, min(255, int(s_val * 1.45)))
    v_boosted = max(160, min(255, int(v_val * 1.35)))
    return QColor.fromHsv(h_val, s_boosted, v_boosted)

def extract_music_info(file_path: str, engine_meta: dict | None, ffmpeg_path: str) -> dict:
    """
    Extracts track title, artist, album, cover art image, and ambient color
    from audio tags and embedded pictures using MPV metadata and ffmpeg.
    """
    meta = engine_meta or {}
    base_name = os.path.splitext(os.path.basename(file_path))[0]

    title = meta.get("title") or meta.get("TITLE") or base_name
    artist = meta.get("artist") or meta.get("ARTIST") or meta.get("album_artist") or ""
    album = meta.get("album") or meta.get("ALBUM") or ""

    cover_image = None

    if os.path.exists(ffmpeg_path):
        try:
            cmd = [
                ffmpeg_path,
                "-nostdin",
                "-y",
                "-i", file_path,
                "-an",
                "-vcodec", "copy",
                "-f", "image2pipe",
                "-"
            ]
            creation_flags = 0x08000000 if os.name == "nt" else 0
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
                timeout=3.0
            )
            if res.stdout and len(res.stdout) > 200:
                img = QImage.fromData(res.stdout)
                if not img.isNull():
                    cover_image = img
        except Exception:
            pass

    if cover_image is None:
        folder = os.path.dirname(os.path.abspath(file_path))
        candidates = ["cover.jpg", "folder.jpg", "cover.png", "front.jpg", "album.jpg", "thumb.jpg"]
        for cand in candidates:
            cand_path = os.path.join(folder, cand)
            if os.path.exists(cand_path):
                img = QImage(cand_path)
                if not img.isNull():
                    cover_image = img
                    break

    color = extract_ambient_color(cover_image)

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "image": cover_image,
        "color": color
    }

class MusicOverlay(QWidget):
    """
    Fullscreen frameless ambient backdrop for audio/music playback.
    Displays dynamic radial ambient glow matching the cover art,
    a high-res rounded cover card, and clean typography.
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

        self.title = ""
        self.artist = ""
        self.album = ""
        self.cover_pixmap = None
        self.blurred_backdrop = None
        self.dot_blurred_backdrop = None
        self._stick_categories = []
        self.ambient_color = QColor(59, 130, 246)
        self.default_music_icon = get_svg_icon("music_note", "#94a3b8", 64)
        self.ambient_mode = "dot"

        self.beat_map = []
        self._target_beat = 0.0
        self._target_inst = 0.0
        self._target_vocal = 0.0
        self._beat_size = 0.0
        self._ambient_opacity = 0.0
        self._vocal_intensity = 0.0

        self._start_time = time.time()
        self.tempo_bpm = 74.0
        self.is_playing = True

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16)
        self.anim_timer.timeout.connect(self._on_tick)

    def set_beat_map(self, beat_map: list):
        self.beat_map = beat_map or []
        self._target_beat = 0.0
        self._target_inst = 0.0
        self._target_vocal = 0.0

    def update_playback_time(self, current_seconds: float):
        if not self.beat_map:
            return
        idx = int(current_seconds / 0.05)
        if 0 <= idx < len(self.beat_map):
            entry = self.beat_map[idx]
            if isinstance(entry, (tuple, list)):
                self._target_beat = float(entry[0]) if len(entry) > 0 else 0.0
                self._target_inst = float(entry[1]) if len(entry) > 1 else 0.0
                self._target_vocal = float(entry[2]) if len(entry) > 2 else self._target_inst
            else:
                val = float(entry)
                self._target_beat = val
                self._target_inst = val
                self._target_vocal = val

    def _on_tick(self):
        if not self.isVisible():
            return
        if not self.is_playing:
            changed = False
            if self._beat_size > 0.005:
                self._beat_size *= 0.88
                changed = True
            if self._ambient_opacity > 0.005:
                self._ambient_opacity *= 0.90
                changed = True
            if self._vocal_intensity > 0.005:
                self._vocal_intensity *= 0.88
                changed = True
            if changed:
                self.update()
            return

        if self.beat_map:
            b_diff = self._target_beat - self._beat_size
            b_rate = 0.48 if b_diff > 0 else 0.22
            self._beat_size += b_diff * b_rate

            m_diff = self._target_inst - self._ambient_opacity
            m_rate = 0.30 if m_diff > 0 else 0.14
            self._ambient_opacity += m_diff * m_rate

            v_diff = self._target_vocal - self._vocal_intensity
            v_rate = 0.42 if v_diff > 0 else 0.20
            self._vocal_intensity += v_diff * v_rate
        else:
            cycle_duration = max(0.25, 60.0 / max(30.0, self.tempo_bpm))
            elapsed = time.time() - self._start_time
            phase = (elapsed % cycle_duration) / cycle_duration
            pulse = get_heartbeat_scale(phase) * 3.5
            self._beat_size = pulse
            self._ambient_opacity = pulse * 0.8
            self._vocal_intensity = pulse * 0.7

        self.update()

    def set_playback_state(self, is_playing: bool):
        self.is_playing = bool(is_playing)
        if not self.is_playing:
            self.update()

    def set_playback_speed(self, speed: float):
        self.tempo_bpm = 74.0 * max(0.4, min(speed, 3.0))

    def showEvent(self, event):
        super().showEvent(event)
        self._start_time = time.time()
        if not self.anim_timer.isActive():
            self.anim_timer.start(16)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.anim_timer.stop()

    def set_ambient_mode(self, mode: str):
        self.ambient_mode = str(mode or "dot").lower()
        self.update()

    def _create_blurred_backdrop(self, img: QImage, downscale_size: int = 32) -> QPixmap | None:
        if not img or img.isNull():
            return None
        try:
            w, h = img.width(), img.height()
            cw, ch = max(10, int(w * 0.75)), max(10, int(h * 0.75))
            cx, cy = (w - cw) // 2, (h - ch) // 2
            cropped = img.copy(cx, cy, cw, ch)

            tiny = cropped.scaled(
                downscale_size, downscale_size,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            soft = tiny.scaled(
                640, 360,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            return QPixmap.fromImage(soft)
        except Exception:
            return None

    def set_track_info(self, info: dict):
        self.title = info.get("title", "Unknown Track")
        self.artist = info.get("artist", "")
        self.album = info.get("album", "")
        self.ambient_color = info.get("color", QColor(59, 130, 246))

        raw_img = info.get("image")
        if raw_img and not raw_img.isNull():
            self.cover_pixmap = QPixmap.fromImage(raw_img)
            self.blurred_backdrop = self._create_blurred_backdrop(raw_img, downscale_size=32)
            self.dot_blurred_backdrop = self._create_blurred_backdrop(raw_img, downscale_size=8)
        else:
            self.cover_pixmap = None
            self.blurred_backdrop = None
            self.dot_blurred_backdrop = None

        track_key = f"{self.title}_{self.artist}_{self.album}"
        seed = 0
        for ch in track_key:
            seed = (seed * 31 + ord(ch)) & 0xFFFFFFFF
        rng = random.Random(seed)
        pool = [0, 0, 0, 1, 1, 1, 2, 2, 3, 3] * 25
        rng.shuffle(pool)
        self._stick_categories = pool

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        cx = w // 2
        cy = int(h * 0.40)

        red = int(self.ambient_color.red())
        green = int(self.ambient_color.green())
        blue = int(self.ambient_color.blue())

        beat_val = max(0.0, min(1.0, float(self._beat_size)))
        inst_val = max(0.0, min(1.0, float(self._ambient_opacity)))
        vocal_val = max(0.0, min(1.0, float(self._vocal_intensity)))

        painter.fillRect(self.rect(), QColor(11, 14, 23, 255))

        max_dim = max(w, h)
        base_art_size = min(300, max(170, int(min(w, h) * 0.44)))
        art_size = base_art_size * (1.0 + beat_val * 0.035)

        if self.ambient_mode == "sticks":
            bar_w = 6.0
            spacing = 5.0
            step = bar_w + spacing
            margin = 32.0
            thumbnail_half = art_size / 2.0
            gap_from_thumb = 28.0

            left_avail = (cx - thumbnail_half - gap_from_thumb) - margin
            right_avail = (w - margin) - (cx + thumbnail_half + gap_from_thumb)

            num_bars_per_side = max(12, int(min(left_avail, right_avail) // step))
            left_start_x = (cx - thumbnail_half - gap_from_thumb) - (num_bars_per_side * step - spacing)
            right_start_x = cx + thumbnail_half + gap_from_thumb

            baseline_y = cy
            max_stick_h = min(190.0, art_size * 0.95)
            min_stick_h = 7.0

            elapsed = time.time() - self._start_time

            sticks_path = QPainterPath()

            def add_stick_column(bx: float, dist_idx: int, progress_from_thumb: float):
                if self._stick_categories:
                    category = self._stick_categories[dist_idx % len(self._stick_categories)]
                else:
                    category = dist_idx % 4

                if category == 0:
                    sub_pulse = math.sin(elapsed * 7.5 + dist_idx * 0.7) * 0.08 * beat_val
                    task_h = 0.15 + beat_val * 0.85 + sub_pulse

                elif category == 1:
                    tempo_freq = (self.tempo_bpm / 60.0) * 3.14
                    tempo_wave = math.sin(elapsed * tempo_freq + dist_idx * 0.5) * 0.5 + 0.5
                    task_h = 0.12 + inst_val * 0.68 + tempo_wave * 0.20

                elif category == 2:
                    vocal_flutter = math.sin(elapsed * 9.5 + dist_idx * 0.9) * 0.5 + 0.5
                    task_h = 0.10 + vocal_val * 0.72 + vocal_flutter * 0.18 * (0.3 + vocal_val * 0.7)

                else:
                    shimmer = math.sin(elapsed * 13.5 + dist_idx * 1.3) * 0.5 + 0.5
                    task_h = 0.08 + (inst_val * 0.45 + beat_val * 0.25) * shimmer

                edge_taper = 1.0 - progress_from_thumb * 0.20
                task_h = task_h * edge_taper

                stick_h = min_stick_h + (max_stick_h - min_stick_h) * min(1.0, max(0.0, task_h))

                by = baseline_y - stick_h / 2.0
                sticks_path.addRoundedRect(QRectF(bx, by, bar_w, stick_h), bar_w / 2.0, bar_w / 2.0)

            for i in range(num_bars_per_side):
                bx = left_start_x + i * step
                dist_idx = num_bars_per_side - 1 - i
                progress = dist_idx / max(1, num_bars_per_side - 1)
                add_stick_column(bx, dist_idx, progress)

            for i in range(num_bars_per_side):
                bx = right_start_x + i * step
                dist_idx = i
                progress = dist_idx / max(1, num_bars_per_side - 1)
                add_stick_column(bx, dist_idx, progress)

            painter.save()
            painter.setClipPath(sticks_path)
            if self.blurred_backdrop:
                painter.drawPixmap(self.rect(), self.blurred_backdrop)
                tint_alpha = min(210, max(45, int(70 + inst_val * 95 + beat_val * 35)))
                painter.fillRect(self.rect(), QColor(red, green, blue, tint_alpha))
            else:
                bar_alpha = min(255, max(50, int(110 + inst_val * 115 + beat_val * 30)))
                painter.fillRect(self.rect(), QColor(red, green, blue, bar_alpha))
            painter.restore()

        else:
            bg_radius = max_dim * (0.36 + beat_val * 0.24)
            dot_path = QPainterPath()
            dot_path.addEllipse(QRectF(cx - bg_radius, cy - bg_radius, bg_radius * 2, bg_radius * 2))

            painter.save()
            painter.setClipPath(dot_path)
            dot_bg = self.dot_blurred_backdrop or self.blurred_backdrop
            if dot_bg:
                painter.drawPixmap(self.rect(), dot_bg)
                bg_glow = QRadialGradient(cx, cy, bg_radius)
                bg_glow.setColorAt(0.0, QColor(0, 0, 0, int(15 + (1.0 - inst_val) * 45)))
                bg_glow.setColorAt(0.45, QColor(0, 0, 0, int(55 + (1.0 - inst_val) * 65)))
                bg_glow.setColorAt(0.80, QColor(11, 14, 23, 205))
                bg_glow.setColorAt(1.0, QColor(11, 14, 23, 255))
                painter.fillRect(self.rect(), bg_glow)
            else:
                bg_alpha = min(255, max(0, int(85 + inst_val * 165)))
                bg_mid = min(255, max(0, int(35 + inst_val * 125)))
                bg_glow = QRadialGradient(cx, cy, bg_radius)
                bg_glow.setColorAt(0.0, QColor(red, green, blue, bg_alpha))
                bg_glow.setColorAt(0.40, QColor(red, green, blue, bg_mid))
                bg_glow.setColorAt(0.75, QColor(15, 20, 32, 235))
                bg_glow.setColorAt(1.0, QColor(11, 14, 23, 255))
                painter.fillRect(self.rect(), bg_glow)
            painter.restore()

            aura_rad = art_size * (0.88 + beat_val * 0.58)
            aura_alpha = min(255, max(0, int(145 + inst_val * 110)))
            aura_mid = min(255, max(0, int(55 + inst_val * 125)))

            aura = QRadialGradient(cx, cy, aura_rad)
            aura.setColorAt(0.0, QColor(red, green, blue, aura_alpha))
            aura.setColorAt(0.48, QColor(red, green, blue, aura_mid))
            aura.setColorAt(1.0, QColor(red, green, blue, 0))
            painter.fillRect(
                QRect(int(cx - aura_rad), int(cy - aura_rad), int(aura_rad * 2), int(aura_rad * 2)),
                aura
            )

        art_rect = QRectF(cx - art_size / 2, cy - art_size / 2, art_size, art_size)
        corner_radius = 18.0
        art_path = QPainterPath()
        art_path.addRoundedRect(art_rect, corner_radius, corner_radius)

        if self.cover_pixmap and not self.cover_pixmap.isNull():
            painter.save()
            painter.setClipPath(art_path)
            scaled_pm = self.cover_pixmap.scaled(
                int(art_size), int(art_size),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            sx = int(cx - art_size / 2 + (art_size - scaled_pm.width()) / 2)
            sy = int(cy - art_size / 2 + (art_size - scaled_pm.height()) / 2)
            painter.drawPixmap(sx, sy, scaled_pm)
            painter.restore()
        else:
            painter.save()
            painter.fillPath(art_path, QColor(24, 30, 46, 210))
            icon_sz = min(72, int(art_size * 0.35))
            ix = int(cx - icon_sz / 2)
            iy = int(cy - icon_sz / 2)
            self.default_music_icon.paint(painter, QRect(ix, iy, icon_sz, icon_sz))
            painter.restore()

        painter.save()
        painter.setPen(QColor(255, 255, 255, 45))
        painter.drawPath(art_path)
        painter.restore()

        text_y = int(cy + art_size / 2 + 28)

        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#ffffff"))
        fm = QFontMetrics(title_font)
        avail_w = max(200, w - 80)
        disp_title = fm.elidedText(self.title, Qt.TextElideMode.ElideRight, avail_w)
        painter.drawText(
            QRect(int((w - avail_w) / 2), text_y, avail_w, 30),
            Qt.AlignmentFlag.AlignCenter,
            disp_title
        )

        sub_text = self.artist
        if self.album:
            sub_text = f"{self.artist} — {self.album}" if self.artist else self.album

        if sub_text:
            sub_font = QFont("Segoe UI", 12, QFont.Weight.DemiBold)
            painter.setFont(sub_font)
            painter.setPen(QColor("#94a3b8"))
            sub_fm = QFontMetrics(sub_font)
            disp_sub = sub_fm.elidedText(sub_text, Qt.TextElideMode.ElideRight, avail_w)
            painter.drawText(
                QRect(int((w - avail_w) / 2), text_y + 32, avail_w, 24),
                Qt.AlignmentFlag.AlignCenter,
                disp_sub
            )

