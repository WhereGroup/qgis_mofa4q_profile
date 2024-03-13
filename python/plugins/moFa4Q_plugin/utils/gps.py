from qgis.core import (Qgis, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsGpsDetector, QgsPoint,
                       QgsProject, QgsRectangle)
from qgis.core import QgsGpsConnection
from qgis.gui import QgisInterface
from .tr import tr


class Gps():
    """
    Establish a connection to GPS device programmatically.
    Important info:
        - https://zuidt.nl/blog/html/2014/06/12/use_your_gps_dongle_with_qgis.html
        - https://gis.stackexchange.com/questions/188002/connect-disconnect-gps-device-via-pyqgis
        - https://github.com/roam-qgis/Roam/blob/master/src/roam/api/gps.py
    """

    EPSG_SOURCE = "EPSG:4326"

    # isAvailable = True

    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.isClicked = False

        # initialize gps connection
        portName = "internalGPS"
        self.detector = QgsGpsDetector(portName)
        self.detector.detected.connect(self._gpsFound)
        self.detector.detectionFailed.connect(self._gpsFailed)
        self.detector.advance()

    def runGps(self):
        """Calls each time the GPS button will be clicked"""
        self.isClicked = True
        # if not self.isAvailable:
        # self.gpsfailed()

    def close(self):
        """Necessary to simulate the close the tool"""
        pass

    #  private methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _gpsFound(self, gpsConnection: QgsGpsConnection):
        """
        Signal when the detector found the gps connection

        Args:
            gpsConnection (QgsGpsConnection): the established connection
        """
        # print("GPS connection found! Start listening to stateChanged events", gpsConnection)
        self.gpsConnection = gpsConnection
        gpsConnection.stateChanged.connect(self._gpsStateChanged)

    def _gpsStateChanged(self, gpsInfo):
        """Signal for gps change

        Args:
            gpsInfo (QgsGpsConnection): the established connection
        """
        # fixType: NMEA_FIX_BAD = 1 NMEA_FIX_2D = 2 NMEA_FIX_3D = 3
        # print("gpsInfo", gpsInfo)
        if gpsInfo.fixType >= 2:
            if self.isClicked:
                print("lon: %s - lat: %s" % (gpsInfo.longitude, gpsInfo.latitude))
                self._centerMapWithGPS(gpsInfo.longitude, gpsInfo.latitude)
                self.isClicked = False
            # https://doc.qt.io/archives/qt-4.8/qobject.html#deleteLater
            # https://www.riverbankcomputing.com/static/Docs/PyQt5/api/qtcore/qobject.html?highlight=qobject#QObject
            # self.gpsConnection.deleteLater()
        else:
            self.iface.messageBar().pushMessage("Info", tr("Die GPS-Verbindung wird hergestellt"), level=Qgis.Info)

    def _gpsFailed(self):
        self.iface.messageBar().pushMessage("Error", tr("GPS wird nicht unterstützt oder ist nicht aktiv"),
                                            level=Qgis.Warning)
        # self.isAvailable = False
        # test for maschine without gps support
        # self.centerMapWithGPS(13.286723005883237, 52.494161248931206)

    def _centerMapWithGPS(self, lon: float, lat: float):
        """Sets the map to the position of GPS

        Args:
            lon (float): longitude
            lat (float): latitude
        """
        mapPos = QgsPoint(lon, lat)
        # print("===>> rect", mapPos.x(), mapPos.y(), mapPos.x(), mapPos.y())

        rect = QgsRectangle(mapPos.x(), mapPos.y(), mapPos.x(), mapPos.y())

        crs = QgsCoordinateReferenceSystem()
        crs.createFromString(Gps.EPSG_SOURCE)

        canvas = self.iface.mapCanvas()

        if canvas.scale() > self.TARGET_SCALE:
            canvas.zoomScale(self.TARGET_SCALE)

        targetCrs = QgsCoordinateReferenceSystem()
        targetCrs.createFromString(canvas.mapSettings().destinationCrs().authid())

        tr = QgsCoordinateTransform(crs, targetCrs, QgsProject.instance())
        targetRect = tr.transform(rect)
        canvas.setExtent(targetRect)
        canvas.refresh()
