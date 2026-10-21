"""Tamanho do vocabulário de nomes de produtos no banco do ramo 'dados' (filtro dos encartes)."""

import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos import encartes_ocr  # noqa: E402

subprocess.run(["git", "fetch", "-q", "origin", "dados"], check=False)
with open("precos_dados.db", "wb") as f:
    r = subprocess.run(["git", "show", "origin/dados:precos.db"], stdout=f)
print("git show:", r.returncode, Path("precos_dados.db").stat().st_size, "bytes")
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
v = encartes_ocr.vocabulario(con, dic)
print("vocabulário:", len(v), sorted(v)[:30])
for t in ["posta sesaos", "asa alma ad", "Dove origina", "CLUBE NENE es", "Leite Longa Vida Piracanjuba", "TOMATE GRAPE", "BANANA NANICA", "pérola | tao 5kg as", "EXCLUSIVA LTRA as", "a TioJoão Tio",
          "urífica brilho", "sao CEE e porre", "mimo Seeção", "Filé de Tilápia Copacol", "Picanha Bovina Minerva Peça a Vácuo"]:
    print(t, encartes_ocr.conhecido(t, v))
