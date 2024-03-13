# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Show at initialization a popup if geopackages older than 4 weeks.
 ***************************************************************************/
"""
import os
import pathlib
import subprocess
from typing import Optional, List

from PyQt5.QtGui import QCloseEvent, QMovie
from PyQt5.QtWidgets import QWidget, QApplication, QLabel
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (QDialog)
from qgis.core import QgsProject, QgsExpressionContextUtils
from qgis.gui import QgisInterface
from .tr import tr

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), "../components/geopackages_dialog.ui"))


class GpkgPopup(QDialog, FORM_CLASS):
    """Shows a warning popup if public geopackages are older than 28 days/ 4 weeks.
    Possibility to open the synch-tool
    """
    lblDescr1: QLabel
    lblDescr2: QLabel
    lblList1: QLabel
    lblList2: QLabel
    lblLoadIndicator: QLabel

    def __init__(self, iface: QgisInterface, parent: QWidget):
        super(GpkgPopup, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.btnClose.clicked.connect(self.closeDialog)
        self.movie = QMovie(':/plugins/moFa4Q_plugin/icons/load_indicator.gif')
        self.lblLoadIndicator.setMovie(self.movie)
        self.syncPath = None

    def closeDialog(self):
        self.close()

    def openSynchTool(self):
        """Starts a warning popup and if dialog will be confirmed, synch tool will be opened"""
        self.movie.start()
        QApplication.processEvents()
        sync_pool_cmd: str = pathlib.Path(self.syncPath).as_posix()
        subprocess.Popen([sync_pool_cmd], shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

        self.iface.mainWindow().close()
        QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), 'is_warning_shown', False)

    def closeEvent(self, _: QCloseEvent):
        self.closeDialog()
        QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), 'is_warning_shown', False)

    def show(self, titelName: Optional[str] = None, gpkgOlder4Weeks: Optional[List[str]] = None,
             corruptQlrs: Optional[List[str]] = None):
        is_warning_shown = QgsExpressionContextUtils.projectScope(QgsProject.instance()).variable('is_warning_shown')
        # print('is_warning_shown', is_warning_shown)
        QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), 'is_warning_shown', True)
        if titelName:
            l = QLabel(tr(titelName))
            l.setStyleSheet("QLabel{font-size: 13pt;}")
            self.vLayout.addWidget(l)
        else:
            if gpkgOlder4Weeks:
                l = QLabel(tr("Die folgenden Geopackages sind älter als 4 Wochen:"))
                l.setStyleSheet("QLabel{font-size: 13pt;}")
                self.vLayout.addWidget(l)
                l2 = QLabel(", ".join(gpkgOlder4Weeks))
                l2.setStyleSheet("QLabel{font-size: 13pt;}")
                self.vLayout.addWidget(l2)
            if corruptQlrs:
                l = QLabel(tr("Die folgenden QLR-Dateien sind wahrscheinlich beschädigt und sollten aktualisiert werden"))
                l.setStyleSheet("QLabel{font-size: 13pt;}")
                self.vLayout.addWidget(l)
                l2 = QLabel(", ".join(corruptQlrs))
                l2.setStyleSheet("QLabel{font-size: 13pt;}")
                self.vLayout.addWidget(l2)
        super().show()

    def setSyncToolPath(self, default_install_path) -> bool:
        """"set Install Path for Synctool"""
        install_sync_path = os.path.join(default_install_path, "batch", "mofa4q_sync.bat")
        print('install_sync_path: ', install_sync_path)
        result = False
        if os.path.isfile(install_sync_path):
            self.syncPath = install_sync_path
            self.btnOpen.clicked.connect(self.openSynchTool)
            result = True
        return result
