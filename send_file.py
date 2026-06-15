"""
Discord File Sender - Envia arquivo em qualquer canal
Uso: python send_file.py arquivo.py
"""
import sys, os
import discord
from discord.ext import commands

TOKEN = os.environ.get('DISCORD_TOKEN', '')

if len(sys.argv) < 2:
    print("Uso: python send_file.py arquivo.py [#canal]")
    print("Ex: python send_file.py Program.py")
    print("Ex: python send_file.py builder2.py geral")
    sys.exit(1)

file_path = sys.argv[1]
channel_name = sys.argv[2] if len(sys.argv) > 2 else None

if not os.path.exists(file_path):
    print(f"Erro: {file_path} nao encontrado")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    
    # Find channel
    target = None
    for guild in bot.guilds:
        for ch in guild.text_channels:
            if channel_name:
                if channel_name.lower() in ch.name.lower():
                    target = ch
                    break
            else:
                # Use first available channel
                if ch.permissions_for(guild.me).send_messages:
                    target = ch
                    break
        if target: break
    
    if not target:
        print("Nenhum canal encontrado!")
        await bot.close()
        return
    
    # Send file
    print(f"Enviando {file_path} para #{target.name} em {target.guild.name}...")
    await target.send(file=discord.File(file_path))
    print("Arquivo enviado com sucesso!")
    await bot.close()

bot.run(TOKEN)
