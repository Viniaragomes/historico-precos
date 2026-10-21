"""Teste real do vínculo por nome (Big Box e Fort), usando o banco da coleta (ramo 'dados') como referência."""

import shutil
import sqlite3
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as d:
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from historico_precos.ramo_dados import recuperar

    recuperar(f"{d}/c.db")
    subprocess.run([sys.executable, "-m", "historico_precos", "--banco", f"{d}/c.db", "referencia-off"], check=False)
    subprocess.run([sys.executable, "-m", "historico_precos", "--banco", f"{d}/c.db", "catalogo-nome", "--minutos", "8", "--limite", "150"], check=False)
    con = sqlite3.connect(f"{d}/c.db")
    print("\nexemplos vinculados:")
    for linha in con.execute("SELECT loja, nome, preco, ean, semelhanca, nome_catalogo FROM produtos_loja WHERE ean IS NOT NULL LIMIT 15"):
        print("  ", linha)
    print("\nexemplos lidos sem vínculo:")
    for linha in con.execute("SELECT loja, nome, marca, preco FROM produtos_loja WHERE lido_em IS NOT NULL AND ean IS NULL LIMIT 10"):
        print("  ", linha)
