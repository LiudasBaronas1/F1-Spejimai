@echo off
rem F1 Spejimai - diegimas. Paleidziama automatiskai pirma karta atidarius "F1 Spejimai.vbs".
rem Sukuria Python aplinka (.venv), idiegia bibliotekas ir darbalaukio nuoroda. Argumentas "auto" - be pauzes pabaigoje.
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  F1 SPEJIMAI - diegimas (tik pirma karta, 2-5 minutes)
echo  ======================================================
echo.
if exist ".venv\Scripts\python.exe" goto packages

set "PYCMD="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1 && set "PYCMD=py -3"
if not defined PYCMD python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1 && set "PYCMD=python"
if not defined PYCMD (
  echo Nerasta Python 3.10 ar naujesne versija. Bandau idiegti Python 3.12 ^(winget^)...
  winget install --id Python.Python.3.12 -e --silent --scope user --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYCMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PYCMD (
  echo.
  echo KLAIDA: Python nerastas ir automatiskai idiegti nepavyko.
  echo Atsisiuskite ji is https://www.python.org/downloads/ ^(diegiant pazymekite "Add python.exe to PATH"^)
  echo ir dar karta paleiskite "F1 Spejimai.vbs".
  pause
  exit /b 1
)
echo Kuriu Python aplinka...
%PYCMD% -m venv .venv
if errorlevel 1 (echo KLAIDA: nepavyko sukurti Python aplinkos. & pause & exit /b 1)

:packages
echo Diegiu bibliotekas...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --disable-pip-version-check
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (echo KLAIDA: nepavyko idiegti biblioteku ^(ar yra internetas?^). & pause & exit /b 1)

echo Kuriu darbalaukio nuoroda "F1 Spejimai"...
set "F1ROOT=%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = (Resolve-Path $env:F1ROOT).Path; $vbs = Get-ChildItem -LiteralPath $root -Filter *.vbs | Select-Object -First 1;" ^
  "$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'F1 Spejimai.lnk';" ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk); $s.TargetPath = 'wscript.exe';" ^
  "$s.Arguments = '\"' + $vbs.FullName + '\"'; $s.WorkingDirectory = $root;" ^
  "$s.IconLocation = (Join-Path $root 'programa\ikona.ico'); $s.Save()"

echo.
echo Baigta.
if /i not "%~1"=="auto" pause
exit /b 0
