@echo off
setlocal
cd /d "%~dp0"
echo.
echo AXM UC / Neural Experiment Cockpit
echo -----------------------------------
echo Local-only dashboard. No active screenshot rendering.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\uc_neural_dashboard.py --open-browser
) else (
  python tools\uc_neural_dashboard.py --open-browser
)
set EXITCODE=%errorlevel%
echo.
if not "%EXITCODE%"=="0" echo Dashboard stopped with code %EXITCODE%.
pause
exit /b %EXITCODE%
