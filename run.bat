:: We asume python in path ith python3

:: Full Windows power is needed to store command output in variable
for /F "tokens=*" %%R IN ('where pythonw.exe') DO SET python=%%R

set PATH=%PATH%;%python%\..\Lib\site-packages\PyQt5

start %python% %~dp0pytraycharmap %~dp0menu\charmap.yaml

:: or so if it is in sys.path
:: start %python% -m pytraycharmap %~dp0menu\charmap.yaml
