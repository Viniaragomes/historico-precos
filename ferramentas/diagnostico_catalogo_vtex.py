"""Por que o catálogo VTEX (Atacadão, Oba) quase não traz produtos? Roda 4 minutos por loja com log detalhado."""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.__main__ import LOJAS_PADRAO, carregar_lojas  # noqa: E402
from historico_precos.fontes import vtex  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
nav = Navegador()
for loja in [l for l in carregar_lojas(str(LOJAS_PADRAO)) if l.get("tipo", "vtex") == "vtex"]:
    print("\n=====", loja["nome"], {k: v for k, v in loja.items() if k != "nome"})
    url = vtex.ARVORE.format(dominio=loja["dominio"])
    print("robots permite a árvore:", nav.permitido(url))
    texto = nav.get_texto(url)
    print("árvore (texto):", (texto or "")[:300])
    import json
    try:
        arvore = json.loads(texto) if texto else None
    except Exception as e:
        arvore = None
        print("não é JSON:", e)
    print("árvore de categorias:", type(arvore).__name__, len(arvore or []))
    folhas = vtex._folhas(arvore or [])
    print("folhas:", len(folhas), folhas[:3])
    fim = time.monotonic() + 240
    n, com_preco, exemplos = 0, 0, []
    for produto, pts in vtex.catalogo(nav, loja, None, ate=lambda: time.monotonic() > fim):
        n += 1
        com_preco += bool(pts)
        if len(exemplos) < 5:
            exemplos.append((produto.ean, produto.nome, [p.preco for p in pts]))
    print(f"{n} produtos em 4 min, {com_preco} com preço; exemplos: {exemplos}")
    print("registro de falhas:", nav.registro[-8:])
