:: Full Windows power is needed to store command output in variable!

:: We asume first python in path is python3 with PyQt5 installed
set python=
for /F "tokens=*" %%R in ('where pythonw.exe') do call :setpython %%R

set PATH=%PATH%;%python%\..\Lib\site-packages\PyQt5
start %python% %~dp0pytraycharmap %~dp0menu\charmap.yaml
goto :eof

:: In Windows, we need a "function" to set a variable,
:: we can't just set it inside for loop body
:setpython
if "%python%"=="" set python=%1
goto :eof

:: or so if it is in sys.path
:: start %python% -m pytraycharmap %~dp0menu\charmap.yaml
