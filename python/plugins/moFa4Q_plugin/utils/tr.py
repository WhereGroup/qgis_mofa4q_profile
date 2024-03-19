from qgis.PyQt.QtCore import QCoreApplication


def tr(string):
    """Get the translation for a string using Qt translation API.

    We implement this ourselves since we do not inherit QObject.

    :param message: String for translation.
    :type message: str, QString

    :returns: Translated version of message.
    :rtype: QString
    """
    return QCoreApplication.translate('@default', string)
