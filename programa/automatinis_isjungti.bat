@echo off
chcp 65001 >nul
schtasks /Delete /F /TN "F1 spejimai - automatinis"
echo Automatinis spejimas isjungtas.
pause
