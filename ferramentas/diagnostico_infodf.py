"""InfoDF (IPE-DF): chamadas de API no script e a lista de indicadores (procura preço/inflação)."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=3)
BASE = "https://infodf.ipe.df.gov.br"
inicio = nav.get_texto(BASE + "/") or ""
main = next(iter(re.findall(r'src="(main-[^"]+\.js)"', inicio)), None)
texto = nav.get_texto(f"{BASE}/{main}") or ""
print("trechos com /api/ ou apiUrl:")
for m in re.finditer(r"apiUrl|externalApiUrl|/api/v\d", texto):
    print("  ...", texto[max(0, m.start() - 120):m.start() + 160].replace("\n", " "))
candidatos = sorted(set(re.findall(r"[`\"'](/api/v\d/[a-z0-9_/-]*)", texto)) |
                    set(re.findall(r"\}(/api/v\d/[a-z0-9_/-]*)", texto)) | set(re.findall(r"\}/([a-z][a-z0-9_-]{2,40}/?)[`\"']", texto)))
print("\ncandidatos:", candidatos[:80])
for caminho in ["/api/v1/indicador/", "/api/v1/indicadores/", "/api/v1/painel/", "/api/v1/paineis/", "/api/v1/tema/", "/api/v1/temas/"]:
    dado = nav.get_texto(BASE + caminho)
    if dado is None:
        print(caminho, "-> sem resposta", nav.registro[-1:] if nav.registro else "")
        continue
    try:
        j = json.loads(dado)
    except json.JSONDecodeError:
        print(caminho, "-> não é JSON:", dado[:120].replace("\n", " "))
        continue
    itens = j.get("results", j) if isinstance(j, dict) else j
    print(f"\n{caminho} -> JSON, {len(itens) if isinstance(itens, list) else '?'} itens")
    if isinstance(itens, list):
        for it in itens[:200]:
            linha = json.dumps(it, ensure_ascii=False)
            if re.search(r"pre[çc]o|infla|ipca|cesta|custo|consum|abastec|aliment", linha, re.I):
                print("   **", linha[:300])
        print("   exemplo:", json.dumps(itens[:2], ensure_ascii=False)[:800])
    else:
        print("   ", json.dumps(j, ensure_ascii=False)[:800])
