"""Conab por caminhos legítimos: (1) Boletim Hortigranjeiro no gov.br; (2) dados.gov.br com a chave do usuário.

A chave vem do segredo DADOS_GOV_BR_CHAVE (variável de ambiente) e NUNCA é impressa.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.rede import USER_AGENT, Navegador  # noqa: E402

nav = Navegador(intervalo=3)

print("== 1. Boletim Hortigranjeiro (gov.br)")
for url in ["https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/hortigranjeiros-prohort/boletim-hortigranjeiro",
            "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/hortigranjeiros-prohort/boletim-hortigranjeiro/2026"]:
    texto = nav.get_texto(url)
    print(url, "->", "sem resposta" if texto is None else f"{len(texto)} bytes")
    if texto:
        pdfs = sorted(set(re.findall(r'href="([^"]+\.pdf)"', texto)))
        pastas = sorted(set(re.findall(r'href="(https://www\.gov\.br/conab/[^"]*boletim-hortigranjeiro[^"]*)"', texto)))
        print("  PDFs:", pdfs[:15])
        print("  subpáginas:", pastas[:20])
print("falhas:", nav.registro[-3:])

print("\n== 2. dados.gov.br")
chave = os.environ.get("DADOS_GOV_BR_CHAVE", "").strip()
print("chave configurada no GitHub:", "sim" if chave else "não")
if chave:
    for url in ["https://dados.gov.br/dados/api/publico/conjuntos-dados?isPrivado=false&pagina=1&nomeConjuntoDados=conab",
                "https://dados.gov.br/dados/api/publico/organizacao?pagina=1&nomeOrganizacao=conab"]:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json",
                                                   "chave-api-dados-abertos": chave})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                dado = json.loads(r.read().decode("utf-8", "replace"))
            print(url.split("?")[0], "-> 200")
            itens = dado if isinstance(dado, list) else dado.get("registros") or dado.get("result") or dado
            print(json.dumps(itens, ensure_ascii=False)[:2500])
        except urllib.error.HTTPError as e:
            print(url.split("?")[0], "-> HTTP", e.code, e.read(300).decode("utf-8", "replace"))
        except Exception as e:
            print(url.split("?")[0], "-> erro", str(e)[:200])
