from typing import Optional

from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient, QPaintEvent
from PyQt6.QtCore import Qt, QPointF, pyqtSlot, QObject

# noinspection PyPep8Naming
class Led(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.setFixedSize(24, 24)
        self._on: bool = False
        self._light_color = QColor.fromRgbF(255, 0, 0)
        self._glow_effect = QGraphicsDropShadowEffect()
        self._glow_effect.setBlurRadius(48)
        self._glow_effect.setColor(self._light_color.lighter(150))
        self._glow_effect.setOffset(0, 0)
        self._glow_effect.setEnabled(self._on)
        self.setGraphicsEffect(self._glow_effect)
        self._parent: Optional[QObject] = None
        first_parent: Optional[QObject] = self.parent()
        if isinstance(first_parent, QWidget):
            self._parent = first_parent.parent()


    def isOn(self) -> bool:
        return self._on

    @pyqtSlot(bool)
    def setOn(self, on: bool) -> None:
        self._on = on
        self._glow_effect.setEnabled(self._on)
        self.update()

    def getLightColor(self) -> QColor:
        return self._light_color

    @pyqtSlot(QColor)
    def setLightColor(self, color: QColor) -> None:
        self._light_color = color
        self._glow_effect.setColor(self._light_color.lighter(150))
        self.update()

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        led_color = self._light_color if self._on else QColor(Qt.GlobalColor.darkGray)

        # defining a radial gradient to render the LED color and simulate a clear ambient reflection on its surface
        radius = self.width() / 2.0
        radial_gradient = QRadialGradient(QPointF(radius, radius), radius - 1, QPointF(radius, radius / 2.0))
        radial_gradient.setColorAt(0, led_color.lighter(300))
        radial_gradient.setColorAt(0.5, led_color)
        radial_gradient.setColorAt(1, led_color.darker(200))

        # set Pen for the outline and Brush for the filling
        painter.setPen(QPen(Qt.GlobalColor.gray, 2))
        painter.setBrush(radial_gradient)

        # draws the gray outline with a single directive and fills the circular area of the LED with the gradient
        painter.drawEllipse(QPointF(radius, radius), radius - 1, radius - 1)
