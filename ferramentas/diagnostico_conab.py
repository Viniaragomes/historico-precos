"""Quais Ceasas têm dado na planilha da Conab (setembro/2026), por produto, e as datas das colunas."""

import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos import xlsx  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=3)
url = ("https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/hortigranjeiros-prohort/boletim-hortigranjeiro/2026/"
       "tabelas-de-dados-boletim-hortigranjeiro-setembro-2026.xlsx")
abas = xlsx.ler(nav.get_bytes(url))
for nome in [a for a in abas if a.startswith("Preços-") and a not in ("Preços-Hortaliças", "Preços-Frutas")]:
    linhas = abas[nome]
    cab = next(l for l in linhas if l and len(l) > 3 and all(isinstance(x, float) and x > 40000 for x in l[1:4]))
    datas = [(date(1899, 12, 30) + timedelta(days=int(x))).strftime("%m/%Y") for x in cab[1:] if isinstance(x, float)]
    print(f"\n{nome}: colunas {datas[0]} a {datas[-1]}")
    for l in linhas[linhas.index(cab) + 1:]:
        if l and isinstance(l[0], str) and l[0].strip():
            vals = [x for x in l[1:len(datas) + 1]]
            cheios = sum(1 for x in vals if isinstance(x, float) and x > 0)
            ultimo = next((f"{x:.2f}" for x in reversed(vals) if isinstance(x, float) and x > 0), "-")
            print(f"   {l[0].strip():<40} {cheios:>2}/{len(datas)} meses com preço, último R$ {ultimo}/kg")
