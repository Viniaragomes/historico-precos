"""Lista de supermercados do DF a partir de fontes públicas: encartesdf (último ano), Kimbino e Portafolhetos (Brasília)."""

import json
import re
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.fontes.encartesdf import API, separar_titulo, _limpar  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador()
desde = (date.today() - timedelta(days=365)).isoformat()
cont, ultimo, exemplos = Counter(), {}, {}
for pagina in range(1, 60):
    posts = nav.get_json(f"{API}?per_page=100&page={pagina}&after={desde}T00:00:00&_fields=date,link,title")
    if not isinstance(posts, list) or not posts:
        break
    for p in posts:
        mercado, _ = separar_titulo(_limpar((p.get("title") or {}).get("rendered", "")))
        cont[mercado] += 1
        ultimo[mercado] = max(ultimo.get(mercado, ""), p.get("date", "")[:10])
        exemplos.setdefault(mercado, p.get("link"))
    if len(posts) < 100:
        break
print(f"===== encartesdf.com.br: {len(cont)} mercados com encarte desde {desde}")
for m, n in sorted(cont.items(), key=lambda x: -x[1]):
    print(f"  {n:>4} encartes | último {ultimo[m]} | {m} | {exemplos[m]}")

for nome, url, padrao in [("Kimbino", "https://www.kimbino.com.br/cidade/brasilia/categoria/supermercados/", r'href="/([a-z0-9-]+)/"'),
                          ("Portafolhetos", "https://www.portafolhetos.com.br/cidade/brasilia/categoria/supermercados/", r'href="/([a-z0-9-]+)/"'),
                          ("Portafolhetos (todas)", "https://www.portafolhetos.com.br/cidade/brasilia/", r'href="/([a-z0-9-]+)/"')]:
    h = nav.get_texto(url) or ""
    redes = sorted(set(re.findall(padrao, h)) - {"cidade", "categoria", "site", "exit", "api", "ajax"})
    print(f"\n===== {nome} ({url}): {len(redes)} slugs")
    print("  " + ", ".join(redes))
    time.sleep(2)
