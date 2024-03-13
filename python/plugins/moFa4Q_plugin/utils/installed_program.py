# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Print the map in a pdf.
 ***************************************************************************/
"""
import os
import re

import win32con
import winreg


class OsInstallPath:
    """Main class"""
    TEST_SEARCH = "mofa4q"

    @staticmethod
    def _list_installed_programs(hive, flag):
        aReg = winreg.ConnectRegistry(None, hive)
        aKey = winreg.OpenKey(aReg, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0, win32con.KEY_READ | flag)
        count_subkey = winreg.QueryInfoKey(aKey)[0]
        arr = []
        for i in range(count_subkey):
            try:
                asubkey_name = winreg.EnumKey(aKey, i)
                asubkey = winreg.OpenKey(aKey, asubkey_name)
                arr.append(
                    [winreg.QueryValueEx(asubkey, "DisplayName")[0],
                     winreg.QueryValueEx(asubkey, "UninstallString")[0]])
            except EnvironmentError:
                continue
        return arr

    @staticmethod
    def _get_all_list_programs():
        x = OsInstallPath._list_installed_programs(win32con.HKEY_LOCAL_MACHINE, win32con.KEY_WOW64_32KEY)
        y = OsInstallPath._list_installed_programs(win32con.HKEY_LOCAL_MACHINE, win32con.KEY_WOW64_64KEY)
        z = OsInstallPath._list_installed_programs(win32con.HKEY_CURRENT_USER, 0)
        return [x + y + z]

    @staticmethod
    def get_locate_programs(search_program: str) -> list[str]:
        if isinstance(search_program, str):
            search_text = search_program
        else:
            search_text = OsInstallPath.TEST_SEARCH

        find_name = None
        find_dirname = None

        for s in OsInstallPath._get_all_list_programs():
            for xs in s:
                if re.search(search_text, xs[0].lower()):
                    find_dirname = os.path.dirname(xs[1]).replace('"', '')
                    find_name = xs[0]
                    print('Name :', find_name)
                    print('Path: ', find_dirname)
                    break  # break here

        return [find_name, find_dirname]
