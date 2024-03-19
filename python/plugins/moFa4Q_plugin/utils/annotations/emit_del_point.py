from PyQt5.QtCore import pyqtSignal, Qt
from qgis.core import QgsPointXY
from qgis.gui import QgsMapToolEmitPoint, QgsMapMouseEvent


class EmitDelPoint(QgsMapToolEmitPoint):
    completedSignal = pyqtSignal(float, float, QgsPointXY)

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        QgsMapToolEmitPoint.__init__(self, self.canvas)

    def close(self):
        self.iface.actionPan().trigger()

    def canvasReleaseEvent(self, event: QgsMapMouseEvent) -> None:
        """Overrides, on mouse down a rectangle will be drawn"""
        if event.button() == Qt.LeftButton:
            xPixel: float = event.pos().x()
            yPixel: float = event.pos().y()
            point: QgsPointXY = self.canvas.getCoordinateTransform().toMapCoordinates(xPixel, yPixel)
            self.completedSignal.emit(xPixel, yPixel, point)
