"""Testa resolução e modo do Tesseract no PDF do Dona e numa imagem do Tatico: quantos preços com nome saem."""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos import encartes_ocr  # noqa: E402
from historico_precos.fontes import folhetos_df  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador()
(e,) = folhetos_df.dona(nav)[:1]
dados = nav.get_bytes(e.pdf)
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    arq = tmp / "d.pdf"
    arq.write_bytes(dados)
    for dpi in (150, 200, 300):
        subprocess.run(["pdftoppm", "-r", str(dpi), "-l", "1", "-png", str(arq), str(tmp / f"r{dpi}")], check=True)
        png = next(tmp.glob(f"r{dpi}-*.png"))
        for psm in ("11", "12", "3"):
            tsv = subprocess.run(["tesseract", str(png), "stdout", "-l", "por", "--psm", psm, "tsv"], capture_output=True, text=True).stdout
            tr = encartes_ocr.trechos_das_linhas(encartes_ocr.linhas_do_tsv(tsv))
            print(f"dpi {dpi} psm {psm}: {len(tr)} trechos", [(t.texto[:40], t.preco) for t in tr[:12]])
