"""Teste para rodar no SEU computador: o Tiendeo aceita um robô identificado, que respeita o robots.txt?

Uso (na pasta do projeto):  python ferramentas/teste_tiendeo.py

O que ele faz, e só isso:
  1. se apresenta como robô (não finge ser navegador);
  2. lê o robots.txt do Tiendeo; se o site recusar ou o robots.txt não permitir, PARA;
  3. se permitir, abre UMA página (encartes do Comper em Brasília) e diz o que dá para ler nela.
Não guarda nada e não insiste: um 403 é a resposta do site, e fica respeitada.
"""

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402

BASE = "https://www.tiendeo.com.br"
PAGINA = BASE + "/brasilia/comper"


def abrir(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


print("Robô identificado como:", USER_AGENT)
try:
    status, robots = abrir(BASE + "/robots.txt")
except urllib.error.HTTPError as e:
    print(f"\nO Tiendeo recusou até o robots.txt (HTTP {e.code}). Resposta do site: não aceita robôs. Paramos aqui.")
    sys.exit(0)
except Exception as e:
    print(f"\nNão deu para conectar: {e!r}")
    sys.exit(0)

rp = RobotFileParser()
rp.parse(robots.splitlines())
print("robots.txt lido. Trecho:\n" + "\n".join(robots.splitlines()[:25]))
if not rp.can_fetch(USER_AGENT, PAGINA):
    print(f"\nO robots.txt NÃO permite {PAGINA}. Paramos aqui.")
    sys.exit(0)
print(f"\nO robots.txt permite {PAGINA}. Abrindo uma única vez...")
try:
    status, html = abrir(PAGINA)
except urllib.error.HTTPError as e:
    print(f"O site recusou a página (HTTP {e.code}). Paramos aqui.")
    sys.exit(0)

texto = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)).split())
print(f"HTTP {status}, {len(html)} bytes")
print("Tem __NEXT_DATA__ (dados estruturados):", "__NEXT_DATA__" in html)
print("Blocos ld+json:", html.count("application/ld+json"))
print("Preços no texto:", re.findall(r"R\$\s*\d{1,4},\d{2}", texto)[:10])
print("Datas de validade no texto:", re.findall(r"\d{2}/\d{2}(?:/\d{2,4})?", texto)[:10])
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
if m:
    d = json.loads(m.group(1))
    print("Chaves da página:", list(d.get("props", {}).get("pageProps", {}).keys())[:20])
print("\nCopie tudo o que apareceu aqui e mande para o Claude.")
