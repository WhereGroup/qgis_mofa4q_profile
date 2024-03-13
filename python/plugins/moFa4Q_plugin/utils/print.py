# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Print the map in a pdf.
 ***************************************************************************/
"""
import os
import traceback
from typing import Dict, List

from PyQt5.QtCore import QSizeF
from PyQt5.QtGui import QColor, QIntValidator, QMovie, QCloseEvent, QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtWidgets import QWidget, QComboBox, QApplication, QSlider, QPushButton, QLineEdit, QCheckBox
from PyQt5.QtXml import QDomDocument
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (QDialog)
from qgis._core import QgsAnnotationManager
from qgis.core import (QgsGeometry, QgsLayoutExporter,
                       QgsPointXY, QgsLayoutItemMap,
                       QgsPrintLayout, QgsProject, QgsReadWriteContext,
                       QgsRectangle, QgsWkbTypes, Qgis)
from qgis.gui import QgisInterface, QgsRubberBand, QgsFileWidget

from .tr import tr

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), "../components/print_dialog.ui"))


class PrintDialog(QDialog, FORM_CLASS):
    """Opens a dialog to handle the print."""

    STROKE_WIDTH = 6
    STROKE_COLOR = QColor(222, 167, 67, 255)
    FILL_COLOR = QColor(222, 167, 67, 100)
    TEMP_STROKE_COLOR = QColor(222, 167, 67, 255)
    TEMP_FILL_COLOR = QColor(170, 255, 128, 100)
    OFFSET = 40
    FORMAT_DIMS: Dict[str, List[int]] = {
        'A4 Hochformat': [200, 287],
        'A4 Querformat': [287, 178],
        'A3 Querformat': [410, 265],
        'A2 Querformat': [584, 410],
        'A1 Querformat': [831, 584],
        'A0 Querformat': [1179, 831],
    }

    FORMAT_FILES: Dict[str, str] = {
        'A4 Hochformat': 'a4_hoch',
        'A4 Querformat': 'a4_quer',
        'A3 Querformat': 'a3_quer',
        'A2 Querformat': 'a2_quer',
        'A1 Querformat': 'a1_quer',
        'A0 Querformat': 'a0_quer',
    }
    STYLE: str = """
        QSlider::handle:horizontal {
            background: #ffffff;
            border: 2px solid #999999;
            width: 18px;
            height: 18px;
            margin: -10px 0;
        }
    """

    geomRb = None
    cmbFormat: QComboBox
    cmbScale: QComboBox
    txtRot: QLineEdit
    hSlider: QSlider
    mQgsFileWidget: QgsFileWidget
    btnClose: QPushButton
    btnPrint: QPushButton
    btnExport: QPushButton

    def __init__(self, iface: QgisInterface, parent: QWidget):
        super(PrintDialog, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.move(parent.x() + self.OFFSET, parent.y() + self.OFFSET)

        # self.rbA4.setChecked(True)

        self.movie = QMovie(':/plugins/moFa4Q_plugin/icons/load_indicator.gif')
        self.lblLoadIndicator.setMovie(self.movie)

        self.txtRot.setValidator(QIntValidator(0, 360))
        self.txtRot.setText("0")
        self.txtRot.textChanged.connect(self._changeRotation)
        self.hSlider.setMinimum(-180)
        self.hSlider.setMaximum(+180)
        self.hSlider.setTickInterval(5)
        self.hSlider.setSingleStep(5)
        self.hSlider.setValue(0)
        self.hSlider.setTickInterval(5)
        self.hSlider.setStyleSheet(self.STYLE)
        self.hSlider.valueChanged.connect(self._changeSlideRotation)

        self.mQgsFileWidget.setStorageMode(self.mQgsFileWidget.SaveFile)
        self.mQgsFileWidget.setFilter('*.pdf')

        self.btnClose.clicked.connect(self._closeDialog)
        self.btnPrint.clicked.connect(self._print)
        self.btnExport.clicked.connect(self._pdfExport)
        self.cmbFormat.currentIndexChanged.connect(self._changeRotation)
        self.cmbScale.currentIndexChanged.connect(self._changePreview)
        self.profile_path = self.iface.userProfileManager().userProfile().folder()

        # self.workerThread = RunThread()
        # self.workerThread.checkIfComplete.connect(self._onCountChanged)

    def showPreview(self):
        """Shows a preview on the canvas related to the print area"""
        self.setEnabled(True)
        self.movie = QMovie(':/plugins/moFa4Q_plugin/icons/load_indicator.gif')
        self.lblLoadIndicator.setMovie(self.movie)
        if self.geomRb is not None:
            self.geomRb.reset()
        self.geomRb = QgsRubberBand(self.iface.mapCanvas(), QgsWkbTypes.PolygonGeometry)
        self.geomRb.setColor(self.STROKE_COLOR)
        self.geomRb.setWidth(self.STROKE_WIDTH)
        self.geomRb.setFillColor(self.FILL_COLOR)
        self.previewRect = self._getPreviewRect(True)
        self.geomRb.addGeometry(self._getRotatedPreview())

    def closeEvent(self, _: QCloseEvent):
        """It overrides the method of the super class."""
        self._closeDialog()

    def show(self):
        """It overrides the method of the super class."""
        super().show()
        self.showPreview()

    # private methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _closeDialog(self):
        self.close()
        if self.geomRb:
            self.geomRb.reset()

    def _getRotatedPreview(self):
        txtRot = self.txtRot.text().strip()
        angle = 0
        try:
            angle = float(txtRot)
        except ValueError:
            pass
        geo = QgsGeometry.fromRect(self.previewRect)
        geo.rotate(angle, QgsPointXY(self.xPoint, self.yPoint))
        return geo

    def _getPreviewRect(self, isInit: bool) -> QgsRectangle:
        """
        Calculates preview on pdf based on scale, pdf format

        Args:
            isInit (bool): is after the open popup or change events

        Returns:
            bounding box representing the print area
        """
        extent = self.iface.mapCanvas().extent()
        if isInit:
            self.xPoint = (extent.xMaximum() - extent.xMinimum()) / 2 + extent.xMinimum()
            self.yPoint = (extent.yMaximum() - extent.yMinimum()) / 2 + extent.yMinimum()
        scale = self.cmbScale.currentText()
        scale = int(scale[2:])

        mapScale = self.iface.mapCanvas().scale()
        if scale * 18 < mapScale:
            self.lblMsg.setText(
                tr("Der Druck-Preview ist wahrscheinlich zu klein <br/> und nicht sichtbar. Bitte hereinzoomen"))
        else:
            self.lblMsg.setText("")

        # dimension on map in m equals to:  dimension on pdf in mm * scale / 1000
        dim = self.FORMAT_DIMS[self.cmbFormat.currentText()]
        width = dim[0] * scale / 1000
        height = dim[1] * scale / 1000
        return QgsRectangle(self.xPoint - width / 2, self.yPoint - height / 2,
                            self.xPoint + (width / 2), self.yPoint + (height / 2))

    # def _changeFormat(self):
    #     self.geomRb.reset(QgsWkbTypes.PolygonGeometry)
    #     self.previewRect = self._getPreviewRect(False)
    #     self.geomRb.addGeometry(self._getRotatedPreview())

    def _changePreview(self):
        self.geomRb.reset(QgsWkbTypes.PolygonGeometry)
        self.previewRect = self._getPreviewRect(False)
        self.geomRb.addGeometry(self._getRotatedPreview())

    def _changeRotation(self):
        # print('_changeRotation')
        intValue = 0
        try:
            intValue = int(self.txtRot.text().strip())
        except ValueError:
            pass
        self.hSlider.setValue(intValue)
        self._changePreview()

    def _changeSlideRotation(self):
        # print('_changeSlideRotation')
        intValue = self.hSlider.value()
        plusValue = '+' if intValue > 0 else ''
        self.txtRot.setText(plusValue + str(intValue))
        self._changePreview()

    def _onFinish(self):
        self.iface.messageBar().pushMessage(tr("Erfolgreich"), tr("Die Pdf-Datei wurde erfolgreich erstellt."))
        self._closeDialog()

    def _sendToThePrinter(self, layout: QgsPrintLayout):
        actualPrinter = QgsLayoutExporter(layout)
        printer = QPrinter()
        printDialog = QPrintDialog(printer)

        if printDialog.exec_() == QDialog.Accepted:
            success = actualPrinter.print(printer, QgsLayoutExporter.PrintExportSettings())
            return success
        return False

    def _print(self):
        """
        Sends content directly to the printer.
        """
        try:
            layout = self._getlayout()
            result: int = self._sendToThePrinter(layout)
            # print('result', result)
            if result == 0:
                self._onFinish()
            else:
                self.iface.messageBar().pushMessage(tr("Fehler"),
                                                    tr("Fehler. PDF-Datei wurde nicht zum Drucker gesendet. %s"
                                                       % traceback.format_exc()), level=Qgis.Warning,
                                                    duration=0)
            self._onFinish()
            QApplication.processEvents()
        except Exception:
            QApplication.processEvents()
            self.iface.messageBar().pushMessage(tr("Fehler"), tr("Fehler. Layout nicht gespeichert. %s"
                                                                 % traceback.format_exc()), level=Qgis.Warning,
                                                duration=0)
            self._closeDialog()
            if self.geomRb:
                self.geomRb.reset()

    def _pdfExport(self):
        """
        Generates the pdf.
        """
        # self.annotationManager: QgsAnnotationManager = QgsProject.instance().annotationManager()
        # for textAnnotation in self.annotationManager.annotations():
        #     textDocument: QTextDocument = textAnnotation.document()
        #     print('===> event ===>', textDocument, textDocument.size())
        #     qSizeF = textDocument.size()
        try:

            # checks if filePath exits
            filePath = self.mQgsFileWidget.filePath()
            if filePath is None or filePath == "" or (".pdf" in os.path.basename(filePath)) is False:
                self.lblMsg.setText("PDF-Datei wurde nicht definiert")
                return

            if os.path.exists(os.path.dirname(filePath)) is False:
                self.lblMsg.setText("Der Pfad existiert nicht")
                return

            self.setEnabled(False)
            self.movie.start()
            QApplication.processEvents()

            layout = self._getlayout()
            exporter = QgsLayoutExporter(layout)
            exporter.exportToPdf(filePath, QgsLayoutExporter.PdfExportSettings())

            self._onFinish()
            QApplication.processEvents()
        except Exception:
            QApplication.processEvents()
            self.iface.messageBar().pushMessage(tr("Fehler"), tr("Fehler. PDF-Datei wurde nicht generiert. %s"
                                                                 % traceback.format_exc()), level=Qgis.Warning,
                                                duration=0)
            self._closeDialog()
            if self.geomRb:
                self.geomRb.reset()

    def _getlayout(self) -> QgsPrintLayout:
        # Load template layout
        currentPath: str = os.path.dirname(os.path.abspath(__file__))
        templatePath: str = os.path.join(self.profile_path, "composer_templates",
                                         self.FORMAT_FILES[self.cmbFormat.currentText()] + '.qpt')
        with open(templatePath, "rt") as t:
            template_content = t.read()
        domDocument = QDomDocument()
        domDocument.setContent(template_content, False)
        
        # Create Layout
        project = QgsProject.instance()
        layout = QgsPrintLayout(project)
        layout.loadFromTemplate(domDocument, QgsReadWriteContext())

        mapItem: QgsLayoutItemMap = layout.referenceMap()
        # print("map", map)
        txtRot = self.txtRot.text().strip()
        angle = float(txtRot) if txtRot != "" else 0
        mapItem.setMapRotation(-angle)
        mapItem.setExtent(self.previewRect)

        self._updateLblsAndImgs(layout, currentPath, angle)
        return layout

    def _updateLblsAndImgs(self, layout: QgsPrintLayout, currentPath: str, angle: int) -> None:
        """
        Updates the content of pdf below the map (texts, images)

        Args:
            layout: print layout
            currentPath: current path
            angle: angle of rotation
        """
        # logo
        imgLogo = layout.itemById("imgLogo")
        imgLogo.setPicturePath(os.path.join(currentPath, "../icons", "logo.png"))

        # compass
        imgCompass = layout.itemById("imgCompass")
        imgCompass.setPictureRotation(-angle)
        imgCompass.setPicturePath(os.path.join(currentPath, "../icons", "north_arrow.png"))
