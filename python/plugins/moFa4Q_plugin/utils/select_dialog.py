from functools import partial
from qgis.PyQt.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLayout,
                                 QListWidget, QListWidgetItem, QPushButton,
                                 QVBoxLayout, QWidget)
from qgis.core import QgsFeature
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapToolIdentify
from .tr import tr


class SelectDialog(QDialog):
    """
    If more than one feature is selected, the user can choose, which one can be shown.
    """
    MAX_FEATURE = 25
    MSG_HIGHT = 110

    results = []

    dialogSygnal = pyqtSignal(QgsMapToolIdentify.IdentifyResult)

    def __init__(self, iface):
        super(SelectDialog, self).__init__()
        self.iface = iface

    def show(self, results):
        super().show()
        self.results = results
        layout = QVBoxLayout()
        self.setLayout(layout)

        # print("results", results)
        if len(results) > self.MAX_FEATURE:
            lbl = QLabel(tr("Es wurden mehr als {} Feature identifiziert. Bitte zoomen Sie hinein um die Anzahl zu verringern").format(
                self.MAX_FEATURE))
            layout.addWidget(lbl)
            self.setFixedHeight(self.MSG_HIGHT)
        else:
            listWidget = QListWidget()
            layout.addWidget(listWidget)

            rowCount = -1
            for row in results:
                rowCount += 1
                self.addRow(row, rowCount, listWidget)

    def addRow(self, row, rowCount, listWidget):
        itemN = QListWidgetItem()
        widget = QWidget()
        hLayout = QHBoxLayout()
        lblWidget = QLabel(row.mLayer.name() + " fid: " + str(row.mFeature.id()))
        btnShowFeature = QPushButton(tr("Feature anzeigen"))
        hLayout.addWidget(lblWidget)
        hLayout.addWidget(btnShowFeature)
        hLayout.addStretch()
        hLayout.setSizeConstraint(QLayout.SetFixedSize)
        widget.setLayout(hLayout)
        itemN.setSizeHint(widget.sizeHint())
        listWidget.addItem(itemN)
        listWidget.setItemWidget(itemN, widget)
        btnShowFeature.clicked.connect(partial(self.showFeature, rowCount))

        #Add widget to QListWidget funList
        listWidget.addItem(itemN)
        listWidget.setItemWidget(itemN, widget)

    def showFeature(self, rowCount):
        self.close()
        self.iface.openFeatureForm(self.results[rowCount].mLayer, QgsFeature(self.results[rowCount].mFeature), True)
        self.dialogSygnal.emit(self.results[rowCount])
