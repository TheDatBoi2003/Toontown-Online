@echo off
title Open Toontown - Game Client
cd..

rem Read the contents of PPYTHON_PATH into %PPYTHON_PATH%:
set /P PPYTHON_PATH=<PPYTHON_PATH

:game
cls
echo = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
echo Username [!]
echo = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
set /P LOGIN_TOKEN="Username: "
echo.
cls

%PPYTHON_PATH% -m toontown.launcher.QuickStartLauncher
pause
