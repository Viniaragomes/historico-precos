"""Mostra as comparações entre mercados publicadas no app (encartes do dia)."""

import json
import urllib.request

with urllib.request.urlopen("https://viniaragomes.github.io/historico-precos/dados/encartes.json", timeout=30) as r:
    d = json.loads(r.read())
c = d.get("comparacoes", [])
print(d["atualizado_em"], len(d["encartes"]), "encartes;", len(c), "produtos em 2+ mercados")
for x in c:
    print(f"\n{x['produto']}  (diferença R$ {x['diferenca']:.2f}, {x['diferenca_pct']}%)")
    for o in x["ofertas"]:
        print(f"   {'R$ %7.2f' % o['p'] if o['p'] is not None else '(sem preço)':>11}  {o['mercado']:<30} lido: {o['t']}")
