"""Confere os encartes publicados no app: quantos, de quais mercados e exemplos de preços lidos."""

import json
import urllib.request

BASE = "https://viniaragomes.github.io/historico-precos/"
with urllib.request.urlopen(BASE + "dados/encartes.json", timeout=30) as r:
    d = json.loads(r.read())
print(d["atualizado_em"], len(d["encartes"]), "encartes,", sum(len(e["trechos"]) for e in d["encartes"]), "preços lidos")
for e in d["encartes"]:
    print(f"\n{len(e['trechos']):>4}  {e['mercado']} | até {e['validade_fim']} | pdf: {bool(e.get('pdf'))} | {e['post']}")
    for t in e["trechos"][:6]:
        print(f"        R$ {t['p']:>7.2f}  {t['t']}")
with urllib.request.urlopen(BASE + "sw.js", timeout=30) as r:
    print("\n", r.read().decode()[:120])
