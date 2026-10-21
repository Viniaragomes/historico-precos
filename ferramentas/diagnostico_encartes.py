"""Lê os encartes vigentes do DF com Tesseract e mostra o que saiu, para conferir a qualidade da leitura."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from historico_precos import encartes_ocr  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

encartes = encartes_ocr.ler_encartes(Navegador(), dias=4, max_imagens=40)
print(f"{len(encartes)} encarte(s) vigente(s); Tesseract: {encartes_ocr.tesseract_disponivel()}")
for e in encartes:
    print(f"\n== {e.mercado} | até {e.validade_fim} | {len(e.imagens)} imagem(ns) | {e.post}")
    for t in e.trechos[:40]:
        print(f"   R$ {t.preco:>7.2f} | {t.texto}")
