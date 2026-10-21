"""Teste real do coletor da Conab (planilhas no gov.br), em banco temporário."""

import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as d:
    subprocess.run([sys.executable, "-m", "historico_precos", "--banco", f"{d}/c.db", "conab", "--exportar", f"{d}/conab.json"], check=False)
