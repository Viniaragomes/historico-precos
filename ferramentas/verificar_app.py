"""Confere o app publicado: arquivos, quantos produtos, quantos com preço e exemplos."""

import json
import urllib.request

BASE = "https://viniaragomes.github.io/historico-precos/"
for caminho in ["", "sw.js", "dados/ceasa-df.json", "dados/conab.json"]:
    try:
        with urllib.request.urlopen(BASE + caminho, timeout=30) as r:
            print(r.status, caminho or "/", len(r.read()), "bytes")
    except Exception as e:
        print("ERRO", caminho, e)
with urllib.request.urlopen(BASE + "dados/indice.json", timeout=30) as r:
    indice = json.loads(r.read())
prods = indice["produtos"]
com_preco = [p for p in prods if p.get("menor_preco")]
print(f"\nindice.json: {len(prods)} produtos, {len(com_preco)} com preço recente, {sum(1 for p in prods if p.get('compra_df'))} com preço de compra no DF")
for p in prods[:80]:
    print(f"  {p['ean']} {str(p.get('nome'))[:45]:<45} {p.get('menor_preco')} {p.get('loja') or ''} lojas={p.get('lojas')}")
