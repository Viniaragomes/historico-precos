"""InfoDF (IPE-DF): endereço da API (assets/env.js) e rotas/temas citados no script principal."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=3)
BASE = "https://infodf.ipe.df.gov.br"
inicio = nav.get_texto(BASE + "/")
print("página inicial:", "sem resposta " + str(nav.registro[-1:]) if inicio is None else f"{len(inicio)} bytes")
if inicio:
    env = nav.get_texto(BASE + "/assets/env.js") or ""
    print("\n== env.js:\n", env[:1500])
    for js in re.findall(r'src="(main-[^"]+\.js)"', inicio) + re.findall(r'href="(chunk-[^"]+\.js)"', inicio):
        texto = nav.get_texto(f"{BASE}/{js}") or ""
        print(f"\n== {js}: {len(texto)} bytes")
        apis = sorted(set(re.findall(r"[\"'`](/?api/[^\"'`\s]{0,120})[\"'`]", texto)))
        print("   endereços de API:", apis[:60])
        rotas = sorted(set(re.findall(r'path:\s*"([^"]+)"', texto)))
        print("   rotas:", rotas[:80])
        temas = sorted({m.lower() for m in re.findall(r"[A-Za-zçãéíóúâêô ]{0,30}(?:pre[çc]o|infla[çc]|IPCA|cesta|custo de vida|consumo)[A-Za-zçãéíóúâêô ]{0,30}", texto, re.I)})
        print("   textos sobre preço/inflação:", temas[:40])
