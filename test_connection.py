#!/usr/bin/env python3
"""
Script de teste para diagnosticar problemas de conexao do RAT
"""

import requests
import json
import platform
import sys

CENTRAL_SERVER_URL = 'http://localhost:5000'
PC_NAME = platform.node()

def test_server_ping():
    """Testa se o servidor esta respondendo"""
    print("[TEST] Testando ping no servidor...")
    try:
        response = requests.get(f"{CENTRAL_SERVER_URL}/api/ping", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Servidor respondeu: {data}")
            return True
        else:
            print(f"[ERRO] Servidor respondeu com status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERRO] Nao conseguiu conectar ao servidor: {e}")
        return False

def test_register():
    """Testa o registro do PC"""
    print(f"\n[TEST] Testando registro do PC '{PC_NAME}'...")
    try:
        response = requests.post(
            f"{CENTRAL_SERVER_URL}/api/register",
            json={
                "pc_name": PC_NAME,
                "system_info": {
                    "hostname": platform.node(),
                    "os": platform.system(),
                    "os_version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                }
            },
            timeout=5
        )
        print(f"[OK] Status: {response.status_code}")
        print(f"[OK] Response: {response.json()}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"[ERRO] Erro ao registrar: {e}")
        return False

def test_heartbeat():
    """Testa heartbeat"""
    print(f"\n[TEST] Testando heartbeat...")
    try:
        response = requests.post(
            f"{CENTRAL_SERVER_URL}/api/heartbeat",
            json={"pc_name": PC_NAME},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Heartbeat recebido: {data}")
            return True
        else:
            print(f"[ERRO] Heartbeat falhou com status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERRO] Erro no heartbeat: {e}")
        return False

def test_get_pcs():
    """Testa listagem de PCs"""
    print(f"\n[TEST] Testando listagem de PCs...")
    try:
        response = requests.get(f"{CENTRAL_SERVER_URL}/api/pcs", timeout=5)
        if response.status_code == 200:
            data = response.json()
            pcs = data.get('pcs', [])
            print(f"[OK] PCs conectados: {len(pcs)}")
            for pc in pcs:
                print(f"  - {pc['name']}: {pc['status']}")
            return True
        else:
            print(f"[ERRO] Falha ao listar PCs: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERRO] Erro ao listar PCs: {e}")
        return False

if __name__ == "__main__":
    print(f"[INFO] Testando conexao com servidor: {CENTRAL_SERVER_URL}")
    print(f"[INFO] PC: {PC_NAME}\n")
    
    results = {
        "Ping": test_server_ping(),
        "Register": test_register(),
        "Heartbeat": test_heartbeat(),
        "List PCs": test_get_pcs()
    }
    
    print("\n" + "="*50)
    print("RESUMO DOS TESTES:")
    print("="*50)
    for test, result in results.items():
        status = "PASSOU" if result else "FALHOU"
        print(f"{test:20} [{status}]")
    
    sys.exit(0 if all(results.values()) else 1)
