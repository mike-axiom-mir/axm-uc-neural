@echo off
setlocal
cd /d "%~dp0"
echo UC simulation learning lab: a separate AXM learner, saved after each bounded run.
echo The existing WALDO experiment keeps its current settings.
set "UC_SIM_RESUME="
if exist "state\neural-experiment\simulation\session.json" set "UC_SIM_RESUME=--resume"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\run_uc_simulation_lab.py --prepare %UC_SIM_RESUME%
) else (
  python tools\run_uc_simulation_lab.py --prepare %UC_SIM_RESUME%
)
if errorlevel 1 echo The lab is on HOLD. Read the message above; existing learned state is preserved.
pause
