
import locale
import os

from PyQt5.QtWidgets import QWidget
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QDialog, QHeaderView, QTableWidgetItem
from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsDistanceArea, QgsGeometry, QgsProject, QgsWkbTypes)
from qgis.core import QgsPointXY
from qgis.gui import QgisInterface, QgsMapMouseEvent
from qgis.gui import QgsMapTool, QgsRubberBand

from .tr import tr

epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")


class MeasureTool(QgsMapTool):
    """Based on Shapetool (https://plugins.qgis.org/plugins/shapetools/)"""

    def __init__(self, iface: QgisInterface, parent: QWidget, isArea=False):
        QgsMapTool.__init__(self, iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.measureDialog = MeasureDialog(iface, parent, isArea)
        self.vertex = None
        locale.setlocale(locale.LC_ALL, "")

    def activate(self):
        """When activated set the cursor to a crosshair."""
        self.canvas.setCursor(Qt.CrossCursor)
        self.measureDialog.show()

    def close(self):
        """Close the geodesic measure tool dialog box."""
        self.removeVertexMarker()
        if self.measureDialog.isVisible():
            self.measureDialog.closeDialog()

    def endInteractiveLine(self):
        if self.measureDialog.isVisible():
            self.measureDialog.endRubberband()

    def canvasPressEvent(self, event: QgsMapMouseEvent):
        """ Capture the coordinates when the user click on the mouse for measurements."""
        # print("canvasPressEvent!")
        self.removeVertexMarker()
        pt = self.snapPoint(event.originalPixelPoint())
        button = event.button()
        canvasCRS = self.canvas.mapSettings().destinationCrs()
        if canvasCRS != epsg4326:
            transform = QgsCoordinateTransform(canvasCRS, epsg4326, QgsProject.instance())
            pt = transform.transform(pt.x(), pt.y())
        self.measureDialog.addPoint(pt, button)
        if button == 2:
            self.measureDialog.stop()

    def canvasMoveEvent(self, event: QgsMapMouseEvent):
        """Captures the coordinate as the user moves the mouse over the canvas."""
        if self.measureDialog.ready():
            pt = self.snapPoint(event.originalPixelPoint())
        if self.measureDialog.motionReady():
            try:
                canvasCRS = self.canvas.mapSettings().destinationCrs()
                if canvasCRS != epsg4326:
                    transform = QgsCoordinateTransform(canvasCRS, epsg4326, QgsProject.instance())
                    pt = transform.transform(pt.x(), pt.y())
                self.measureDialog.inMotion(pt)
            except Exception:
                return

    def snapPoint(self, qpoint: QgsPointXY):
        match = self.canvas.snappingUtils().snapToMap(qpoint)
        if match.isValid():
            self.vertex.setCenter(match.point())
            return (match.point())  # Returns QgsPointXY
        else:
            self.removeVertexMarker()
            return self.toMapCoordinates(qpoint)  # QPoint input, returns QgsPointXY

    def removeVertexMarker(self):
        if self.vertex is not None:
            self.canvas.scene().removeItem(self.vertex)
            self.vertex = None


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '../components/measure_dialog.ui'))


class MeasureDialog(QDialog, FORM_CLASS):
    ICON_SIZE = 10
    STROKE_WIDTH = 3
    STROKE_COLOR = QColor(222, 167, 67, 255)
    FILL_COLOR = QColor(222, 167, 67, 100)
    TEMP_STROKE_COLOR = QColor(222, 167, 67, 255)
    TEMP_FILL_COLOR = QColor(170, 255, 128, 100)
    polygonPoint = []

    def __init__(self, iface, parent, isArea):
        super(MeasureDialog, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.isArea = isArea

        self.btnClose.clicked.connect(self.closeDialog)
        self.btnReset.clicked.connect(self.resetDialog)

        if isArea:
            self.tableWidget.setVisible(False)
            self.setFixedHeight(100)
            self.label.setText(tr("Gesamtfläche"))
        else:
            self.setFixedHeight(325)
            self.tableWidget.setColumnCount(1)
            self.tableWidget.setSortingEnabled(False)
            self.tableWidget.setHorizontalHeaderLabels([tr('Segmente [Meter]')])
            self.tableWidget.setShowGrid(False)
            verticalHeader = self.tableWidget.verticalHeader()
            verticalHeader.setVisible(False)
            verticalHeader.setSectionResizeMode(QHeaderView.Fixed)
            verticalHeader.setDefaultSectionSize(20)

        self.capturedPoints = []
        self.distances = []
        self.activeMeasuring = True
        self.lastMotionPt = None
        self.currentDistance = 0.0

        self.pointRb = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.pointRb.setColor(self.STROKE_COLOR)
        self.pointRb.setIconSize(self.ICON_SIZE)

        self.geomRb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry if isArea else QgsWkbTypes.LineGeometry)
        self.geomRb.setColor(self.STROKE_COLOR)
        self.geomRb.setWidth(self.STROKE_WIDTH)

        self.tempRb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry if isArea else QgsWkbTypes.LineGeometry)
        self.tempRb.setColor(self.TEMP_STROKE_COLOR)
        self.tempRb.setWidth(1)

        if isArea:
            self.geomRb.setFillColor(QColor(self.FILL_COLOR))
            self.tempRb.setFillColor(QColor(self.TEMP_FILL_COLOR))

    def ready(self):
        return self.activeMeasuring

    def stop(self):
        self.activeMeasuring = False
        self.lastMotionPt = None
        self.tempRb.reset(QgsWkbTypes.PolygonGeometry if self.isArea else QgsWkbTypes.LineGeometry)

    def closeEvent(self, event):
        self.closeDialog()

    def closeDialog(self):
        self.clear()
        self.close()
        self.iface.actionPan().trigger()

    def resetDialog(self):
        self.clear()

    def motionReady(self):
        if len(self.capturedPoints) > 0 and self.activeMeasuring:
            return True
        return False

    def addPoint(self, pt, button):
        #print("call method addPoint")
        self.currentDistance = 0
        index = len(self.capturedPoints)
        if index > 0 and pt == self.capturedPoints[index - 1]:
            # the clicked point is the same as the previous so just ignore it
            return
        self.capturedPoints.append(pt)
        # Add rubber band points
        canvasCrs = self.canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(epsg4326, canvasCrs, QgsProject.instance())
        ptCanvas = transform.transform(pt.x(), pt.y())
        self.pointRb.addPoint(ptCanvas, True)
        # If there is more than 1 captured point add it to the table
        if index > 0:
            # self.saveToLayerButton.setEnabled(True)
            (distance, startAngle, endAngle) = self.calcParameters(
                self.capturedPoints[index - 1], self.capturedPoints[index])
            self.distances.append(distance)
            self.insertParams(index, distance, startAngle, endAngle)
            # Add Rubber Band Line
            linePts = self.getLinePts(self.capturedPoints[index - 1], self.capturedPoints[index])

            if not self.isArea:
                self.geomRb.addGeometry(QgsGeometry.fromPolylineXY(linePts), None)
            else:
                if self.geomRb.numberOfVertices() == 0:
                    self.geomRb.addGeometry(QgsGeometry.fromPolylineXY(linePts), None)
                else:
                    self.geomRb.addPoint(linePts[1])

        self.formatTotal()

    def endRubberband(self):
        index = len(self.capturedPoints)
        if index <= 0:
            return
        if index == 1:
            self.newDialog()
            return
        if self.motionReady():
            if self.lastMotionPt is not None:
                self.lastMotionPt = None
                self.tempRb.reset(QgsWkbTypes.PolygonGeometry if self.isArea else QgsWkbTypes.LineGeometry)
                self.tableWidget.setRowCount(self.tableWidget.rowCount() - 1)
        self.stop()
        self.currentDistance = 0
        self.formatTotal()

    def inMotion(self, pt):
        index = len(self.capturedPoints)
        if index <= 0:
            return
        (self.currentDistance, startAngle, endAngle) = self.calcParameters(self.capturedPoints[index - 1], pt)
        self.insertParams(index, self.currentDistance, startAngle, endAngle)
        # self.formatTotal()
        linePts = self.getLinePts(self.capturedPoints[index - 1], pt)
        self.lastMotionPt = pt

        if not self.isArea:
            self.tempRb.setToGeometry(QgsGeometry.fromPolylineXY(linePts), None)
        else:
            if self.geomRb.numberOfVertices() == 0:
                self.polygonPoint = linePts[0]
                self.tempRb.setToGeometry(QgsGeometry.fromPolylineXY(linePts), None)
            else:
                self.tempRb.reset(QgsWkbTypes.PolygonGeometry)
                self.tempRb.addGeometry(QgsGeometry.fromPolylineXY([self.polygonPoint, linePts[0], linePts[1]]), None)

    def calcParameters(self, pt1, pt2):
        """Calculation of the distance. Instead of using the implementation of the plugin (below in the comment),
        the standard functionalities of QGIS has been used."""

        """
        gline = geod.Inverse(pt1.y(), pt1.x(), pt2.y(), pt2.x())
        az2 = (gline['azi2'] + 180) % 360.0
        if az2 > 180:
            az2 = az2 - 360.0
        az1 = gline['azi1']

        # Check to see if the azimuth values should be in the range or 0 to 360
        # The default is -180 to 180
        if settings.mtAzMode:
            if az1 < 0:
                az1 += 360.0
            if az2 < 0:
                az2 += 360
        print("Original implementation", gline['s12'], az1, az2)
        """

        distance = QgsDistanceArea()
        distance.setEllipsoid('WGS84')
        m = distance.measureLine(pt1, pt2)
        #print("new implementation: ", m)
        return (m, None, None)

    def getLinePts(self, pt1, pt2):
        canvasCrs = self.canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(epsg4326, canvasCrs, QgsProject.instance())
        pt1c = transform.transform(pt1.x(), pt1.y())
        pt2c = transform.transform(pt2.x(), pt2.y())
        return [pt1c, pt2c]

    def insertParams(self, position, distance, startAngle, endAngle):
        if position > self.tableWidget.rowCount():
            self.tableWidget.insertRow(position - 1)
        # item = QTableWidgetItem('{:.4f}'.format(distance))
        item = QTableWidgetItem(locale.format("%.1f", distance, grouping=True))

        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignRight)
        self.tableWidget.setItem(position - 1, 0, item)

    def formatTotal(self):
        if not self.isArea:
            total = self.currentDistance
            ptcnt = len(self.capturedPoints)
            if ptcnt >= 2:
                i = 0
                while i < ptcnt - 1:
                    total += self.distances[i]
                    i += 1
            self.distanceLineEdit.setText(self.unitTotDistance(total))
        else:
            self.distanceLineEdit.setText(self.unitTotArea(self.geomRb.asGeometry().area()))

    def clear(self):
        self.tableWidget.setRowCount(0)
        self.capturedPoints = []
        self.distances = []
        self.activeMeasuring = True
        self.currentDistance = 0.0
        self.distanceLineEdit.setText('')
        self.pointRb.reset(QgsWkbTypes.PointGeometry)
        self.geomRb.reset(QgsWkbTypes.PolygonGeometry if self.isArea else QgsWkbTypes.LineGeometry)
        self.tempRb.reset(QgsWkbTypes.PolygonGeometry if self.isArea else QgsWkbTypes.LineGeometry)

    def unitTotDistance(self, distance):
        if distance > 1000:  # kilometers
            return locale.format("%.2f", distance / 1000.0, grouping=True) + " km"
        else:  # meters
            return locale.format("%.1f", distance, grouping=True) + " m"

    def unitTotArea(self, area):
        #print("area", area)
        if area == -1.0:
            return ''
        else:  # meters
            return locale.format("%.1f", area, grouping=True) + ' m²'
