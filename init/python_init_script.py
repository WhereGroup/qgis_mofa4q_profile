#!/usr/bin/python3

import os
import fileinput
from shutil import copyfile

textToSearch = "%PROFILE_FOLDER%"
print("Text to search for:", textToSearch)

dirPath = os.path.normcase(os.path.join(os.path.dirname(__file__), ".."))

copyfile(dirPath + "/init/QGIS3.ini", dirPath + "/QGIS/QGIS3.ini")
copyfile(dirPath + "/init/QGISCUSTOMIZATION3.ini", dirPath + "/QGIS/QGISCUSTOMIZATION3.ini")

textToReplace = dirPath.replace('\\', '/')
print("Text to replace it with:", textToReplace)

filename = dirPath + "/QGIS/QGIS3.ini"
with fileinput.FileInput(filename, inplace=True) as file:
    for line in file:
        print(line.replace(textToSearch, textToReplace), end='')

filename = dirPath + "/QGIS/QGISCUSTOMIZATION3.ini"
with fileinput.FileInput(filename, inplace=True) as file:
    for line in file:
        print(line.replace(textToSearch, textToReplace), end='')
