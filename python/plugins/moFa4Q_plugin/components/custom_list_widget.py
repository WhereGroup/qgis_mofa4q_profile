from PyQt5.QtWidgets import QTreeWidgetItem, QListWidgetItem, QTreeWidget
from qgis.core import QgsProject, QgsMapLayer, QgsLayerTreeGroup


class CustomQTreeWidgetItem(QTreeWidgetItem):
    """Custom QTreeWidgetItem class with additional info regarding layer id and name and value of checkbox"""

    def __init__(self, id: str, name: str, checked: bool, layerTree: QTreeWidget):
        super().__init__()
        self.__id: str = id
        self.__name: str = name
        self.__checked: bool = checked
        self.__layerTree: QTreeWidget = layerTree

    @property
    def id(self) -> int:
        return self.__id

    @id.setter
    def id(self, id: int):
        self.__id = id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def checked(self) -> bool:
        return self.__checked

    @checked.setter
    def checked(self, checked: bool):
        self.__checked = checked
        # print('self.__id', self.__id)
        layer: QgsMapLayer = QgsProject.instance().layerTreeRoot().findLayer(str(self.__id))
        # Layer item was toggled
        if layer:
            layer.setItemVisibilityChecked(checked)

        else:
            root = QgsProject.instance().layerTreeRoot()
            group: QgsLayerTreeGroup = root.findGroup(str(self.__id))
            group.setItemVisibilityChecked(self.__checked)

    @property
    def layerTree(self) -> QTreeWidget:
        return self.__layerTree


class CustomQListWidgetItem(QListWidgetItem):
    id = 0
    checked = False

    def setId(self, id):
        self.id = id

    def getId(self):
        return self.id

    def setChecked(self, checked):
        self.checked = checked

    def isChecked(self):
        return self.checked
