"""Confere o app publicado: produtos, dicionário de códigos e alguns códigos testados no celular."""

import json
import urllib.request

BASE = "https://viniaragomes.github.io/historico-precos/"


def pegar(c):
    with urllib.request.urlopen(BASE + c, timeout=30) as r:
        return json.loads(r.read())


ind = pegar("dados/indice.json")
print("produtos com preço:", sum(1 for p in ind["produtos"] if p.get("menor_preco")), "de", len(ind["produtos"]))
print("dicionário:", pegar("dados/codigos/_sobre.json"))
for ean in ["7500435172561", "7896006716112", "7898955519028"]:
    try:
        print(ean, "->", pegar(f"dados/codigos/{ean[:6]}.json").get(ean))
    except Exception as e:
        print(ean, "-> arquivo do prefixo não existe:", e)
