import platform
import socket
import subprocess


def check_internet() -> bool:
    score = 0

    for host, port in (("8.8.8.8", 53), ("1.1.1.1", 53)):
        try:
            socket.create_connection((host, port), timeout=5)
            score += 1
        except (OSError, socket.timeout):
            pass

    ping_param = "-n" if platform.system().lower() == "windows" else "-c"
    for host in ("8.8.8.8", "1.1.1.1"):
        try:
            kwargs = {
                "args": ["ping", ping_param, "1", host],
                "timeout": 5,
                "stderr": subprocess.STDOUT,
            }
            if platform.system() == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            subprocess.check_output(**kwargs)
            score += 1
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            pass

    return score >= 2
