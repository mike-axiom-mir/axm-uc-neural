@echo off
setlocal
cd /d "%~dp0"
echo.
echo AXM Expanded UC Creative Experiment
echo ===================================
echo 8 active hours, 100 GB stop threshold, cross-capability exploration.
echo.
echo Initial coverage includes:
echo   parametric 3D ^| materials ^| textured 3D products ^| browser games
echo   web/software ^| coded visual runtime ^| multi-hand mesh flows
echo   Python tools ^| compound projects packaged through another UC capability
echo.
echo The Creative dashboard toggle can pause/resume this loop.
echo Main UC source/canon is not modified by this launcher.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -c "import sys;sys.path.insert(0,'src');from axm_uc.experiment_controls import set_control;set_control('.', 'uc_creative_enabled', True)"
  py -3 tools\run_uc_expanded_creative.py --hours 8 --max-bytes 100000000000 --max-runs 100000 --follow-control
  set EXITCODE=%errorlevel%
  py -3 -c "import sys;sys.path.insert(0,'src');from axm_uc.experiment_controls import set_control;set_control('.', 'uc_creative_enabled', False)"
) else (
  python -c "import sys;sys.path.insert(0,'src');from axm_uc.experiment_controls import set_control;set_control('.', 'uc_creative_enabled', True)"
  python tools\run_uc_expanded_creative.py --hours 8 --max-bytes 100000000000 --max-runs 100000 --follow-control
  set EXITCODE=%errorlevel%
  python -c "import sys;sys.path.insert(0,'src');from axm_uc.experiment_controls import set_control;set_control('.', 'uc_creative_enabled', False)"
)
echo.
if not "%EXITCODE%"=="0" echo Expanded Creative experiment stopped on HOLD. Existing creations and state were preserved.
echo Output: creations\neural-experiment\expanded-creative
pause
exit /b %EXITCODE%
