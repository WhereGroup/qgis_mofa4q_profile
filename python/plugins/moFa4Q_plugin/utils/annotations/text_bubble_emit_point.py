from PyQt5.QtCore import pyqtSignal, Qt
from qgis._gui import QgsMapMouseEvent
from qgis.core import QgsPointXY
from qgis.gui import QgsMapToolEmitPoint


class TextBubbleEmitPoint(QgsMapToolEmitPoint):
    """Extend of QgsMapToolEmitPoint to add a text annotation (with or without text bubble)"""

    pointCompletedSignal = pyqtSignal(QgsPointXY)

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        QgsMapToolEmitPoint.__init__(self, self.canvas)

    def close(self):
        """Necessary to simulate the close the tool"""
        pass

    def canvasPressEvent(self, event: QgsMapMouseEvent):
        """Overrides, on mouse down a rectangle will be drawn

        Args:
           event: click event
        """
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            y = event.pos().y()

            # clicked position on screen to map coordinates
            point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
            self.pointCompletedSignal.emit(point)
