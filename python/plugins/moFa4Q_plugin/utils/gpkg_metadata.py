import os.path
import sqlite3

from qgis.core import Qgis
from qgis.gui import QgisInterface

from .tr import tr


class GpkgMetadata():
    """
    Checks content of a geopackage to check whether the file contains vector,
    raster data, single layer or few layers
    """

    STR_TABLE = 'SELECT table_name, data_type, identifier FROM gpkg_contents'

    def __init__(self, iface: QgisInterface, filePath: str):
        self.iface = iface
        self.conn = None
        self.c = None

        if not os.path.isfile(filePath):
            self.iface.messageBar().pushMessage(tr("Fehler"), tr(
                "Geopackage-Datei {} nicht gefunden.").format(filePath), level=Qgis.Warning)
        else:
            self.createDBConn(filePath)

    def getInfo(self):
        if not self.c:
            return []

        cursor = self.c.execute(self.STR_TABLE)
        infoArray = []
        for sqlRow in cursor:
            infoArray.append({'table_name': sqlRow[0], 'data_type': sqlRow[1], 'identifier': sqlRow[2]})
        self.conn.close()
        return infoArray

    def createDBConn(self, path: str):
        try:
            self.conn = sqlite3.connect(path)
            self.c = self.conn.cursor()
        except sqlite3.Error:
            self.iface.messageBar().pushMessage(tr("Fehler"), tr(
                f"File {path} gefunden aber die Datei kann nicht geöffnet werden"), level=Qgis.Warning)
