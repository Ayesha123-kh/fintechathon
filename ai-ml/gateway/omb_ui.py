"""Open the OpenMausBot dashboard from this machine.

OMB only listens on 127.0.0.1 inside its container, so Docker cannot publish it. This forwards
http://127.0.0.1:8799 here to that port (through `docker exec`) while it runs. Requests arrive as loopback, which OMB
trusts as the owner, so no sign-in is needed. Only this machine can reach it.

Usage:  python3 ai-ml/gateway/omb_ui.py [container-name] [local-port]
"""
import socket, subprocess, sys, threading

CONTAINER = sys.argv[1] if len(sys.argv) > 1 else "fintechathon-omb-1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8799
BRIDGE = "const s=require('net').connect(8799,'127.0.0.1');process.stdin.pipe(s);s.pipe(process.stdout);s.on('close',()=>process.exit())"

def handle(conn):
    p = subprocess.Popen(["docker", "exec", "-i", CONTAINER, "node", "-e", BRIDGE],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    def up():
        try:
            while (d := conn.recv(65536)):
                p.stdin.write(d); p.stdin.flush()
        except OSError: pass
        finally:
            try: p.stdin.close()
            except OSError: pass
    threading.Thread(target=up, daemon=True).start()
    try:
        while (d := p.stdout.read1(65536)):
            conn.sendall(d)
    except OSError: pass
    finally:
        conn.close(); p.kill()

srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", PORT)); srv.listen(32)
print(f"OpenMausBot dashboard: http://127.0.0.1:{PORT}  (Ctrl+C to stop)", flush=True)
while True:
    c, _ = srv.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
