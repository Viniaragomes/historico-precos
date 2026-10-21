"""Por que o PDF do Dona não rende preços? Tamanho, páginas, texto embutido e leitura por imagem."""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos import encartes_ocr  # noqa: E402
from historico_precos.fontes import folhetos_df  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador()
for e in folhetos_df.dona(nav):
    print(e)
    dados = nav.get_bytes(e.pdf)
    print("baixado:", len(dados or b""), "bytes")
    if not dados:
        continue
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / "d.pdf"
        arq.write_bytes(dados)
        print(subprocess.run(["pdfinfo", str(arq)], capture_output=True, text=True).stdout)
        print("texto embutido:", subprocess.run(["pdftotext", str(arq), "-"], capture_output=True, text=True).stdout[:800])
        print("trechos do texto:", encartes_ocr.texto_do_pdf(arq)[:10])
        paginas = encartes_ocr.paginas_do_pdf(arq)
        print("páginas renderizadas:", [(p.name, p.stat().st_size) for p in paginas])
        for p in paginas[:2]:
            tr = encartes_ocr.ocr(encartes_ocr._preparar(p.read_bytes(), Path(tmp), "x-" + p.name))
            print(p.name, len(tr), tr[:10])
            print(subprocess.run(["tesseract", str(p), "stdout", "-l", "por"], capture_output=True, text=True).stdout[:700])
