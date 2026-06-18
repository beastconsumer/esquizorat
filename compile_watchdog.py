"""
Compila watchdog.exe com PANEL_URL injetada
Uso: set PANEL_URL=http://IP:5000 && python compile_watchdog.py
"""
import sys, os, shutil, subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
WATCHDOG_PY = PROJECT_DIR / 'watchdog.py'
DIST_DIR = PROJECT_DIR / 'dist'
OUTPUT_NAME = 'watchdog'

panel_url = os.environ.get('PANEL_URL', '')

if not panel_url:
    print("ERRO: set PANEL_URL=http://SEU_IP:5000")
    print("Uso: set PANEL_URL=URL && python compile_watchdog.py")
    sys.exit(1)

if not WATCHDOG_PY.exists():
    print(f"ERRO: {WATCHDOG_PY} nao encontrado")
    sys.exit(1)

# Backup original
bak = WATCHDOG_PY.with_suffix('.py.bak')
shutil.copy2(WATCHDOG_PY, bak)

# Inject PANEL_URL
with open(WATCHDOG_PY, 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace('PANEL_URL_PLACEHOLDER', panel_url)
with open(WATCHDOG_PY, 'w', encoding='utf-8') as f:
    f.write(code)

print(f"[BUILD] PANEL_URL injetada: {panel_url}")

# Compile with PyInstaller
spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
a = Analysis(['watchdog.py'], pathex=[r'{str(PROJECT_DIR)}'], binaries=[], datas=[],
    hiddenimports=['requests','winreg','ctypes'],
    hookspath=[], hooksconfig={{}}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='watchdog', debug=False, bootloader_ignore_signals=False,
    strip=True, upx=True, console=False, disable_windowed_traceback=True)
'''

spec_file = PROJECT_DIR / 'watchdog.spec'
spec_file.write_text(spec_content)

result = subprocess.run([
    sys.executable, '-m', 'PyInstaller',
    str(spec_file),
    '--distpath', str(DIST_DIR),
    '--workpath', str(PROJECT_DIR / 'build_watchdog'),
], cwd=str(PROJECT_DIR))

# Cleanup
spec_file.unlink(missing_ok=True)
shutil.copy2(bak, WATCHDOG_PY)
bak.unlink()
shutil.rmtree(PROJECT_DIR / 'build_watchdog', ignore_errors=True)

if result.returncode == 0:
    exe_path = DIST_DIR / f'{OUTPUT_NAME}.exe'
    if exe_path.exists():
        size = exe_path.stat().st_size / (1024 * 1024)
        print(f"SUCESSO: {exe_path} ({size:.1f} MB)")
    else:
        # PyInstaller on Windows adds .exe
        alt = DIST_DIR / f'{OUTPUT_NAME}.exe'
        if alt.exists():
            size = alt.stat().st_size / (1024 * 1024)
            print(f"SUCESSO: {alt} ({size:.1f} MB)")
        else:
            print("ERRO: watchdog.exe nao encontrado")
            files = list(DIST_DIR.iterdir())
            print(f"Arquivos em dist: {[f.name for f in files]}")
else:
    print("ERRO: compilacao falhou")
