@echo off
setlocal
cd /d "%~dp0"
echo.
echo AXM UC real workflow practice lab
echo =================================
echo Searches installed UC operators, executes bounded candidate pipelines,
echo keeps measured failures, confirms repeatable successes, and retains only
echo reusable workflow structures with evidence.
echo.
echo This does NOT change main UC, neural weights, or canon automatically.
echo Learned workflow evidence is written under:
echo   creations\neural-experiment\workflow-practice
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\run_uc_workflow_practice.py --profile all
) else (
  python tools\run_uc_workflow_practice.py --profile all
)
set EXITCODE=%errorlevel%
echo.
if not "%EXITCODE%"=="0" echo Workflow practice stopped on HOLD. Existing evidence was preserved.
pause
exit /b %EXITCODE%
