"""Por que o encartesdf.com.br não abre do GitHub? DNS, IPv4/IPv6 e resposta HTTP."""

import socket
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
