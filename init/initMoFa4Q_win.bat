set QGIS_DIRECTORY="C:\Program Files\QGIS 3.4\bin"

call %QGIS_DIRECTORY%\o4w_env.bat
call %QGIS_DIRECTORY%\qt5_env.bat
call %QGIS_DIRECTORY%\py3_env.bat

python3 python_init_script.py

