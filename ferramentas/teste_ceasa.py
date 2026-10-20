"""Teste real do coletor da CEASA-DF: boletim do dia + 1 mês de histórico do formulário, em banco temporário."""

import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as d:
    subprocess.run([sys.executable, "-m", "historico_precos", "--banco", f"{d}/c.db", "ceasa-df", "--historico", "1",
                    "--produtos", "TOMATE,CEBOLA", "--exportar", f"{d}/ceasa-df.json"], check=False)
