@echo off
setlocal enabledelayedexpansion

:: ================================================================
:: DESFAZER AÇÕES DO WINDOWS DEFENDER E SEGURANÇA
:: ================================================================
:: Este script reverte as modificações feitas pelo RAT.exe
:: Use com cuidado - executar com privilégios de administrador
:: ================================================================

color 0A
echo.
echo ================================================================
echo REVERSOR DE AÇÕES DO RAT - Windows Security Rollback
echo ================================================================
echo.

:: Verificar privilégios administrativos
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Este script requer privilegios de administrador.
    echo Execute clicando com botão direito e "Executar como administrador"
    pause
    exit /b 1
)

echo [INFO] Executando como administrador...
echo.

:: ==========================================
:: 1. REMOVER EXCLUSÃO DO WINDOWS DEFENDER
:: ==========================================
echo ----------------------------------------
echo 1. PROCESSANDO WINDOWS DEFENDER...
echo ----------------------------------------

:: Obter as pastas de possíveis exclusões (caminhos comuns do RAT)
echo [INFO] Removendo exclusões do Windows Defender...

:: Remover exclusões de caminho (as principais pastas)
powershell -Command "Remove-MpPreference -ExclusionPath 'C:\Users\%%USERNAME%%\Documents' -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Remove-MpPreference -ExclusionPath 'C:\Users\%%USERNAME%%\AppData\Local' -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Remove-MpPreference -ExclusionPath 'C:\Users\%%USERNAME%%\AppData\Roaming' -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Remove-MpPreference -ExclusionPath 'C:\Users\%%USERNAME%%\Desktop' -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Remove-MpPreference -ExclusionPath '%%USERPROFILE%%' -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Remove-MpPreference -ExclusionPath '%%APPDATA%%' -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Remove-MpPreference -ExclusionPath '%%LOCALAPPDATA%%' -ErrorAction SilentlyContinue" 2>nul

:: Remover exclusões de processo (pelo nome fugindo RAT)
powershell -Command "Remove-MpPreference -ExclusionProcess 'RAT.exe' -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Remove-MpPreference -ExclusionProcess 'Program.exe' -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Remove-MpPreference -ExclusionProcess 'python.exe' -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Remove-MpPreference -ExclusionProcess 'py.exe' -ErrorAction SilentlyContinue" 2>nul

:: Restaurar tamponamento de amostras do Defender se foi desabilitado
powershell -Command "Set-MpPreference -SubmitSamplesConsent 1 -Force -ErrorAction SilentlyContinue" 2>nul

echo [OK] Ações do Windows Defender reversadas.
echo.

:: ==========================================
:: 2. REABILITAR TASK MANAGER
:: ==========================================
echo ----------------------------------------
echo 2. HABILITANDO TASK MANAGER...
echo ----------------------------------------

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v "DisableTaskMgr" /t REG_DWORD /d 0 /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v "DisableTaskMgr" /f >nul 2>&1
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "DisableTaskMgr" /t REG_DWORD /d 0 /f >nul 2>&1
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "DisableTaskMgr" /f >nul 2>&1

echo [OK] Task Manager reativado.
echo.

:: ==========================================
:: 3. REMOVER CHAVES DE REGISTRO MALICIOSAS
:: ==========================================
echo ----------------------------------------
echo 3. LIMPANDO REGISTROS DE INICIALIZACAO...
echo ----------------------------------------

:: Remover chaves de inicialização do RAT
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "RAT" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "RAT" /f >nul 2>&1
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce" /v "RAT" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" /v "RAT" /f >nul 2>&1

:: Outros possíveis nomes do RAT
for %%R in ("Program" "Python" "Discord" "SystemUpdate" "ServiceUpdate" "windows_update" "svchost32") do (
    reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "%%~R" /f >nul 2>&1
    reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "%%~R" /f >nul 2>&1
    reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce" /v "%%~R" /f >nul 2>&1
    reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" /v "%%~R" /f >nul 2>&1
)

echo [OK] Registros de inicialização limpos.
echo.

:: ==========================================
:: 4. REMOVER TAREFAS AGENDADAS MALICIOSAS
:: ==========================================
echo ----------------------------------------
echo 4. PROCESSANDO TAREFAS AGENDADAS...
echo ----------------------------------------

for %%T in ("RAT" "Program" "Python" "Discord_Updater" "System_Update" "windows_service_update") do (
    schtasks /delete /tn "%%~T" /f >nul 2>&1
)

echo [OK] Tarefas maliciosas removidas.
echo.

:: ==========================================
:: 5. DESABILITAR SERVICOS MALICIOSOS
:: ==========================================
echo ----------------------------------------
echo 5. VERIFICANDO SERVICOS MALICIOSOS...
echo ----------------------------------------

sc stop "RAT" >nul 2>&1
sc delete "RAT" >nul 2>&1
sc stop "PythonUpdater" >nul 2>&1  
sc delete "PythonUpdater" >nul 2>&1
sc stop "DiscordService" >nul 2>&1
sc delete "DiscordService" >nul 2>&1

echo [OK] Serviços maliciosos interrompidos.
echo.

:: ==========================================
:: 6. REATIVAR FIREWALL/SEGURANÇA
:: ==========================================
echo ----------------------------------------
echo 6. RESTAURANDO FIREWALL E SEGURANCA...
echo ----------------------------------------

:: Reativar Windows Firewall para todos os perfis
netsh advfirewall set allprofiles state on >nul 2>&1
netsh advfirewall firewall delete rule name="RAT" >nul 2>&1
netsh advfirewall firewall delete rule name="PyTest" >nul 2>&1
netsh advfirewall firewall delete rule name="Discord Update" >nul 2>&1
netsh advfirewall firewall delete rule name="Python Update" >nul 2>&1

:: Limpar políticas de firewall esquisitas criadas
powershell -Command "Get-NetFirewallRule | Where-Object {$_.DisplayName -like '*RAT*'} | Remove-NetFirewallRule" 2>nul
powershell -Command "Get-NetFirewallRule | Where-Object {$_.DisplayName -like '*Python*'} | Remove-NetFirewallRule" 2>nul
powershell -Command "Get-NetFirewallRule | Where-Object {$_.DisplayName -like '*Discord*'} | Remove-NetFirewallRule" 2>nul

echo [OK] Firewall e segurança restabelecidos.
echo.

:: ==========================================
:: 7. SCANEAMENTO É SUGESTÕES FINAIS
:: ==========================================
echo ================================================================
echo REVERSÃO CONCLUÍDA!
echo ================================================================
echo.
echo [STATUS] Principais ações reversadas:
echo   - Exclusão do Windows Defender removida
echo   - Task Manager reativado
echo   - Registros de inicialização limpos
echo   - Tarefas maliciosas apagadas
echo   - Firewall e proteção restabelecidos
echo.
echo [AVISO] Verificações recomendadas:
echo   1. Verificar se o arquivo RAT.exe ainda existe em:
echo      - C:\Users\%USERNAME%\AppData\Local\
echo      - C:\Users\%USERNAME%\AppData\Roaming\
echo      - Documentos e area de trabalho
echo.
echo   2. Executar Windows Update para garantir sistema atualizado
echo   3. Executar varredura completa no Windows Defender
echo   4. Verificar em Grupo Local de Politicas (gpedit.msc)
echo      se há políticas suspeitas de execução
echo.
echo   [OPÇÃO] Deseja executar varredura no Windows Defender agora? (S/N)"
echo.

set /p scaneamento=Digite S para sim, N para não: 
if /i "%scaneamento%"=="S" (
    echo.
    echo Execute o Windows Defender Security separadamente, pois este script
    echo será finalizado. Abra o Windows Security - Proteção contra vírus
    echo e ameaças - Verificar agora.
    start windowsdefender:
)

echo.
echo [INFO] Script finalizado. Reinicie o computador para garantir efetividade.
echo.
pause