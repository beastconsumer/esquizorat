#!/usr/bin/env python3
"""
Script para simular RAT.exe se conectando ao painel
"""

import requests
import json
import time
import sys

CENTRAL_SERVER = 'http://localhost:5000'

def test_register():
    """Simula registro de um PC"""
    print("\n[SIM] Registrando PC: TEST-PC-001")
    
    response = requests.post(
        f"{CENTRAL_SERVER}/api/register",
        json={
            "pc_name": "TEST-PC-001",
            "system_info": {
                "hostname": "TEST-PC-001",
                "os": "Windows",
                "os_version": "10.0",
                "machine": "x86_64",
                "processor": "Intel Core i7"
            }
        },
        timeout=5
    )
    
    if response.status_code in [200, 201]:
        print(f"[OK] PC registrado: {response.json()}")
        return True
    else:
        print(f"[ERRO] Falha ao registrar: {response.status_code}")
        return False

def test_heartbeat():
    """Simula heartbeat do PC"""
    print("\n[SIM] Enviando heartbeat...")
    
    response = requests.post(
        f"{CENTRAL_SERVER}/api/heartbeat",
        json={"pc_name": "TEST-PC-001"},
        timeout=5
    )
    
    if response.status_code == 200:
        print(f"[OK] Heartbeat enviado")
        return True
    else:
        print(f"[ERRO] Heartbeat falhou")
        return False

def test_get_pcs():
    """Testa listagem de PCs"""
    print("\n[SIM] Listando PCs...")
    
    response = requests.get(
        f"{CENTRAL_SERVER}/api/pcs",
        timeout=5
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] {data['count']} PCs conectados:")
        for pc in data.get('pcs', []):
            print(f"     - {pc['name']}: {pc['status']}")
        return True
    else:
        print(f"[ERRO] Falha ao listar: {response.status_code}")
        return False

if __name__ == "__main__":
    print(f"[INFO] Testando conexao com servidor: {CENTRAL_SERVER}")
    
    if test_register():
        for i in range(3):
            time.sleep(1)
            test_heartbeat()
        test_get_pcs()
    else:
        print("\n[ERRO] Servidor nao disponivel")
        sys.exit(1)
