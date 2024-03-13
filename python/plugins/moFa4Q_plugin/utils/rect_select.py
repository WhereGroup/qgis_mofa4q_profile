from qgis.PyQt.QtGui import QColor
from qgis.core import (QgsPointXY, QgsRectangle, QgsWkbTypes, QgsGeometry,
                       QgsFeature, QgsVectorLayer)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand, QgsMapToolIdentify, QgsHighlight
from PyQt5.QtCore import Qt

from .select_dialog import SelectDialog


class RectSelect(QgsMapToolEmitPoint):
    """
    /***************************************************************************
    Defines the functionalities to select an extent (rectangle) for feature identification
    and highlight selected features
    based on https://github.com/qgis/QGIS/blob/master/python/plugins/processing/gui/RectangleMapTool.py
    ***************************************************************************/
    """
    STROKE_COLOR=QColor(255,150,0,255)
    FILL_COLOR=QColor(255,150,0,127)
    STROKE_WIDTH=3
    ICON_SIZE=25

    startPoint = None
    isEmittingPoint = None
    endPoint = None
    selectDialog = None
    highlights = []

    def __init__(self, iface):
        """ Initiate a Maptool to draw a rubber band with polygon-properties on the map """
        self.iface = iface
        self.canvas = iface.mapCanvas()
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.rubberBandDraw = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBandDraw.setColor(self.STROKE_COLOR)
        self.rubberBandDraw.setWidth(self.STROKE_WIDTH)
        self.rubberBandDraw.setIconSize(self.ICON_SIZE)
        self.rubberBandDraw.setFillColor(self.FILL_COLOR)
        self.identityG = QgsMapToolIdentify(self.canvas)
        self.reset()

    def reset(self):
        """ Clears all """
        self.resetSelect()
        self.resetHighlights()

    def resetSelect(self):
        """ Clears canvas from previous rectangle """
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBandDraw.reset(QgsWkbTypes.PolygonGeometry)

    def resetHighlights(self):
        for highlight in self.highlights:
            highlight.hide()
        self.highlights = []

    def canvasPressEvent(self, e):
        """ Overrides, on mouse down a rectangle will be drawn """
        # print("canvasPressEvent ")
        self.resetHighlights()
        if self.rectangle() is not None:
            self.resetSelect()
        self.startPoint = self.toMapCoordinates(e.pos())
        self.endPoint = self.startPoint
        self.isEmittingPoint = True
        self.showRect(self.startPoint, self.endPoint)

    def canvasReleaseEvent(self, e):
        """ Overrides, on mouse release new vertices are drawn and appended to the rubber band """
        self.isEmittingPoint = False
        if self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
            # print("===>> for one point only", self.endPoint.x(), self.endPoint.y())
            pointGeo = QgsGeometry.fromWkt("POINT({} {})".format(self.endPoint.x(), self.endPoint.y()))
            results = self.identityG.identify(pointGeo, self.identityG.TopDownAll, self.identityG.VectorLayer)
            self.openDialog(results)
            self.resetSelect()
            return

        if self.rectangle() is not None:
            # print(self.rectangle())
            results = self.identityG.identify(QgsGeometry.fromRect(self.rectangle()), self.identityG.TopDownAll,
                                              self.identityG.VectorLayer)
            self.openDialog(results)
            self.resetSelect()

    def canvasMoveEvent(self, e):
        """ Overrides, on mouse move """
        if not self.isEmittingPoint:
            return

        self.endPoint = self.toMapCoordinates(e.pos())
        self.showRect(self.startPoint, self.endPoint)

    def showRect(self, startPoint, endPoint):
        self.rubberBandDraw.reset(QgsWkbTypes.PolygonGeometry)

        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPoint.x(), endPoint.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(endPoint.x(), startPoint.y())

        self.rubberBandDraw.addPoint(point1, False)
        self.rubberBandDraw.addPoint(point2, False)
        self.rubberBandDraw.addPoint(point3, False)
        # True to update canvas
        self.rubberBandDraw.addPoint(point4, True)
        self.rubberBandDraw.show()

    def rectangle(self):
        if self.startPoint is None or self.endPoint is None:
            return None
        elif self.startPoint.x() == self.endPoint.x() or \
                self.startPoint.y() == self.endPoint.y():
            return None

        return QgsRectangle(self.startPoint, self.endPoint)

    def openDialog(self, results):
        # print("results", results)
        if len(results) == 1:
            self.iface.openFeatureForm(results[0].mLayer, QgsFeature(results[0].mFeature), True)
            self.highlightSelFeatures(results)
        elif len(results) > 1:
            self.selectDialog = SelectDialog(self.iface)
            self.selectDialog.show(results)
            self.selectDialog.dialogSygnal.connect(self.resetAndHighlightSelFeature)
            if len(results) < self.selectDialog.MAX_FEATURE:
                self.highlightSelFeatures(results)

    def highlightSelFeatures(self, results):
        # print("result", results)
        for result in results:
            self.highlightSelFeature(result)
    
    def resetAndHighlightSelFeature(self, result):
        self.resetHighlights()
        self.highlightSelFeature(result)

    def highlightSelFeature(self, result):
        highlight = QgsHighlight(self.canvas, result.mFeature, result.mLayer)
        highlight.setColor(QColor(Qt.yellow))
        # highlight.setBuffer(20.5)
        # highlight.setWidth(10000)
        # highlight.setMinWidth(333.)
        highlight.setFillColor(QColor(Qt.yellow))
        # color.setAlpha(50)
        # highlight.setFillColor(color)
        self.highlights.append(highlight)
        highlight.show()
        # self.canvas.refresh()
