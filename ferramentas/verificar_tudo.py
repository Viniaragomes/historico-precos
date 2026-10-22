"""Verificação geral do app publicado: produtos, preços, encartes, dicionário, atacado e versão."""

import json
import re
import urllib.request

BASE = "https://viniaragomes.github.io/historico-precos/"


def pegar(c, j=True):
    try:
        with urllib.request.urlopen(BASE + c, timeout=30) as r:
            t = r.read()
        return json.loads(t) if j else t.decode()
    except Exception as e:
        return f"ERRO {e}"


ind = pegar("dados/indice.json")
if isinstance(ind, dict):
    ps = ind["produtos"]
    com = [p for p in ps if p.get("menor_preco")]
    print("produtos no índice:", len(ps), "| com preço:", len(com))
    from collections import Counter
    print("lojas do menor preço:", Counter(p.get("loja") or p.get("menor_loja") for p in com).most_common(8))
else:
    print("índice:", ind)
enc = pegar("dados/encartes.json")
print("encartes:", enc if isinstance(enc, str) else (enc["atualizado_em"], len(enc["encartes"]), "encartes",
      sum(len(e["trechos"]) for e in enc["encartes"]), "preços", len(enc.get("comparacoes", [])), "comparações"))
print("dicionário:", pegar("dados/codigos/_sobre.json"))
for f in ["ceasa-df.json", "conab.json"]:
    d = pegar("dados/" + f)
    print(f, d if isinstance(d, str) else (d.get("atualizado_em"), len(d.get("series", [])), "séries"))
sw = pegar("sw.js", False)
print("versão publicada:", re.search(r'"v\d+"', sw).group(0) if isinstance(sw, str) and "ERRO" not in sw else sw)
cfg = pegar("config.json")
print("Supabase ligado:", bool(isinstance(cfg, dict) and cfg.get("comunidade", {}).get("url")))
