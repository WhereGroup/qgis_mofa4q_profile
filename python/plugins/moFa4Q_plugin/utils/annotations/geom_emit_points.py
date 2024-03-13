from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from qgis.core import QgsPointXY, QgsWkbTypes
from qgis.gui import QgisInterface
from qgis.gui import QgsMapToolEmitPoint
from qgis.gui import QgsRubberBand, QgsMapToolIdentify, QgsMapMouseEvent


class GeomEmitPoints(QgsMapToolEmitPoint):
    STROKE_COLOR = QColor(255, 150, 0, 255)
    FILL_COLOR = QColor(255, 150, 0, 127)
    STROKE_WIDTH = 3
    ICON_SIZE = 25
    completedSignal = pyqtSignal(list)
    def __init__(self, iface: QgisInterface, isPolygon: bool = False):
        self.iface = iface
        self.isPolygon = isPolygon
        self.canvas = iface.mapCanvas()
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.starEditing: bool = False
        self.rubberBandDraw = QgsRubberBand(self.canvas,
                                            QgsWkbTypes.PolygonGeometry if isPolygon else QgsWkbTypes.LineGeometry)
        self.rubberBandDraw.setColor(self.STROKE_COLOR)
        self.rubberBandDraw.setWidth(self.STROKE_WIDTH)
        self.rubberBandDraw.setIconSize(self.ICON_SIZE)
        self.rubberBandDraw.setFillColor(self.FILL_COLOR)
        self.identityG = QgsMapToolIdentify(self.canvas)
        self.points = []

    def reset(self):
        self.rubberBandDraw.reset(QgsWkbTypes.PolygonGeometry if self.isPolygon else QgsWkbTypes.LineGeometry)

    # private methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def close(self):
        """Necessary to simulate the close the tool"""
        pass

    def canvasDoubleClickEvent(self, event: QgsMapMouseEvent):
        # print('canvasDoubleClickEvent')
        self.completedSignal.emit(self.points)
        self.points = []
        self.starEditing = False

    def canvasMoveEvent(self, event: QgsMapMouseEvent) -> None:
        if not self.starEditing:
            return
        x = event.pos().x()
        y = event.pos().y()
        point: QgsPointXY = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
        self.rubberBandDraw.removeLastPoint()
        self.rubberBandDraw.addPoint(point, True)
        self.rubberBandDraw.show()

    def canvasPressEvent(self, event: QgsMapMouseEvent) -> None:
        """Overrides, on mouse down a rectangle will be drawn"""
        # if event.button() == Qt. if event.type() == QEvent.MouseButtonDblClick::
        # print('event.type()', event.type())
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            y = event.pos().y()
            self.starEditing = True

            # clicked position on screen to map coordinates
            point: QgsPointXY = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)

            # print(f"point", point)
            self.points.append(point)
            self.rubberBandDraw.addPoint(point, True)
            self.rubberBandDraw.show()
            self.canvas.refresh()
            # print(f"self.points", self.points)
