#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from pathlib import Path

project_dir = Path(__file__).parent

unnecessary_files = [
    "builder.py",
    "build_rat.py",
    "run_builder.bat",
    "central_server.py",
    "web_api.py",
    "web_api_integrated.py",
    "control_panel.html",
    "panel.html",
    "cleanup.py",
    "quick_start.py",
    "validar_projeto.py",
    "GUIA_RAPIDO.txt",
    "PANEL_README.md",
    "RESUMO_FINAL.txt",
    "HealthChecker.py",
    "RickRoll.mp4",
    "libopus.dll",
    "LICENSE",
    "VALIDAR_PROJETO.bat",
    "PARAR_SERVIDOR.bat",
    "INICIAR_PAINEL_CENTRAL.bat",
    "LAUNCHER.bat",
    "install.bat",
    "Program.spec",
    "central_control.db",
]

unnecessary_dirs = [
    "HealthChecker_Portable_20251227_015549",
    "logs",
    "data",
    "core",
    "dist",
    "build",
    "hooks",
    "__pycache__",
]

print("=" * 80)
print(" LIMPEZA DO PROJETO - Removendo arquivos desnecessarios")
print("=" * 80)
print()

removed_count = 0

print("[*] Removendo arquivos...")
for filename in unnecessary_files:
    filepath = project_dir / filename
    if filepath.exists():
        try:
            filepath.unlink()
            print(f"[OK] Removido: {filename}")
            removed_count += 1
        except Exception as e:
            print(f"[ERRO] Nao foi possivel remover {filename}: {e}")

print()
print("[*] Removendo diretrios...")
for dirname in unnecessary_dirs:
    dirpath = project_dir / dirname
    if dirpath.exists():
        try:
            shutil.rmtree(dirpath)
            print(f"[OK] Removido: {dirname}/")
            removed_count += 1
        except Exception as e:
            print(f"[ERRO] Nao foi possivel remover {dirname}: {e}")

print()
print("=" * 80)
print(f" LIMPEZA CONCLUIDA - {removed_count} itens removidos")
print("=" * 80)
print()
print("Arquivos necessarios mantidos:")
print("  - Program.py")
print("  - central_client.py")
print("  - web_api_docker.py")
print("  - panel_docker.html")
print("  - builder2.py")
print("  - defender_rollback.bat")
print("  - cleanup_project.bat (para futuras limpezas)")
print("  - Dockerfile")
print("  - docker-compose.yml")
print("  - docker-entrypoint.sh")
print("  - requirements.txt")
print("  - config.json")
print("  - icon.ico")
print("  - logo.png")
print()
