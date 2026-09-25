@echo off
setlocal
cd /d "%~dp0"
echo.
echo AXM UC + OpenWALDO weekend experiment
echo --------------------------------------
echo This window feeds NEW UC experience into the local OpenWALDO learner.
echo Leave your UC creative/production loop running separately.
echo Press Ctrl+C to stop this feeder.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\run_uc_openwaldo_local.py --watch
) else (
  python tools\run_uc_openwaldo_local.py --watch
)
set EXITCODE=%errorlevel%
echo.
if not "%EXITCODE%"=="0" (
  echo Experiment feeder stopped with code %EXITCODE%.
  echo Read state\neural-experiment\openwaldo-local\STATUS.json for the last grounded state.
)
pause
exit /b %EXITCODE%
