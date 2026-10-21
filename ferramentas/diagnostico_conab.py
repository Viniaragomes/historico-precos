"""Planilhas de dados do Boletim Hortigranjeiro da Conab (gov.br): abas, cabeçalhos e onde aparece a CEASA/DF."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos import xlsx  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=3)
PASTA = "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/hortigranjeiros-prohort/boletim-hortigranjeiro/2026"
texto = nav.get_texto(PASTA) or ""
planilhas = sorted(set(re.findall(r'href="([^"]+\.xlsx)"', texto)))
print("planilhas:", planilhas)
url = next((u for u in planilhas if "setembro" in u), planilhas[-1] if planilhas else None)
dados = nav.get_bytes(url) if url else None
print(url, len(dados or b""), "bytes")
if dados:
    abas = xlsx.ler(dados)
    print("abas:", list(abas))
    for nome, linhas in list(abas.items())[:40]:
        print(f"\n--- {nome}: {len(linhas)} linhas")
        for l in linhas[:6]:
            print("   ", [x for x in l][:16])
        df = [l for l in linhas if any(isinstance(x, str) and ("DF" in x.upper() or "BRAS" in x.upper()) for x in l)]
        for l in df[:3]:
            print("   DF:", l[:16])
