"""Procura um código de barras em todas as fontes que o robô usa, para saber onde ele existe."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.fontes import openfoodfacts, vtex  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

EAN = os.environ.get("EAN", "7898955519028")
nav = Navegador(intervalo=3)
print("Open Food Facts:", openfoodfacts.identificar(nav, EAN))
lojas = [l for l in json.loads(Path("lojas.json").read_text(encoding="utf-8"))["lojas"] if l.get("tipo") == "vtex" and l.get("ativa", True)]
for loja in lojas:
    pontos, links = vtex.buscar_por_ean(nav, loja, EAN)
    print(f"{loja['nome']}: {[(p.preco, p.descricao) for p in pontos]} {links} {nav.registro[-1:] if not links else ''}")
try:
    from historico_precos.mapa_df import qlik
    motor = qlik.Motor()
    doc = motor.abrir_app()
    linhas = qlik.precos_por_gtin(motor, doc, [EAN])
    motor.fechar()
    print("Mapa de Preços do DF (NF-e):", len(linhas), "dia(s)", [(l["data"], l["mediana"], l["descricao"]) for l in linhas[-5:]])
except Exception as e:
    print("Mapa de Preços do DF: erro", e)
