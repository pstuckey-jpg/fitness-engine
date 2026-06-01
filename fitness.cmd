@echo off
setlocal

if "%~1"=="" (
  echo Usage: fitness.cmd add
  echo        fitness.cmd brief
  exit /b 1
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python -m cli.main %1
  exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 -m cli.main %1
  exit /b %ERRORLEVEL%
)

set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PYTHON%" (
  "%BUNDLED_PYTHON%" -m cli.main %1
  exit /b %ERRORLEVEL%
)

echo Python was not found. Install Python or run this inside Codex with the bundled runtime available.
exit /b 1
