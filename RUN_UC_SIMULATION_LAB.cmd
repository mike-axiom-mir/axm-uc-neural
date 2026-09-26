@echo off
setlocal
cd /d "%~dp0"
echo UC simulation learning lab: a separate AXM learner, saved after each bounded run.
echo The existing WALDO experiment keeps its current settings.
set "UC_SIM_CHECKPOINT=state\neural-experiment\simulation\session-workflow-v2.json"
set "UC_SIM_RESUME="
if exist "%UC_SIM_CHECKPOINT%" set "UC_SIM_RESUME=--resume"
if exist "state\neural-experiment\simulation\session.json" if not exist "%UC_SIM_CHECKPOINT%" echo Earlier canvas-only checkpoint found and preserved; workflow-v2 starts separately.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\run_uc_simulation_lab.py --prepare --checkpoint "%UC_SIM_CHECKPOINT%" %UC_SIM_RESUME%
) else (
  python tools\run_uc_simulation_lab.py --prepare --checkpoint "%UC_SIM_CHECKPOINT%" %UC_SIM_RESUME%
)
if errorlevel 1 echo The lab is on HOLD. Read the message above; existing learned state is preserved.
pause
