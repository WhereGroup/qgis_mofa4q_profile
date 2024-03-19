import os
import re
from shutil import copyfile

from PyQt5.QtCore import QSettings


class QgisInitialize:
    """ Initialize Settings from qgis init-file"""
    TEST_SEARCH = "%PROFILE_FOLDER%"
    QGIS_PROJ_OPEN_AT_LAUNCH_PATH = "qgis/projOpenAtLaunchPath"

    def __init__(self, iface, profile_path, default_install_path, default_project, text_to_search=None):
        self.locale = None
        self.iface = iface
        self.PROFILE_PATH = profile_path
        self.DEFAULT_INSTALL_PATH = default_install_path
        self.DEFAULT_PROJECT = default_project

        new_proj_open_at_launch_path = os.path.normcase(os.path.normpath(os.path.join(self.DEFAULT_INSTALL_PATH, self.DEFAULT_PROJECT)))
        proj_open_at_launch_path = QSettings().value(self.QGIS_PROJ_OPEN_AT_LAUNCH_PATH)
        proj_open_at_launch_path = os.path.normcase(proj_open_at_launch_path)

        if isinstance(text_to_search, str):
            self.TEST_SEARCH = text_to_search

        if (isinstance(proj_open_at_launch_path, str)) and (new_proj_open_at_launch_path != proj_open_at_launch_path):
            self._init_qgis_configuration()

    def _sync(self):
        """ QSettings sync(self) """
        # Reload QGIS Setting
        QSettings().sync()

    def _init_qgis_configuration(self) -> None:
        """replace textToSearch of init-file with profile_path"""
        # QgsMessageLog.logMessage("call _init_qgis_configuration()", level=Qgis.Info)
        dirPath = os.path.normcase(self.PROFILE_PATH)
        textToReplace = dirPath.replace('\\', '/')

        if os.path.isdir(dirPath):
            copyfile(os.path.normcase(dirPath + "/init/QGIS3.ini"), os.path.normcase(dirPath + "/QGIS/QGIS3.ini"))
            copyfile(os.path.normcase(dirPath + "/init/QGISCUSTOMIZATION3.ini"),
                     os.path.normcase(dirPath + "/QGIS/QGISCUSTOMIZATION3.ini"))

            filename = os.path.join(dirPath + "/QGIS/QGIS3.ini")
            if os.path.isfile(filename):
                with open(filename, 'r') as instream:
                    content = instream.read()
                content = re.sub(self.TEST_SEARCH, textToReplace, content)
                with open(filename, 'w') as outstream:
                    outstream.write(content)

            filename = os.path.join(dirPath + "/QGIS/QGISCUSTOMIZATION3.ini")
            if os.path.isfile(filename):
                with open(filename, 'r') as instream:
                    content = instream.read()
                content = re.sub(self.TEST_SEARCH, textToReplace, content)
                with open(filename, 'w') as outstream:
                    outstream.write(content)

        # Closing the file after the loop finishes
        outstream.close()
        # Reload QSettings
        self._sync()

    def get_locale(self):
        """ Get Locale env from QSettings"""
        self.locale = QSettings().value('locale/userLocale')[0:2]
        return self.locale
