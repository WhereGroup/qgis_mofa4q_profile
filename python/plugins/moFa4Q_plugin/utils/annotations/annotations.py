# -*- coding: utf-8 -*-
import os
from functools import partial
from typing import Dict, List, Union

from PyQt5.QtCore import QCoreApplication, QObject, QPointF, QSizeF, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QTextDocument
from PyQt5.QtWidgets import QAction, QApplication, QMessageBox, QPushButton
from qgis.core import QgsLineSymbol, QgsCurvePolygon, QgsAnnotationPolygonItem, QgsFillSymbol, \
    QgsMarkerSymbol, QgsAnnotationItem, QgsProject, QgsTextAnnotation, QgsPointXY, QgsAnnotationLineItem, QgsGeometry, \
    QgsLineString, QgsAnnotationLayer, QgsAnnotationManager, QgsLayerTree, QgsLayerTreeLayer, QgsTextFormat
from qgis.gui import QgsMapCanvas, QgisInterface

import yaml

from .custom_bubble_text_annotation import CustomBubbleTextAnnotation
from .custom_point_text_annotation import CustomPointTextAnnotation
from .dialog_for_geom import DialogForGeom
from .dialog_for_text_bubble import DialogForTextBubble
from .emit_del_point import EmitDelPoint
from .geom_emit_points import GeomEmitPoints
from .text_bubble_emit_point import TextBubbleEmitPoint
from ...components.btn_tool_map import BtnToolMap


class Annotations(QObject):
    """Handles the customization of annotations of QGIS"""

    TEXT_BUBBLE_WIDTH = 210
    TEXT_BUBBLE_HEIGHT = 1080
    TEXT_BUBBLE_OFFSET = 6
    TEXT_BUBBLE_OPACITY = 0.65
    TEXT_SIZE_PX = 17

    updateToggleToolsSignal = pyqtSignal(str)
    # updateAnnotationSignal = pyqtSignal(str)

    def __init__(self, iface: QgisInterface, mapButtons: Dict[str, BtnToolMap], pluginDir: str, prjConfig: any):
        super().__init__()
        self.iface = iface
        self.canvas: QgsMapCanvas = iface.mapCanvas()
        self.mapButtons = mapButtons
        self.pluginDir = pluginDir
        self.mActionPan: QAction = iface.mainWindow().findChild(QAction, 'mActionPan')

        self.mapButtons['textPopup'] = BtnToolMap('textPopup', 'text_bubble.png', QPushButton(),
                                                  self._addStartTextBubble, False)
        self.mapButtons['textPopup'].isAnnotation = True

        self.mapButtons['delTextPopup'] = BtnToolMap('delTextPopup', 'del_text_bubble.png', QPushButton(),
                                                     self._delTextBubble, True)
        self.mapButtons['delTextPopup'].isAnnotation = True

        self.mapButtons['lineEdit'] = BtnToolMap('lineEdit', 'line_edit.png', QPushButton(), self._addStartLine, False)
        self.mapButtons['lineEdit'].isAnnotation = True

        self.mapButtons['polygonEdit'] = BtnToolMap('polygonEdit', 'polygon_edit.png', QPushButton(),
                                                    self._addStartPolygon, False)
        self.mapButtons['polygonEdit'].isAnnotation = True

        self.mapButtons['delGeom'] = BtnToolMap('delGeom', 'del_geom.png', QPushButton(),
                                                self._delGeom, True)
        self.mapButtons['delGeom'].isAnnotation = True

        self.annotationManager: QgsAnnotationManager = QgsProject.instance().annotationManager()
        self.annotationLayer = QgsAnnotationLayer('custom_annotations', QgsAnnotationLayer.LayerOptions(
            QgsProject.instance().transformContext()))
        QgsProject.instance().addMapLayer(self.annotationLayer, False)
        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        root.insertLayer(0, self.annotationLayer)

        self._readAnnotations()

        self.isVisible: bool = True
        if 'annotations' in prjConfig:
            config = prjConfig['annotations']
            if config and 'isVisible' in config:
                self.isVisible = config['isVisible']
                if not self.isVisible:
                    self.setAnnotationsVisibility(False)

        QTimer.singleShot(50, self._refreshFrame4TextAnnotation)

    # public methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def setAnnotationsVisibility(self, isVisible) -> None:
        """
        Manages visibility of annotations from layer tree

        Args:
            isVisible: set the visibility
        """
        self.isVisible = isVisible
        annotationManager: QgsAnnotationManager = QgsProject.instance().annotationManager()
        annotation: QgsTextAnnotation
        for annotation in annotationManager.annotations():
            annotation.setVisible(isVisible)

        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        for childItem in root.children():
            # print(childItem, type(childItem))
            if type(childItem) == QgsLayerTreeLayer and type(childItem.layer()) == QgsAnnotationLayer:
                # annotationLayer: QgsAnnotationLayer = childItem.layer()
                childItem.setItemVisibilityChecked(isVisible)

        self._setBtnsVisibility(isVisible)
        self.canvas.refresh()

    def delAllAnnotations(self) -> None:
        """Removes of all annotations and clear the annotation yaml file"""
        self.reset()

        self.canvas.refresh()
        self._writeAnnotations()

    def reset(self) -> None:
        """Removes of all annotations. For text annotation it is not possible to user method clear, it does always
        remove all annotations
        """
        annotation: QgsTextAnnotation
        for annotation in self.annotationManager.annotations():
            self.annotationManager.removeAnnotation(annotation)

        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        for childItem in root.children():
            # print(childItem, type(childItem))
            if type(childItem) == QgsLayerTreeLayer and type(childItem.layer()) == QgsAnnotationLayer:
                childItem.layer().clear()

    # private methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _addStartTextBubble(self) -> None:
        self.updateToggleToolsSignal.emit('textPopup')
        mapTool = self.mapButtons['textPopup']
        if not mapTool.tool:
            mapTool.tool = TextBubbleEmitPoint(self.iface)
            mapTool.tool.pointCompletedSignal.connect(self._textBubblePointCompleted)
        self.canvas.setMapTool(mapTool.tool)

    def _textBubblePointCompleted(self, qgsPointXY: QgsPointXY) -> None:
        # print('_textBubblePointCompleted', qgsPointXY)
        self.qgsPointXY = qgsPointXY
        mapTool = self.mapButtons['textPopup']
        if not mapTool.additionalTool:
            mapTool.additionalTool = DialogForTextBubble(self.iface, self.iface.mainWindow())
            # mapTool.additionalTool.completedSignal.connect(partial(self._textBubbleCompleted, qgsPointXY))
            mapTool.additionalTool.completedSignal.connect(self._textBubbleDialogCompleted)
        mapTool.additionalTool.show()

    def _textBubbleDialogCompleted(self, txtMsg: str, color: str, isBubble: bool) -> None:
        # print("_textBubbleDialogCompleted", txtMsg)
        self.iface.actionPan().trigger()
        if txtMsg and txtMsg != '':
            if isBubble:
                self.annotationManager.addAnnotation(self._getNewBubbleTextAnnotation(txtMsg, color, self.qgsPointXY))
            else:
                self.annotationLayer.addItem(self._getNewPointTextAnnotation(txtMsg, color, self.qgsPointXY))
            self.canvas.refresh()
            self._writeAnnotations()
            QTimer.singleShot(50, self._refreshFrame4TextAnnotation)

        self.iface.actionPan().trigger()

    def _getNewBubbleTextAnnotation(self, txtMsg: str, color: str, qgsPointXY: QgsPointXY):
        # print('txtMsg', txtMsg, color)
        textAnnotation = CustomBubbleTextAnnotation(txtMsg, color)
        lines: List[str] = txtMsg.splitlines()
        formatLines = ''.join([f'{line}<br/>' for line in lines])
        textDocument = QTextDocument()
        textDocument.setDocumentMargin(10)
        font = QFont()
        font.setPixelSize(self.TEXT_SIZE_PX)
        textDocument.setDefaultFont(font)
        textDocument.documentLayout().documentSizeChanged.connect(
            partial(self._onDocumentLayoutUpdated, textDocument, textAnnotation))

        textDocument.setHtml(f'<p style=""><font color="{color}">{formatLines}</font></p>')
        textAnnotation.setDocument(textDocument)

        # self._retrieveMmSize(textDocument)

        # method setFrameSize() does not work properly, therefore the measurement of frame are given in mm!
        # mmDim = self._convertPxToMM(QSizeF(1920, 1080))
        mmDim = self._convertPxToMM(QSizeF(self.TEXT_BUBBLE_WIDTH, self.TEXT_BUBBLE_HEIGHT))
        # first, standard dimension
        textAnnotation.setFrameSizeMm(QSizeF(mmDim[0] + 1, mmDim[1]))
        textDocument.adjustSize()  # it changes the height of the document
        textAnnotation.setMapPosition(qgsPointXY)
        fillSymbol = QgsFillSymbol.createSimple({"color": "#ffffff"})
        fillSymbol.setOpacity(self.TEXT_BUBBLE_OPACITY)

        textAnnotation.setFillSymbol(fillSymbol)
        symbol = QgsMarkerSymbol()
        symbol.setSize(0)
        textAnnotation.setMarkerSymbol(symbol)
        return textAnnotation

    def _getNewPointTextAnnotation(self, txtMsg: str, color: str, qgsPointXY: QgsPointXY):
        # print('_getNewPointTextAnnotation', txtMsg, color)

        textAnnotation = CustomPointTextAnnotation(txtMsg, qgsPointXY, color)

        qgsTextFormat = QgsTextFormat()
        qgsTextFormat.setColor(QColor(color))
        # font = QFont('MS Shell Dlg 2', 20)
        # font.setPointSize(100)
        # qgsTextFormat.setFont(font)
        qgsTextFormat.setSize(self.TEXT_SIZE_PX - 5)
        qgsTextFormat.setColor(QColor(color))
        textAnnotation.setFormat(qgsTextFormat)
        textAnnotation.setAlignment(Qt.AlignLeft)

        return textAnnotation

    def _convertPxToMM(self, size) -> [float, float]:
        """Support method to convert px dimension to millimeter dimension

        Args:
            size: size in pixel

        Returns:
            dimensions in mm
        """
        INCH_MM = 25.4
        dpi = self.iface.mainWindow().physicalDpiY()
        pxMM = INCH_MM / dpi
        return (size.width() * pxMM, size.height() * pxMM)

    def _retrieveMmSize(self, textDocument: QTextDocument) -> None:
        """Retrieves the dim in millimeter

        Args:
            textDocument: obj QTextDocument
        """
        size = textDocument.size()
        mmDim = self._convertPxToMM(size)
        print("Event ====> Document Size in mm:", size, mmDim)

    def _setRetrieveMmSize(self, textDocument: QTextDocument, textAnnotation: QgsTextAnnotation):
        """Sets dim in millimeter. It adapts the dimension of the frame based on the dimension of text document.

        Args:
            textDocument: instance of QTextDocument
            textAnnotation: instance of QgsTextAnnotation
        """
        size = textDocument.size()
        mmDim = self._convertPxToMM(size)
        textAnnotation.setFrameSizeMm(QSizeF(mmDim[0] + 1, mmDim[1] - self.TEXT_BUBBLE_OFFSET))
        textAnnotation.setFrameOffsetFromReferencePointMm(
            QPointF(self.TEXT_BUBBLE_OFFSET, - mmDim[1] + (self.TEXT_BUBBLE_OFFSET)))
        # print("Event ====> Document Size in mm:", size)

    def _onDocumentLayoutUpdated(self, textDocument, textAnnotation):
        # Signal emitted when textDocument layout is updated
        self._setRetrieveMmSize(textDocument, textAnnotation)

    def _refreshFrame4TextAnnotation(self):
        """Refresh the dimension of the frame of text annotation after their creation.
        It is necessary due to a bug in the calculation of height of QTextDocument
        """
        for textAnnotation in self.annotationManager.annotations():
            textDocument: QTextDocument = textAnnotation.document()
            size = textDocument.size()
            # print('===> _refreshFrame4TextAnnotation', textDocument, size)
            mmDim = self._convertPxToMM(size)
            textAnnotation.setFrameSizeMm(QSizeF(mmDim[0], mmDim[1] - 4))

    # Line ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _addStartLine(self) -> None:
        # print('_addStartLine')
        self.updateToggleToolsSignal.emit('lineEdit')
        mapTool: BtnToolMap = self.mapButtons['lineEdit']
        if not mapTool.tool:
            mapTool.tool = GeomEmitPoints(self.iface)
            mapTool.tool.completedSignal.connect(self._polylineCompleted)
        self.canvas.setMapTool(mapTool.tool)

    def _polylineCompleted(self, points: List[QgsPointXY]) -> None:
        self.qgsPointXYs = points
        mapTool: BtnToolMap = self.mapButtons['lineEdit']
        if not mapTool.additionalTool:
            mapTool.additionalTool = DialogForGeom(self.iface, self.iface.mainWindow())
            mapTool.additionalTool.completedSignal.connect(self._polylineDialogCompleted)
        mapTool.additionalTool.show()

    def _polylineDialogCompleted(self, width: str, lineStyle: int, opacity: str, color: str) -> None:
        # print("_polylineDialogCompleted", numValue, color)
        mapTool: BtnToolMap = self.mapButtons['lineEdit']
        mapTool.tool.reset()
        lineStyleStr = 'solid'
        if lineStyle == 1:
            lineStyleStr = 'dash'
        elif lineStyle == 2:
            lineStyleStr = 'dash dot'

        if width:
            self.annotationLayer.addItem(self._getNewLineAnnotation(width, lineStyleStr, opacity, color,
                                                                    self.qgsPointXYs))
            self._writeAnnotations()
        self.iface.actionPan().trigger()

    def _getNewLineAnnotation(self, width: str, lineStyle: str, opacity: str, color: str,
                              qgsPointXYs: List[QgsPointXY]) -> QgsAnnotationLineItem:
        curve = QgsLineString(qgsPointXYs)
        annotationItem = QgsAnnotationLineItem(curve)

        props: Dict = {}
        props['line_style'] = lineStyle
        props['width'] = width
        props['color'] = QColor(color)
        lineSymbol = QgsLineSymbol.createSimple(props)
        lineSymbol.setOpacity(float(opacity))
        lineSymbol.setColor(QColor(color))

        annotationItem.setSymbol(lineSymbol)
        return annotationItem

    # polygon ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _addStartPolygon(self) -> None:
        # print('_addStartPolygon')
        self.updateToggleToolsSignal.emit('polygonEdit')
        mapTool: BtnToolMap = self.mapButtons['polygonEdit']
        if not mapTool.tool:
            mapTool.tool = GeomEmitPoints(self.iface, True)
            mapTool.tool.completedSignal.connect(self._polygonCompleted)
        self.canvas.setMapTool(mapTool.tool)

    def _polygonCompleted(self, points: List[QgsPointXY]) -> None:
        self.qgsPointXYs = points
        mapTool: BtnToolMap = self.mapButtons['polygonEdit']
        if not mapTool.additionalTool:
            mapTool.additionalTool = DialogForGeom(self.iface, self.iface.mainWindow(), True)
            mapTool.additionalTool.completedSignal.connect(self._polygonDialogCompleted)

        mapTool.additionalTool.show()

    def _polygonDialogCompleted(self, width: str, lineStyle: str, opacity: str, color: str) -> None:
        # print("_polygonDialogCompleted", dimension, color)
        mapTool: BtnToolMap = self.mapButtons['polygonEdit']
        mapTool.tool.reset()
        if opacity and color:
            polygon: QgsGeometry = QgsGeometry.fromPolygonXY([self.qgsPointXYs])
            annotationItem: QgsAnnotationPolygonItem = (
                self._getNewPolygonAnnotation(opacity, color, polygon))
            self.annotationLayer.addItem(annotationItem)
            self._writeAnnotations()
        self.iface.actionPan().trigger()

    def _getNewPolygonAnnotation(self, numValue: str, color: str, polygon: QgsGeometry) \
            -> QgsAnnotationPolygonItem:
        curve = QgsCurvePolygon()
        curve.fromWkt(polygon.asWkt())
        annotationItem: QgsAnnotationPolygonItem = QgsAnnotationPolygonItem(curve)
        # print(self.annotationItem)
        symbol: QgsFillSymbol = annotationItem.symbol()
        symbolClone: QgsFillSymbol = symbol.clone()
        symbolClone.setColor(QColor(color))
        symbolClone.setOpacity(float(numValue))
        # lineSymbol = QgsLineSymbol()
        # lineSymbol.setWidth(0.5)
        # lineSymbol.setColor(QColor("orange"))
        # symbol2.deleteSymbolLayer(0)
        # symbol2.appendSymbolLayer(lineSymbol)
        annotationItem.setSymbol(symbolClone)

        return annotationItem

    # Delete text, line or polygon ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _delTextBubble(self) -> None:
        # print('delTextPopup')
        self.updateToggleToolsSignal.emit('delTextPopup')
        mapTool: BtnToolMap = self.mapButtons['delTextPopup']
        if not mapTool.tool:
            mapTool.tool = EmitDelPoint(self.iface)
            mapTool.tool.completedSignal.connect(self._textBubbleDelCompleted)

        if mapTool.btn.isChecked():
            self.canvas.setMapTool(mapTool.tool)
        else:
            self.iface.actionPan().trigger()

    def _textBubbleDelCompleted(self, x: float, y: float, _: QgsPointXY) -> None:
        # print('_textBubbleDelCompleted')
        annotation: QgsTextAnnotation
        for annotation in self.annotationManager.annotations():
            comparePointXY: QgsPointXY = annotation.mapPosition()
            comparePixelXY: QgsPointXY = self.canvas.getCoordinateTransform().transform(
                comparePointXY.x(), comparePointXY.y())
            checkPixelXY = QgsPointXY(x, y)
            # print('===>', checkPixelXY, comparePixelXY)
            if checkPixelXY.compare(comparePixelXY, 100):
                markerSymbol: QgsMarkerSymbol = annotation.markerSymbol()
                defaultSize: float = markerSymbol.size()
                markerSymbol.setSize(2.0)

                fillSymbol: QgsFillSymbol = annotation.fillSymbol()
                defaultColor: QColor = fillSymbol.color()
                defaultOpacity: float = fillSymbol.opacity()
                fillSymbol.setColor(QColor('lightyellow'))
                fillSymbol.setOpacity(self.TEXT_BUBBLE_OPACITY)

                retValue = self._showMessage("Sind Sie sicher, dass Sie den ausgewählten Text löschen wollen?")
                if retValue == QMessageBox.Cancel:
                    markerSymbol.setSize(defaultSize)
                    fillSymbol.setColor(defaultColor)
                    fillSymbol.setOpacity(defaultOpacity)
                else:
                    self.annotationManager.removeAnnotation(annotation)
                    self._writeAnnotations()
                self.canvas.refresh()
                break

    def _delGeom(self) -> None:
        # print('_delGeom')
        self.updateToggleToolsSignal.emit('delGeom')
        mapTool: BtnToolMap = self.mapButtons['delGeom']
        if not mapTool.tool:
            mapTool.tool = EmitDelPoint(self.iface)
            mapTool.tool.completedSignal.connect(self._delGeomCompleted)

        if mapTool.btn.isChecked():
            self.canvas.setMapTool(mapTool.tool)
        else:
            self.iface.actionPan().trigger()

    def _delGeomCompleted(self, x: float, y: float, qgsPointXY: QgsPointXY) -> None:
        # print('_delGeomCompleted')

        annotationId: object
        for annotationId in self.annotationLayer.items():
            # print('id;', annotationId, type(annotationId))
            annotation: QgsAnnotationItem = self.annotationLayer.item(annotationId)
            if type(annotation) == QgsAnnotationPolygonItem:
                curvePolygon: QgsCurvePolygon = annotation.geometry()
                polygon: QgsGeometry = QgsGeometry.fromWkt(curvePolygon.asWkt())
                if polygon.contains(qgsPointXY):
                    # print("found geometry!")
                    retValue = self._showMessage("Sind Sie sicher, dass Sie den ausgewählten Polygon löschen wollen?")
                    if retValue == QMessageBox.Cancel:
                        pass
                    else:
                        self.annotationLayer.removeItem(annotationId)
                        self._writeAnnotations()
                    break
            else:
                lineString: QgsLineString = annotation.geometry()
                geom: QgsGeometry = QgsGeometry.fromWkt(lineString.asWkt())
                buff: QgsGeometry = geom.buffer(100, 2)
                if buff.contains(qgsPointXY):
                    # print("found geometry!")
                    retValue = self._showMessage("Sind Sie sicher, dass Sie die ausgewählte Linie löschen wollen?")
                    if retValue == QMessageBox.Cancel:
                        pass
                    else:
                        self.annotationLayer.removeItem(annotationId)
                        self._writeAnnotations()
                    break

    # Other methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _readAnnotations(self):
        """Reads annotation from a yml file"""
        app: QCoreApplication = QApplication.instance()
        screen = app.primaryScreen()
        self.screenSize: float = screen.size()

        annotationFile: str = os.path.join(self.pluginDir, "annotations.yaml")
        if os.path.isfile(annotationFile):
            with open(annotationFile, 'r') as stream:
                dataLoaded = yaml.safe_load(stream)
            self.annotationConfig = dataLoaded if dataLoaded else {}
        else:
            self.annotationConfig = {}

        # print('self.annotationConfig', self.annotationConfig)
        if 'textAnnotations' in self.annotationConfig:
            textAnnotationConfig = self.annotationConfig['textAnnotations']
            for annConfig in textAnnotationConfig:
                # print('textAnnotation', annConfig)
                geom: QgsGeometry = QgsGeometry.fromWkt(annConfig['geom'])
                print('textAnnotations', geom.asPoint())
                self.annotationManager.addAnnotation(
                    self._getNewBubbleTextAnnotation(annConfig['text'], annConfig['color'], geom.asPoint()))

        if 'geomAnnotations' in self.annotationConfig:
            geomAnnotationConfig = self.annotationConfig['geomAnnotations']
            for annConfig in geomAnnotationConfig:
                if annConfig['type'] == 'QgsAnnotationLineItem':
                    # print('geomAnnotationConfig', geomAnnotationConfig)
                    qgsLineString = QgsLineString([])
                    qgsLineString.fromWkt(annConfig['geom'])
                    self.annotationLayer.addItem(self._getNewLineAnnotation(annConfig['width'], annConfig['line_style'],
                                                                            annConfig['opacity'],
                                                                            annConfig['color'], qgsLineString))
                elif annConfig['type'] == 'QgsAnnotationPolygonItem':
                    # print('geomAnnotationConfig', geomAnnotationConfig)
                    geom: QgsGeometry = QgsGeometry.fromWkt(annConfig['geom'])
                    annotationItem: QgsAnnotationPolygonItem = self._getNewPolygonAnnotation(annConfig['opacity'],
                                                                                             annConfig['color'],
                                                                                             geom)
                    self.annotationLayer.addItem(annotationItem)

                elif annConfig['type'] == 'QgsAnnotationPointTextItem':
                    geom: QgsGeometry = QgsGeometry.fromWkt(annConfig['geom'])
                    self.annotationLayer.addItem(self._getNewPointTextAnnotation(annConfig['text'], annConfig['color'],
                                                                                 geom.asPoint()))
        self.canvas.refresh()

    def _writeAnnotations(self):
        """Writes annotation in a yml file"""
        with open(os.path.join(self.pluginDir, "annotations.yaml"), 'w', encoding='utf8') as outfile:
            self.annotationConfig: any = {
                "textAnnotations": self._getYmlTextAnnotations(),
                "geomAnnotations": self._getYmlGeomAnnotations()
            }
            # print(self.annotationConfig)
            yaml.dump(self.annotationConfig, outfile)

    def _getYmlTextAnnotations(self) -> List[any]:
        textAnnotationYml: List[any] = []
        annotation: CustomBubbleTextAnnotation
        for annotation in self.annotationManager.annotations():
            qgsPointXY: QgsPointXY = annotation.mapPosition()
            textAnnotationYml.append({"type": "QgsTextAnnotation", "text": annotation.textMsg,
                                      "color": annotation.color,
                                      "geom": qgsPointXY.asWkt()})
        # print("annotationYml", textAnnotationYml)
        return textAnnotationYml

    def _getYmlGeomAnnotations(self) -> List[any]:
        geomAnnotationYml: List[any] = []
        annotationId: Union[QgsAnnotationPolygonItem, QgsAnnotationLineItem, CustomPointTextAnnotation]
        for annotationId in self.annotationLayer.items():
            annotation = self.annotationLayer.item(annotationId)
            if type(annotation) == QgsAnnotationPolygonItem:
                symbol: QgsFillSymbol = annotation.symbol()
                qColor: QColor = symbol.color()
                curvePolygon: QgsCurvePolygon = annotation.geometry()
                geomAnnotationYml.append({"type": "QgsAnnotationPolygonItem", "color": qColor.rgb(),
                                          "opacity": symbol.opacity(), "geom": curvePolygon.asWkt()})
            elif type(annotation) == QgsAnnotationLineItem:
                # print(annotation, annotation.geometry(), annotation.symbol())
                symbol: QgsLineSymbol = annotation.symbol()
                qColor: QColor = symbol.color()
                properties = symbol.symbolLayers()[0].properties()
                lineString: QgsLineString = annotation.geometry()
                geomAnnotationYml.append({"type": "QgsAnnotationLineItem", "line_style": properties["line_style"],
                                          "width": symbol.width(), "opacity": symbol.opacity(),
                                          "color": qColor.rgb(),
                                          "geom": lineString.asWkt()})
            elif type(annotation) == CustomPointTextAnnotation:
                geomAnnotationYml.append({"type": "QgsAnnotationPointTextItem", "text": annotation.textMsg,
                                          "color": annotation.color,
                                          "geom": annotation.point().asWkt()})

        # print("annotationYml", geomAnnotationYml)
        return geomAnnotationYml

    def _setBtnsVisibility(self, isBtnsActive: bool) -> None:
        """
        Manages visibility of all buttons for annotations. When checkbox in layer of layer tree is disabled, also all
        buttons should be disabled

        Args:
            isBtnsActive: set the visibility of the buttons for annotations
        """
        childItem: BtnToolMap
        for childItem in self.mapButtons.values():
            if childItem.isAnnotation:
                btn: QPushButton = childItem.btn
                btn.setDisabled(not isBtnsActive)

    def _showMessage(self, msgText: str) -> int:
        msg = QMessageBox()
        msg.setText(msgText)
        msg.setWindowTitle("Info")
        msg.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
        retval = msg.exec_()
        return retval
