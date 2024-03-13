import yaml
import os
from qgis.core import (QgsLayerDefinition)
from PyQt5.QtWidgets import QMessageBox, QApplication
from qgis.core import QgsProject, QgsExpressionContextUtils


def openProject():
    pass


def saveProject():
    pass


def closeProject():
    isWarningShown = QgsExpressionContextUtils.projectScope(QgsProject.instance()).variable('is_warning_shown')
    if not bool(isWarningShown):
        msg = QMessageBox()
        msg.setText("Bitte haben Sie ein wenig Geduld - MoFa4q wird gespeichert und geschlossen")
        msg.setWindowTitle("Info")
        msg.setStandardButtons(QMessageBox.NoButton)
        msg.show()
        QApplication.processEvents()

        _writeQlrsForPubLayers()


def _writeQlrsForPubLayers() -> None:
    """Writes public layers in QLR files"""
    homePath = QgsProject.instance().homePath()
    qlrList = []
    sequenceQlr = os.path.join(homePath, "geopackages", "public", "sequence_qlr.yml")
    if os.path.isfile(sequenceQlr):
        with open(sequenceQlr, 'r') as stream:
            qlrList = yaml.safe_load(stream)

    # childItem: Union[QgsLayerTreeLayer, QgsLayerTreeGroup]
    for childItem in QgsProject.instance().layerTreeRoot().children():
        if childItem.name() in qlrList:
            # qlrList.append(childItem.name())
            qlrFile: str = os.path.join(homePath, "geopackages", "public", childItem.name() + '.qlr')
            QgsLayerDefinition().exportLayerDefinition(qlrFile, [childItem])

    """qlrListFileOutput: str = os.path.join(homePath, "geopackages", "public", 'sequence_qlr.yml')
    # print('qlrList', qlrList)
    with open(qlrListFileOutput, 'w', encoding='utf8') as outfile:
        yaml.dump(qlrList, outfile)"""
