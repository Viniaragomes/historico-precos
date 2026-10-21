"""Teste real: catálogo do Atacadão pela API pública, 20 páginas (até 1.000 produtos), em banco temporário."""

import subprocess
import sys
import tempfile
import time

with tempfile.TemporaryDirectory() as d:
    inicio = time.monotonic()
    subprocess.run([sys.executable, "-m", "historico_precos", "--banco", f"{d}/c.db", "catalogo-vtex", "--max-paginas", "20"], check=False)
    print(f"tempo: {time.monotonic() - inicio:.0f} s")
    import sqlite3
    con = sqlite3.connect(f"{d}/c.db")
    print("produtos:", con.execute("SELECT COUNT(*) FROM produtos").fetchone()[0], "| preços:", con.execute("SELECT COUNT(*) FROM precos").fetchone()[0])
    for linha in con.execute("SELECT p.ean, p.nome, x.preco, x.cidade FROM produtos p JOIN precos x USING (ean) LIMIT 8"):
        print("  ", linha)
