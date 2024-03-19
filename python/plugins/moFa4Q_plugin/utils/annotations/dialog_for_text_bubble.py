import os
from functools import partial
from typing import List, Dict, Union, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QPixmap, QColor, QIcon, QCloseEvent
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QPushButton, QTextEdit, QWidget, QCheckBox)
from qgis.PyQt import uic
from qgis.gui import QgisInterface

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), "../../components/input_dialog_for_text_bubble.ui"))


class DialogForTextBubble(QDialog, FORM_CLASS):
    checkBox: QCheckBox
    textEdit: QTextEdit
    buttonBox: QDialogButtonBox

    btnBlack: QPushButton
    btnRed: QPushButton
    btnBlue: QPushButton
    btnGreen: QPushButton

    OFFSET = 40
    BTN_COLOR_WIDTH = 150

    completedSignal = pyqtSignal(str, str, bool)

    def __init__(self, iface: QgisInterface, parent: QWidget):
        super(DialogForTextBubble, self).__init__(parent)
        self.iface = iface
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
        self.textEdit.setText('')

    def close(self):
        """It overrides the method of the super class."""
        super().close()
        self.completedSignal.emit(None, None, False)

    # private methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _initUI(self):
        self.setWindowTitle('Nachricht eingeben')
        self.checkBox.setChecked(True)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.close)
        self.buttonBox.button(self.buttonBox.Ok).clicked.connect(self._saveDialog)

        self.colorBtns: List[Dict[str, Union[QPushButton, str]]] = [{'btn': self.btnBlack, 'color': 'black'},
                                                                    {'btn': self.btnRed, 'color': 'red'},
                                                                    {'btn': self.btnBlue, 'color': 'blue'},
                                                                    {'btn': self.btnGreen, 'color': 'green'}]
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

    def _btnColorClicked(self, btn):
        # print('btn==>', btn)
        item: Dict[str, Union[QPushButton, str]]
        for item in self.colorBtns:
            if item['btn'] != btn:
                item['btn'].setChecked(False)
            else:
                self.color = item['color']

    def _saveDialog(self):
        # print("saveDialog")
        self.completedSignal.emit(self.textEdit.toPlainText(), self.color, self.checkBox.isChecked())
        self.close()

    def customCloseEvent(self, _: QCloseEvent):
        self.close()
