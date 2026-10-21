"""Tamanho do vocabulário de nomes de produtos no banco do ramo 'dados' (filtro dos encartes)."""

import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos import encartes_ocr  # noqa: E402

subprocess.run(["git", "fetch", "-q", "origin", "dados"], check=False)
from historico_precos.ramo_dados import recuperar  # noqa: E402

print("recuperado:", recuperar("precos_dados.db"), Path("precos_dados.db").stat().st_size, "bytes")
con = sqlite3.connect("precos_dados.db")
for t in ["produtos", "precos", "produtos_loja"]:
    try:
        print(t, con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    except Exception as e:
        print(t, e)
print("fontes de produtos:", con.execute("SELECT fonte, COUNT(*) FROM produtos GROUP BY fonte").fetchall())
with open("dicionario.db.gz", "wb") as f:
    subprocess.run(["git", "show", "origin/dados:dicionario.db.gz"], stdout=f)
dic = encartes_ocr.abrir_dicionario("dicionario.db.gz")
for minimo in (5, 20, 50, 100):
  v = encartes_ocr.vocabulario(con, dic, minimo=minimo)
  print("\nmínimo", minimo, "vocabulário:", len(v))
  for t in ["posta sesaos", "asa alma ad", "Dove origina", "CLUBE NENE es", "Leite Longa Vida Piracanjuba", "TOMATE GRAPE", "BANANA NANICA", "pérola | tao 5kg as", "EXCLUSIVA LTRA as", "a TioJoão Tio",
          "urífica brilho", "sao CEE e porre", "mimo Seeção", "Filé de Tilápia Copacol", "Picanha Bovina Minerva Peça a Vácuo"]:
    print("  ", t, encartes_ocr.conhecido(t, v))
