from qgis.core import QgsTextAnnotation


class CustomBubbleTextAnnotation(QgsTextAnnotation):
    """Customization of the QgsTextAnnotation with additional attributes (textMsg, isBubble, color)"""

    def __init__(self, textMsg: str, color: str):
        super(CustomBubbleTextAnnotation, self).__init__()
        self.textMsg: str = textMsg
        self.color: str = color
