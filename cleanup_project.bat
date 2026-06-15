@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo Limpando arquivos desnecessarios do projeto...
echo.

del /f /q builder.py 2>nul
del /f /q build_rat.py 2>nul
del /f /q run_builder.bat 2>nul
del /f /q central_server.py 2>nul
del /f /q web_api.py 2>nul
del /f /q web_api_integrated.py 2>nul
del /f /q control_panel.html 2>nul
del /f /q panel.html 2>nul
del /f /q cleanup.py 2>nul
del /f /q quick_start.py 2>nul
del /f /q validar_projeto.py 2>nul
del /f /q GUIA_RAPIDO.txt 2>nul
del /f /q PANEL_README.md 2>nul
del /f /q RESUMO_FINAL.txt 2>nul
del /f /q HealthChecker.py 2>nul
del /f /q RickRoll.mp4 2>nul
del /f /q libopus.dll 2>nul
del /f /q LICENSE 2>nul
del /f /q VALIDAR_PROJETO.bat 2>nul
del /f /q PARAR_SERVIDOR.bat 2>nul
del /f /q INICIAR_PAINEL_CENTRAL.bat 2>nul
del /f /q LAUNCHER.bat 2>nul
del /f /q install.bat 2>nul
del /f /q Program.spec 2>nul
del /f /q central_control.db 2>nul

rmdir /s /q HealthChecker_Portable_* 2>nul
rmdir /s /q logs 2>nul
rmdir /s /q data 2>nul
rmdir /s /q core 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q build 2>nul
rmdir /s /q hooks 2>nul
rmdir /s /q __pycache__ 2>nul

echo.
echo Limpeza concluida!
echo.
pause
