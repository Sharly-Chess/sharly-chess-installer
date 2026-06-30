import ctypes
import os
import subprocess
import sys

def _is_windows_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def ensure_admin_privileges():
    if sys.platform == 'win32':
        if not _is_windows_admin():
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit()
    else:
        if os.geteuid() != 0:
            subprocess.run(["sudo", sys.executable] + sys.argv)
            sys.exit()
