from PyQt5.QtGui import QColor
from .search import Search


class ObjSearch(Search):
    """
    Reads the geopackage for the object and search in the table objektsuche the
    matched addresses
    """

    STR_QUERY = "SELECT search FROM objektsuche WHERE search LIKE ?"
    STR_QUERY_GEOM = "SELECT X(geom), Y(geom), SRID(geom) FROM objektsuche WHERE search = ?"
    COLOR_VERTEX = QColor(222, 13, 13)

    def __init__(self, iface, filePath, lineEditSearch, pushButton):
        super().__init__(iface, filePath, lineEditSearch, pushButton)
