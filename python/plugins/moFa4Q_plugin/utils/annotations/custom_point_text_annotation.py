from qgis.core import QgsAnnotationPointTextItem, QgsPointXY
from qgis.core import Qgis


class CustomPointTextAnnotation(QgsAnnotationPointTextItem):
    """Customization of the QgsAnnotationPointTextItem with additional attributes (textMsg, color)"""

    def __init__(self, textMsg: str, pointXY: QgsPointXY, color: str):
        super(CustomPointTextAnnotation, self).__init__(textMsg, pointXY)
        self.setRotationMode(Qgis.SymbolRotationMode.RespectMapRotation)
        self.textMsg: str = textMsg
        self.color: str = color
