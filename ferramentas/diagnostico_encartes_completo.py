"""Roda a leitura de encartes exatamente como a coleta (banco + dicionário como vocabulário) e resume o resultado."""

import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.ramo_dados import recuperar  # noqa: E402

recuperar("precos.db")
subprocess.run(["git", "show", "origin/dados:dicionario.db.gz"], stdout=open("dicionario.db.gz", "wb"))
t = time.time()
subprocess.run([sys.executable, "-m", "historico_precos", "encartes-dia", "--exportar", "encartes_teste.json"], check=False)
print(f"\ntempo: {time.time() - t:.0f}s")
d = json.loads(Path("encartes_teste.json").read_text(encoding="utf-8"))
por = Counter()
for e in d["encartes"]:
    por[e["mercado"]] += len(e["trechos"])
print("preços lidos:", sum(por.values()), dict(por.most_common()))
print("comparações:", len(d["comparacoes"]), "| com preço em 2+ mercados:",
      sum(1 for c in d["comparacoes"] if sum(o["p"] is not None for o in c["ofertas"]) >= 2))
for c in d["comparacoes"][:15]:
    print(" ", c["produto"], "|", " · ".join(f"{o['mercado']} {o['p'] if o['p'] is not None else '-'}" for o in c["ofertas"]))
print("\namostra de preços lidos por mercado:")
for e in d["encartes"]:
    if e["trechos"]:
        print(" ", e["mercado"], [(t["t"][:45], t["p"]) for t in e["trechos"][:8]])
