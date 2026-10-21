"""Por que o encartesdf.com.br não abre do GitHub? DNS, IPv4/IPv6 e resposta HTTP."""

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import subprocess

for host in ["encartesdf.com.br", "www.encartesdf.com.br"]:
    try:
        ends = sorted({(i[0].name, i[4][0]) for i in socket.getaddrinfo(host, 443)})
        print(host, "->", ends)
    except Exception as e:
        print(host, "DNS falhou:", e)
    for v in ["-4", "-6"]:
        r = subprocess.run(["curl", v, "-sS", "-o", "/dev/null", "-m", "20", "-w", "%{http_code} %{remote_ip}",
                            f"https://{host}/wp-json/wp/v2/posts?per_page=1&_fields=date,title"], capture_output=True, text=True)
        print("  curl", v, r.stdout, r.stderr.strip()[:200])
r = subprocess.run(["curl", "-sS", "-m", "20", "https://dns.google/resolve?name=encartesdf.com.br&type=A"], capture_output=True, text=True)
print("DNS Google:", r.stdout[:400], r.stderr[:200])

# Python: cada endereço separado, com o erro de cada um
import ssl  # noqa: E402
import time  # noqa: E402

for fam, nome in [(socket.AF_INET, "IPv4"), (socket.AF_INET6, "IPv6")]:
    t = time.time()
    try:
        ip = socket.getaddrinfo("encartesdf.com.br", 443, fam)[0][4]
        s = socket.socket(fam)
        s.settimeout(30)
        s.connect(ip)
        tls = ssl.create_default_context().wrap_socket(s, server_hostname="encartesdf.com.br")
        tls.sendall(b"GET /robots.txt HTTP/1.1\r\nHost: encartesdf.com.br\r\nConnection: close\r\n\r\n")
        print("Python", nome, "ok:", tls.recv(200)[:80], f"{time.time() - t:.1f}s")
    except Exception as e:
        print("Python", nome, "falhou:", repr(e), f"{time.time() - t:.1f}s")

from historico_precos.rede import Navegador  # noqa: E402
import sys  # noqa: E402,F401
nav = Navegador()
print("Navegador robots:", (nav.get_texto("https://encartesdf.com.br/robots.txt") or "")[:120])
