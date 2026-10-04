@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Paleidziami automatiniai testai (naudojama laikina testine duomenu baze)...
".venv\Scripts\python.exe" -m unittest discover -s tests -t . -v
pause
