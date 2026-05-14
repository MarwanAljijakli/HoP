import socket
import threading
import uuid
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
import paramiko


SCRIPT_DIR = Path(__file__).resolve().parent

HOST = "0.0.0.0"
PORT = 2222
LOG_FILE = SCRIPT_DIR / "honeypot_logs.jsonl"
HOST_KEY_FILE = SCRIPT_DIR / "honeypot_host.key"

# Canonical interaction log shared with the cognitive engine.
# Resolved once at startup from the honeypot script's location.
COGNITIVE_LOG = (
    SCRIPT_DIR / ".." / ".." / ".." / ".." / "Ai section" / "Ai section" / "logs" / "honeypot.jsonl"
).resolve()
try:
    COGNITIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


def write_cognitive_log(entry: dict) -> None:
    try:
        with open(COGNITIVE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


AI_BASE_URL = "http://127.0.0.1:5000"
AI_TIMEOUT_SEC = 10

# Load persistent host key (generate once on first run).
if HOST_KEY_FILE.exists():
    HOST_KEY = paramiko.RSAKey(filename=str(HOST_KEY_FILE))
else:
    HOST_KEY = paramiko.RSAKey.generate(2048)
    HOST_KEY.write_private_key_file(str(HOST_KEY_FILE))


def log_event(event: dict) -> None:
    event["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


class FakeSessionState:
    def __init__(self):
        self.current_dir = "/home/admin"
        self.username = "admin"
        self.hostname = "ubuntu-web-01"

    def prompt(self) -> str:
        return f"{self.username}@{self.hostname}:{self.current_dir}$ "


class HoneypotServer(paramiko.ServerInterface):
    def __init__(self, client_ip: str, session_id: str):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.session_id = session_id
        self.username = None

    def check_auth_password(self, username, password):
        self.username = username

        log_event({
            "event_type": "auth_attempt",
            "source_ip": self.client_ip,
            "session_id": self.session_id,
            "username": username,
            "password": password,
            "result": "accepted"
        })

        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True


def fake_command_output(command: str, state: FakeSessionState) -> str:
    cmd = command.strip()

    if not cmd:
        return ""

    if cmd in ("exit", "logout", "quit"):
        return "__EXIT__"

    if cmd == "pwd":
        return state.current_dir

    if cmd in ("whoami", "id -un"):
        return state.username

    if cmd == "hostname":
        return state.hostname

    if cmd.startswith("cd "):
        target = cmd[3:].strip()
        if target == "~" or target == "/home/admin":
            state.current_dir = "/home/admin"
        elif target == "/var/www":
            state.current_dir = "/var/www"
        elif target == "..":
            if state.current_dir != "/":
                parts = state.current_dir.rstrip("/").split("/")
                state.current_dir = "/" if len(parts) <= 2 else "/".join(parts[:-1])
        elif target.startswith("/"):
            state.current_dir = target
        else:
            if state.current_dir.endswith("/"):
                state.current_dir += target
            else:
                state.current_dir += "/" + target
        return ""

    if cmd in ("ls", "ls -la", "ls -l", "dir"):
        if state.current_dir == "/home/admin":
            return (
                "total 28\n"
                "drwxr-xr-x 3 admin admin 4096 Apr  4 12:10 .\n"
                "drwxr-xr-x 3 root  root  4096 Apr  1 09:21 ..\n"
                "-rw------- 1 admin admin  220 Apr  1 09:22 .bash_logout\n"
                "-rw-r--r-- 1 admin admin 3771 Apr  1 09:22 .bashrc\n"
                "-rw-r--r-- 1 admin admin  807 Apr  1 09:22 .profile\n"
                "-rw-r--r-- 1 admin admin   64 Apr  4 11:59 notes.txt\n"
                "drwxr-xr-x 2 admin admin 4096 Apr  4 12:05 .ssh\n"
            )
        if state.current_dir == "/var/www":
            return (
                "total 12\n"
                "drwxr-xr-x 2 www-data www-data 4096 Apr  3 18:12 .\n"
                "drwxr-xr-x 8 root     root     4096 Apr  1 08:00 ..\n"
                "-rw-r--r-- 1 www-data www-data  612 Apr  3 18:12 index.html\n"
            )
        return "total 0"

    if cmd == "cat notes.txt" and state.current_dir == "/home/admin":
        return "backup reminder: rotate nginx logs, check web root, update keys"

    if cmd == "cat /etc/passwd":
        return (
            "root:x:0:0:root:/root:/bin/bash\n"
            "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
            "bin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
            "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
            "admin:x:1000:1000:Admin User:/home/admin:/bin/bash\n"
        )

    if cmd == "uname -a":
        return "Linux ubuntu-web-01 5.15.0-91-generic x86_64 GNU/Linux"

    if cmd == "ps aux":
        return (
            "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
            "root         1  0.0  0.3  22500  3200 ?        Ss   09:00   0:01 /sbin/init\n"
            "root       412  0.0  0.2  18000  2100 ?        Ss   09:01   0:00 nginx: master process\n"
            "www-data   413  0.0  0.2  18400  2300 ?        S    09:01   0:00 nginx: worker process\n"
            "admin      944  0.0  0.1   9800  1400 pts/0    Ss   12:10   0:00 -bash\n"
        )

    if cmd == "netstat -tulnp":
        return (
            "Active Internet connections (only servers)\n"
            "tcp   0   0 0.0.0.0:22     0.0.0.0:*    LISTEN   721/sshd\n"
            "tcp   0   0 0.0.0.0:80     0.0.0.0:*    LISTEN   412/nginx\n"
        )

    if cmd == "help":
        return "Available commands: pwd, whoami, hostname, ls, cd, cat, uname -a, ps aux, netstat -tulnp, exit"

    return f"bash: {cmd}: command not found"


def ai_command_output(session_id: str, src_ip: str, command: str, current_dir: str, username: str):
    """POST attacker command to cognitive /act. Returns (text, fallback_reason).
    Success -> (response_text, None). Any failure -> (None, '<short_reason>')."""
    payload = json.dumps({
        "session_id": session_id,
        "src_ip": src_ip,
        "input": command,
        "history": [],
        "current_dir": current_dir,
        "username": username,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{AI_BASE_URL}/act",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=AI_TIMEOUT_SEC) as resp:
            if resp.status != 200:
                return None, f"http_{resp.status}"
            try:
                data = json.loads(resp.read().decode("utf-8"))
            except json.JSONDecodeError as e:
                return None, f"bad_json_{type(e).__name__}"
        text = (data or {}).get("response")
        if not isinstance(text, str) or text == "":
            return None, "empty_response"
        if text.startswith("Error:"):
            return None, "ai_error"
        return text, None
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", None)
        return None, f"url_error_{type(reason).__name__}" if reason is not None else "url_error"
    except TimeoutError:
        return None, "timeout"
    except Exception as e:
        return None, f"exception_{type(e).__name__}"


def handle_client(client_socket: socket.socket, addr):
    client_ip, client_port = addr
    session_id = str(uuid.uuid4())

    log_event({
        "event_type": "connection_open",
        "source_ip": client_ip,
        "source_port": client_port,
        "session_id": session_id
    })

    transport = None
    chan = None
    peer_ip = client_ip

    try:
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(HOST_KEY)

        server = HoneypotServer(client_ip=client_ip, session_id=session_id)
        transport.start_server(server=server)

        try:
            peer = transport.getpeername()
            if peer:
                peer_ip = peer[0]
        except Exception:
            pass

        chan = transport.accept(20)
        if chan is None:
            log_event({
                "event_type": "channel_failed",
                "source_ip": peer_ip,
                "session_id": session_id
            })
            return

        server.event.wait(10)
        if not server.event.is_set():
            log_event({
                "event_type": "shell_request_timeout",
                "source_ip": peer_ip,
                "session_id": session_id
            })
            return

        state = FakeSessionState()
        if server.username:
            state.username = server.username

        chan.send("\r\n")
        chan.send("Welcome to Ubuntu 22.04 LTS\r\n")
        chan.send("Last login: Tue Apr  4 11:58:12 2026 from 10.0.2.15\r\n")
        chan.send(state.prompt())

        buffer = ""

        while True:
            data = chan.recv(1024)
            if not data:
                break

            text = data.decode("utf-8", errors="ignore")

            for ch in text:
                if ch in ("\r", "\n"):
                    chan.send("\r\n")
                    command = buffer.strip()
                    buffer = ""

                    if command:
                        ai_text, fallback_reason = ai_command_output(
                            session_id, peer_ip, command, state.current_dir, state.username
                        )
                        if ai_text is not None:
                            output = ai_text
                        else:
                            output = fake_command_output(command, state)
                            log_event({
                                "event_type": "fallback",
                                "source_ip": peer_ip,
                                "session_id": session_id,
                                "input_command": command,
                                "fallback_reason": fallback_reason,
                            })
                            cognitive_response = "logout" if output == "__EXIT__" else output
                            write_cognitive_log({
                                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                "session_id": session_id,
                                "src_ip": peer_ip,
                                "input": command,
                                "response": cognitive_response,
                                "model": "fallback-rules",
                                "temperature": "0",
                            })

                        if output == "__EXIT__":
                            chan.send("logout\r\n")
                            return

                        if output:
                            chan.send(output + "\r\n")

                    chan.send(state.prompt())

                elif ch in ("\x08", "\x7f"):
                    if buffer:
                        buffer = buffer[:-1]
                        chan.send("\b \b")

                elif ch.isprintable():
                    buffer += ch
                    chan.send(ch)

    except Exception as e:
        log_event({
            "event_type": "error",
            "source_ip": peer_ip,
            "session_id": session_id,
            "error": str(e)
        })
    finally:
        try:
            if chan:
                chan.close()
        except Exception:
            pass

        try:
            if transport:
                transport.close()
        except Exception:
            pass

        try:
            client_socket.close()
        except Exception:
            pass

        log_event({
            "event_type": "connection_closed",
            "source_ip": peer_ip,
            "session_id": session_id
        })


def start_server():
    if not LOG_FILE.exists():
        open(LOG_FILE, "a", encoding="utf-8").close()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(100)

    print(f"[+] Honeypot listening on {HOST}:{PORT}", flush=True)
    print(f"[+] Logs -> {LOG_FILE}", flush=True)

    while True:
        client, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client, addr), daemon=True)
        thread.start()


if __name__ == "__main__":
    start_server()
