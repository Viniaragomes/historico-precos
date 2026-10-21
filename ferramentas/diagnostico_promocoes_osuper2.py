"""Consultas de promoções na API do Fort (osuper, GraphQL) e do Big Box (Instabuy), e o robots.txt dessas APIs."""

import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402


def pegar(url, t=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=t) as r:
        return r.read().decode("utf-8", "replace")


for host in ["https://api.fortatacadista.com.br", "https://api.ibecom.com.br", "https://api-legada.ibecom.com.br"]:
    try:
        print(host, "robots.txt:\n", pegar(host + "/robots.txt", 15)[:400])
    except Exception as e:
        print(host, "robots.txt:", repr(e)[:100])

print("\n===== Fort (osuper)")
html = pegar("https://www.fortatacadista.com.br/promocoes")
js = pegar(re.search(r'<script[^>]+src="([^"]+bundle[^"]+)"', html).group(1), 60)
for m in re.finditer(r"https?://[^\"'`\s]*?(?:api|graphql)[^\"'`\s]*", html + js):
    pass
print("urls com api/graphql:", sorted(set(re.findall(r"https?://[^\"'`\s]*?(?:api|graphql)[^\"'`\s]{0,40}", html + js)))[:15])
print("trechos 'graphql':", [js[max(0, m.start() - 120):m.start() + 60] for m in re.finditer(r"graphql", js)][:5])
ops = sorted(set(re.findall(r'(?:query|mutation)\s+([A-Za-z]+)\s*[({]', js)))
print("operações com promo/oferta/produto:", [o for o in ops if re.search(r"promo|offer|ofert|product|categor|search|highlight|section|showcase", o, re.I)])
for nome in [o for o in ops if re.search(r"promo|offer|ofert", o, re.I)][:4]:
    i = js.find(f"query {nome}")
    print(f"\n--- {nome}:\n", js[i:i + 1500])
estado = re.search(r"window\.INITIAL_STATE\s*=\s*(\{.*?\})\s*;?\s*</script>", html, re.S)
if estado:
    t = estado.group(1)
    print("\nINITIAL_STATE: tamanho", len(t), "| chaves de 1º nível:", re.findall(r'^\{"(\w+)"|,"(\w+)":\{', t[:3000])[:20])
    for chave in ["storeId", "store_id", "apiUrl", "graphqlUrl", "apiEndpoint", "tenant", "\"id\""]:
        k = t.find(chave)
        if k >= 0:
            print("  ", chave, "->", t[k:k + 160])

print("\n===== Big Box (Instabuy)")
html = pegar("https://bigboxdelivery.com.br/promocoes")
srcs = re.findall(r'<script[^>]+src="([^"]+)"', html)
achados = set()
for s in srcs:
    try:
        js = pegar(urljoin("https://bigboxdelivery.com.br/", s), 30)
    except Exception:
        continue
    for m in re.finditer(r"(api(?:-legada)?\.ibecom\.com\.br[^\"'`\s]{0,80}|/apiv\d[^\"'`\s]{0,80}|promo[a-z_]*\b[^\"'`]{0,40})", js):
        achados.add(m.group(1)[:120])
print(sorted(achados)[:60])
k = html.find("storeData")
print("storeData:", html[k:k + 600].replace("\\", ""))
