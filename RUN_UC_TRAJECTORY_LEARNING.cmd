@echo off
setlocal
cd /d "%~dp0"
echo.
echo AXM UC direct trajectory learning lab
echo =====================================
echo Every temporary simulation step teaches the experimental neural brain.
echo Recurrent state and eligibility traces persist inside each 8-step trajectory.
echo Only the terminal result supplies the final reward.
echo.
echo Raw simulation experiences are NOT retained in replay memory.
echo Persistent state:
echo   state\neural-experiment\simulation\trajectory-learning-v1.json
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\run_uc_trajectory_learning.py --prepare
) else (
  python tools\run_uc_trajectory_learning.py --prepare
)
set EXITCODE=%errorlevel%
echo.
if not "%EXITCODE%"=="0" echo Trajectory lab stopped on HOLD. Existing brain state is preserved.
pause
exit /b %EXITCODE%
