import os, sys, marshal, types, base64

# XOR key
K = bytearray([0x53, 0xA1, 0x9F, 0x3C, 0x77, 0xE2, 0x45, 0x1B])

def Xor(data):
    return bytearray([data[i] ^ K[i % len(K)] for i in range(len(data))])

# Read and encrypt
src = r'C:\Users\Pichau\Desktop\checkers2\esquizorat_panel\Program.pyc'
with open(src, 'rb') as f:
    encrypted = Xor(f.read())

# Save as base64 in loader
enc_b64 = base64.b64encode(bytes(encrypted)).decode()

# Create loader
loader = f'''# -*- coding: utf-8 -*-
import base64, marshal, types, sys
K=bytearray([0x53,0xA1,0x9F,0x3C,0x77,0xE2,0x45,0x1B])
E="{enc_b64}"
D=base64.b64decode(E)
C=bytes(D[i]^K[i%8] for i in range(len(D)))
exec(marshal.loads(C[16:]))
'''

out = r'C:\Users\Pichau\Desktop\checkers2\esquizorat_panel\loader.py'
with open(out, 'w', encoding='utf-8') as f:
    f.write(loader)

print(f"Loader criado: {out}")
print(f"Tamanho: {len(loader)} bytes")
print(f"Modo de usar: python loader.py")
