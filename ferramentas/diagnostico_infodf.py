"""InfoDF (IPE-DF): lista completa de indicadores e painéis, com categoria, periodicidade e última atualização."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=3)
for caminho in ["/api/v1/indicador/", "/api/v1/painel/"]:
    j = json.loads(nav.get_texto("https://infodf.ipe.df.gov.br" + caminho) or "[]")
    def achatar(no):  # junta todos os objetos com "nome", em qualquer nível
        if isinstance(no, dict):
            if "nome" in no and "id" in no:
                yield no
            for v in no.values():
                yield from achatar(v)
        elif isinstance(no, list):
            for v in no:
                yield from achatar(v)

    print("formato:", type(j).__name__, list(j)[:10] if isinstance(j, dict) else len(j))
    itens = list(achatar(j))
    vistos = {}
    for x in itens:
        vistos[x.get("id")] = x
    print(f"\n== {caminho}: {len(vistos)} itens")
    for x in sorted(vistos.values(), key=lambda x: (str(x.get("categoria")), x.get("nome") or "")):
        cat = x.get("categoria", {})
        cat = cat.get("nome") if isinstance(cat, dict) else cat
        print(f"  [{x.get('id')}] {cat} | {x.get('nome')} | period. {x.get('periodicidade', '')} | atualizado {str(x.get('ultima_atualizacao'))[:10]}")
