"""Por que o catálogo do Atacadão veio vazio? Árvore de categorias e primeira página de uma categoria."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.fontes import vtex  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=2)
for dominio in ["www.atacadao.com.br", "www.obahortifruti.com.br"]:
    loja = {"nome": dominio, "dominio": dominio, "cep": "70040010"}
    print(f"\n===== {dominio}")
    print("permitido pelo robots:", nav.permitido(vtex.ARVORE.format(dominio=dominio)))
    texto = nav.get_texto(vtex.ARVORE.format(dominio=dominio))
    print("árvore:", "sem resposta" if texto is None else texto[:600])
    print("registro:", nav.registro[-2:])
    arvore = json.loads(texto) if texto and texto.startswith("[") else []
    folhas = vtex._folhas(arvore)
    print("folhas:", len(folhas), folhas[:5])
    extra, cidade = vtex._parametros_regiao(nav, loja)
    print("região:", extra, cidade)
    if folhas:
        url = vtex.POR_CATEGORIA.format(dominio=dominio, caminho=folhas[0][0], de=0, ate=4) + extra
        print("url:", url, "permitido:", nav.permitido(url))
        r = nav.get_texto(url)
        print("resposta:", (r or "None")[:400], nav.registro[-1:])
