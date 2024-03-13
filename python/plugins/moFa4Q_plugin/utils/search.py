import os.path
import sqlite3
import traceback

import qgis.utils
from PyQt5.QtCore import QStringListModel, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QCompleter
from qgis.core import (Qgis, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsPoint, QgsPointXY,
                       QgsProject)
from qgis.gui import QgsVertexMarker

from .tr import tr
from abc import ABC


class Search(ABC):
    """
    Reads a geopackage and searchs in the table attribute table the
    matched text
    """
    STR_QUERY = "SELECT adresse FROM adresse WHERE adresse LIKE ?"
    STR_QUERY_GEOM = "SELECT X(geom), Y(geom), SRID(geom) FROM adresse WHERE adresse = ?"
    #STR_QUERY_GEOM = "SELECT geom, X(geom), Y(geom) FROM addresses"
    TABLE_EPSG = "EPSG:4326"
    MAX_VISIBLE_ITEMS = 15
    COLOR_VERTEX = QColor(153, 0, 204)
    SIZE_VERTEX = 24
    PEN_VERTEX = 4
    ZOOM_SCALE = 2500.0
    marker = None
    gPntXY = None

    def __init__(self, iface, filePath, lineEditSearch, pushButtonShow):
        self.conn = None
        self.iface = iface
        try:
            if os.path.isfile(filePath) is False:
                raise DBConnEx(tr("Der Geopackage-File {} für die Suche wurde nicht gefunden.").format(os.path.basename(filePath)))
            else:
                self.lineEditSearch = lineEditSearch
                self.pushButtonShow = pushButtonShow

                self.createDBConn(filePath)
                self.conn.cursor()

                self.completer = self.getCompleter()
                self.lineEditSearch.setCompleter(self.completer)
                self.model = QStringListModel()
                self.completer.setModel(self.model)

                self.lineEditSearch.textChanged.connect(self.textChanged)
                self.pushButtonShow.clicked.connect(self.centerMarkerOnCanvas)

        except DBConnEx as erMsg:
            self.iface.messageBar().pushMessage(tr("Warning"), tr(
                "Die Suche kann nicht verwendet werden.  {}").format(erMsg), level=Qgis.Info)

        except Exception:
            self.iface.messageBar().pushMessage(tr("Warning"), tr(
                "Die Suche kann nicht verwendet werden. Fehler nicht behoben: {}").format(traceback.format_exc()), level=Qgis.Info)

    def getCompleter(self):
        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setMaxVisibleItems(self.MAX_VISIBLE_ITEMS)
        completer.setFilterMode(Qt.MatchContains)
        completer.activated.connect(self.getPoi)
        return completer

    def createDBConn(self, path):
        try:
            self.conn = qgis.utils.spatialite_connect(path)
        except sqlite3.Error:
            raise DBConnEx(tr("Problem to connect to the server."))

    def resetAll(self):
        """ Closes the connection - It used when plugin is unloaded """
        if self.conn:
            self.conn.close()
        if self.marker:
            self.iface.mapCanvas().scene().removeItem(self.marker)

    def getDataFromDb(self):
        self.c = self.conn.cursor()
        rows = self.c.execute(self.STR_QUERY, ['%' + self.lineEditSearch.text() + '%']).fetchall()
        resultsQuery = []
        for sqlRow in rows:
            resultsQuery.append(sqlRow[0])
        self.model.setStringList(resultsQuery)
        self.c.close()

    def textChanged(self):
        """ Updates the list of possible completions each time a key is pressed for 3 letters """
        #print("=========> textChanged!")
        pattern = str(self.lineEditSearch.text())
        if len(pattern) < 3:
            self.model.setStringList([])
        elif len(pattern) == 3 and self.model.stringList() == []:
            self.getDataFromDb()

    def getPoi(self):
        """ Gets Poi of the selected research """
        self.c = self.conn.cursor()
        self.c.execute("select EnableGpkgAmphibiousMode()")
        rslt = self.c.execute(self.STR_QUERY_GEOM, [self.lineEditSearch.text()]).fetchone()
        #print("geom: ", rslt)
        self.c.close()
        print(rslt[2])
        self.addMarkerOnCanvas(rslt[0], rslt[1], rslt[2])

    def addMarkerOnCanvas(self, x, y, srid):
        """ Add a POI to the canvas """
        canvas = self.iface.mapCanvas()
        gPnt = QgsPoint(x, y)
        if srid == 4326:
            gPnt = self.convertCRS(gPnt, canvas)
        #print("new gPnt", gPnt)
        if self.marker is not None:
            canvas.scene().removeItem(self.marker)
        self.marker = QgsVertexMarker(canvas)
        self.gPntXY = QgsPointXY(gPnt.x(), gPnt.y())

        self.marker.setCenter(self.gPntXY)
        self.marker.setColor(self.COLOR_VERTEX)
        self.marker.setIconSize(self.SIZE_VERTEX)
        self.marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
        self.marker.setPenWidth(self.PEN_VERTEX)
        self.centerMarkerOnCanvas()

    def centerMarkerOnCanvas(self):
        """ Add a POI to the canvas """
        canvas = self.iface.mapCanvas()
        canvas.setCenter(self.gPntXY)
        canvas.zoomScale(self.ZOOM_SCALE)

    def convertCRS(self, gPnt, canvas):
        sourceCrs = QgsCoordinateReferenceSystem()
        sourceCrs.createFromString(self.TABLE_EPSG)

        destCrs = QgsCoordinateReferenceSystem()
        destCrs.createFromString(canvas.mapSettings().destinationCrs().authid())

        tr = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
        gPnt.transform(tr)
        return gPnt


class DBConnEx(Exception):
    """Base class for exceptions in this module."""
    pass
