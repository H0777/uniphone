@echo off
rem Dev launcher: run the working tree without installing (Windows).
setlocal
set "PYTHONPATH=%~dp0src"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m uniphone.run %*
) else (
  python -m uniphone.run %*
)
exit /b %errorlevel%
