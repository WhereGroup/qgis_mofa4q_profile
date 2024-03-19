import os
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Dict, List, Union

from PyQt5.QtCore import QSize, Qt, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QTreeWidget, QAbstractItemView
from qgis.core import QgsProject, QgsLayerTree, QgsLayerTreeGroup, QgsLayerTreeLayer, Qgis, QgsVectorLayer
from qgis.core import QgsRasterLayer
from qgis.gui import QgisInterface

from ..components.custom_list_widget import (CustomQTreeWidgetItem)
from .tr import tr


class LayerTreeType(Enum):
    """Three type of layers (public, private and background layers)"""

    BG = 1
    PUBLIC = 2
    PRIVATE = 3


class LayerTrees(QObject):
    """Defines the 3 layer trees for public, private and background layers"""

    LABEL_FONT = QFont('MS Shell Dlg 2', 10)
    LABEL_FONT_2 = QFont('MS Shell Dlg 2', 11)
    LAYERTREE_STYLE: str = """
        QTreeView {
            qproperty-indentation: 30;
        }
        QTreeView::item {
            height: 15px;
        }
        QTreeView::branch {
            background-color: #fff;
            border-bottom: none;
        }
        QTreeView::branch:has-children:!has-siblings:closed,
        QTreeView::branch:closed:has-children:has-siblings {
            image: url(%(iconClosed)s);
            width: 0;
        }
        QTreeView::branch:open:has-children:!has-siblings,
        QTreeView::branch:open:has-children:has-siblings  {
            image: url(%(iconOpen)s);
        }
        QTreeView::branch:!has-children:closed{
            border-bottom: none;
        }
    """
    BTN_DEL_STYLE: str = """QPushButton{
        background-color: #d8d9db;
        border: 1px solid #d8d9db;
        padding: 5px;
        border-radius: 5px;
    }"""
    TOOL_BOX_STYLE2: str ="""QToolBox::tab {
        background: #d8d9db;
        border: 1px solid #d8d9db;
        border-radius: 5px;
        padding: 2px;
        font-family: MS Shell Dlg 2;
        font-size: 11pt;
    }"""
    ICON_WIDTH = 25
    ICON_HEIGHT = 25
    MOVE_BTN_WIDTH = 30
    BTN_CHECK_WIDTH = 50

    updateYamlSignal = pyqtSignal()
    updatePubQlrSignal = pyqtSignal()
    # updatePrivQlrSignal = pyqtSignal()
    updateAnnotationSignal = pyqtSignal(bool, bool)

    def __init__(self, iface: QgisInterface, leftPanel: QWidget, pluginDir: str, geopackageDir: str, prjConfig: any,
                 bgLayer: QgsRasterLayer, pubQlrStr: List[str], isAnnVisible: bool):
        super().__init__()
        self.iface: List[str] = iface
        self.leftPanel = leftPanel
        self.pluginDir = pluginDir
        self.geopackageDir = geopackageDir
        self.prjConfig = prjConfig
        self.bgLayer: QgsRasterLayer = bgLayer
        self.pubQlrStr: List[str] = pubQlrStr
        self.isAnnVisible: bool = isAnnVisible
        self.internWidth = 0

        self.existingGroups: List[str] = []

        self._initStyle()
        self._initLayerTrees()

    def addLayerInPrivLayerTree(self, groupNode: str) -> None:
        """
        Adds layer/gpkg (available under the folder geopackageDir in private layer tree)

        Args:
            groupNode: name of the groupNode/file/gpkg
        """
        self.leftPanel.privLayerTree: QTreeWidget
        # self.leftPanel.privLayerTree.clear()
        treeWidgetItem = self._getLayerItem(groupNode, True,
                                            self.leftPanel.privLayerTree, LayerTreeType.PRIVATE)
        self.leftPanel.privLayerTree.insertTopLevelItem(0, treeWidgetItem["item"])
        self.leftPanel.privLayerTree.setItemWidget(treeWidgetItem["item"], 0, treeWidgetItem["widget"])
        self._addChildren(groupNode, treeWidgetItem["item"], self.leftPanel.privLayerTree, False,
                          LayerTreeType.PRIVATE)


    def removeLayerInPrivLayerTree(self, fileName: str):
        """
        Removes layer/gpkg in private layer tree (the gpkg is not physically removed, it remains under the folder
        geopackageDir)

        Args:
            fileName: name of the file/gpkg
        """
        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        # print('fileName:', fileName)
        # print('notSavedDataSourceList:', self.leftPanel.notSavedDataSourceList)
        for i in range(self.leftPanel.privLayerTree.topLevelItemCount()):
            item: CustomQTreeWidgetItem = self.leftPanel.privLayerTree.topLevelItem(i)
            if item.id == fileName:
                for j in range(item.childCount()):
                    layerId: str = item.child(j).id
                    layer: QgsVectorLayer = QgsProject.instance().mapLayer(layerId)
                    # print('remove as layer', layerId, layer)
                    QgsProject.instance().removeMapLayer(layer)
                self.leftPanel.privLayerTree.takeTopLevelItem(i)
                groupNode: QgsLayerTreeGroup = root.findGroup(fileName)
                root.removeChildNode(groupNode)

                if fileName in self.existingGroups:
                    self.existingGroups.remove(fileName)
                break

    # private methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _initStyle(self):
        iconClosed = Path(os.path.join(os.path.dirname(__file__), '../icons', 'branch_closed.png')).as_posix()
        iconOpen = Path(os.path.join(os.path.dirname(__file__), '../icons', 'branch_open.png')).as_posix()
        self.treeStyleSheet = self.LAYERTREE_STYLE % {"iconClosed": iconClosed, "iconOpen": iconOpen}

        self.leftPanel.pubLayerTree.setSelectionMode(QAbstractItemView.NoSelection)
        self.leftPanel.pubLayerTree.header().setMinimumSectionSize(self.leftPanel.pubLayerTree.width())
        self.leftPanel.pubLayerTree.setStyleSheet(self.treeStyleSheet)

        self.leftPanel.privLayerTree.setSelectionMode(QAbstractItemView.NoSelection)
        self.leftPanel.privLayerTree.header().setMinimumSectionSize(self.leftPanel.privLayerTree.width())
        self.leftPanel.privLayerTree.setStyleSheet(self.treeStyleSheet)

        self.leftPanel.toolBox2.setStyleSheet(self.TOOL_BOX_STYLE2)

    def _initLayerTrees(self) -> None:
        """Sets up all 3 layer trees (QgsLayerTree) for background, private and public layers."""
        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()

        self._createAnnotationInLayerTree(root)
        self._createPubLayersInLayerTree(root)
        self._createPrivLayersInLayerTree(root)
        self._createBgLayerInLayerTree(root)

    def _createAnnotationInLayerTree(self, root: QgsLayerTree):
        self.leftPanel.annLayerTree.setLayout(self._getLayerItemAnnotation())

    def _createBgLayerInLayerTree(self, root: QgsLayerTree):
        """Creates background layer in layer tree, only if it exists
           Newcreate bgLayerTreeNode with new index for layertree
           bgLayerTreeNode is a default layer from qgis project
        Args:
            root: root item in layer tree
        """
        if self.bgLayer:
            bgLayerTreeNode: QgsLayerTreeLayer = root.findLayer(self.bgLayer.id())
            CloneBgLayerTreeNode = bgLayerTreeNode.clone()
            root.addChildNode(CloneBgLayerTreeNode)
            parent = bgLayerTreeNode.parent()
            parent.removeChildNode(bgLayerTreeNode)
            isVisible: bool = CloneBgLayerTreeNode.itemVisibilityChecked()
            hLayout = self._getLayerItemBg(CloneBgLayerTreeNode, isVisible)
        else:
            hLayout = self._getLayerItemBg(None, False)
        self.leftPanel.bgLayerTree.setLayout(hLayout)

    def _createPubLayersInLayerTree(self, root: QgsLayerTree):
        """Creates items for public layers in layer tree

        Args:
            root: root item in layer tree
        """
        # pubGkpgs: Optional[List[any]] = None
        # if self.prjConfig is not None and 'publicGpkgs' in self.prjConfig:
        #     pubGkpgs = self.prjConfig['publicGpkgs']

        self.leftPanel.layerTree: QTreeWidget
        childItem: Union[QgsLayerTreeLayer, QgsLayerTreeGroup]
        # isVisible: bool
        for childItem in root.children():
            if childItem.name() in self.pubQlrStr:
                # print('childItem', childItem, childItem.name(), childItem.dump())
                # configItem, isVisible = self._getVisibilityBasedOnConfig(childItem, pubGkpgs)
                treeWidgetItem = self._getLayerItem(childItem, childItem.itemVisibilityChecked(),
                                                    self.leftPanel.pubLayerTree, LayerTreeType.PUBLIC)
                currentCount: int = self.leftPanel.pubLayerTree.topLevelItemCount()
                self.leftPanel.pubLayerTree.insertTopLevelItem(currentCount, treeWidgetItem["item"])
                self.leftPanel.pubLayerTree.setItemWidget(treeWidgetItem["item"], 0, treeWidgetItem["widget"])
                self._addChildren(childItem, treeWidgetItem["item"], self.leftPanel.pubLayerTree, False,
                                  LayerTreeType.PUBLIC)

    def _createPrivLayersInLayerTree(self, root: QgsLayerTree):
        """Creates items for private layers in layer tree

        Args:
            root: root item in layer tree
        """
        privGkpgs: List[any] = self.prjConfig['privateGpkgs']
        privGkpgNamesInRoot = [pG['layer'] for pG in privGkpgs]
        # print('==> privGkpgs', rootGkpgName)
        self.leftPanel.layerTree: QTreeWidget
        childItem: Union[QgsLayerTreeLayer, QgsLayerTreeGroup]
        for childItem in root.children():
            if childItem.name() in privGkpgNamesInRoot:
                # print(childItem.name(), childItem.isVisible())
                treeWidgetItem = self._getLayerItem(childItem, childItem.itemVisibilityChecked(),
                                                    self.leftPanel.privLayerTree, LayerTreeType.PRIVATE)
                currentCount: int = self.leftPanel.privLayerTree.topLevelItemCount()
                self.leftPanel.privLayerTree.insertTopLevelItem(currentCount, treeWidgetItem["item"])
                self.leftPanel.privLayerTree.setItemWidget(treeWidgetItem["item"], 0, treeWidgetItem["widget"])
                self._addChildren(childItem, treeWidgetItem["item"], self.leftPanel.privLayerTree,
                                  False, LayerTreeType.PRIVATE)

    def _addChildren(self, father: QgsLayerTreeLayer, item: CustomQTreeWidgetItem, layerTree: QTreeWidget,
                     isMoved: bool, layerTreeType: LayerTreeType) -> None:
        # print('father', father)
        for childItem in reversed(father.children()):
            # print('childItem', childItem, type(childItem))
            # configItem, isVisible = (
            #     self._getVisibilityBasedOnConfig(childItem, configFather['layers']
            #                                      if configFather and 'layers' in configFather else None))

            # print('childItem', configItem, isVisible)
            treeWidgetItem = self._getLayerItem(childItem, childItem.itemVisibilityChecked(), layerTree, layerTreeType,
                                                isMoved)
            item.insertChild(0, treeWidgetItem["item"])
            layerTree.setItemWidget(treeWidgetItem["item"], 0, treeWidgetItem["widget"])
            self._addChildren(childItem, treeWidgetItem["item"], layerTree, isMoved, layerTreeType)

    def _getLayerItemAnnotation(self) -> QWidget:
        layerTree: QTreeWidget = self.leftPanel.annLayerTree
        label: str = tr('Annotations/Notizen')
        lblWidget = QLabel(label)
        lblWidget.setWordWrap(True)
        lblWidget.setFont(self.LABEL_FONT_2)
        lblWidget.setWordWrap(False)
        lblWidget.setStyleSheet("border-width: 0px; font-style: italic")
        btnCheck = self._getBtnCheck(self.isAnnVisible)
        btnDel = self._getBtnDelete()
        hLayout = QHBoxLayout(layerTree)
        hLayout.addWidget(lblWidget)
        hLayout.addStretch()
        hLayout.addWidget(btnDel)
        hLayout.addWidget(btnCheck)

        btnCheck.clicked.connect(partial(self._onAnnotationChanged, btnCheck))
        btnDel.clicked.connect(self._onAnnotationDeleted)
        return hLayout

    def _getLayerItemBg(self, childItem: QgsLayerTreeLayer, isVisible: bool) -> QWidget:
        label: str = tr('Luftbilder')
        lblWidget = QLabel(label)
        lblWidget.setWordWrap(True)
        lblWidget.setFont(self.LABEL_FONT_2)
        lblWidget.setWordWrap(False)
        lblWidget.setStyleSheet("border-width: 0px; font-style: italic")
        btnCheck = self._getBtnCheck(isVisible)
        hLayout = QHBoxLayout(self.leftPanel.bgLayerTree)
        hLayout.addWidget(lblWidget)
        hLayout.addStretch()
        hLayout.addWidget(btnCheck)

        if childItem:
            btnCheck.clicked.connect(partial(self._onBgChanged, btnCheck, childItem))
        return hLayout

    def _getLayerItem(self, childItem: Union[QgsLayerTreeLayer, QgsLayerTreeGroup], isVisible: bool,
                      layerTree: QTreeWidget, layerTreeType: LayerTreeType, isMoved: bool = False) \
            -> Dict[CustomQTreeWidgetItem, QWidget]:

        isFolder: bool = type(childItem) == QgsLayerTreeGroup
        label = tr(childItem.name())
        layerId = childItem.layerId() if hasattr(childItem, 'layerId') else label
        # print('=========> isFolder', isFolder, 'label layerId', label, layerId, isMoved)

        if not isMoved:
            self._checkGroupDuplication(isFolder, label)

        # if hasattr(childItem, 'layerId'):
        #     # print('dataProvider', childItem.layer().dataProvider().dataSourceUri())
        #     # print('dataProvider', childItem.layer().dataProvider().storageType())

        # defines item and widget
        item = CustomQTreeWidgetItem(layerId, label, isVisible, layerTree)
        widget = QWidget()

        folderWidget = QLabel('')
        pixmap = QPixmap(os.path.join(self.pluginDir, 'icons/folder.png'))
        scaled: QPixmap = pixmap.scaled(self.ICON_WIDTH, self.ICON_HEIGHT, Qt.KeepAspectRatio)
        folderWidget.setPixmap(scaled)

        lblWidget = QLabel(label)
        lblWidget.setWordWrap(True)
        lblWidget.setFont(self.LABEL_FONT)
        btnCheck = self._getBtnCheck(isVisible)
        btnUp = QPushButton("↑")
        btnUp.setMaximumWidth(self.MOVE_BTN_WIDTH)
        btnUp.setCursor(Qt.PointingHandCursor)
        btnDown = QPushButton("↓")
        btnDown.setMaximumWidth(self.MOVE_BTN_WIDTH)
        btnDown.setCursor(Qt.PointingHandCursor)

        hLayout = QHBoxLayout(layerTree)
        
        if isFolder:
            hLayout.addWidget(folderWidget)
        hLayout.addWidget(lblWidget)
        hLayout.addStretch()
        hLayout.addWidget(btnCheck)

        hLayout.addWidget(btnUp)
        hLayout.addWidget(btnDown)
        hLayout.setSpacing(1)
        widget.setLayout(hLayout)
        widget.adjustSize()
        lblWidgetWidth = lblWidget.size().width()
        if lblWidgetWidth > self.internWidth:
            self.internWidth = lblWidgetWidth

        btnCheck.clicked.connect(partial(self._onCheckBtnChanged, item, btnCheck, layerTreeType))

        btnUp.clicked.connect(partial(self._onMoveBtnChanged, item, childItem, True, layerTreeType))
        btnDown.clicked.connect(partial(self._onMoveBtnChanged, item, childItem, False, layerTreeType))

        return {'item': item, 'widget': widget}

    def _getBtnCheck(self, isVisible: bool):
        btnCheck = QPushButton()
        btnCheck.setMaximumWidth(self.BTN_CHECK_WIDTH)
        btnCheck.setCheckable(True)
        btnCheck.setChecked(isVisible)
        if isVisible:
            btnCheck.setIcon(QIcon(os.path.join(self.pluginDir, 'icons/checkbox.png')))
        else:
            btnCheck.setIcon(QIcon(os.path.join(self.pluginDir, 'icons/checkbox_dis.png')))
        btnCheck.setIconSize(QSize(self.BTN_CHECK_WIDTH - 10, 40))
        btnCheck.setStyleSheet("QPushButton{background-color: transparent; border: transparent;margin: 0; padding: 5px; height: 15px;}")  # noqa
        btnCheck.setCursor(Qt.PointingHandCursor)
        return btnCheck

    def _getBtnDelete(self):
        btnDel = QPushButton('Alle löschen')
        # btnCheck.setMaximumWidth(self.btnCheckWidth)
        btnDel.setStyleSheet(self.BTN_DEL_STYLE)
        btnDel.setCursor(Qt.PointingHandCursor)
        return btnDel

    def _checkGroupDuplication(self, isFolder: bool, label: str):
        """Groups do not have any id => we use name to identify them.
        Identification problem if two groups have same name (for example in class CustomQTreeWidgetItem
        method findGroup() We use name to find out the group)!

        Args:
            isFolder: bool to check if folder
            label: name of the group
        """
        if isFolder and label in self.existingGroups:
            self.iface.messageBar().pushMessage("Fehler",
                                                f"It is not possible to have two groups with the same name {label}.",
                                                level=Qgis.Warning)
        if isFolder:
            self.existingGroups.append(label)

    # def _getVisibilityBasedOnConfig(self, childItem: Union[QgsLayerTreeLayer, QgsLayerTreeGroup], layers: List[any]) \
    #         -> [any, bool]:
    #     """Only for public layer at init. The rest has already the correct visibility and order
    #     If config of a layer/group is defined in file prj_conf => get the visibility value from it
    #
    #     Args:
    #         childItem: selected item in layer tree
    #         layers: attribute layers in file prj_conf
    #
    #     Returns:
    #         selected item in layer tree and the visibility of selected item
    #     """
    #     selConfigItem: any = None
    #     isVisible: bool = childItem.itemVisibilityChecked()
    #     if layers:
    #         for configItem in layers:
    #             if configItem['layer'] == childItem.name():
    #                 selConfigItem = configItem
    #                 isVisible = configItem['isVisible']
    #                 break
    #
    #     return selConfigItem, isVisible

    def _onCheckBtnChanged(self, item: CustomQTreeWidgetItem, btnCheck: QPushButton, layerTreeType: LayerTreeType):
        """Toggles layer or group visibility in the QTreeWidget

        Args:
            item (CustomQTreeWidgetItem): item in layer tree
            btnCheck (QPushButton): button wich works as checkbox
            layerTreeType (LayerTreeType): layer type
        """
        # print(item, btnCheck.isChecked())
        if btnCheck.isChecked():
            btnCheck.setIcon(QIcon(os.path.join(self.pluginDir, 'icons/checkbox.png')))
        else:
            btnCheck.setIcon(QIcon(os.path.join(self.pluginDir, 'icons/checkbox_dis.png')))

        item.checked = btnCheck.isChecked()
        if layerTreeType == LayerTreeType.PUBLIC:
            # changes on files are done on close of the project in a macro
            pass
            # self.updatePubQlrSignal.emit()
        else:
            self.updateYamlSignal.emit()

    def _onMoveBtnChanged(self, qtItem: CustomQTreeWidgetItem, childItem: Union[QgsLayerTreeLayer, QgsLayerTreeGroup],
                          isUp: bool, layerTreeType: LayerTreeType) -> None:
        """Moves items up and down in the list of layers

        Args:
            qtItem: qt item in layer tree
            childItem: qgs item in layer tree
            isUp: layer moves up or down in the layer tree
            layerTreeType (LayerTreeType): layer type
        """
        # print('qtItem', qtItem, 'childItem', childItem, 'isUp', isUp)

        # isExpanded = qtItem.isExpanded()
        root = QgsProject.instance().layerTreeRoot()
        fatherQtItem = qtItem.parent()
        cloneChildItem = childItem.clone()
        fatherGroup = childItem.parent()
        # print('isExpanded_', isExpanded, 'count', count, 'root', root, 'i', i)

        if fatherGroup == root:  # Group item
            count: int
            i: int
            startI: int
            iInRoot: int
            count = qtItem.layerTree.topLevelItemCount()
            i = qtItem.layerTree.indexOfTopLevelItem(qtItem)
            startI = 1  # annotation
            if layerTreeType == LayerTreeType.PRIVATE:
                startI = len(self.pubQlrStr) + 1  # after annotation + public
            iInRoot = startI + i - 1 if isUp else (startI + i + 2)

            # print('startI', startI)
            # print('in root-----------i', i, 'iInRoot', iInRoot)

            if (isUp and i == 0) or (not isUp and i == count - 1):
                return

            qtItem.layerTree.takeTopLevelItem(i)
            treeWidgetItem = self._getLayerItem(cloneChildItem, qtItem.checked, qtItem.layerTree, layerTreeType,
                                                isMoved=True)
            qtItem.layerTree.insertTopLevelItem(i - 1 if isUp else i + 1, treeWidgetItem["item"])
            qtItem.layerTree.setItemWidget(treeWidgetItem["item"], 0, treeWidgetItem["widget"])
            self._addChildren(cloneChildItem, treeWidgetItem["item"], qtItem.layerTree, True, layerTreeType)
            del qtItem
            fatherGroup.insertChildNode(iInRoot, cloneChildItem)
            fatherGroup.removeChildNode(childItem)

        else:  # Layer items + subgroups
            count: int
            i: int
            if fatherGroup == root:
                count = qtItem.layerTree.topLevelItemCount()
                i = qtItem.layerTree.indexOfTopLevelItem(qtItem)
            else:
                count = fatherQtItem.childCount()
                i = fatherQtItem.indexOfChild(qtItem)
            # print('count', count)
            # print('layers + subgroup  i............', i)
            if (isUp and i == 0) or (not isUp and i == count - 1):
                return

            fatherQtItem.takeChild(i)
            treeWidgetItem = self._getLayerItem(cloneChildItem, qtItem.checked, qtItem.layerTree, layerTreeType,
                                                isMoved=True)
            fatherQtItem.insertChild(i - 1 if isUp else i + 1, treeWidgetItem["item"])
            qtItem.layerTree.setItemWidget(treeWidgetItem["item"], 0, treeWidgetItem["widget"])
            del qtItem
            fatherGroup.insertChildNode(i - 1 if isUp else i + 2, cloneChildItem)
            fatherGroup.removeChildNode(childItem)

        if layerTreeType == LayerTreeType.PUBLIC:
            self.updatePubQlrSignal.emit()
        # elif layerTreeType == LayerTreeType.PRIVATE:
        #     self.updatePrivQlrSignal.emit()
        #     self.updateYamlSignal.emit()
        else:
            self.updateYamlSignal.emit()

    def _onAnnotationChanged(self, btnCheck: QPushButton):
        if btnCheck.isChecked():
            btnCheck.setIcon(QIcon(os.path.join(self.pluginDir, 'icons/checkbox.png')))
        else:
            btnCheck.setIcon(QIcon(os.path.join(self.pluginDir, 'icons/checkbox_dis.png')))
        self.updateAnnotationSignal.emit(btnCheck.isChecked(), False)
        self.updateYamlSignal.emit()

    def _onBgChanged(self, btnCheck: QPushButton, childItem: QgsLayerTreeLayer):
        if btnCheck.isChecked():
            btnCheck.setIcon(QIcon(os.path.join(self.pluginDir, 'icons/checkbox.png')))
        else:
            btnCheck.setIcon(QIcon(os.path.join(self.pluginDir, 'icons/checkbox_dis.png')))

        childItem.setItemVisibilityChecked(btnCheck.isChecked())
        self.updateYamlSignal.emit()

    def _onAnnotationDeleted(self):
        # print("_onAnnotationDeleted")
        self.updateAnnotationSignal.emit(False, True)
