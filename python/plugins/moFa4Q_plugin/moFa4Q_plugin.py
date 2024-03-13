"""
/***************************************************************************
 MoFa4QPlugin
    QGIS plugin for MoFa4Q
    begin                : 2019-06
    git sha              : https://repo.wheregroup.com/qgis/MoFa4Q/tree/master/python/plugins/moFa4Q_plugin
    email                : info@wheregroup.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
from functools import partial
from threading import Timer
from typing import List, Optional, Union, Dict, Any

import yaml
from PyQt5 import uic
from PyQt5.QtCore import (QCoreApplication, QFile, QPropertyAnimation,
                          QSize, Qt, QTranslator, qVersion, QRect,
                          QDateTime)
from PyQt5.QtGui import QColor, QFont, QIcon, QPalette
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout,
                             QLabel, QPushButton, QWidget, QMenuBar, QAction)
from qgis.core import (Qgis, QgsCoordinateReferenceSystem, QgsProject,
                       QgsRasterLayer, QgsVectorLayer, QgsMapLayer)
from qgis.core import QgsLayerDefinition, QgsLayerTreeLayer, QgsLayerTreeGroup, QgsLayerTreeNode
from qgis.core import QgsLayerTree, QgsMessageLog
from qgis.gui import QgisInterface
from qgis.gui import QgsMapCanvas

from .components.btn_tool_map import BtnToolMap
from .components.custom_list_widget import (CustomQListWidgetItem)
from .resources import *  # noqa
from .utils.address_search import AddressSearch
from .utils.annotations.annotations import Annotations
from .utils.gpkg_metadata import GpkgMetadata
from .utils.gpkg_popup import GpkgPopup
from .utils.gps import Gps
from .utils.installed_program import OsInstallPath
from .utils.layer_trees import LayerTrees
from .utils.measure_tool import MeasureTool
from .utils.obj_search import ObjSearch
from .utils.print import PrintDialog
from .utils.qgis_initalize import QgisInitialize
from .utils.rect_select import RectSelect
from .utils.tr import tr


class MoFa4QPlugin:
    """Main Class of the plugin moFa4Q_plugin"""

    LOCAL_FOLDER_GEOPACKAGE = "../../../geopackages"
    ADDRESS_GEOPACKAGE = "/search/adresse.gpkg"
    GEOSEARCH_GEOPACKAGE = "/search/objektsuche.gpkg"
    DEFAULT_PROJECT = "mofa4q.qgz"
    BUTTON_SIZE = 100
    PROJECT_CRS = "EPSG:25832"
    TITLE = "MoFa4Q - QGIS [MoFa4Q]"
    TIME_FORMAT = "yyyy-MM-dd HH:mm:ss"
    TIMESTAMP_FILE = "_tmstmp.txt"
    DEFAULT_INSTALL_PATH = "C:/MoFa4Q"
    IMPRINT_CONTACT_COMPANY = "WhereGroup"
    IMPRINT_CONTACT_PERSON = "WhereGroup GmbH"
    IMPRINT_CONTACT_PERSON_EMAIL = " (info@wheregroup.com)"
    SHOW_MOFA4Q_CHANGELOG = True
    MAIN_WINDOW_ICON = "icons/mofa4q.ico"
    MOFA4Q_CHANGELOG_NAME = "changelog.txt"

    def __init__(self, iface: QgisInterface):
        QgsMessageLog.logMessage(f"PLUGIN {os.path.basename(__file__)}: init", level=Qgis.Info)
        print(f"PLUGIN {os.path.basename(__file__)}: init")
        # Save reference to the QGIS interface
        self.iface = iface
        self.pluginDir = os.path.dirname(__file__)
        self.geopackageDir = os.path.normcase(os.path.join(self.pluginDir, self.LOCAL_FOLDER_GEOPACKAGE))
        self.profile_path = os.path.normcase(self.iface.userProfileManager().userProfile().folder())
        self.locate_install_path = OsInstallPath.get_locate_programs('mofa4q')

        #
        if os.path.exists(self.locate_install_path[1]):
            #print('locate_install_path', self.locate_install_path[0])
            #print('locate_install_path', self.locate_install_path[1])
            self.DEFAULT_INSTALL_PATH = self.locate_install_path[1]
            print(f"PLUGIN {os.path.basename(__file__)}: set new DEFAULT_INSTALL_PATH")


        # Check DEFAULT_INSTALL_PATH and profile_path
        if (os.path.exists(self.DEFAULT_INSTALL_PATH)) and (self.DEFAULT_INSTALL_PATH == self.profile_path):
            self.metadataPath = os.path.normcase(os.path.join(self.DEFAULT_INSTALL_PATH, "manifest.txt"))
            self.mofa4QChangelogPath = os.path.join(self.DEFAULT_INSTALL_PATH, self.MOFA4Q_CHANGELOG_NAME)
        elif self.DEFAULT_INSTALL_PATH != self.profile_path:
            self.metadataPath = os.path.normcase(os.path.join(self.DEFAULT_INSTALL_PATH, "manifest.txt"))
            self.mofa4QChangelogPath = os.path.join(self.DEFAULT_INSTALL_PATH, self.MOFA4Q_CHANGELOG_NAME)
        else:
            self.metadataPath = os.path.normcase(os.path.join(self.pluginDir, "metadata.txt"))
            self.DEFAULT_INSTALL_PATH = self.profile_path
            self.mofa4QChangelogPath = os.path.join(self.DEFAULT_INSTALL_PATH, self.MOFA4Q_CHANGELOG_NAME)

        # initialize paths and reload QSettings()
        QgisInitialize(self.iface, self.profile_path, self.DEFAULT_INSTALL_PATH, self.DEFAULT_PROJECT)

        # initialize locale
        self.locale = QgisInitialize.get_locale(self)

        locale_path = os.path.join(
            self.pluginDir,
            'i18n',
            'lng_{}.qm'.format(self.locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.lblBgWidget: Optional[QLabel] = None
        self.leftPanel: Optional[QWidget] = None
        self.leftPanelWidth: Optional[float] = None
        self.addressSearch: Optional[AddressSearch] = None
        self.objSearch: Optional[ObjSearch] = None
        self.gpkgPopup: Optional[GpkgPopup] = None

        self.closeLeftPanelAnimation: bool = False
        self.mapButtons: Dict[str, BtnToolMap] = {}
        self.gpkgNames: List[str] = []
        self.printDialog: Optional[PrintDialog] = None
        self.rectSelect: Optional[RectSelect] = None

    def initGui(self) -> None:
        """Init plugin."""
        QgsMessageLog.logMessage(f"PLUGIN {os.path.basename(__file__)}, readPath:" +
                                 QgsProject.instance().readPath("./"), level=Qgis.Info)
        print(f"PLUGIN {os.path.basename(__file__)}, readPath:" + QgsProject.instance().readPath("./"))

        if QgsProject.instance().readPath("./") == "./":
            QgsMessageLog.logMessage(tr("Project QGZ will be loaded"), level=Qgis.Info)
            QgsProject.instance().readProject.connect(self.runProjectReady)
        else:
            # following code is for the plugin reloaded (done via "Plugin Reloader")
            QgsMessageLog.logMessage(tr("Plugin reloaded"), level=Qgis.Info)
            self.runProjectReady()

    def unload(self) -> None:
        """Removes all the 4 buttons and close the left panel."""
        QgsMessageLog.logMessage(tr(f"PLUGIN {os.path.basename(__file__)}: unload"), level=Qgis.Info)
        print(tr(f"PLUGIN {os.path.basename(__file__)}: unload"))
        # if True == True: # only for text purpouse
        try:
            self.btnBurger.setParent(None)
            # print('remove btnBurger')

            btnToolMap: BtnToolMap
            for btnToolMap in self.mapButtons.values():
                btnToolMap.btn.setParent(None)
                if btnToolMap.tool:
                    btnToolMap.tool.close()
                if btnToolMap.additionalTool:
                    btnToolMap.additionalTool.close()

            # self.mapButtons = {}

            if self.leftPanel is not None:
                self.leftPanel.setParent(None)
                self.leftPanel = None
                # print('remove leftPanel')

            self.lblBgWidget = None

            # close connection for search
            if self.addressSearch is not None:
                self.addressSearch.resetAll()

            # close connection for search
            if self.objSearch is not None:
                self.objSearch.resetAll()

            # QgsProject.instance().removeAllMapLayers()

            rootChild: QgsLayerTreeNode
            root = QgsProject.instance().layerTreeRoot()
            for rootChild in root.children():
                if type(rootChild) == QgsLayerTreeGroup:
                    self._removeGroup(rootChild.name())
                elif type(rootChild) == QgsLayerTreeLayer:
                    if type(rootChild.layer()) != QgsRasterLayer:
                        root.removeChildNode(rootChild)

            if self.rectSelect:
                self.rectSelect.reset()

            self.annotations.reset()

        except Exception as e:  # necessary if in debug mode will be deleted one of prev objects
            print('Exception in method unload', e)

    def runProjectReady(self) -> None:
        """Buttons + layers can be initialized only when project/canvas is ready."""
        QgsMessageLog.logMessage(tr(f"PLUGIN {os.path.basename(__file__)}: runProjectReady"), level=Qgis.Info)
        print(f"PLUGIN {os.path.basename(__file__)}: runProjectReady")

        self._readProjConf()

        isDebug = False
        if "isDebug" in self.prjConfig and self.prjConfig["isDebug"]:
            isDebug = True

        for el in self.iface.mainWindow().findChildren(QMenuBar):
            el.setVisible(isDebug)

        # Check screen resolution and adjust gui elements
        self._adjustToScreenSize()

        # workaround to change MainWindows Icon and remove * from title
        self._changeQgisMainWindow()

        self._initBgLayer()
        self._initPrivLayers()
        self._initPubLayers()

        self._addBurger()

        self.mapCanvasWidth = self.iface.mapCanvas().width()
        self.mapCanvasHeight = self.iface.mapCanvas().height()

        self.mapButtons['zoomIn'] = BtnToolMap('zoomIn', 'plus_icon.png', QPushButton(), self._runZoomIn, False)
        self.mapButtons['zoomOut'] = BtnToolMap('zoomOut', 'minus_icon.png', QPushButton(), self._runZoomOut, False)
        self.mapButtons['zoomToExtend'] = BtnToolMap('zoomToExtend', 'extent_icon.png', QPushButton(),
                                                     self._runZoomOutToExtent, False)
        self.mapButtons['gps'] = BtnToolMap('gps', 'gps_icon.png', QPushButton(), self._runGps, False)
        self.mapButtons['measureTool'] = BtnToolMap('measureTool', 'line_icon.png', QPushButton(),
                                                    self._runLineCalculation, False)
        self.mapButtons['measureAreaTool'] = BtnToolMap('measureAreaTool', 'area_icon.png', QPushButton(),
                                                        self._runAreaCalculation, False)
        self.mapButtons['featureInfo'] = BtnToolMap('infoIcon', 'info_icon.png', QPushButton(),
                                                    self._runFeatureInfo, True)
        self.mapButtons['print'] = BtnToolMap('print', 'print_icon.png', QPushButton(), self._runPrint, False)

        self.annotations = Annotations(self.iface, self.mapButtons, self.pluginDir, self.prjConfig)
        self.annotations.updateToggleToolsSignal.connect(self._toggleBtnTools)
        # self.annotations.updateAnnotationSignal.connect(self._saveAnnotations)

        btnCount: int = 0
        maxRowBtn: Optional[int] = None
        for btnName in self.mapButtons.keys():
            # print('maxRowBtn', maxRowBtn)
            btnToolMap: BtnToolMap = self.mapButtons[btnName]
            maxRowBtn = self._addMapButton(btnToolMap, btnCount, maxRowBtn)
            # if not btnToolMap.isLeft:
            btnCount = btnCount + 1

        self.iface.mapCanvas().renderStarting.connect(self._refreshBtnsPosAndLbl)

        self._initLeftPanel()

        self._initCheckData()

        self._showMaptips()

        # workaround (see comment of the method _setDirty())
        timer = Timer(2, self._setDirty)
        timer.start()

    # private methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _getBgLayer(self) -> Optional[QgsRasterLayer]:
        """
        Finds out whether a background layer, is defined directly in the project
        and it is a raster

        Returns:
            layer if exists (bg image maybe not available in not productive env).
        """
        layer: Optional[QgsRasterLayer] = None
        layersFromPrj = QgsProject.instance().layerTreeRoot().children()
        # print(layersFromPrj, len(layersFromPrj))
        if len(layersFromPrj) > 1:
            self.iface.messageBar().pushMessage("Fehler",
                                                tr("Mehrere Layer sind im Projekt definiert."), level=Qgis.Warning)
        if len(layersFromPrj) == 1:
            if layersFromPrj[0].layer().type() != QgsMapLayer.RasterLayer:
                self.iface.messageBar().pushMessage("Fehler",
                                                    tr("Der Layer im Projekt ist kein Raster-Layer."),
                                                    level=Qgis.Warning)
            else:
                layer = layersFromPrj[0].layer()
        return layer if layer and layer.isValid() else None

    def _initBgLayer(self) -> None:
        self.bgLayer: Optional[QgsRasterLayer] = self._getBgLayer()
        if self.bgLayer and 'bgGpkg' in self.prjConfig:
            config = self.prjConfig['bgGpkg']
            if config and 'isVisible' in config and not config['isVisible']:
                QgsProject.instance().layerTreeRoot().findLayer(self.bgLayer.id()).setItemVisibilityChecked(False)

    def _initPrivLayers(self) -> None:
        """Initialization of all private layers"""
        self.privAllGeopackages = self._getAllGeopackagesInFolder('private')

        privGpkgs: List[any] = self.prjConfig['privateGpkgs']
        for gpkg in reversed(privGpkgs):
            if 'layer' in gpkg:
                filename: str = gpkg['layer'] + '.gpkg'
                # check if file still exists
                if filename not in self.privAllGeopackages.keys():
                    self.iface.messageBar().pushMessage(tr("Fehler"), tr(
                        f"File nicht gefunden: {filename}"), level=Qgis.Warning)
                    continue

                self._createPrivateLayersFromGpkg(gpkg)

        self.iface.mapCanvas().refresh()

    def _initPubLayers(self) -> None:
        """Reads sequence_qlr and import them in qgis project"""
        sequenceQlr = os.path.join(self.geopackageDir, "public", "sequence_qlr.yml")
        if os.path.isfile(sequenceQlr):
            with open(sequenceQlr, 'r') as stream:
                self.pubQlrStr = yaml.safe_load(stream)
                if not self.pubQlrStr:
                    self.pubQlrStr = []
        else:
            self.pubQlrStr = []

        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        # self.qlrStr = ['group2', 'group3', 'test2']
        qlrStr: str
        for qlrStr in self.pubQlrStr:
            qlrItem: str = os.path.join(self.geopackageDir, "public", qlrStr + '.qlr')
            isValid: bool = QgsLayerDefinition().loadLayerDefinition(qlrItem, QgsProject.instance(), root)
            if not isValid:
                self.iface.messageBar().pushMessage("Warnung",
                                                    tr(f"QLR-Datei {qlrStr + '.qlr'} nicht gültig"), level=Qgis.Warning)

        # public are added at the bottom of layer tree, code fixes order of the public layers,
        # they go to the top (annotation layer is not added yet)
        pubGroups: List[QgsLayerTreeNode] = root.children()[-len(self.pubQlrStr):]
        # print('pubGroups', pubGroups)
        for pubGroup in reversed(pubGroups):
            # print(pubGroup)
            root.insertChildNode(0, pubGroup.clone())
            root.removeChildNode(pubGroup)

    def _initLeftPanel(self) -> None:
        self.leftPanel = uic.loadUi(os.path.join(
            self.pluginDir, 'components', 'left_panel.ui'))
        self.leftPanel.setParent(self.iface.mapCanvas())
        self.leftPanel.setAutoFillBackground(True)
        self.leftPanel.hide()
        p = QPalette()
        p.setColor(self.leftPanel.backgroundRole(), QColor(230, 230, 230))
        self.leftPanel.setPalette(p)
        # self.leftPanel.resize(QSize(self.leftPanelWidth, 870))
        self.leftPanel.scrollArea.setWidgetResizable(True)
        self.leftPanel.closeBtn.setCursor(Qt.PointingHandCursor)
        self.leftPanel.closeBtn.clicked.connect(self._closeLeftPanel)
        self.leftPanel.mQgsFileWidget.fileWidget().setFilter("*.gpkg")
        self.leftPanel.importGpkFile.clicked.connect(self._importFile)

        self.leftPanel.scrollArea.setStyleSheet(self.scrollAreaStyleSheet)

        self.leftPanel.lineEditSearch.setFont(self.labelFont)
        self.leftPanel.pushButtonShowAddress.setFont(self.labelFont)

        self.leftPanel.labelInfo.setFont(self.labelFont)

        self.layerTrees = LayerTrees(self.iface, self.leftPanel, self.pluginDir, self.geopackageDir, self.prjConfig,
                                     self.bgLayer, self.pubQlrStr, self.annotations.isVisible)
        self.layerTrees.updateYamlSignal.connect(self._saveProjConf)
        self.layerTrees.updatePubQlrSignal.connect(self._saveQlrForPubLayers)
        # self.layerTrees.updatePrivQlrSignal.connect(self._saveQlrForPrivLayers)
        self.layerTrees.updateAnnotationSignal.connect(self._updateAnnotationFromLayerTree)

        self._initDataSourceLists()

        # starts the search initialization
        self.addressSearch = AddressSearch(self.iface, self.geopackageDir + self.ADDRESS_GEOPACKAGE,
                                           self.leftPanel.lineEditSearch, self.leftPanel.pushButtonShowAddress)

        self.objSearch = ObjSearch(self.iface, self.geopackageDir + self.GEOSEARCH_GEOPACKAGE,
                                   self.leftPanel.lineEditObjSearch, self.leftPanel.pushButtonShowObjSearch)

        self._addInfo()

        # sum of closed page in left panel
        self.closedPagesHeight = (self.leftPanel.page_2.size().height() + self.leftPanel.page_3.size().height() +
                                  self.leftPanel.page_4.size().height() + self.leftPanel.page_5.size().height())

        if self.leftPanelWidth < self.layerTrees.internWidth + 290:
            self.leftPanelWidth = self.layerTrees.internWidth + 290
        # self.leftPanelWidth = 400
        # self.leftPanel.resize(QSize(self.leftPanelWidth, 870))

    def _adjustToScreenSize(self) -> None:
        app: QCoreApplication = QApplication.instance()
        screen = app.primaryScreen()
        size: float = screen.size()
        width: float = size.width()
        self.labelFont = QFont('MS Shell Dlg 2', 11)

        # Set size for PC (1920 x 1080)
        if width < 2736:
            self.BUTTON_SIZE = 50
            self.leftPanelWidth = 530

            # Layeritems
            self.btnCheckWidth = 50
            self.moveBtnWidth = 30

            # DataSources
            self.scrollAreaStyleSheet = ''

        # Special implementation for Surface Pro (2736 x 1744)
        else:
            self.BUTTON_SIZE = 100
            self.leftPanelWidth = 900

            # LayerItems
            self.btnCheckWidth = 100
            self.moveBtnWidth = 70

        # DataSources
        self.scrollAreaStyleSheet = """
            QLabel, QPushButton, QWidget {
                font-size: 11pt;
            }
            # scrollAreaWidgetContents > QLabel {
                font-size: 12pt;
            }
        """

    def _onDirtyChanged(self):
        """Sets the project title without "*" and sets project_crs is used"""
        self.iface.mainWindow().setWindowTitle(self.TITLE)

        if QgsProject.instance().crs().authid() != self.PROJECT_CRS:
            QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(self.PROJECT_CRS))

    def _addBurger(self) -> None:
        self.btnBurger = QPushButton()
        self.btnBurger.resize(self.BUTTON_SIZE + 8, self.BUTTON_SIZE + 8)
        self.btnBurger.setIcon(QIcon(':/plugins/moFa4Q_plugin/icons/burger.png'))
        self.btnBurger.setIconSize(QSize(self.BUTTON_SIZE, self.BUTTON_SIZE))
        self.btnBurger.setParent(self.iface.mapCanvas())
        self.btnBurger.show()
        self.btnBurger.clicked.connect(self._openLeftPanel)
        self.btnBurger.setCursor(Qt.PointingHandCursor)

    def _addInfo(self) -> None:
        app_version = ""
        app_name = self.TITLE
        app_company = self.IMPRINT_CONTACT_COMPANY
        support_qgis = Qgis.version().split('-', 1)[0]
        mof4q_changelog_content = ""

        with open(self.metadataPath, "r") as file:
            rows = (line.split("=") for line in file)
            for row in rows:
                if row[0] == "appVersion":
                    app_version = row[1]

        if self.SHOW_MOFA4Q_CHANGELOG:
            original_string = self.mofa4QChangelogPath
            original_string = original_string.replace("\\", '/');
            if os.path.isfile(os.path.normcase(self.mofa4QChangelogPath)):
                with open(original_string, 'r') as f:
                    mof4q_changelog_content = f.read();

        self.leftPanel.labelInfo.setText(
            tr("Name: {}\nVersion: {}\nQGIS-Version: {}\nLanguage: {}\n\nKontaktdaten\n  Firma: {}\n  Ansprechpartner: {}\n  Email: {}\n\nÄnderungsprotokoll:\n{}")
            .format(app_name, app_version, support_qgis, self.locale, app_company,
                    self.IMPRINT_CONTACT_PERSON, self.IMPRINT_CONTACT_PERSON_EMAIL, mof4q_changelog_content)
        )
        self.leftPanel.labelInfo.setWordWrap(True)

    def _addMapButton(self, btnToolMap: BtnToolMap, btnCount: int, maxRowBtn: Optional[int]) -> int:
        """Adds button on the canvas on the right side. It is responsive to the dimension of the screen.
        A second colum of button will be added, if not enough space.

        Args:
            btnToolMap: a button shown on the right side on the canvas
            btnCount: numeration of button (first button with index 0 is shown in the top right corner of the canvas)
            maxRowBtn: max number of button shown in a column

        Returns:
            max number of button shown in a column
        """
        btnToolMap.btn.resize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        width = self.iface.mapCanvas().size().width()
        height = self.iface.mapCanvas().size().height()
        y = (self.BUTTON_SIZE + 5) * btnCount

        # find how many buttons are visible in one column
        if not maxRowBtn and ((self.BUTTON_SIZE + 5) * (btnCount + 1)) > height:
            maxRowBtn = btnCount

        if maxRowBtn:
            y = y - ((self.BUTTON_SIZE + 5) * maxRowBtn)
        columnNum: int = 2 if maxRowBtn else 1
        btnToolMap.btn.move(width - (columnNum * self.BUTTON_SIZE) - (5 if columnNum > 1 else 0), y)

        btnToolMap.btn.setIcon(QIcon(':/plugins/moFa4Q_plugin/icons/' + btnToolMap.iconPath))
        btnToolMap.btn.setIconSize(QSize(self.BUTTON_SIZE, self.BUTTON_SIZE))
        btnToolMap.btn.setParent(self.iface.mapCanvas())
        btnToolMap.btn.setCheckable(btnToolMap.checkable)
        btnToolMap.btn.show()
        btnToolMap.btn.clicked.connect(btnToolMap.fn)
        btnToolMap.btn.setCursor(Qt.PointingHandCursor)
        if btnToolMap.checkable:
            btnToolMap.btn.setCheckable(True)

        return maxRowBtn

    def _readProjConf(self) -> None:
        """Reads project configuration file"""
        prjConf = os.path.join(self.pluginDir, "prj_conf.yaml")
        if os.path.isfile(prjConf):
            with open(prjConf, 'r') as stream:
                dataLoaded = yaml.safe_load(stream)
            self.prjConfig = dataLoaded if dataLoaded else {}
            # print('self.prjConfig', self.prjConfig)
        else:
            self.prjConfig = {}

        if 'privateGpkgs' not in self.prjConfig or not self.prjConfig['privateGpkgs']:
            self.prjConfig['privateGpkgs'] = []

    def _writeProjConf(self) -> None:
        """Writes project configuration file"""
        with open(os.path.join(self.pluginDir, "prj_conf.yaml"), 'w', encoding='utf8') as outfile:
            privLayerConfig = []
            bgLayerConfig = {}
            childItem: Union[QgsLayerTreeLayer, QgsLayerTreeGroup]
            for childItem in QgsProject.instance().layerTreeRoot().children():
                if childItem.name() in self.pubQlrStr:
                    pass
                    # pubLayerConfig.append(self._prepareConf(childItem))
                elif childItem.name() in [name[:-5] for name in self.privAllGeopackages]:
                    privLayerConfig.append(self._prepareConf(childItem))
                elif self.bgLayer and childItem.name() == self.bgLayer.name():
                    bgLayerConfig = {'isVisible': childItem.isVisible()}

                annotationConfig = {'isVisible': self.annotations.isVisible}

            # self.prjConfig['publicGpkgs'] = pubLayerConfig
            self.prjConfig['privateGpkgs'] = privLayerConfig
            self.prjConfig['bgGpkg'] = bgLayerConfig
            self.prjConfig['annotations'] = annotationConfig

            yaml.dump(self.prjConfig, outfile)

    def _writeQlrsForPubLayers(self) -> None:
        """Normal update of QLR files due to performance problem is done in QGIS-macro when the project is going to close. # noqa
        However, the change of order of the main qlr groups is done soon => update file sequence_qlr.yml
        """
        qlrList: List[str] = []
        childItem: Union[QgsLayerTreeLayer, QgsLayerTreeGroup]
        for childItem in QgsProject.instance().layerTreeRoot().children():
            if childItem.name() in self.pubQlrStr:
                qlrList.append(childItem.name())
                # qlrFile: str = os.path.join(self.geopackageDir, "public", childItem.name() + '.qlr')
                # QgsLayerDefinition().exportLayerDefinition(qlrFile, [childItem])

        qlrListFileOutput: str = os.path.join(self.geopackageDir, "public", 'sequence_qlr.yml')
        # print('qlrList', qlrList)
        with open(qlrListFileOutput, 'w', encoding='utf8') as outfile:
            yaml.dump(qlrList, outfile)

    def _prepareConf(self, childItem: Union[QgsLayerTreeLayer, QgsLayerTreeGroup]) -> any:
        isGroup: bool = type(childItem) == QgsLayerTreeGroup
        if isGroup:
            group = {
                'layer': childItem.name(),
                'isVisible': childItem.itemVisibilityChecked(),
                'layers': []
            }
            for childChildItem in childItem.children():
                group['layers'].append(self._prepareConf(childChildItem))
            return group
        else:
            layer = {
                'layer': childItem.name(),
                'isVisible': childItem.itemVisibilityChecked(),
            }
            return layer

    def _createPrivateLayersFromGpkg(self, configInfo: any) -> None:
        """Creates private layers from a geopackage. It applies also the style to the layer if it is stored in gpkg.
        Initialization of this private layers is resource-intensive.

        Args:
            configInfo: info coming from yaml file
        """
        filename: str = configInfo['layer'] + '.gpkg'
        isVisible: bool = configInfo['isVisible']
        gpkgMetadata = GpkgMetadata(self.iface, os.path.join(self.geopackageDir, 'private', filename))
        allLayersInGpkg: List[any] = gpkgMetadata.getInfo()
        currentCount: int = 0

        # add layer group to qgis treeRoot
        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        groupNode: QgsLayerTreeGroup = root.insertGroup(currentCount, filename[:-5])

        # get all tables inside the added geopackage and check if they are vector, raster
        # or something else (e.g. layer styles)
        layerInGpkg: any
        for layerInSettings in configInfo['layers']:
            for layerInfo in allLayersInGpkg:
                if layerInfo['identifier'] == layerInSettings['layer']:
                    layerInGpkg = layerInfo
                    break

            # print(filename, layerInGpkg, groupNode, layerInSettings['isVisible'])
            self._createPrivateLayer(filename, layerInGpkg, groupNode, layerInSettings['isVisible'])

        groupNode.setItemVisibilityChecked(isVisible)

    def _createPrivateLayer(self, filename: str, layerInGpkg: any, groupNode: QgsLayerTreeGroup,
                            isVisible: bool) -> None:
        # print('filename', filename)
        layer: QgsMapLayer
        if layerInGpkg["data_type"] == "features":  # add vector layer
            path = self.geopackageDir + "/private/" + filename + "|layername=" + layerInGpkg["identifier"]
            layer = QgsVectorLayer(path, layerInGpkg["identifier"], "ogr")
        elif layerInGpkg["data_type"] in ["tiles", "2d-gridded-coverage"]:  # add raster layer
            path = "GPKG:" + self.geopackageDir + "/private/" + filename + ":" + layerInGpkg["identifier"]
            layer = QgsRasterLayer(path, layerInGpkg["identifier"], "gdal")

        if layer.isValid():
            QgsProject.instance().addMapLayer(layer, False)
            currentLayerCount = len(groupNode.children())
            layerNode = groupNode.insertLayer(currentLayerCount, layer)
            layerNode.setItemVisibilityChecked(isVisible)
        else:
            self.iface.messageBar().pushMessage("Fehler",
                                                tr(f"Layer {layerInGpkg['identifier']} konnte nicht hinzugefügt\
                                                            werden."), level=Qgis.Warning)

    def _removeGroup(self, name: str) -> None:
        """
        Removes top group/layer. It is used only in unload of plugin - not production

        Args:
            name: name of group
        """
        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        group: QgsLayerTreeGroup = root.findGroup(name)
        if group is not None:
            for child in group.children():
                dump = child.dump()
                QgsProject.instance().removeMapLayer(dump.split("=")[-1].strip())
            root.removeChildNode(group)

    def _refreshBtnsPosAndLbl(self) -> None:
        """
        Refresh the position of right buttons, if canvas dimension has been changed.
        Additionally, set the style for the label of the background layer if exists.
        """
        if self.bgLayer and self.lblBgWidget and self.bgLayer.hasScaleBasedVisibility():
            if self.bgLayer.maximumScale() > self.iface.mapCanvas().scale():
                self.lblBgWidget.setStyleSheet("color: gray")
            else:
                self.lblBgWidget.setStyleSheet("color: black")
        width = self.iface.mapCanvas().size().width()
        height = self.iface.mapCanvas().size().height()

        btnToolMap: BtnToolMap
        btnCount: int = 0
        maxRowBtn: Optional[int] = None
        for btnName in self.mapButtons.keys():
            btnToolMap: BtnToolMap = self.mapButtons[btnName]
            y: float = (self.BUTTON_SIZE + 5) * btnCount
            if not maxRowBtn and ((self.BUTTON_SIZE + 5) * (btnCount + 1)) > height:
                maxRowBtn = btnCount

            if maxRowBtn:
                y = y - ((self.BUTTON_SIZE + 5) * maxRowBtn)
            columnNum: int = 2 if maxRowBtn else 1
            btnToolMap.btn.move(width - (columnNum * self.BUTTON_SIZE) - (5 if columnNum > 1 else 0), y)
            btnCount = btnCount + 1

        if self.mapCanvasWidth != width:
            self.mapCanvasWidth = width

        if self.mapCanvasHeight != height:
            self.mapCanvasHeight = height
            if self.leftPanel is not None:
                self.leftPanel.resize(self.leftPanel.size().width(), height)

        tool: PrintDialog = self.mapButtons['print'].tool
        if tool and tool.isVisible():
            tool.showPreview()

    def _updateAnnotationFromLayerTree(self, isChecked: bool, isDel: bool) -> None:
        # print('_updateAnnotationFromLayerTree', isChecked, isDel)
        if not isDel:
            self.annotations.setAnnotationsVisibility(isChecked)
        else:
            self.annotations.delAllAnnotations()

    def _openLeftPanel(self) -> None:
        """Opens the left panel over the canvas"""
        self.btnBurger.hide()

        self.leftPanel.show()
        self._slideAnimation(False)

    def _closeLeftPanel(self) -> None:
        """Closes the left panel."""
        if self.leftPanel is not None:
            self.btnBurger.show()
            self._slideAnimation(True)

    def _slideAnimation(self, isOpen) -> None:
        height = self.iface.mapCanvas().size().height()
        self.leftPanel.resize(self.leftPanelWidth, height)
        self.leftPanel.toolBox.resize(self.leftPanel.toolBox.size().width(), height)
        self.leftPanel.toolBox2.resize(self.leftPanel.toolBox.size().width() - 20, height)
        self.leftPanel.privLayerTree.resize(self.leftPanel.toolBox.size().width() - 20,
                                            height - self.closedPagesHeight - 35)
        self.leftPanel.pubLayerTree.resize(self.leftPanel.toolBox.size().width() - 20,
                                           height - self.closedPagesHeight - 35)

        openGeometry = QRect(0, 0, self.leftPanelWidth, height)
        closedGeometry = QRect(0, 0, 0, height)

        self.animation = QPropertyAnimation(self.leftPanel, b"geometry")
        self.animation.setDuration(200)

        if isOpen:  # open, will be closed
            self.leftPanel.hide()
        else:  # close, will be opened
            self.leftPanel.show()
            self.animation.setStartValue(closedGeometry)
            self.animation.setEndValue(openGeometry)
            self.animation.start()

    def _getAllGeopackagesInFolder(self, subFolder: str) -> Dict:
        geopackages = {}

        for fileName in os.listdir(self.geopackageDir + '/' + subFolder):
            if fileName.endswith(".gpkg"):
                try:
                    gpkgMetadata = GpkgMetadata(self.iface, os.path.join(self.geopackageDir, subFolder, fileName))
                    geopackages[fileName] = gpkgMetadata.getInfo()
                except Exception:
                    self.iface.messageBar().pushMessage("Fehler",
                                                        tr(f"Info-Metadata vom Layer {fileName} ist nicht lesbar."),
                                                        level=Qgis.Warning)
        return geopackages

    def _initDataSourceLists(self) -> None:
        # print('initDataSourceLists()')
        self.leftPanel.dataSourceList.setSelectionMode(QAbstractItemView.NoSelection)
        self.leftPanel.notSavedDataSourceList.setSelectionMode(QAbstractItemView.NoSelection)
        gpkgNames: List[str] = [name[:-5] for name in self.privAllGeopackages.keys()]
        for groupNode in QgsProject.instance().layerTreeRoot().children():
            if groupNode.name() in gpkgNames:
                gpkgNames.remove(groupNode.name())
                itemN = self._getSavedDataSourceItem(groupNode.name())
                self.leftPanel.dataSourceList.addItem(itemN["item"])
                self.leftPanel.dataSourceList.setItemWidget(
                    itemN["item"], itemN["widget"])
        for fileName in gpkgNames:
            # print(os.path.join(root, fileName))
            itemN = self._getNotSavedDataSourceItem(fileName)
            self.leftPanel.notSavedDataSourceList.addItem(itemN["item"])
            self.leftPanel.notSavedDataSourceList.setItemWidget(
                itemN["item"], itemN["widget"])

    def _getSavedDataSourceItem(self, fileName: str) -> Dict[str, Any]:
        item = CustomQListWidgetItem()
        item.setId(fileName)
        widget = QWidget()
        lblWidget = QLabel(fileName)
        btnDel = QPushButton(tr("Löschen"))
        btnDel.setCursor(Qt.PointingHandCursor)
        hLayout = QHBoxLayout(self.leftPanel.dataSourceList)
        hLayout.addWidget(lblWidget)
        hLayout.addStretch()
        hLayout.addWidget(btnDel)
        btnDel.clicked.connect(partial(self._onDataSourceDelClicked, fileName))

        # hLayout.setSizeConstraint(QLayout.SetFixedSize)
        widget.setLayout(hLayout)
        item.setSizeHint(widget.sizeHint())

        return {'item': item, 'widget': widget}

    def _getNotSavedDataSourceItem(self, fileName: str) -> Dict[str, Any]:
        item = CustomQListWidgetItem()
        item.setId(fileName)
        widget = QWidget()
        lblWidget = QLabel(fileName)
        btnAdd = QPushButton(tr("Hinzufügen"))
        btnAdd.setCursor(Qt.PointingHandCursor)
        hLayout = QHBoxLayout(self.leftPanel.dataSourceList)
        hLayout.addWidget(lblWidget)
        hLayout.addStretch()
        hLayout.addWidget(btnAdd)

        btnAdd.clicked.connect(partial(self._onDataSourceAddClicked, fileName))

        # hLayout.setSizeConstraint(QLayout.SetFixedSize)
        widget.setLayout(hLayout)
        item.setSizeHint(widget.sizeHint())

        return {'item': item, 'widget': widget}

    def _onDataSourceDelClicked(self, fileName: str) -> None:
        """Removes datasource from project and from the private tree layer

        Args:
            fileName: file name
        """
        self.layerTrees.removeLayerInPrivLayerTree(fileName)

        # remove from datasource and add to available
        for i in range(self.leftPanel.dataSourceList.count()):
            if self.leftPanel.dataSourceList.item(i).getId() == fileName:
                self.leftPanel.dataSourceList.takeItem(i)
                break

        itemN = self._getNotSavedDataSourceItem(fileName)
        self.leftPanel.notSavedDataSourceList.addItem(itemN["item"])
        self.leftPanel.notSavedDataSourceList.setItemWidget(itemN["item"], itemN["widget"])

        self.iface.mapCanvas().refresh()

        self.privAllGeopackages = self._getAllGeopackagesInFolder('private')
        self._saveProjConf()

    def _onDataSourceAddClicked(self, fileName: str) -> None:
        """Adds datasource to project and to the private tree layer

        Args:
            fileName: file name
        """
        dirGeopackage: str = os.path.abspath(os.path.join(self.pluginDir, self.LOCAL_FOLDER_GEOPACKAGE, 'private'))
        gpkgMetadata = GpkgMetadata(self.iface, os.path.join(dirGeopackage, fileName + '.gpkg'))
        allLayersInGpkg: List[str] = gpkgMetadata.getInfo()

        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        # new private layer should be added after all public layers and 1 layer for annotations
        pubGroupsCount: int = len(self.pubQlrStr)
        group: QgsLayerTreeGroup = root.insertGroup(pubGroupsCount + 1, fileName)
        allLayersInGpkg.sort(key=lambda x: x['identifier'])

        for layerInGpkg in allLayersInGpkg:
            self._createPrivateLayer(fileName + '.gpkg', layerInGpkg, group, True)

        self.layerTrees.addLayerInPrivLayerTree(group)

        itemN = self._getSavedDataSourceItem(fileName)
        self.leftPanel.dataSourceList.insertItem(0, itemN["item"])
        self.leftPanel.dataSourceList.setItemWidget(itemN["item"], itemN["widget"])

        # remove from available datasource and add to saved datasource
        for i in range(self.leftPanel.notSavedDataSourceList.count()):
            if self.leftPanel.notSavedDataSourceList.item(i).getId() == fileName:
                self.leftPanel.notSavedDataSourceList.takeItem(i)
                break

        self.privAllGeopackages = self._getAllGeopackagesInFolder('private')
        self._saveProjConf()

    def _saveProjConf(self) -> None:
        # print('_saveProjConf')
        self._writeProjConf()
        self._onDirtyChanged()

    def _saveQlrForPubLayers(self) -> None:
        print('_saveQlrForPubLayers')
        self._writeQlrsForPubLayers()
        self._onDirtyChanged()

    def _importFile(self) -> None:
        """Imports file in folder"""
        filePath = self.leftPanel.mQgsFileWidget.fileWidget().filePath()
        fileName = os.path.basename(filePath)
        if filePath == "":
            self.iface.messageBar().pushMessage(tr("Fehler"), tr("Keine Datei ausgewählt."), level=Qgis.Warning)
        elif filePath.endswith(".gpkg") is False:
            self.iface.messageBar().pushMessage(tr("Fehler"), tr(
                "Die gewählte Datei ist kein Geopackage."), level=Qgis.Warning)
        elif os.path.isfile(os.path.abspath(os.path.join(self.pluginDir, self.LOCAL_FOLDER_GEOPACKAGE, 'private',
                                                         fileName))):
            self.iface.messageBar().pushMessage(tr("Fehler"), tr("Die Datei existiert bereits."), level=Qgis.Warning)
        else:
            qFile = QFile(filePath)
            if qFile.exists() is False:
                self.iface.messageBar().pushMessage(tr("Fehler"), tr(
                    "Die Datei wurde nicht gefunden."), level=Qgis.Warning)
            else:
                isCopy = qFile.copy(os.path.abspath(os.path.join(
                    self.pluginDir, self.LOCAL_FOLDER_GEOPACKAGE, 'private', fileName)))
                if isCopy is False:
                    self.iface.messageBar().pushMessage(tr("Fehler"),
                                                        tr("Die Datei konnte nicht kopiert werden. Prüfen Sie Ihre Berechtigungen."), # noqa
                                                        level=Qgis.Warning)
                else:
                    self.iface.messageBar().pushMessage(tr("Erfolgreich"), tr("Die Datei wurde kopiert."))
                    itemN = self._getNotSavedDataSourceItem(fileName[:-5])
                    self.leftPanel.notSavedDataSourceList.addItem(itemN["item"])
                    self.leftPanel.notSavedDataSourceList.setItemWidget(itemN["item"], itemN["widget"])

    def _checkGpkg28DayOlder(self) -> List[str]:
        """Shows a warning popup if public geopackages are older then 28 days/ 4 weeks

        Returns:
            names of geopackages which are too old
        """
        fourWeeksAgo = QDateTime.currentDateTime().addDays(-28)
        gpkgOlder4Weeks: List[str] = []

        for fileName in self.pubQlrStr:
            if fileName.lower() != 'osm' and fileName.lower() != 'topplus_grau':
                # print("=====>>>  ", fileName)
                tmpsFile: str = os.path.join(self.geopackageDir, 'public',
                                             os.path.splitext(fileName)[0] + self.TIMESTAMP_FILE)
                # print("loop", tmpsFile)
                if QFile.exists(tmpsFile):
                    # print("tmpsFile exists")
                    with open(tmpsFile, "r") as f:
                        updatedDate = QDateTime.fromString(f.readline(), self.TIME_FORMAT)
                        # print("updatedDate", updatedDate.toString())
                        # print("compare: ",  updatedDate.toTime_t(), fourWeeksAgo.toTime_t(), updatedDate.toTime_t() < fourWeeksAgo.toTime_t())  # noqa
                        if updatedDate.toString() == "" or updatedDate.toTime_t() < fourWeeksAgo.toTime_t():
                            gpkgOlder4Weeks.append(fileName + '.gpkg')

        return gpkgOlder4Weeks

    def _initCheckData(self) -> None:
        """Checks data at the initialization (public layers, qlrs, timestamps).
        If there is a problem, a warning is displayed.
        """
        allGeopackages = self._getAllGeopackagesInFolder('public')
        if not any(allGeopackages.values()):
            self.gpkgPopup = GpkgPopup(self.iface, self.iface.mainWindow())
            self.gpkgPopup.setSyncToolPath(self.DEFAULT_INSTALL_PATH)
            self.gpkgPopup.show(titelName=tr('keine Geopackages im Ordner public gefunden. Starte das SyncTool!'))
        else:
            gpkgOlder4Weeks = self._checkGpkg28DayOlder()
            corruptQlrs = self._checkQlrDim0Kb()
            if len(gpkgOlder4Weeks) > 0 or len(corruptQlrs) > 0:
                self.gpkgPopup = GpkgPopup(self.iface, self.iface.mainWindow())
                self.gpkgPopup.show(gpkgOlder4Weeks=gpkgOlder4Weeks, corruptQlrs=corruptQlrs)

    def _checkQlrDim0Kb(self) -> List[str]:
        """Checks if one of QLR files in public is empty (0 KB). It meas it is corrupt!
        In this case, the corresponding GPKG file should be deleted, so that the synch-tool will download the file again

        Returns:
            names of QLR corrupt files
        """
        corruptQlrs: List[str] = []
        publicDir = os.path.join(self.geopackageDir, 'public')
        for fileName in os.listdir(publicDir):
            qlrFile = os.path.join(publicDir, fileName)
            if fileName.endswith(".qlr") and os.path.getsize(qlrFile) == 0:
                corruptQlrs.append(fileName)
                tmpName = os.path.join(publicDir, os.path.splitext(fileName)[0] + '_qlr_tmstmp.txt')
                if os.path.isfile(tmpName):
                    open(tmpName, 'w').close()

        return corruptQlrs

    def _showMaptips(self) -> None:
        """Activates action map tips ("Kartenhinweise anzeigen"). At the click of the map it will be shown
        what is setting under layer properties in tab display
        """
        mActionMapTips: QAction = self.iface.mainWindow().findChild(QAction, 'mActionMapTips')
        if mActionMapTips:
            # print("mActionMapTips is ", mActionMapTips.isChecked())
            if not mActionMapTips.isChecked():
                mActionMapTips.trigger()

    def _toggleBtnTools(self, btnWillBeNotClose: str) -> None:
        """Toggles buttons on the right side

        Args:
            btnWillBeNotClose (str): name representing the button that will be not closed
        """
        # print("_closeOpenTools")
        for btnName in self.mapButtons.keys():
            # print('====> btn, tool', bItem)
            if btnName != btnWillBeNotClose:
                btnTool: BtnToolMap = self.mapButtons[btnName]
                if btnTool.tool:
                    btnTool.tool.close()

                if btnTool.additionalTool:
                    btnTool.additionalTool.close()

                if btnTool.checkable and btnTool.btn.isChecked():
                    btnTool.btn.setChecked(False)

                if btnName == 'featureInfo' and self.rectSelect:
                    self.rectSelect.reset()
        self.iface.actionPan().trigger()

    def _runZoomIn(self) -> None:
        """Runs zoom in"""
        canvas = self.iface.mapCanvas()
        canvas.zoomIn()

    def _runZoomOut(self) -> None:
        """Runs zoom out"""
        canvas = self.iface.mapCanvas()
        canvas.zoomOut()

    def _runGps(self) -> None:
        """Calls GPS util to use GPS functionality"""
        gpsTool: BtnToolMap = self.mapButtons['gps']
        self._toggleBtnTools('gps')
        if not gpsTool.tool:
            gpsTool.tool = Gps(self.iface)
        gpsTool.tool.runGps()

    def _runZoomOutToExtent(self) -> None:
        """Zooms to full extent"""
        # self.gpkgPopup.show(titelName='xxxx')
        canvas: QgsMapCanvas = self.iface.mapCanvas()
        canvas.zoomToFullExtent()

    def _runLineCalculation(self) -> None:
        """Runs the tool to calculate the distance"""
        measureTool = self.mapButtons['measureTool']
        self._toggleBtnTools('measureTool')
        if not measureTool.tool:
            measureTool.tool = MeasureTool(self.iface, self.iface.mainWindow())
        canvas = self.iface.mapCanvas()
        canvas.setMapTool(measureTool.tool)
        measureTool.tool.activate()

    def _runAreaCalculation(self) -> None:
        """Runs the tool to calculate the area"""
        measureAreaTool = self.mapButtons['measureAreaTool']
        self._toggleBtnTools('measureAreaTool')
        if not measureAreaTool.tool:
            measureAreaTool.tool = MeasureTool(self.iface, self.iface.mainWindow(), isArea=True)
        canvas = self.iface.mapCanvas()
        canvas.setMapTool(measureAreaTool.tool)
        measureAreaTool.tool.activate()

    def _runFeatureInfo(self) -> None:
        featureInfo = self.mapButtons['featureInfo']
        self._toggleBtnTools('featureInfo')
        if featureInfo.btn.isChecked():
            self.rectSelect = RectSelect(self.iface)
            self.iface.mapCanvas().setMapTool(self.rectSelect)

    def _runPrint(self) -> None:
        """Opens print dialog"""
        printDialog = self.mapButtons['print']
        self._toggleBtnTools('print')

        if not printDialog.tool:
            printDialog.tool = PrintDialog(self.iface, self.iface.mainWindow())
        printDialog.tool.show()

    def _changeQgisMainWindow(self) -> None:
        """Change Main Window"""
        QgsProject.instance().isDirtyChanged.connect(self._onDirtyChanged)
        self.iface.mainWindow().setWindowTitle(self.TITLE)

        icon_path = os.path.join(self.pluginDir, self.MAIN_WINDOW_ICON)
        if os.path.isfile(icon_path):
            icon = QIcon(icon_path)
            self.iface.mainWindow().setWindowIcon(icon)

    def _setDirty(self) -> None:
        """Workaround to fix the title of the main QGIS window. QGIS changes its title to the default title after all
        processes:
        1- loading plugin
        2- loading project
        3- calling runProjectReady method due to signal <readProject>
        However, we need to use a custom title defined with< TITLE> -example("mofa4q - QGIS [MoFa4Q]")
        To fix this, we need to call the <isDirtyChanged> signal in a separate thread that sets the correct title.
        """
        # QgsMessageLog.logMessage("call _setDirty()", level=Qgis.Info)
        QgsProject.instance().setDirty(True)
