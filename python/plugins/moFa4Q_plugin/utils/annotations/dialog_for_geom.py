import os
from functools import partial
from typing import List, Dict, Union, Optional

from PyQt5.QtCore import pyqtSignal, QRect
from PyQt5.QtGui import QPixmap, QColor, QIcon, QCloseEvent
from PyQt5.QtWidgets import (QDialog, QLabel, QDialogButtonBox, QPushButton, QComboBox, QWidget)

from qgis.PyQt import uic
from qgis.gui import QgisInterface

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), "../../components/dialog_for_geom.ui"))


class DialogForGeom(QDialog, FORM_CLASS):
    """Dialog for annotation lines and polygons"""

    lblWidth: QLabel
    lblType: QLabel
    lblOpacity: QLabel
    cmbWidth: QComboBox
    cmbType: QComboBox
    cmbOpacity: QComboBox

    verticalLayout: QWidget

    buttonBox: QDialogButtonBox

    btnBlack: QPushButton
    btnRed: QPushButton
    btnBlue: QPushButton
    btnGreen: QPushButton
    btnYellow: QPushButton

    OFFSET = 40
    BTN_COLOR_WIDTH = 150
    Q_RECT_POLYGON = QRect(0, 0, 401, 155)
    Q_RECT_POLYLINE = QRect(0, 0, 401, 275)
    HEIGHT_POLYGON = 155
    HEIGHT_POLYLINE = 275

    completedSignal = pyqtSignal(str, int, str, str)

    def __init__(self, iface: QgisInterface, parent: QWidget, isPolygon: bool = False):
        super(DialogForGeom, self).__init__(parent)
        self.iface = iface
        self.isPolygon = isPolygon
        self.color: Optional[str] = None
        self.setupUi(self)
        self.closeEvent = self.customCloseEvent
        # self.move(parent.x() + self.OFFSET, parent.y() + self.OFFSET)
        self._initUI()

    def show(self):
        """It overrides the method of the super class."""
        super().show()
        if not self.btnBlack.isChecked():
            self.btnBlack.click()
        if self.isPolygon:
            self.verticalLayout.setGeometry(self.Q_RECT_POLYGON)
            self.setFixedHeight(self.HEIGHT_POLYGON)
            self.cmbOpacity.setCurrentIndex(2)
        else:
            self.verticalLayout.setGeometry(self.Q_RECT_POLYLINE)
            self.setFixedHeight(self.HEIGHT_POLYLINE)
            self.cmbWidth.setCurrentIndex(3)
            self.cmbOpacity.setCurrentIndex(4)
            self.cmbType.setCurrentIndex(0)

        self.cmbWidth.setVisible(not self.isPolygon)
        self.lblWidth.setVisible(not self.isPolygon)
        self.cmbType.setVisible(not self.isPolygon)
        self.lblType.setVisible(not self.isPolygon)

    def close(self):
        """It overrides the method of the super class."""
        super().close()
        self.completedSignal.emit(None, None, None, None)

    # private methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _initUI(self):
        self.setWindowTitle('Nachricht eingeben')

        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.close)
        self.buttonBox.button(self.buttonBox.Ok).clicked.connect(self._saveDialog)

        self.colorBtns: List[Dict[str, Union[QPushButton, str]]] = [{'btn': self.btnBlack, 'color': 'black'},
                                                                    {'btn': self.btnRed, 'color': 'red'},
                                                                    {'btn': self.btnBlue, 'color': 'blue'},
                                                                    {'btn': self.btnGreen, 'color': 'green'},
                                                                    {'btn': self.btnYellow, 'color': 'yellow'}]
        self._setupColorForBtns()

    def _setupColorForBtns(self):
        item: Dict[str, Union[QPushButton, str]]
        for item in self.colorBtns:
            pixmap = QPixmap(self.BTN_COLOR_WIDTH, self.BTN_COLOR_WIDTH)
            pixmap.fill(QColor(item['color']))
            item['btn'].setIcon(QIcon(pixmap))
            item['btn'].setCheckable(True)
            item['btn'].setChecked(False)
            item['btn'].clicked.connect(partial(self._btnColorClicked, item['btn']))

        self.btnBlack.click()

    def _btnColorClicked(self, btn: QPushButton):
        if not btn.isChecked():
            btn.setChecked(True)
            return
        item: Dict[str, Union[QPushButton, str]]
        for item in self.colorBtns:
            if item['btn'] != btn:
                item['btn'].setChecked(False)
            else:
                self.color = item['color']

    def _saveDialog(self):
        # print("saveDialog")
        self.completedSignal.emit(self.cmbWidth.currentText(), self.cmbType.currentIndex(),
                                  self.cmbOpacity.currentText(), self.color)
        super().close()

    def customCloseEvent(self, event: QCloseEvent):
        self.close()
