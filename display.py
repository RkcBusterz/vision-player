from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QWidget

class VideoDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.setStyleSheet("background-color: #000000; border-radius: 8px;")

    def update_frame(self, frame_bytes: bytes, width: int, height: int):
        self.image = QImage(frame_bytes, width, height, width * 3, QImage.Format.Format_RGB888)
        self.update()

    def clear(self):
        self.image = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.image:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            scaled = self.image.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)
        else:
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
