@echo off
chcp 65001 >nul
echo Ijungiu automatini spejima pries kiekviena sesija (tikrinama kas 15 min.)...
schtasks /Create /F /TN "F1 spejimai - automatinis" /SC MINUTE /MO 15 /TR "\"%~dp0.venv\Scripts\pythonw.exe\" \"%~dp0cli.py\" automatinis"
if errorlevel 1 (echo Nepavyko. & pause & exit /b 1)
echo Ijungta. Likus ~40 min. iki sesijos gausite Windows pranesima su spejimu. Isjungti: automatinis_isjungti.bat
pause
