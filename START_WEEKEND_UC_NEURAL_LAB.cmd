@echo off
setlocal
cd /d "%~dp0"
echo.
echo AXM Weekend UC + OpenWALDO Lab
echo ===============================
echo Starting the visual cockpit and the local neural feeder.
echo.
echo Neural learning is OFF by default.
echo Turn it ON from the dashboard when you want the learning boundary to begin.
echo Run your UC creative/production loop normally in this checkout.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  start "AXM UC Neural Cockpit" cmd /k py -3 tools\uc_neural_dashboard.py --open-browser
  start "AXM OpenWALDO Feeder" cmd /k py -3 tools\run_uc_openwaldo_local.py --watch
) else (
  start "AXM UC Neural Cockpit" cmd /k python tools\uc_neural_dashboard.py --open-browser
  start "AXM OpenWALDO Feeder" cmd /k python tools\run_uc_openwaldo_local.py --watch
)
echo.
echo Cockpit and feeder launched.
echo Close those windows or press Ctrl+C inside them to stop.
pause
